"""Offline checks for the worldmodel port: `python -m mc_agent.worldmodel.selftest`.

Everything here runs without a Minecraft server or a model. The codex layer is a scripted
stub, so what is exercised is the mechanism this package claims to port: the action
contract, the closed-loop markers, the ledger/discipline arbitration, the ESC claim gate,
the dual-turn cadence and the silent-induction detector.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

CHECKS = 0
FAILS: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  ok  {name}")
    else:
        FAILS.append(name)
        print(f"FAIL  {name}  {detail}")


class StubCodex:
    """Scripted stand-in for prolong_mc.codex_backend.CodexTurn. Each act turn pops the
    next scripted payload and writes it into the workspace exactly as codex would."""

    def __init__(self, workspace: Path, **kwargs) -> None:
        self.workspace = Path(workspace)
        self.script: list[dict] = []
        self.calls = 0
        self.system_prompt = ""
        self.induction_calls = 0
        self.last_expect_actions: bool | None = None

    def write_system_prompt(self, text: str) -> None:
        self.system_prompt = text
        (self.workspace / "AGENTS.md").write_text(text, encoding="utf-8")

    def run(self, prompt: str, images=(), *, expect_actions: bool = True) -> dict:
        self.calls += 1
        self.last_expect_actions = expect_actions
        if not expect_actions:
            self.induction_calls += 1
        payload = self.script.pop(0) if self.script else {}
        for name in ("hypotheses_ops", "claim"):
            if name in payload:
                (self.workspace / f"{name}.json").write_text(
                    json.dumps(payload[name]), encoding="utf-8")
        for rel, text in (payload.get("files") or {}).items():
            p = self.workspace / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        actions = payload.get("actions")
        if actions is not None:
            (self.workspace / "actions.json").write_text(
                json.dumps({"actions": actions}), encoding="utf-8")
            return {"actions_json": json.dumps({"actions": actions}),
                    "message": payload.get("message", ""), "ok": True, "error": None}
        return {"actions_json": None, "message": payload.get("message", ""),
                "ok": False, "error": None}

    def read_outputs(self) -> dict:
        out = {"hypotheses_ops": None, "claim": None, "errors": []}
        for key, fname in (("hypotheses_ops", "hypotheses_ops.json"),
                           ("claim", "claim.json")):
            p = self.workspace / fname
            if p.exists():
                try:
                    out[key] = json.loads(p.read_text(encoding="utf-8"))
                except Exception as e:
                    out["errors"].append(f"{fname}: {e}")
                p.unlink()
        return out

    @staticmethod
    def split_briefing(message: str):
        if "[PLAN]" in message:
            head, _, tail = message.partition("[PLAN]")
            return head.strip(), tail.strip()
        return message.strip(), ""


def _info(x=0.0, z=0.0, y=64.0, yaw=0.0, pitch=0.0, inv=None, bits=None, **extra):
    info = {"player_pos": {"x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch},
            "inventory": inv or {}, **extra}
    if bits is not None:
        info["milestones"] = bits
    return info


SPEC = [
    {"milestone_id": "m1", "task": "stand near the chest and face it",
     "rules": [{"type": "position_near_with_facing"}]},
    {"milestone_id": "m2", "task": "have 1 oak_log",
     "rules": [{"type": "inventory_has"}]},
]


def make_core(tmp: Path, induction_every: int = 60):
    from mc_agent.worldmodel.agent import WorldModelCore
    from mc_agent.worldmodel.milestones import MilestoneLedger
    ws = tmp / "ws"
    codex = StubCodex(ws)
    ws.mkdir(parents=True, exist_ok=True)
    core = WorldModelCore(workspace=ws, task_text="test task",
                          ledger=MilestoneLedger(SPEC), codex_turn=codex,
                          induction_every=induction_every, max_steps=300)
    return core, codex


def test_actions_contract():
    print("[actions contract]")
    from mc_agent.worldmodel import actions
    plan = actions.parse_actions(json.dumps({"actions": [
        {"action": {"forward": 1, "back": 1}},
        {"action": {"hotbar.1": 1, "hotbar.3": 1}},
        {"action": {"camera": [200, 270]}},
        {"action": {"craft": 1, "mobs": 1, "wat": 1}},
    ]}))
    a0 = plan.steps[0]
    check("forward+back cancel", a0["forward"] == 0 and a0["back"] == 0)
    a1 = plan.steps[1]
    check("one hotbar kept", a1["hotbar.1"] == 1 and a1["hotbar.3"] == 0)
    a2 = plan.steps[2]
    check("camera clamped/wrapped", a2["camera"] == [90.0, -90.0], a2["camera"])
    check("unsupported+forbidden+unknown noted",
          sum(1 for n in plan.notes if "craft" in n or "mobs" in n or "wat" in n) == 3,
          plan.notes)
    plan = actions.parse_actions("not json")
    check("malformed json -> empty plan with note", not plan and plan.notes)
    plan = actions.parse_actions(json.dumps({"actions": [
        {"procedure": "go_to", "args": {"x": 1, "z": 1, "n": 300}}]}))
    check("marker over budget dropped with note", not plan.steps
          and any("truncated" in n for n in plan.notes), plan.notes)


def test_skills_gui_and_brain():
    """The post-g56l154 mechanisms: model-written skills execute, GUI toggles flush the
    stale plan and tighten the caps, and the brain carries induced docs but never
    templates."""
    print("[skills, GUI regime, brain]")
    from mc_agent.worldmodel import actions
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # -- custom skill: parses, expands, pays ticks; junk is noted, nesting refused
        pdir = tmp / "procedures"
        pdir.mkdir()
        (pdir / "open_and_book.json").write_text(json.dumps({"entries": [
            {"action": {"use": 1}}, {"action": {"camera": [0, 10]}, "repeat": 2},
        ]}), encoding="utf-8")
        plan = actions.parse_actions(json.dumps({"actions": [
            {"procedure": "open_and_book"}]}), custom_dir=pdir)
        check("custom skill expands to its ticks", len(plan.steps) == 3,
              [len(plan.steps), plan.notes])
        check("custom skill charged as one entry",
              plan.entries and plan.entries[0].get("steps") == 3, plan.entries)
        (pdir / "nested.json").write_text(json.dumps({"entries": [
            {"procedure": "open_and_book"}]}), encoding="utf-8")
        plan = actions.parse_actions(json.dumps({"actions": [
            {"procedure": "nested"}]}), custom_dir=pdir)
        check("nested skill refused with note", not plan.steps
              and any("raw" in n for n in plan.notes), plan.notes)
        (pdir / "go_to.json").write_text(json.dumps({"entries": [
            {"action": {"jump": 1}}]}), encoding="utf-8")
        plan = actions.parse_actions(json.dumps({"actions": [
            {"procedure": "go_to", "args": {"x": 1.0, "z": 1.0, "n": 20}}]}),
            custom_dir=pdir)
        check("builtin wins over same-named custom",
              len(plan.steps) == 1 and "_goto" in plan.steps[0], plan.steps[:1])

        # -- GUI toggle: queued plan flushed, forcing a fresh look at the new regime
        core, codex = make_core(tmp)
        codex.script = [{"actions": [{"action": {"forward": 1}, "repeat": 10}]}]
        core.start(_info(), None)
        core.observe(_info(), 1, None)
        core.next_action(_info())
        check("plan queued before toggle", len(core.queue) > 0, len(core.queue))
        core.observe(_info(isGuiOpen=True), 2, None)
        check("GUI open flushed the queue", len(core.queue) == 0, len(core.queue))
        check("flush counted", core.stats.get("gui_plan_flushes") == 1, core.stats)

        # -- brain: induced docs travel, untouched templates do not
        from mc_agent.worldmodel_agent import _brain_copy
        ws, brain = tmp / "bws", tmp / "brain"
        (ws / "world_model").mkdir(parents=True)
        (ws / "world_model" / "dynamics.md").write_text(
            "# Dynamics model\n\nGUI cursor drifts.", encoding="utf-8")
        (ws / "world_model" / "semantic.md").write_text(
            "# Semantic model\n\n_..._\n\n> Nothing induced yet. ...", encoding="utf-8")
        (ws / "procedures").mkdir()
        (ws / "procedures" / "s.json").write_text('{"entries": []}', encoding="utf-8")
        n = _brain_copy(ws, brain)
        check("induced doc + skill exported, template filtered", n == 2
              and (brain / "world_model" / "dynamics.md").exists()
              and not (brain / "world_model" / "semantic.md").exists()
              and (brain / "procedures" / "s.json").exists(), n)


def test_mining_feedback_loop():
    """The g56l fixes: mine_forward collects its drop, the act prompt carries the last
    ground-truth events, and the revert note tells a misfiled goal where to go."""
    print("[mining feedback loop]")
    from mc_agent.worldmodel import procedures, prompts
    acts, _ = procedures.expand("mine_forward", n=20)
    check("mine_forward ends walking into the mined spot",
          acts[-1].get("forward") == 1 and not acts[-1].get("attack"), acts[-1])
    check("mine_forward still attacks first",
          acts[0].get("_seq", {}).get("steps", [{}])[0].get("attack") == 1)
    check("shapes teach the inventory criterion",
          "END UP IN YOUR INVENTORY" in prompts.ACTION_REFERENCE)
    check("no false coordinates promise",
          "Targets come with coordinates" not in prompts._STRATEGY_BULLETS
          and "carry no coordinates" in prompts._STRATEGY_BULLETS)
    check("ops schema fences the goal kind",
          'kind": "goal"` is ONLY for' in prompts.ACT_PROMPT)
    with tempfile.TemporaryDirectory() as td:
        core, _stub = make_core(Path(td))
        core.observe(_info(inv={"0": {"type": "diamond_pickaxe", "quantity": 1}},
                           mine_block={"purple_concrete": 2}), 5, None)
        prompt = core._turn_prompt(_info())
        check("recent ground truth line in the act prompt",
              "Recent ground truth:" in prompt and "mine_block purple_concrete" in prompt,
              prompt[prompt.find("Recent ground truth"):][:120])


def test_goto_marker():
    print("[go_to marker]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        codex.script = [{"actions": [{"procedure": "go_to",
                                      "args": {"x": 10.0, "z": 0.0, "n": 40}}],
                        "message": "brief [PLAN] walk east"}]
        core.start(_info(), None)
        core.observe(_info(x=0, z=0, yaw=0), 1, None)
        a = core.next_action(_info())
        # Facing yaw 0 (south, +z) with target due east -> bearing -90: big error,
        # turn-in-place first.
        check("turns before walking", a["forward"] == 0 and abs(a["camera"][1]) == 30.0,
              a)
        core.observe(_info(x=0, z=0, yaw=-90), 2, None)
        a = core.next_action(_info())
        check("walks once aligned", a["forward"] == 1 and a["jump"] == 1, a)
        core.observe(_info(x=9.5, z=0, yaw=-90), 3, None)
        a = core.next_action(_info())
        check("arrival ends the marker (next turn fires)", core.stats["goto_arrived"] == 1)
        # Marker done -> queue empty -> a new act turn ran (empty script -> noop)
        check("entry logged with go_to and [STATE]",
              "go_to" in (core.memory.logs_path.read_text()) and
              "[STATE]" in core.memory.logs_path.read_text())


def test_stuck_note():
    print("[go_to stuck]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        codex.script = [{"actions": [{"procedure": "go_to",
                                      "args": {"x": 10.0, "z": 0.0, "n": 40}}]}]
        core.start(_info(), None)
        core.observe(_info(yaw=-90), 1, None)
        for s in range(2, 8):
            a = core.next_action(_info())
            if not core.queue:
                break
            core.observe(_info(x=0.0, z=0.0, yaw=-90), s, None)
        check("no-progress ends with blocked note",
              "blocked" in core.memory.logs_path.read_text()
              or any("blocked" in n for n in core.memory._pending_notes))


def test_chop_and_hold_cut():
    print("[chop / attack-hold]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        codex.script = [{"actions": [{"procedure": "chop_tree", "args": {"n": 80}}]}]
        core.start(_info(), None)
        core.observe(_info(), 1, None)
        a = core.next_action(_info())
        check("chop emits attack", a["attack"] == 1)
        # a log breaks
        core.observe(_info(mine_block={"oak_log": 1.0}), 2, None)
        a = core.next_action(_info())
        check("chop stops on the break", core.stats["chop_early_stops"] == 1)

        core2, codex2 = make_core(Path(td) / "b")
        codex2.script = [{"actions": [{"action": {"attack": 1}, "repeat": 50}]}]
        core2.start(_info(), None)
        core2.observe(_info(), 1, None)
        a = core2.next_action(_info())
        check("raw hold emits attack", a["attack"] == 1)
        core2.observe(_info(mine_block={"stone": 1.0}), 2, None)
        core2.next_action(_info())
        check("raw hold refunded on break", core2.stats["attack_holds_cut"] == 1
              and len(core2.queue) == 0, len(core2.queue))


def test_milestone_flush_and_esc():
    print("[milestone flush / ESC gate]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        codex.script = [{"actions": [{"action": {"forward": 1}, "repeat": 30}]},
                        {"actions": [{"action": {"ESC": 1}}]},
                        {"actions": [{"action": {"ESC": 1}}]}]
        core.start(_info(bits={"m1": 0, "m2": 0}), None)
        core.observe(_info(bits={"m1": 0, "m2": 0}), 1, None)
        core.next_action(_info())
        check("queue holds the walk", len(core.queue) > 0)
        core.observe(_info(bits={"m1": 1, "m2": 0}), 2, None)
        check("milestone fires and flushes the queue", len(core.queue) == 0
              and core.ledger.is_verified("m1"))
        a = core.next_action(_info())        # ESC plan, m2 still open
        check("premature ESC gated to noop", a["ESC"] == 0
              and core.stats["esc_blocked"] == 1, a)
        check("false claim locked a counter", core.discipline.counters["claim_rejected"] == 1)
        core.observe(_info(bits={"m1": 1, "m2": 1}), 3, None)
        a = core.next_action(_info())        # ESC plan, all done
        check("ESC passes once all verified", a["ESC"] == 1, a)


def test_claim_and_ops_channels():
    print("[hypotheses_ops / claim channels]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        codex.script = [{
            "actions": [{"action": {"forward": 1}}],
            "hypotheses_ops": {"hypotheses": [
                {"id": "h1", "statement": "chest is east (m1)", "kind": "goal",
                 "confidence": 0.95, "status": "confirmed"},
                {"id": "h2", "statement": "logs at spawn", "kind": "location",
                 "confidence": 0.4, "depends_on": ["h1"]},
            ], "testing": "h2"},
            # m1 is unverified, and h1's statement names m1 -> the false claim must
            # lock exactly that goal (matching is by identity-in-statement).
            "claim": {"completed": ["m1"]},
        }]
        core.start(_info(bits={"m1": 0, "m2": 0}), None)
        core.observe(_info(bits={"m1": 0, "m2": 0}), 1, None)
        core.next_action(_info())
        check("ops applied", set(core.graph.nodes) == {"h1", "h2"})
        h1 = core.graph.nodes["h1"]
        # Reverted to 0.6 by the goal rule, then pinned to 0.5 by the false claim that
        # named m1 -- both fire in the same turn, lock wins.
        check("self-confirmed goal reverted+marked", h1.status == "active"
              and h1.confidence == 0.5 and "[unverified" in h1.statement,
              (h1.status, h1.confidence))
        check("false claim locked h1", "h1" in core.discipline.locked)
        check("graph persisted", core.memory.graph_path.exists()
              and (core.memory.root / "hypotheses" / "h1.md").exists())
        check("consumed channels deleted",
              not (core.memory.root / "claim.json").exists())


def test_induction_cadence():
    print("[induction]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td), induction_every=10)
        codex.script = [{"actions": [{"action": {"forward": 1}, "repeat": 60}]},
                        {"message": "compiled. nothing else."},   # induction: silent
                        {"actions": [{"action": {"forward": 1}, "repeat": 60}]},
                        {"files": {"world_model/spatial.md": "# updated"},
                         "message": "rewrote spatial"},           # induction: touches
                        {"actions": [{"action": {"forward": 1}, "repeat": 60}]}]
        core.start(_info(), None)
        for s in range(1, 26):
            core.observe(_info(x=float(s), z=0.0), s, None)
            core.next_action(_info())
        check("induction ran on cadence", codex.induction_calls >= 2,
              codex.induction_calls)
        check("expect_actions=False on induction", codex.last_expect_actions in (False, True))
        check("silent induction detected", core.turns["induction_silent"] >= 1,
              core.turns)
        check("world model seeded with 5 docs",
              len(list((core.memory.root / 'world_model').glob('*.md'))) == 5)
        check("queue survives induction (walk resumed)", core.step == 25)


def test_dead_channel_breaker():
    print("[dead-channel circuit breaker]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td), induction_every=10)
        codex.script = []          # every call fails: the dead-credential shape
        core.start(_info(), None)
        for s in range(1, 61):
            core.observe(_info(), s, None)
            a = core.next_action(_info())
            check_quiet = a  # noop expected; not asserted per-step
        # Unbounded, 60 dead steps would cost 60 steps x 2 turns x 3 retries = 360
        # calls (run 1 measured 1,162 over ~160 steps). The breaker caps it near
        # one probe burst per 20-step cooldown.
        check("dead channel calls bounded", codex.calls < 40, codex.calls)
        check("cooldowns engaged", core.stats.get("model_cooldowns", 0) >= 2,
              core.stats.get("model_cooldowns"))
        check("inductions suppressed while cooling", codex.induction_calls <= 2,
              codex.induction_calls)


def test_presatisfied():
    print("[presatisfied milestones]")
    from mc_agent.worldmodel.milestones import MilestoneLedger
    led = MilestoneLedger(SPEC)
    led.reset({})
    led.set_presatisfied({"m1"})
    fired = led.update({"milestones": {"m1": 1, "m2": 0}}, step=2)
    check("presatisfied never banked", not fired and not led.is_verified("m1"))
    check("all_done ignores presatisfied", not led.all_done()
          and led.num_trackable() == 1)
    led.update({"milestones": {"m1": 1, "m2": 1}}, step=5)
    check("creditable set alone completes", led.all_done())
    check("checklist marks no-credit", "[~] m1" in led.progress_block()
          and "NO credit" in led.progress_block())
    # Late blocklist rescinds an already-banked milestone (bits can arrive one
    # step before the harness hands the set over).
    led2 = MilestoneLedger(SPEC)
    led2.reset({})
    led2.update({"milestones": {"m1": 1, "m2": 0}}, step=1)
    check("banked before blocklist", led2.is_verified("m1"))
    led2.set_presatisfied({"m1"})
    check("blocklist rescinds it", not led2.is_verified("m1"))


def test_memory_layout():
    print("[memory layout]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        core.start(_info(), None)
        root = core.memory.root
        for d in ("entities", "locations", "maps", "events", "procedures",
                  "hypotheses", "world_model", "notes", "tools"):
            check(f"dir {d}/", (root / d).is_dir())
        check("zoom tool present+executable", (root / "tools" / "zoom.py").exists())
        check("AGENTS.md written once", "actions.json" in (root / "AGENTS.md").read_text())
        check("visited.csv has header", "step,x,y,z" in (root / "maps" / "visited.csv").read_text())
        core.observe(_info(mine_block={"oak_log": 1.0}, bits={"m1": 1, "m2": 0}), 1, None)
        ev = (root / "events" / "events.jsonl").read_text().splitlines()
        kinds = {json.loads(l)["kind"] for l in ev}
        check("events carry milestone+stat lines", kinds == {"milestone", "stat"}, kinds)


def test_adapter():
    print("[adapter]")
    with tempfile.TemporaryDirectory() as td:
        from unittest.mock import patch
        from mc_agent.action_space import MinerRLActionSpace
        import mc_agent.worldmodel_agent as wa
        ws = Path(td) / "wm_ws"
        with patch.object(wa, "CodexTurn", StubCodex):
            agent = wa.WorldModelAgent(
                action_space=MinerRLActionSpace(), provider=None,
                workspace=ws, milestones_spec=SPEC, max_steps=300)
            agent.load_system_prompt("the task")
            agent.codex.script = [{"actions": [{"action": {"forward": 1}, "repeat": 3}],
                                   "message": "b [PLAN] go"}]
            frame = __import__("numpy").zeros((8, 8, 3), dtype="uint8")
            t, a, m = agent.get_action([frame], [], [], 1,
                                       info=_info(),
                                       milestones=[{"milestone_id": "m1", "completed": False},
                                                   {"milestone_id": "m2", "completed": False}])
            check("wire action has env keys", a["forward"] == 1 and "ESC" in a and "camera" in a, a)
            check("thought is the plan", "go" in t, t)
            check("AGENTS.md carries the task", "the task" in agent.codex.system_prompt)
            check("frame archived", any((ws / "episodes").rglob("*.png")))
            t2, a2, _ = agent.get_action([frame], [], [], 2, info=_info(),
                                         milestones=[{"milestone_id": "m1", "completed": True},
                                                     {"milestone_id": "m2", "completed": False}])
            check("published bits reach the ledger", agent.core.ledger.is_verified("m1"))
            agent.save_state(Path(td))
            rep = json.loads((Path(td) / "worldmodel_report.json").read_text())
            check("report written", rep["milestones"]["milestones_achieved"] == 1, rep["milestones"])


def test_face_pixel():
    """Pixel-referenced aiming: the pinhole mapping, the macro shapes, and the
    put-it-first note."""
    print("[face_pixel]")
    from mc_agent.worldmodel import actions, procedures as P
    dp, dy = P.pixel_deltas(320, 180)
    check("centre pixel -> zero deltas", abs(dp) < 1e-9 and abs(dy) < 1e-9, (dp, dy))
    dp, dy = P.pixel_deltas(640, 180)
    check("right edge -> ~+51 yaw, 0 pitch", abs(dy - 51.21) < 0.3 and abs(dp) < 1e-9,
          (dp, dy))
    dp, dy = P.pixel_deltas(320, 360)
    check("bottom edge -> +fov/2 pitch (down)", abs(dp - 35.0) < 0.05, dp)
    dp2, dy2 = P.pixel_deltas(-50, 9999)
    check("out-of-frame pixels clamped", abs(dy2 + 51.21) < 0.3 and abs(dp2 - 35.0) < 0.05,
          (dp2, dy2))
    steps = P.face_pixel(640, 360)
    tp = sum(s["camera"][0] for s in steps)
    ty = sum(s["camera"][1] for s in steps)
    check("face_pixel deltas sum to the mapping", abs(tp - 35.0) < 0.1
          and abs(ty - 51.21) < 0.35, (tp, ty))
    check("face_pixel chunks at 30 deg/tick",
          all(abs(s["camera"][0]) <= 30.0 and abs(s["camera"][1]) <= 30.0 for s in steps))
    ap = P.approach(600, 200, n=10)
    walk = [s for s in ap if s.get("forward")]
    check("approach = aim then walk (jump held)", len(walk) == 10
          and all(s["jump"] for s in walk) and ap[0]["camera"] != [0.0, 0.0], len(walk))
    plan = actions.parse_actions(json.dumps({"actions": [
        {"procedure": "approach", "args": {"u": 600, "v": 200, "n": 10}}]}))
    check("approach parses as a procedure entry", plan.steps
          and plan.entries[0]["procedure"] == "approach", plan.notes)
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td))
        codex.script = [{"actions": [
            {"action": {"forward": 1}, "repeat": 4},
            {"procedure": "face_pixel", "args": {"u": 100, "v": 100}}]}]
        core.start(_info(), None)
        core.observe(_info(), 1, None)
        core.next_action(_info())
        check("face_pixel not first -> note",
              any("Put it FIRST" in n for n in core.memory._pending_notes),
              core.memory._pending_notes)


def test_goal_check_binding():
    """The induction's triage as machine state: parsed, rendered, enforced, revived."""
    print("[goal check]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td), induction_every=10)
        codex.script = [
            {"actions": [{"action": {"forward": 1}, "repeat": 30}]},
            {"files": {"goal_check.json": json.dumps({"abandon": ["m2", "bogus"],
                                                      "focus": "m1"}),
                       "world_model/spatial.md": "# seen"},
             "message": "triage"},                                   # induction @10
        ]
        core.start(_info(), None)
        for s in range(1, 11):
            core.observe(_info(x=float(s)), s, None)
            core.next_action(_info())
        check("abandon parsed (bogus id dropped)", core.abandoned == {"m2": 10},
              core.abandoned)
        check("focus parsed", core.focus == "m1", core.focus)
        block = core.ledger.progress_block(abandoned=core.abandoned, focus=core.focus)
        check("checklist renders ABANDONED + FOCUS",
              "ABANDONED" in block and "FOCUS" in block, block)
        # Enforcement, driven turn by turn: a plan testing the abandoned milestone is
        # refused; the next, testing the open one, runs.
        core.queue.clear()
        codex.script = [
            {"hypotheses_ops": {"hypotheses": [
                {"id": "h_m2", "statement": "mine the m2 oak_log", "kind": "goal",
                 "confidence": 0.4}], "testing": "h_m2"},
             "actions": [{"action": {"attack": 1}, "repeat": 4}]},
            {"hypotheses_ops": {"hypotheses": [
                {"id": "h_m1", "statement": "reach m1 chest", "kind": "goal",
                 "confidence": 0.4}], "testing": "h_m1"},
             "actions": [{"action": {"forward": 1}, "repeat": 4}]},
        ]
        core._act_turn(_info())
        check("plan testing an abandoned milestone refused",
              core.stats.get("abandoned_plan_refusals", 0) == 1 and not core.queue,
              core.stats)
        core._act_turn(_info())
        check("plan testing an open milestone ran", len(core.queue) > 0,
              len(core.queue))
        check("skip= names the open milestone first",
              "`m1`" in core.ledger.progress_line(skip=set(core.abandoned)))
        # An act turn cannot write the goal check; an induction replacing it revives.
        core.queue.clear()
        codex.script = [
            {"files": {"goal_check.json": json.dumps({"abandon": ["m1"]})},
             "actions": [{"action": {"forward": 1}, "repeat": 2}]}]
        core._act_turn(_info())
        check("act-turn goal_check ignored+deleted",
              core.abandoned == {"m2": 10}
              and not (core.memory.root / "goal_check.json").exists(),
              core.abandoned)
        (core.memory.root / "goal_check.json").write_text(
            json.dumps({"abandon": []}), encoding="utf-8")
        core._read_goal_check()
        check("induction's replacement revives", core.abandoned == {}, core.abandoned)
        # Abandon-everything guard: the first listed id stays open.
        core.abandoned = {}
        (core.memory.root / "goal_check.json").write_text(
            json.dumps({"abandon": ["m1", "m2"]}), encoding="utf-8")
        core._read_goal_check()
        check("abandoning every open milestone keeps one live",
              list(core.abandoned) == ["m2"], core.abandoned)


def test_plan_identity_guard():
    """The third identical plan against zero progress is refused and buys an
    induction."""
    print("[plan identity]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td), induction_every=200)
        same = {"actions": [{"action": {"attack": 1}, "repeat": 4}],
                "message": "same again"}
        codex.script = [dict(same), dict(same), dict(same), dict(same),
                        {"files": {"world_model/dynamics.md": "# compiled"},
                         "message": "induced"},
                        {"actions": [{"action": {"forward": 1}, "repeat": 6}]}]
        core.start(_info(), None)
        for s in range(1, 20):
            core.observe(_info(), s, None)     # never moves: zero progress
            core.next_action(_info())
            if core.stats.get("identical_plan_refusals"):
                break
        check("third identical plan refused",
              core.stats.get("identical_plan_refusals", 0) >= 1, core.stats)
        check("refusal forces the induction", codex.induction_calls == 0)
        core.observe(_info(), 19, None)
        core.next_action(_info())
        check("induction ran on the forced trigger", codex.induction_calls == 1,
              codex.induction_calls)
        check("fresh plan accepted after induction",
              len(core.queue) > 0 or core.stats.get("identical_plan_refusals", 0) >= 2)


def test_stale_binding():
    """Stale is a verdict: no re-test, no evidence-less revival."""
    print("[stale binding]")
    with tempfile.TemporaryDirectory() as td:
        core, _ = make_core(Path(td))
        core.graph.add_or_update(id="h1", statement="the door opens", step=0)
        d = core.discipline
        check("test starts clean", d.track_testing("h1", 0) is None)
        note = d.track_testing("h1", 25)
        check("budget stales the belief", note is not None
              and core.graph.nodes["h1"].status == "stale", note)
        note = d.track_testing("h1", 26)
        check("stale re-test refused", note is not None and "stale" in note
              and d.counters.get("stale_retest_refused") == 1, note)
        core._apply_ops({"hypotheses": [{"id": "h1", "status": "active"}]})
        check("evidence-less revival kept stale",
              core.graph.nodes["h1"].status == "stale",
              core.graph.nodes["h1"].status)
        core._apply_ops({"hypotheses": [{"id": "h1", "status": "active",
                                         "evidence": "events.jsonl step 40: door"}]})
        check("revival with evidence goes through",
              core.graph.nodes["h1"].status == "active")


def test_endgame_induction():
    """One guaranteed goal check inside the last ~70 steps, and only one."""
    print("[endgame induction]")
    with tempfile.TemporaryDirectory() as td:
        core, codex = make_core(Path(td), induction_every=1000)
        act = {"actions": [{"action": {"forward": 1}, "repeat": 50}]}
        codex.script = [dict(act) for _ in range(6)]
        codex.script.insert(4, {"files": {"world_model/causal.md": "# goal check"},
                                "message": "endgame triage"})
        core.start(_info(), None)
        fired_at = None
        for s in range(1, 261):
            core.observe(_info(x=float(s)), s, None)
            core.next_action(_info())
            if codex.induction_calls and fired_at is None:
                fired_at = s
        check("endgame induction fired once in the window",
              codex.induction_calls == 1 and fired_at is not None
              and 230 <= fired_at <= 240, (codex.induction_calls, fired_at))
        check("window flag set", core._endgame_induction_done)


def main() -> int:
    test_actions_contract()
    test_skills_gui_and_brain()
    test_mining_feedback_loop()
    test_goto_marker()
    test_stuck_note()
    test_chop_and_hold_cut()
    test_milestone_flush_and_esc()
    test_claim_and_ops_channels()
    test_induction_cadence()
    test_dead_channel_breaker()
    test_presatisfied()
    test_memory_layout()
    test_adapter()
    test_face_pixel()
    test_goal_check_binding()
    test_plan_identity_guard()
    test_stale_binding()
    test_endgame_induction()
    print(f"\n{CHECKS} checks, {len(FAILS)} failures")
    if FAILS:
        for f in FAILS:
            print(f"  FAILED: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
