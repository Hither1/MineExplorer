#!/usr/bin/env python3
"""Parse the strict 4-hop campaign logs into per-step trajectory digests + per-cell metrics.

Evidence tooling behind experiments/BEHAVIOR_helixon_4hop.md. Reads the runner logs
(outputs/log-<prefix>-<arm>-<channel>-<scene>.txt), PRO-LONG's workspace logs.txt and codex
event streams, and the scene metadata; writes, under OUT (default outputs/_traj_analysis):

  traj/<cell>.jsonl      one record per step: pos, yaw, pitch, action, thought, memory, rules
  read/<cell>.md         human-readable digest: header, phase table, one block per step with the
                         distance / facing error to every milestone target
  prolong/<cell>.md      PRO-LONG only: one section per analyzer turn (commands + briefing)
  summary.csv            per-cell metrics (stuck fraction, action mix, ESC, per-milestone near-miss ...)

Usage: python scripts/analyze_4hop_traj.py [OUT]
Cells: {c4h: Qwen3.8-27B, q35: Qwen3.5-27B} x {default-vllm, hypothesis-vllm, prolong-codex} x 7 scenes.
"""
import ast
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'outputs' / '_traj_analysis')
SCENES = ['0182', '0306', '0311', '0482', '0603', '0726', '0763']
PREFIX_MODEL = {'c4h': 'Qwen3.8-27B', 'q35': 'Qwen3.5-27B'}
ARMS = [('default', 'vllm'), ('hypothesis', 'vllm'), ('prolong', 'codex')]

for d in ['traj', 'read', 'prolong']:
    (OUT / d).mkdir(parents=True, exist_ok=True)


def load_scene(scene):
    m = json.load(open(ROOT / f'bench_4hop7/_split/{scene}/{scene}/multi-agent/metadata.json'))
    ms = m['milestones']['milestones'] if isinstance(m['milestones'], dict) else m['milestones']
    return m, ms


def rule_eval(rule, pos, yaw, spawn):
    """Return (satisfied?, dist, facing_diff) for position rules; None otherwise."""
    p = rule['params']
    t = rule['type']
    if t == 'position_near_with_facing':
        tx, ty, tz = p['target']
        tx += spawn[0]; ty += spawn[1]; tz += spawn[2]
        d = math.sqrt((pos[0]-tx)**2 + (pos[1]-ty)**2 + (pos[2]-tz)**2)
        dx, dz = tx-pos[0], tz-pos[2]
        if abs(dx) < 1e-6 and abs(dz) < 1e-6:
            fd = 0.0
        else:
            exp = math.degrees(math.atan2(-dx, dz))
            fd = abs((yaw - exp + 180.0) % 360.0 - 180.0)
        ok = d <= p['max_distance'] and fd <= p['facing_tolerance']/2.0
        return ok, d, fd
    if t == 'position_inside_box':
        mn = [p['min'][i]+spawn[i] for i in range(3)]
        mx = [p['max'][i]+spawn[i] for i in range(3)]
        inside = all(mn[i] <= pos[i] <= mx[i] for i in range(3))
        # horizontal distance to box (0 if inside in xz)
        dx = max(mn[0]-pos[0], 0, pos[0]-mx[0])
        dz = max(mn[2]-pos[2], 0, pos[2]-mx[2])
        return inside, math.hypot(dx, dz), None
    return None


STEP_RE = re.compile(r'--- Step (\d+)/(\d+) ---')
POS_RE = re.compile(r"step=(\d+) player_pos=(\{.*?\}) rules_passed=(\[.*\])$")
RAW_RE = re.compile(r'\[(DefaultAgent|HypothesisAgent)\] Raw LLM response \(attempt (\d+)\):')
MS_RE = re.compile(r"Milestone '(\w+)' completed at step (\d+) \(frame (\d+)\)")
ESC_REJ_RE = re.compile(r"step=(\d+) Agent requested ESC but")
LOGLINE_RE = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ \| ')
PROLONG_Q_RE = re.compile(r'\[prolong\] step (\d+): queued (\d+) entries = (\d+) steps \(turn (\d+)\)')
JSONFAIL_RE = re.compile(r'JSON parsing failed on attempt|Response content that failed to parse|All retries exhausted|Provider call hit its ceiling')


import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('action_space', str(ROOT / 'mc_agent' / 'action_space.py'))
_mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
extract_json_from_response = _mod.extract_json_from_response


def parse_json_block(text):
    """Extract the response dict the harness would have used (repo extractor first)."""
    text = text.strip()
    try:
        d = extract_json_from_response(text)
        if isinstance(d, dict) and 'action' in d:
            return d
    except Exception:
        pass
    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.S)
    cand = m.group(1) if m else None
    if cand is None:
        i = text.find('{'); j = text.rfind('}')
        if i >= 0 and j > i:
            cand = text[i:j+1]
    if cand is None:
        return None
    try:
        return json.loads(cand)
    except Exception:
        try:
            return json.loads(cand, strict=False)
        except Exception:
            return None


def parse_direct_log(path):
    """default / hypothesis logs -> list of step dicts."""
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    steps = {}
    cur_step = None
    raw_buf = None
    raw_attempt = None
    last_resp = {}      # step -> parsed json of the LAST attempt (the one used if it parsed)
    resp_attempts = Counter()
    ms_events = {}
    esc_rej = []
    json_fail_steps = set()
    spawn = None
    for ln in lines:
        m = STEP_RE.search(ln)
        if m and LOGLINE_RE.match(ln):
            # flush
            if raw_buf is not None and cur_step is not None:
                last_resp[cur_step] = parse_json_block('\n'.join(raw_buf))
                raw_buf = None
            cur_step = int(m.group(1))
            continue
        m = RAW_RE.search(ln)
        if m:
            if raw_buf is not None and cur_step is not None:
                last_resp[cur_step] = parse_json_block('\n'.join(raw_buf))
            raw_buf = []
            raw_attempt = int(m.group(2))
            resp_attempts[cur_step] += 1
            continue
        if raw_buf is not None:
            if LOGLINE_RE.match(ln):
                # end of raw block
                if cur_step is not None:
                    parsed = parse_json_block('\n'.join(raw_buf))
                    if parsed is not None or cur_step not in last_resp:
                        last_resp[cur_step] = parsed
                raw_buf = None
            else:
                raw_buf.append(ln)
                continue
        if JSONFAIL_RE.search(ln) and cur_step is not None:
            json_fail_steps.add(cur_step)
        m = POS_RE.search(ln)
        if m:
            s = int(m.group(1))
            pos = ast.literal_eval(m.group(2))
            rules = ast.literal_eval(m.group(3))
            steps[s] = {'step': s, 'x': pos['x'], 'y': pos['y'], 'z': pos['z'],
                        'pitch': pos.get('pitch'), 'yaw': pos.get('yaw'),
                        'rules': {k: (v[0] if v else None) for k, v in rules}}
            continue
        m = MS_RE.search(ln)
        if m:
            ms_events[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        m = ESC_REJ_RE.search(ln)
        if m:
            esc_rej.append(int(m.group(1)))
        if 'MilestoneChecker] Reset. Spawn=' in ln and spawn is None:
            sp = ast.literal_eval(ln.split('Spawn=')[1].split('  Milestones')[0])
            spawn = (sp['x'], sp['y'], sp['z'])
    if raw_buf is not None and cur_step is not None:
        last_resp[cur_step] = parse_json_block('\n'.join(raw_buf))
    out = []
    for s in sorted(steps):
        r = steps[s]
        resp = last_resp.get(s)
        r['thought'] = (resp or {}).get('thought') if isinstance(resp, dict) else None
        r['action'] = (resp or {}).get('action') if isinstance(resp, dict) else None
        r['memory'] = (resp or {}).get('memory_update') if isinstance(resp, dict) else None
        r['hypotheses'] = (resp or {}).get('hypotheses') if isinstance(resp, dict) else None
        r['plan'] = (resp or {}).get('plan') if isinstance(resp, dict) else None
        r['parsed'] = resp is not None
        r['attempts'] = resp_attempts.get(s, 0)
        r['json_fail'] = s in json_fail_steps
        out.append(r)
    return out, ms_events, esc_rej, spawn


def parse_prolong(cell_dir, log_path):
    """prolong: runner log for positions/rules; workspace logs.txt for programs; events for briefings."""
    lines = open(log_path, encoding='utf-8', errors='replace').read().split('\n')
    steps = {}
    ms_events = {}
    esc_rej = []
    spawn = None
    turns = []  # (step, entries, nsteps, turn)
    for ln in lines:
        m = POS_RE.search(ln)
        if m:
            s = int(m.group(1))
            pos = ast.literal_eval(m.group(2))
            rules = ast.literal_eval(m.group(3))
            steps[s] = {'step': s, 'x': pos['x'], 'y': pos['y'], 'z': pos['z'],
                        'pitch': pos.get('pitch'), 'yaw': pos.get('yaw'),
                        'rules': {k: (v[0] if v else None) for k, v in rules}}
            continue
        m = MS_RE.search(ln)
        if m:
            ms_events[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        m = ESC_REJ_RE.search(ln)
        if m:
            esc_rej.append(int(m.group(1)))
        m = PROLONG_Q_RE.search(ln)
        if m:
            turns.append({'step': int(m.group(1)), 'entries': int(m.group(2)),
                          'nsteps': int(m.group(3)), 'turn': int(m.group(4))})
        if 'MilestoneChecker] Reset. Spawn=' in ln and spawn is None:
            sp = ast.literal_eval(ln.split('Spawn=')[1].split('  Milestones')[0])
            spawn = (sp['x'], sp['y'], sp['z'])
    # workspace logs.txt: per action program + [PLAN] text
    ws = cell_dir / 'prolong_workspace' / 'logs.txt'
    plan_by_step = {}
    prog_by_step = {}
    notes_by_step = defaultdict(list)
    if ws.exists():
        txt = ws.read_text(encoding='utf-8', errors='replace')
        sections = re.split(r'\n=+\n', txt)
        for sec in sections:
            mh = re.search(r'Action (\d+) \| Step (\d+)', sec)
            if not mh:
                continue
            step = int(mh.group(2))
            mp = re.search(r'\[PLAN\]\n(.*?)(?:\n\nTool Call:|\n\[NOTE\]|\Z)', sec, re.S)
            if mp:
                plan_by_step[step] = mp.group(1).strip()
            mt = re.search(r'Tool Call: (\{.*?\}) x(\d+) \[tick (\d+)/(\d+)\]', sec)
            if mt:
                try:
                    act = json.loads(mt.group(1))
                except Exception:
                    act = mt.group(1)
                prog_by_step[step] = {'action': act, 'repeat': int(mt.group(2)), 'tick': int(mt.group(3))}
            for mn in re.finditer(r'\[NOTE\] (.*)', sec):
                notes_by_step[step].append(mn.group(1))
    # events: per turn briefing (agent_message) + commands
    turn_msgs = {}
    for ef in sorted((cell_dir / 'codex_turns').glob('turn_*.events.jsonl')):
        tn = int(re.search(r'turn_(\d+)', ef.name).group(1))
        msgs, cmds = [], []
        for line in open(ef, encoding='utf-8', errors='replace'):
            try:
                e = json.loads(line)
            except Exception:
                continue
            it = e.get('item') or {}
            if e.get('type') == 'item.completed' and it.get('type') == 'agent_message':
                msgs.append(it.get('text', ''))
            if e.get('type') == 'item.completed' and it.get('type') == 'command_execution':
                cmds.append(it.get('command', ''))
        turn_msgs[tn] = {'messages': msgs, 'commands': cmds}
    out = []
    for s in sorted(steps):
        r = steps[s]
        pr = prog_by_step.get(s)
        r['action'] = pr['action'] if pr else None
        r['repeat'] = pr['repeat'] if pr else None
        r['tick'] = pr['tick'] if pr else None
        r['plan'] = plan_by_step.get(s)
        r['notes'] = notes_by_step.get(s)
        r['thought'] = plan_by_step.get(s)
        r['parsed'] = pr is not None
        out.append(r)
    return out, ms_events, esc_rej, spawn, turns, turn_msgs, plan_by_step


def action_class(a):
    """Classify a wire/LLM action dict into a coarse category."""
    if not isinstance(a, dict):
        return 'none'
    keys = {k for k, v in a.items() if (v not in (0, None, [0, 0], [0.0, 0.0]) and not (isinstance(v, list) and all(float(x) == 0 for x in v)))}
    cam = a.get('camera')
    has_cam = isinstance(cam, list) and len(cam) == 2 and (abs(float(cam[0])) > 0 or abs(float(cam[1])) > 0)
    mv = bool(keys & {'forward', 'back', 'left', 'right'})
    if a.get('ESC'):
        return 'ESC'
    if a.get('attack'):
        return 'attack+move' if mv else 'attack'
    if a.get('use'):
        return 'use'
    if has_cam and mv:
        return 'turn+move'
    if has_cam:
        return 'turn'
    if mv:
        if a.get('jump'):
            return 'jump+move'
        return 'move'
    if a.get('jump'):
        return 'jump'
    if keys:
        return 'other'
    return 'noop'


def summarize(cell, arm, scene, spawn, steps, ms, esc_rej, meta_ms, extra=None):
    """Compute per-cell metrics."""
    n = len(steps)
    if n == 0:
        return {'cell': cell, 'steps': 0}
    # movement
    moved = []
    for i in range(1, n):
        a, b = steps[i-1], steps[i]
        moved.append(math.hypot(b['x']-a['x'], b['z']-a['z']))
    stuck = sum(1 for d in moved if d < 0.05)
    path_len = sum(moved)
    maxd_spawn = max(math.hypot(s['x']-spawn[0], s['z']-spawn[2]) for s in steps)
    final_spawn = math.hypot(steps[-1]['x']-spawn[0], steps[-1]['z']-spawn[2])
    # yaw coverage: distinct 30-degree sectors visited
    sectors = set()
    for s in steps:
        if s['yaw'] is not None:
            sectors.add(int(((s['yaw'] % 360) // 30)))
    pitch_ext = sum(1 for s in steps if s['pitch'] is not None and abs(s['pitch']) >= 60)
    # per-milestone best approach
    per_ms = {}
    for mobj in meta_ms:
        mid = mobj['milestone_id']
        rules = mobj.get('rules', [])
        if not rules:
            continue
        r = rules[0]
        rec = {'type': r['type'], 'done_frame': ms.get(mid, (None, None))[1]}
        if r['type'] in ('position_near_with_facing', 'position_inside_box'):
            best_d, best_step, best_fd_at_bestd = 1e9, None, None
            n_dist_ok = 0
            n_dist_ok_face_bad = 0
            first_dist_ok = None
            for s in steps:
                ev = rule_eval(r, (s['x'], s['y'], s['z']), s['yaw'] or 0.0, spawn)
                ok, d, fd = ev
                if d < best_d:
                    best_d, best_step, best_fd_at_bestd = d, s['step'], fd
                if r['type'] == 'position_near_with_facing':
                    if d <= r['params']['max_distance']:
                        n_dist_ok += 1
                        if first_dist_ok is None:
                            first_dist_ok = s['step']
                        if fd > r['params']['facing_tolerance']/2.0:
                            n_dist_ok_face_bad += 1
                elif r['type'] == 'position_inside_box':
                    if d == 0:
                        n_dist_ok += 1
                        if first_dist_ok is None:
                            first_dist_ok = s['step']
            rec.update({'min_dist': round(best_d, 2), 'min_dist_step': best_step,
                        'facing_diff_at_min': None if best_fd_at_bestd is None else round(best_fd_at_bestd, 1),
                        'steps_within_dist': n_dist_ok, 'first_within_dist': first_dist_ok,
                        'steps_within_dist_but_facing_bad': n_dist_ok_face_bad,
                        'max_distance': r['params'].get('max_distance'),
                        'facing_tol_half': (r['params'].get('facing_tolerance') or 0)/2.0})
        per_ms[mid] = rec
    # actions
    ac = Counter(action_class(s.get('action')) for s in steps)
    esc_press = sum(1 for s in steps if isinstance(s.get('action'), dict) and s['action'].get('ESC'))
    invalid_sprint = sum(1 for s in steps if isinstance(s.get('action'), dict) and (s['action'].get('sprint') or s['action'].get('sneak')) and not (s['action'].get('forward') or s['action'].get('back') or s['action'].get('left') or s['action'].get('right')))
    sprint = sum(1 for s in steps if isinstance(s.get('action'), dict) and s['action'].get('sprint') and (s['action'].get('forward') or s['action'].get('back') or s['action'].get('left') or s['action'].get('right')))
    jump = sum(1 for s in steps if isinstance(s.get('action'), dict) and s['action'].get('jump'))
    attack = sum(1 for s in steps if isinstance(s.get('action'), dict) and s['action'].get('attack'))
    use = sum(1 for s in steps if isinstance(s.get('action'), dict) and s['action'].get('use'))
    parsed = sum(1 for s in steps if s.get('parsed'))
    # longest attack streak (consecutive attack steps)
    best_streak = cur = 0
    for s in steps:
        if isinstance(s.get('action'), dict) and s['action'].get('attack'):
            cur += 1; best_streak = max(best_streak, cur)
        else:
            cur = 0
    # camera turn magnitude
    yaw_turn_total = 0.0
    for s in steps:
        a = s.get('action')
        if isinstance(a, dict) and isinstance(a.get('camera'), list) and len(a['camera']) == 2:
            yaw_turn_total += abs(float(a['camera'][1]))
    row = {
        'cell': cell, 'arm': arm, 'scene': scene, 'steps': n,
        'milestones': len(ms), 'ms_frames': ','.join(str(ms.get(m['milestone_id'], (None, -1))[1]) for m in meta_ms),
        'stuck_frac': round(stuck/max(1, n-1), 3), 'path_len': round(path_len, 1),
        'max_spawn_dist': round(maxd_spawn, 1), 'final_spawn_dist': round(final_spawn, 1),
        'yaw_sectors_of_12': len(sectors), 'pitch_extreme_steps': pitch_ext,
        'act_move': ac.get('move', 0), 'act_turn': ac.get('turn', 0), 'act_turn_move': ac.get('turn+move', 0),
        'act_jump_move': ac.get('jump+move', 0), 'act_attack': ac.get('attack', 0)+ac.get('attack+move', 0),
        'act_use': ac.get('use', 0), 'act_noop': ac.get('noop', 0), 'act_esc': ac.get('ESC', 0), 'act_other': ac.get('other', 0)+ac.get('jump', 0),
        'sprint_steps': sprint, 'jump_steps': jump, 'attack_steps': attack, 'attack_max_streak': best_streak, 'use_steps': use,
        'esc_presses': esc_press, 'invalid_sprint_noop': invalid_sprint, 'esc_rejected': len(esc_rej), 'first_esc_rej': esc_rej[0] if esc_rej else None,
        'parsed_steps': parsed, 'yaw_turn_total_deg': round(yaw_turn_total),
        'per_ms': json.dumps(per_ms),
    }
    if extra:
        row.update(extra)
    return row


def ny(y):
    return ((float(y or 0.0) + 180.0) % 360.0) - 180.0


def segments(steps):
    """Coarse phase segmentation: consecutive steps with the same action class."""
    segs = []
    cur = None
    for s in steps:
        c = action_class(s.get('action'))
        if cur and cur['cls'] == c:
            cur['end'] = s['step']; cur['n'] += 1
            cur['ex'] = s
        else:
            if cur: segs.append(cur)
            cur = {'cls': c, 'start': s['step'], 'end': s['step'], 'n': 1, 'sx': s, 'ex': s}
    if cur: segs.append(cur)
    # merge tiny segments (<3) into a "mixed" run
    merged = []
    for sg in segs:
        if merged and (sg['n'] < 3 and merged[-1]['n'] < 3 or merged[-1]['cls'] == 'mixed' and sg['n'] < 3):
            m = merged[-1]
            m['cls'] = 'mixed'; m['end'] = sg['end']; m['n'] += sg['n']; m['ex'] = sg['ex']
        else:
            merged.append(dict(sg))
    return merged


def write_read(cell, arm, steps, spawn, meta_ms, ms, esc_rej, task_text=''):
    """Human-readable compact trajectory digest."""
    L = []
    L.append(f'# {cell}  arm={arm}')
    L.append(f'TASK: {task_text}')
    L.append('MILESTONE RULES (spawn-relative coords; x+ = east, z+ = south; Minecraft yaw: 0=south(+z), 90=west(-x), 180/-180=north(-z), -90=east(+x)):')
    for mobj in meta_ms:
        for r in mobj.get('rules', []):
            L.append(f"  - {mobj['milestone_id']}: {r['type']} {json.dumps(r['params'])}")
    L.append(f'spawn_abs={tuple(round(v,1) for v in spawn)}  milestones_done(frame)={ {k:v[1] for k,v in ms.items()} }  esc_rejected_steps(n={len(esc_rej)})={esc_rej[:8]}{"..." if len(esc_rej)>8 else ""}')
    # segments
    L.append('PHASES (action-class runs; pos = spawn-relative x,z at start -> end):')
    for sg in segments(steps):
        a, b = sg['sx'], sg['ex']
        L.append(f"  steps {sg['start']:>3}-{sg['end']:>3} ({sg['n']:>3}) {sg['cls']:<11} ({a['x']-spawn[0]:.1f},{a['z']-spawn[2]:.1f})->({b['x']-spawn[0]:.1f},{b['z']-spawn[2]:.1f}) yaw {ny(a['yaw']):.0f}->{ny(b['yaw']):.0f}")
    L.append('')
    L.append('STEPS: step | rel_pos(x,y,z) yaw pitch | moved | per-milestone d=3D dist to target / f=facing error deg (* = rule satisfied this step; "-" = non-position rule) | action | T: thought (trunc) | M: memory (shown when changed, every ~25 steps) | H: hypothesis ops (new statements / status changes)')
    prev = None
    prev_mem = None
    prev_plan = None
    last_mem_step = -100
    for s in steps:
        rel = (s['x']-spawn[0], s['y']-spawn[1], s['z']-spawn[2])
        mv = 0.0 if prev is None else math.hypot(s['x']-prev['x'], s['z']-prev['z'])
        ds = []
        for mobj in meta_ms:
            r = (mobj.get('rules') or [None])[0]
            if not r:
                continue
            ev = rule_eval(r, (s['x'], s['y'], s['z']), s['yaw'] or 0.0, spawn)
            mid = mobj['milestone_id'][:12]
            if ev is None:
                ds.append(f"{mid}:{'*' if s['rules'].get(mobj['milestone_id']) else '-'}")
            else:
                ok, d, fd = ev
                star = '*' if s['rules'].get(mobj['milestone_id']) else ''
                ds.append(f"{mid}:d{d:.1f}" + (f"/f{fd:.0f}" if fd is not None else '') + star)
        a = s.get('action')
        astr = json.dumps(a, separators=(',', ':')) if isinstance(a, dict) else str(a)
        if arm == 'prolong':
            astr += f" [{s.get('tick')}/{s.get('repeat')}]"
        th = re.sub(r'\s+', ' ', (s.get('thought') or ''))
        line = f"{s['step']:>3} | ({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) yaw={ny(s['yaw']):.0f} p={s['pitch']:.0f} | mv={mv:.2f} | {' '.join(ds)} | {astr}"
        if arm == 'prolong':
            if s.get('plan') and s.get('plan') != prev_plan:
                line += f"\n      PLAN: {th[:700]}"
                prev_plan = s.get('plan')
            if s.get('notes'):
                line += f"\n      NOTE: {' | '.join(s['notes'])[:300]}"
        else:
            line += f"\n      T: {th[:230]}"
            mem = s.get('memory')
            if mem and (mem != prev_mem) and (s['step'] - last_mem_step >= 25 or s['step'] <= 2 or any(v[0] == s['step'] for v in ms.values())):
                memc = re.sub(r'\s+', ' ', mem)[:330]
                line += f"\n      M: {memc}"
                prev_mem = mem; last_mem_step = s['step']
            if s.get('hypotheses'):
                hs = []
                for h in s['hypotheses']:
                    if isinstance(h, dict) and (h.get('statement') or (h.get('status') in ('confirmed', 'refuted', 'stale'))):
                        st = (h.get('statement') or '')[:90]
                        hs.append(f"{h.get('id')}:{(h.get('status') or '')[:4]}:{h.get('confidence')}" + (f' "{st}"' if st else ''))
                if hs:
                    line += f"\n      H: {' ; '.join(hs)[:400]}"
        L.append(line)
        prev = s
    (OUT / 'read' / f'{cell}.md').write_text('\n'.join(L), encoding='utf-8')


def write_prolong_turns(cell, turns, turn_msgs, plan_by_step, steps_by_num, spawn, meta_ms):
    L = [f'# {cell} analyzer turns']
    for t in turns:
        tn = t['turn']
        tm = turn_msgs.get(tn, {})
        msgs = tm.get('messages', [])
        cmds = tm.get('commands', [])
        s = steps_by_num.get(t['step'] - 1) or steps_by_num.get(t['step'])
        posstr = ''
        if s:
            rel = (s['x']-spawn[0], s['y']-spawn[1], s['z']-spawn[2])
            posstr = f"rel_pos=({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) yaw={ny(s['yaw']):.0f} pitch={s['pitch']:.0f}"
        L.append(f"\n## turn {tn} @ step {t['step']}  entries={t['entries']} steps={t['nsteps']}  {posstr}")
        # commands (short)
        cshort = []
        for c in cmds:
            core = c.split('-lc ', 1)[-1].strip("'\"") if '-lc' in c else c
            core = re.sub(r'\s+', ' ', core)
            if 'actions.json' in core:
                cshort.append('WRITE actions.json: ' + core[core.find('{'):][:500])
            else:
                cshort.append(core[:120])
        L.append('cmds: ' + ' || '.join(cshort))
        for m in msgs:
            L.append('MSG: ' + re.sub(r'\n+', ' / ', m.strip())[:1500])
    (OUT / 'prolong' / f'{cell}.md').write_text('\n'.join(L), encoding='utf-8')


rows = []
for prefix, model in PREFIX_MODEL.items():
    for arm, ch in ARMS:
        for scene in SCENES:
            cell = f'{prefix}-{arm}-{ch}-{scene}'
            log = ROOT / 'outputs' / f'log-{cell}.txt'
            cell_dir = ROOT / 'outputs' / cell / model / '4-hop' / scene
            if not log.exists():
                print('missing', log); continue
            meta, meta_ms = load_scene(scene)
            extra = {}
            if arm == 'prolong':
                steps, ms, esc_rej, spawn, turns, turn_msgs, plan_by_step = parse_prolong(cell_dir, log)
                extra = {'turns': len(turns), 'steps_per_turn': round(len(steps)/max(1, len(turns)), 1),
                         'entries_total': sum(t['entries'] for t in turns)}
                # command stats
                allc = [c for t in turn_msgs.values() for c in t['commands']]
                extra['cmd_tail'] = sum(1 for c in allc if 'tail' in c and 'logs.txt' in c)
                extra['cmd_grep'] = sum(1 for c in allc if 'grep' in c)
                extra['cmd_other_read'] = sum(1 for c in allc if ('actions.json' not in c) and not ('tail' in c and 'logs.txt' in c) and 'grep' not in c)
                write_prolong_turns(cell, turns, turn_msgs, plan_by_step, {s['step']: s for s in steps}, spawn, meta_ms)
            else:
                steps, ms, esc_rej, spawn = parse_direct_log(log)
            with open(OUT / 'traj' / f'{cell}.jsonl', 'w') as f:
                for s in steps:
                    f.write(json.dumps(s) + '\n')
            write_read(cell, arm, steps, spawn, meta_ms, ms, esc_rej, task_text=meta.get('task_text',''))
            rows.append(summarize(cell, arm, scene, spawn, steps, ms, esc_rej, meta_ms, extra))
            print(cell, len(steps), 'steps', len(ms), 'ms', 'esc_rej', len(esc_rej), extra)

keys = []
for r in rows:
    for k in r:
        if k not in keys:
            keys.append(k)
with open(OUT / 'summary.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print('wrote', OUT / 'summary.csv')
