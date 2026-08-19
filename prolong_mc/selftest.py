"""Exercise actions.py and log.py against the contracts the prompt promises."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from prolong_mc.actions import parse_actions, describe_entry
from prolong_mc.log import EpisodeLog, state_line, SEPARATOR

fails = []
def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not cond else ""))
    if not cond: fails.append(name)

# --- actions: the happy path the prompt advertises -------------------------
plan = parse_actions(json.dumps({"actions": [
    {"action": {"forward": 1, "sprint": 1}, "repeat": 10},
    {"action": {"camera": [0, 45]}, "repeat": 1},
]}))
check("happy path kept both entries", len(plan.entries) == 2)
check("repeat expanded to env steps", len(plan.steps) == 11, f"got {len(plan.steps)}")
check("wire format has all 24 keys", set(plan.steps[0]) >= {"forward","sprint","camera","hotbar.1","pickItem","swapHands"})
check("sprint survived", plan.steps[0]["sprint"] == 1)
check("camera survived", plan.steps[-1]["camera"] == [0.0, 45.0])

# --- caps -------------------------------------------------------------------
plan = parse_actions(json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 999}]}), repeat_cap=20, step_cap=40)
check("repeat cap applied", len(plan.steps) == 20, f"got {len(plan.steps)}")
plan = parse_actions(json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 20}] * 5}), step_cap=40)
check("step cap applied", len(plan.steps) == 40, f"got {len(plan.steps)}")
plan = parse_actions(json.dumps({"actions": [{"action": {"jump": 1}, "repeat": 1}] * 30}), action_cap=15, step_cap=100)
check("entry cap applied", len(plan.entries) == 15, f"got {len(plan.entries)}")

# --- rejection paths --------------------------------------------------------
check("malformed json -> empty", not parse_actions("not json{"))
check("wrong shape -> empty", not parse_actions(json.dumps({"actions": "forward"})))
check("bare list accepted", len(parse_actions(json.dumps([{"action": {"jump": 1}, "repeat": 2}])).steps) == 2)
# sneak without a movement key is invalid per DefaultActionSpace.validate_action
check("invalid action rejected, not silently no-opped", not parse_actions(json.dumps({"actions": [{"action": {"sneak": 1}, "repeat": 3}]})))
check("mixed valid/invalid keeps the valid one",
      len(parse_actions(json.dumps({"actions": [{"action": {"sneak": 1}}, {"action": {"forward": 1}, "repeat": 2}]})).steps) == 2)
# two hotbars set at once is invalid
check("double hotbar rejected", not parse_actions(json.dumps({"actions": [{"action": {"hotbar.1": 1, "hotbar.2": 1}}]})))
check("hotbar.3 maps to slot 3", parse_actions(json.dumps({"actions": [{"action": {"hotbar.3": 1}}]})).steps[0]["hotbar.3"] == 1)
check("describe_entry drops zeros", describe_entry({"action": {"forward": 1, "back": 0}, "repeat": 4}) == '{"forward":1} x4')

# --- log --------------------------------------------------------------------
ws = pathlib.Path(tempfile.mkdtemp())
log = EpisodeLog(ws)
spawn = {"x": -3009.5, "y": 71.0, "z": -5572.5, "pitch": 0.0, "yaw": 150.0}
log.write_initial("Find the temple.", spawn, log.save_frame(0, b"\x89PNG-fake"))
prev = spawn
for i in range(1, 13):
    pos = dict(spawn, z=spawn["z"] + i * 0.9, yaw=150.0)
    log.set_plan(f"plan at action {i}")
    log.write_action(action_num=i, step=i, entry_desc='{"forward":1} x5',
                     pos=pos, prev_pos=prev, frame_name=log.save_frame(i, b"\x89PNG-fake"))
    prev = pos
text = log.path.read_text()
check("log has one section per action + initial", text.count(SEPARATOR) == 13, f"got {text.count(SEPARATOR)}")
check("moved computed", "moved=0.90" in text)
check("frames written", len(list((ws / 'frames').glob('*.png'))) == 13)
check("plan recorded", "[PLAN]" in text)

# Upstream's hint/plan pair: the briefing is written once, the plan into every section
# it governed, and the header carries the plan step and the verification state.
lg2 = EpisodeLog(pathlib.Path(tempfile.mkdtemp()))
lg2.write_initial("t", {"x": 0.0, "y": 0.0, "z": 0.0}, None)
lg2.set_plan("go north", briefing="I see a path; the tower is probably north.")
for i in range(1, 4):
    lg2.write_action(action_num=i, step=i, entry_desc="fwd", pos={"x": 0.0, "y": 0.0, "z": float(i)},
                     prev_pos={"x": 0.0, "y": 0.0, "z": float(i - 1)}, frame_name=None,
                     plan_step=(i, 3), verified="no")
t2 = lg2.path.read_text()
check("briefing written once", t2.count("the tower is probably north") == 1, t2)
check("plan written into every section it governed", t2.count("[PLAN]\ngo north") == 3, t2)
check("header carries the plan step", "Action 2 | Step 2 | Plan Step 2/3" in t2, t2)
check("header carries the verification state", t2.count("| Verified: no") == 3, t2)
lg2.write_action(action_num=4, step=4, entry_desc="fwd", pos={"x": 0.0, "y": 0.0, "z": 4.0},
                 prev_pos={"x": 0.0, "y": 0.0, "z": 3.0}, frame_name=None, plan_step=None, verified=None)
t2 = lg2.path.read_text()
check("no-hint protocol prints no Verified field", "Action 4 | Step 4\n" in t2, t2[-200:])

full = log.windowed_copy(ws / "full.txt", None)
w3 = log.windowed_copy(ws / "w3.txt", 3)
w0 = log.windowed_copy(ws / "w0.txt", 0)
check("window=None is the whole log", full.read_text() == text)
check("window=3 keeps initial + last 3", w3.read_text().count(SEPARATOR) == 4, f"got {w3.read_text().count(SEPARATOR)}")
check("window=3 keeps the initial state", "INITIAL STATE" in w3.read_text())
check("window=3 keeps the newest action", "Action 12 " in w3.read_text())
check("window=0 keeps initial + latest only", w0.read_text().count(SEPARATOR) == 2, f"got {w0.read_text().count(SEPARATOR)}")

# stateless: plans go elsewhere, objective trace stays
ws2 = pathlib.Path(tempfile.mkdtemp())
sl = EpisodeLog(ws2, stateless=True)
sl.write_initial("t", spawn, None)
sl.set_plan("secret plan")
sl.write_action(action_num=1, step=1, entry_desc="{} x1", pos=spawn, prev_pos=spawn, frame_name=None)
check("stateless keeps plan out of logs.txt", "secret plan" not in sl.path.read_text())
check("stateless still records the plan", "secret plan" in sl.plans_path.read_text())
check("stateless keeps the objective trace", "[STATE]" in sl.path.read_text())

check("state_line handles missing pos", state_line(None, None) == "[STATE] unavailable")


# --- ProlongAgent: the queue/log wiring, with Codex stubbed out ---------------
from mc_agent.action_space import MinerRLActionSpace
from mc_agent.prolong_agent import ProlongAgent
import numpy as np

ws = pathlib.Path(tempfile.mkdtemp())
agent = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                     workspace=ws / "wsp", action_cap=15, repeat_cap=20, step_cap=40)

turns = {"n": 0, "images": []}
def fake_run(prompt, images=()):
    turns["n"] += 1
    turns["images"].append([pathlib.Path(p).name for p in images])
    turns["last_prompt"] = prompt
    if turns["n"] == 1:
        return {"ok": True, "error": None, "message": "briefing\n[PLAN]\nwalk north",
                "actions_json": json.dumps({"actions": [
                    {"action": {"forward": 1, "sprint": 1}, "repeat": 3},
                    {"action": {"camera": [0, 45]}, "repeat": 1}]})}
    return {"ok": True, "error": None, "message": "[PLAN]\ndone",
            "actions_json": json.dumps({"actions": [{"action": {"ESC": 1}, "repeat": 1}]})}
agent.codex.run = fake_run
agent.load_system_prompt("Find the temple.")
check("AGENTS.md written once", (ws / "wsp" / "AGENTS.md").exists())

frame = np.zeros((64, 64, 3), np.uint8)
pos = {"x": 0.0, "y": 71.0, "z": 0.0, "pitch": 0.0, "yaw": 0.0}
acts, thoughts = [], []
for step in range(1, 6):  # plan 1 gives 4 steps, plan 2 gives 1
    p_ = dict(pos, z=float(step))
    think, action, _ = agent.get_action([frame], [], [], step, info={"player_pos": p_})
    acts.append(action); thoughts.append(think)

check("one analyzer turn covered four steps", turns["n"] == 2, f"turns={turns['n']}")
check("queue drained exactly", len(agent.queue) == 0)
# Assert against the consumer's contract -- eval_benchmark feeds this straight into
# checker.augment_action_with_queries() and env.step() -- not against whatever type
# the agent happens to build internally.
check("action is a wire dict", isinstance(acts[0], dict) and "hotbar.1" in acts[0])
check("first action is forward+sprint", acts[0]["forward"] == 1 and acts[0]["sprint"] == 1)
check("fourth action is the camera turn", acts[3]["camera"] == [0.0, 45.0])
check("fifth action comes from the second plan", acts[4]["ESC"] == 1)
check("plan text reaches the thought", "walk north" in (thoughts[0] or ""))
check("default action is a wire dict too", isinstance(agent.get_default_action(False)[1], dict))

text2 = (ws / "wsp" / "logs.txt").read_text()
check("agent log has initial + actions", text2.count(SEPARATOR) >= 5, f"got {text2.count(SEPARATOR)}")
check("agent log records moved", "moved=1.00" in text2)
check("agent log records the plan", "[PLAN]" in text2)
check("drained ticks are numbered, not repeated wholesale",
      "[tick 1/3]" in text2 and "[tick 2/3]" in text2, text2[:400])
check("log header uses the step the action was issued at", "Action 1 | Step 1" in text2, text2[:400])
check("frames saved by the agent", len(list((ws / "wsp" / "frames").glob("*.png"))) >= 5)

check("every analyzer turn gets the current frame attached",
      turns["images"] == [["step_0001.png"], ["step_0005.png"]], f'got {turns["images"]}')
check("the turn prompt says the view is attached",
      "CURRENT first-person view" in turns["last_prompt"])

# R2: a change in the environment's verification state cuts the plan short and
# re-fires the analyzer, as upstream's queue does on a score change.
agent_f = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                       workspace=ws / "wspf", milestone_hint=True)
f_turns = {"n": 0}
def flush_run(prompt, images=()):
    f_turns["n"] += 1
    return {"ok": True, "error": None, "message": "brief\n[PLAN]\nlong walk",
            "actions_json": json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 10}]})}
agent_f.codex.run = flush_run
agent_f.load_system_prompt("Find the temple.")
NOT_YET = "The environment has NOT verified the task as complete yet. Do not end the episode (ESC) until it is."
DONE = "The environment HAS verified the task as complete. You may now end the episode by setting ESC=1."
for step in range(1, 4):
    agent_f.get_action([frame], [], [], step, milestone_hint=NOT_YET,
                       info={"player_pos": dict(pos, z=float(step))})
check("one plan covers the first steps", f_turns["n"] == 1 and len(agent_f.queue) == 7)
agent_f.get_action([frame], [], [], 4, milestone_hint=DONE, info={"player_pos": dict(pos, z=4.0)})
check("verification change flushes the queue and re-plans",
      f_turns["n"] == 2 and agent_f._flushes == 1 and len(agent_f.queue) == 9,
      f"turns={f_turns['n']} flushes={agent_f._flushes} queue={len(agent_f.queue)}")
tf = (ws / "wspf" / "logs.txt").read_text()
check("the header shows the state the tail will see", "| Verified: no" in tf and "| Verified: yes" in tf, tf[-600:])
check("the briefing is in the log", "brief\n" in tf, tf[:600])
check("the plan is in every section", tf.count("[PLAN]\nlong walk") == 3, f"got {tf.count('[PLAN]')}")
check("the system prompt documents the header field",
      "Verified: yes/no" in (ws / "wspf" / "AGENTS.md").read_text())

# R5: the No-Log control -- no logs.txt where the agent works, state in the prompt.
nl_prompts = []
def nolog_run(prompt, images=()):
    nl_prompts.append((prompt, [pathlib.Path(p).name for p in images]))
    return {"ok": True, "error": None, "message": "[PLAN]\nstep",
            "actions_json": json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 2}]})}
agent_n = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                       workspace=ws / "wsn", log_window=-1, milestone_hint=True)
agent_n.codex.run = nolog_run
agent_n.load_system_prompt("Find the temple.")
for step in range(1, 4):
    agent_n.get_action([frame], [], [], step, milestone_hint=NOT_YET,
                       info={"player_pos": dict(pos, z=float(step))})
check("no-log: the agent's directory has no logs.txt", not (ws / "wsn" / "logs.txt").exists())
check("no-log: the record still has the full log",
      (agent_n.record_dir / "logs.txt").read_text().count(SEPARATOR) >= 3)
check("no-log: the prompt carries the current state",
      "[STATE] pos=(0.00, 71.00, 3.00)" in nl_prompts[-1][0] and "Verified: no" in nl_prompts[-1][0],
      nl_prompts[-1][0])
check("no-log: only the current frame is visible",
      sorted(p.name for p in (ws / "wsn" / "frames").glob("*.png")) == ["step_0003.png"],
      sorted(p.name for p in (ws / "wsn" / "frames").glob("*.png")))
check("no-log: the system prompt is the in-prompt variant",
      "injected directly into your prompt" in (ws / "wsn" / "AGENTS.md").read_text())

agent2 = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                      workspace=ws / "wsp2", analyzer_retries=2)
agent2.codex.run = lambda prompt, images=(): {"ok": False, "error": "boom", "message": "",
                                              "actions_json": None, "overflow": False}
agent2.load_system_prompt("t")
_, bad_action, _ = agent2.get_action([frame], [], [], 1, info={"player_pos": pos})
check("analyzer failure returns None, not a no-op", bad_action is None)

# A failed refill must not leave the previous entry pending: the next call would
# re-append its section, and a log full of duplicate `Action N | moved=0.00` reads to
# the analyzer as a player stuck against a wall.
agent3 = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                      workspace=ws / "wsp3", analyzer_retries=1)
one = {"n": 0}
def one_then_fail(prompt, images=()):
    one["n"] += 1
    if one["n"] == 1:
        return {"ok": True, "error": None, "message": "[PLAN]\ngo",
                "actions_json": json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 1}]}),
                "overflow": False}
    return {"ok": False, "error": "boom", "message": "", "actions_json": None, "overflow": False}
agent3.codex.run = one_then_fail
agent3.load_system_prompt("t")
for step in range(1, 5):
    agent3.get_action([frame], [], [], step, info={"player_pos": dict(pos, z=float(step))})
text3 = (ws / "wsp3" / "logs.txt").read_text()
check("a failed refill does not duplicate the last action section",
      text3.count("Action 1 | Step 1") == 1, f'got {text3.count("Action 1 | Step 1")}')

# A crashed scene rerun must not append a second episode to the first one's log.
agent4 = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                      workspace=ws / "wsp3")
check("a stale workspace is moved aside, not appended to",
      (ws / "wsp3" / "logs.txt").read_text() == "" and (ws / "wsp3.crashed" / "logs.txt").exists())


# --- the ablation arms have to bind, not merely be requested ---------------------
# Upstream enforces both in the directory it hands Codex: stateless deletes everything
# but logs.txt + AGENTS.md each turn, and a window means the truncated copy is the only
# log there is (codex_agent.py:417-460). The port used to reword the prompt and leave
# the full log and the agent's notes in place, which would have made arm C a study of
# whether a model obeys an instruction to forget.

def _stub_turn(prompt, images=()):
    _stub_turn.prompts.append(prompt)
    return {"ok": True, "error": None, "message": "[PLAN]\nkeep going", "overflow": False,
            "actions_json": json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 1}]})}
_stub_turn.prompts = []


def _ablation_agent(name, **kw):
    a = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                     workspace=ws / name, **kw)
    a.codex.run = _stub_turn
    a.load_system_prompt("Find the temple.")
    return a


def _visible_text(root: pathlib.Path) -> str:
    return "\n".join(p.read_text(errors="replace")
                     for p in root.rglob("*") if p.is_file() and p.suffix != ".png")


sl_agent = _ablation_agent("wsl", stateless=True)
sl_ws = ws / "wsl"
sl_agent.get_action([frame], [], [], 1, info={"player_pos": dict(pos, z=1.0)})
(sl_ws / "notes.md").write_text("the temple is north; do not re-search the ridge")
sl_agent.get_action([frame], [], [], 2, info={"player_pos": dict(pos, z=2.0)})
check("stateless deletes what the agent wrote, instead of asking it to forget",
      not (sl_ws / "notes.md").exists())
check("stateless keeps the log and the system prompt",
      (sl_ws / "logs.txt").exists() and (sl_ws / "AGENTS.md").exists())
check("the canonical record is not the directory the agent works in",
      sl_agent.record_dir != sl_agent.workspace and (sl_agent.record_dir / "logs.txt").exists())
check("the plan record the ablation withholds is out of the agent's reach",
      not (sl_ws / "plans.txt").exists() and (sl_agent.record_dir / "plans.txt").exists())
check("stateless still hands over the frames the log names",
      len(list((sl_ws / "frames").glob("*.png"))) == 2,
      f'got {len(list((sl_ws / "frames").glob("*.png")))}')
check("the deletions are audited, not silent", sl_agent._files_removed >= 1)

w_agent = _ablation_agent("wsw", log_window=0)
w_ws = ws / "wsw"
for step in range(1, 5):
    w_agent.get_action([frame], [], [], step, info={"player_pos": dict(pos, z=float(step))})
(w_ws / "notes.md").write_text("kept: the window ablation is not the stateless one")
w_agent.get_action([frame], [], [], 5, info={"player_pos": dict(pos, z=5.0)})
visible = (w_ws / "logs.txt").read_text()
check("the window arm reads a truncated log",
      visible.count(SEPARATOR) == 2, f"got {visible.count(SEPARATOR)}")
check("the full log is not in the directory the agent works in",
      "Action 1 | Step 1" not in _visible_text(w_ws))
# Five calls, five sections: an action is written when its outcome is observed, so the
# fifth one is still pending. The point is that all of them are here and one is there.
check("the record keeps every section the window dropped",
      (w_agent.record_dir / "logs.txt").read_text().count(SEPARATOR) == 5,
      f'got {(w_agent.record_dir / "logs.txt").read_text().count(SEPARATOR)}')
# History is pixels here as well as text, so a window that leaves frames/ whole leaves
# the history readable by another route.
check("frames outside the window are not left behind either",
      len(list((w_ws / "frames").glob("*.png"))) == 2,
      f'got {len(list((w_ws / "frames").glob("*.png")))}')
check("the record keeps every frame", len(list((w_agent.record_dir / "frames").glob("*.png"))) == 5)
check("a window is not a purge: the agent's own files survive it",
      (w_ws / "notes.md").exists())
check("the turn prompt names the copy the agent has, not the one it does not",
      "./logs.txt" in _stub_turn.prompts[-1] and "logs_window" not in _stub_turn.prompts[-1])
check("the current frame is still attached from a directory the agent can see",
      (w_ws / "frames" / "step_0005.png").exists())

# The unablated arm must keep the layout its finished runs were produced under: one
# directory, written in place, no publishing step between the log and the agent.
plain = _ablation_agent("wsp4")
plain.get_action([frame], [], [], 1, info={"player_pos": pos})
check("the headline arm still writes straight into the workspace it is given",
      plain.record_dir == plain.workspace and not (ws / "wsp4_record").exists())
check("nothing is removed when nothing is ablated", plain._files_removed == 0)

# The crashed-scene guard has two directories to move now. Leaving the record behind
# would append a second episode to it while the visible copy looked new.
_ablation_agent("wsl", stateless=True)
check("a crashed ablation run takes its record aside with it",
      (ws / "wsl.crashed" / "logs.txt").exists()
      and (ws / "wsl_record.crashed" / "logs.txt").read_text().count("INITIAL STATE") == 1
      and (ws / "wsl_record" / "logs.txt").read_text() == "",
      f'left behind: {sorted(p.name for p in ws.glob("wsl*"))}')


# --- codex argv: the resume path must stay sandboxed and must not use -s ---------
from prolong_mc.codex_backend import CodexTurn
ct = CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")
first = ct._args()
ct.session_id = "1234abcd-0000-0000-0000-00000000ffff"
resumed = ct._args()
check("first turn is `codex exec`", first[:2] == ["/bin/true", "exec"] and "resume" not in first)
check("resume turn is `codex exec resume`", resumed[1:3] == ["exec", "resume"])
check("no -s anywhere: exec resume rejects it", "-s" not in first and "-s" not in resumed)
check("sandbox set via config on both paths",
      first.count('sandbox_mode="workspace-write"') == 1 and resumed.count('sandbox_mode="workspace-write"') == 1)
check("session id precedes the stdin sentinel", resumed[-2] == ct.session_id and resumed[-1] == "-")

# --- the tool surface, which no filesystem sandbox is on the path of --------------
# Measured on codex-cli 0.147.0 with this account: without these flags the model was
# handed `web__run` (it used it), ~250 `mcp__codex_apps__*` connectors, and the
# sub-agent tools. On this benchmark a web search or a repo-fetching connector reaches
# `benchmark/<scene>/multi-agent/metadata.json`'s target coordinates without touching
# this filesystem, so the flags are the control, not hygiene.
from prolong_mc.codex_backend import (
    EXPECTED_NESTED_TOOLS, SAFE_CODEX_FLAGS, SandboxViolation, request_stats,
)
check("safety flags reach the first turn", all(f in first for f in SAFE_CODEX_FLAGS))
check("safety flags reach the resume turn", all(f in resumed for f in SAFE_CODEX_FLAGS))
check("web search is disabled", 'web_search="disabled"' in SAFE_CODEX_FLAGS)
check("account apps are disabled", "features.apps=false" in SAFE_CODEX_FLAGS)
# `--disable multi_agent` does not remove spawn_agent; this key does (measured).
check("sub-agents are disabled", "agents.enabled=false" in SAFE_CODEX_FLAGS)
check("the expected surface is the five local tools",
      EXPECTED_NESTED_TOOLS == frozenset(
          {"apply_patch", "exec_command", "update_plan", "view_image", "write_stdin"}))

# ... and the tripwire that fires when the surface is not what the flags describe.
_violating = "\n".join(json.dumps(e) for e in [
    {"type": "thread.started", "thread_id": "T1"},
    {"type": "item.completed", "item": {"type": "web_search", "query": "0313 milestone"}},
    {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps"}},
    {"type": "thread.started", "thread_id": "T2"},
    {"type": "turn.completed", "usage": {}},
])
_st = request_stats(_violating)
check("a web search is counted", _st["web_searches"] == 1, str(_st))
check("a connector call is counted", _st["mcp_tool_calls"] == 1)
check("a spawned sub-agent is counted", _st["subthreads"] == 1)
check("a clean stream trips nothing",
      not any(request_stats(json.dumps({"type": "turn.completed", "usage": {}}))[k]
              for k in ("web_searches", "mcp_tool_calls", "subthreads")))

# The workspace codex is handed must be absolute: codex runs with cwd == workspace, so a
# relative one made every `-i` frame and `-o last_message.txt` resolve against the wrong
# directory. The sibling mllm-search port lost every attached image that way, silently.
import os as _os2
_cwd = _os2.getcwd()
_tmp = tempfile.mkdtemp()
_os2.chdir(_tmp)
try:
    check("CodexTurn resolves a relative workspace",
          CodexTurn(pathlib.Path("rel_ws"), model="m", codex_bin="/bin/true").workspace.is_absolute())

finally:
    _os2.chdir(_cwd)

# Attachments must be absolute: codex resolves -i against ITS cwd (the workspace), so a
# relative path that exists for the runner does not exist for codex. The sibling port
# lost all 20 attachments of a run this way, and the only trace was a line in the
# conversation that the event stream never shows.
from prolong_mc.codex_backend import scan_rollout
_ct = CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")
try:
    _ct.run("p", images=[pathlib.Path("frames/x.png")])
    check("a relative attachment is refused", False, "run() accepted a relative -i path")
except ValueError as e:
    check("a relative attachment is refused", "absolute" in str(e))
except Exception as e:
    check("a relative attachment is refused", False, f"raised {type(e).__name__} instead")

# The rollout scanner, against a conversation shaped like the one that caught this.
_roll = pathlib.Path(tempfile.mkdtemp()) / "rollout.jsonl"
_roll.write_text("\n".join([
    json.dumps({"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec",
                "input": 'const r = await tools.view_image({path:"/abs/frames/f0.png"}); image(r.image_url)'}}),
    json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [
        {"type": "input_text", "text": "Codex could not read the local image at `frames/f0.png`: No such file"}]}}),
    json.dumps({"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": []}}),
]))
_counts = scan_rollout(_roll)
check("the rollout scanner sees a nested view_image call", _counts["view_image_calls"] == 1, str(_counts))
check("the rollout scanner sees a failed attachment", _counts["image_attach_failures"] == 1, str(_counts))

# The sandbox wrapper the runner defaults to, and the two things it must never lose.
_wrapper = pathlib.Path(__file__).resolve().parent / "codex_sandbox.sh"
check("the sandbox wrapper exists and is executable",
      _wrapper.exists() and _os2.access(_wrapper, _os2.X_OK), str(_wrapper))
_w = _wrapper.read_text() if _wrapper.exists() else ""
check("the wrapper unshares the network", "--unshare-net" in _w)
check("the wrapper clears the inherited environment", "--clearenv" in _w)
check("the wrapper does not put the game server on the egress allowlist",
      "MC_SANDBOX_URL" not in _w.split("CODEX_SANDBOX_ALLOW")[-1].split("BWRAP_ARGS")[0])

# -i is variadic: anything positional after it is eaten as another image path. On the
# resume path that positional is the session id, so images must be terminated by a flag.
imgs = [pathlib.Path("/tmp/a.png"), pathlib.Path("/tmp/b.png")]
r_img = ct._args(imgs)
check("both images attached on resume", r_img.count("-i") == 2)
check("images are followed by a flag, not by the session id",
      r_img[r_img.index("/tmp/b.png") + 1] == "-m", f"got {r_img[r_img.index('/tmp/b.png') + 1]}")
check("session id survives image attachment", r_img[-2] == ct.session_id)

# --- what codex is told about a locally served model -----------------------------
# The context window is what codex's own accounting runs on, and the auto-compact
# trigger is what decides whether a long resumed conversation stays the conversation
# this arm claims to run. Both must reach BOTH codex paths, and neither may reach a
# hosted model, where codex's own metadata is right and ours would overwrite a fact
# with a guess.
local = CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true",
                  base_url="http://node:30000/v1", context_window=131072)._args()
hosted = CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")._args()
check("local codex is told the real context window",
      "model_context_window=131072" in local, " ".join(local))
check("auto-compaction is pushed past the context window, so overflow arrives first",
      "model_auto_compact_token_limit=1048576" in local, " ".join(local))
check("a hosted model keeps codex's own metadata",
      not any("model_context_window" in a or "auto_compact" in a for a in hosted))

# Thinking, on the arms the server pin cannot reach. vLLM synthesises
# enable_thinking = (effort != "none") from the Responses request and lets it override
# --default-chat-template-kwargs, and codex sends effort verbatim with no template
# kwargs of its own, so this one string is what decides whether the codex arms think.
check("a locally served model keeps the effort it was given, which is what leaves thinking on",
      'model_reasoning_effort="low"' in " ".join(
          CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true",
                    reasoning_effort="low", base_url="http://node:30000/v1")._args()))
import os as _os
from prolong_mc.codex_backend import effort_for as _effort_for
check("the local thinking switch is reachable from the environment, not only from an edit",
      _effort_for("http://node:1/v1", "low") == "low"
      and (_os.environ.update(CODEX_LOCAL_EFFORT="none") or
           _effort_for("http://node:1/v1", "xhigh") == "none")
      and (_os.environ.pop("CODEX_LOCAL_EFFORT", None) or True))
check("a hosted model keeps the effort the caller asked for",
      'model_reasoning_effort="low"' in " ".join(
          CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true",
                    reasoning_effort="low")._args()))



def _provider_argv(**kw):
    """The argv CodexProvider really builds, captured rather than restated here."""
    import unittest.mock as _mock
    from mc_agent.llm_provider import CodexProvider as _CP
    seen = {}

    class _Proc:
        stdout = ""
        stderr = ""
        returncode = 0

    def _capture(cmd, **rest):
        seen["cmd"] = cmd
        return _Proc()

    # The provider runs codex through `run_codex` (a Popen with its own process
    # group), not `subprocess.run`; patch the name it actually calls.
    with _mock.patch("mc_agent.llm_provider.run_codex", _capture):
        try:
            _CP(codex_bin="/bin/true", **kw).chat([{"role": "user", "content": "hi"}])
        except RuntimeError:
            # A stubbed codex writes no -o file, so the provider raises after building
            # the argv. The argv is the subject here.
            pass
    return " ".join(seen["cmd"])


check("the provider path treats local effort the same way the prolong path does",
      'model_reasoning_effort="xhigh"' in
      _provider_argv(base_url="http://node:30000/v1", reasoning_effort="xhigh"))
check("the hosted provider path keeps the effort the run asked for",
      'model_reasoning_effort="xhigh"' in _provider_argv(reasoning_effort="xhigh"))

from mc_agent.llm_provider import CodexProvider
prov = CodexProvider(codex_bin="/bin/true", base_url="http://node:30000/v1",
                     context_window=131072)
check("the provider path carries the same window as the prolong path",
      prov.context_window == 131072)

# The window is not restated in code: it comes from the server's own advert, exported
# by the runner, so a server started at a different length cannot silently disagree.
import importlib, os
import prolong_mc.codex_backend as _cb
os.environ["CODEX_MODEL_CONTEXT_WINDOW"] = "65536"
importlib.reload(_cb)
check("the context window follows the server's advert through the environment",
      "model_context_window=65536" in _cb.CodexTurn(
          pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true",
          base_url="http://node:30000/v1")._args())
del os.environ["CODEX_MODEL_CONTEXT_WINDOW"]
importlib.reload(_cb)

# A compaction event must be counted, not passed over: it means the conversation was
# rewritten, so the arm is no longer the one being compared. Prose is not an event --
# the model writes about compacting plans, and a substring match on the word would
# turn its vocabulary into a finding.
import unittest.mock as _mock


def _run_events(events) -> int:
    turn = _cb.CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")

    class _Proc:
        stdout = "\n".join(json.dumps(e) for e in events) + "\n"
        stderr = ""
        returncode = 0

    with _mock.patch("prolong_mc.codex_backend.run_codex", return_value=_Proc()):
        turn.run("hi")
    return turn.compactions


check("a compaction event is counted",
      _run_events([{"type": "thread.compacted", "usage": {}}]) == 1)
check("a model writing the word 'compact' is not a compaction",
      _run_events([{"type": "item.completed",
                    "item": {"type": "agent_message",
                             "text": "let me compact this plan"}}]) == 0)


# One view_image call emits two events. Counting lines counted it about twice, and
# this number USED to be the evidence for whether a vision-on-demand analyzer ever
# looked; it is now read from the rollout instead (CodexTurn.vision_audit).
def _view_image_calls(events) -> int:
    turn = _cb.CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")

    class _Proc:
        stdout = "\n".join(json.dumps(e) for e in events) + "\n"
        stderr = ""
        returncode = 0

    with _mock.patch("prolong_mc.codex_backend.run_codex", return_value=_Proc()):
        turn.run("hi")
    return turn.view_image_calls


# The event stream is NOT where vision is counted any more, and this is the check that
# says so. codex 0.147 runs the model's tools inside an `exec` cell and `--json` reports
# only shell commands, so a nested `tools.view_image(...)` never appears here at all --
# measured as 0 mentions across every events.jsonl of a run whose conversation holds 20
# calls returning 60 images. A counter over this stream is a constant, which is what made
# "the analyzer opened none across 8 turns" (finding #30) unfalsifiable rather than false.
one_call = [{"type": "item.started", "item": {"id": "i1", "type": "view_image",
                                              "path": "frames/step_0001.png"}},
            {"type": "item.completed", "item": {"id": "i1", "type": "view_image",
                                                "path": "frames/step_0001.png"}}]
check("the event stream is no longer trusted for vision",
      _view_image_calls(one_call) == 0,
      "a nonzero count here means someone re-added an events-based counter; codex does "
      "not emit these items, so it would read 0 on real runs and mislead exactly as before")


# --- RUN_LEDGER bookkeeping must not double as a verdict --------------------------
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import compare_runs

check("a CHANNEL: line does not exclude the run it labels",
      not any(r.startswith("CHANNEL:") for r in compare_runs.load_invalid().values()))
check("frozen channel labels are readable",
      compare_runs.load_channels().get("20260815-210755-qwen35-0313-0544-scored-33ea") == "vllm",
      str(compare_runs.load_channels())[:200])
check("a frozen label wins over whatever scripts/ says today",
      compare_runs.channel("20260815-235931-s0802-qwen-vllm-default-0602") == "vllm")

# An ablated run is the control the headline arm is compared against, so it must not
# land in the headline arm's cell.
check("the stateless ablation reports as its own arm",
      compare_runs.arm_label("prolong", {"prolong_stateless": True}) == "prolong-sl")
check("the window ablation reports as its own arm, window and all",
      compare_runs.arm_label("prolong", {"prolong_log_window": 0}) == "prolong-w0")
check("an unablated prolong run keeps its plain label",
      compare_runs.arm_label("prolong", {"prolong_log_window": None,
                                         "prolong_stateless": False}) == "prolong")

# --- a timed-out call must leave its evidence behind ------------------------------
# The stall is the call worth reading, and it was the only one with no transcript: the
# events are written after the codex process returns, so a timeout discarded them. One
# 15-minute stall in the 40-step default probe left nothing but its duration.
_timeout_dir = pathlib.Path(tempfile.mkdtemp())
_turn = _cb.CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true",
                      transcript_dir=_timeout_dir)


def _raise_timeout(*a, **kw):
    raise subprocess.TimeoutExpired(
        cmd="codex", timeout=900,
        output='{"type":"thread.started"}\n{"type":"item.started"}\n')


import subprocess
with _mock.patch("prolong_mc.codex_backend.run_codex", _raise_timeout):
    _res = _turn.run("hi")
check("a timed-out turn is still reported as a failure", not _res["ok"] and _res["error"] == "timeout")
check("a timed-out turn keeps the events it had already received",
      (_timeout_dir / "turn_0001.timeout.events.jsonl").exists()
      and "thread.started" in (_timeout_dir / "turn_0001.timeout.events.jsonl").read_text(),
      str(sorted(p.name for p in _timeout_dir.iterdir())))
check("the partial transcript is named apart from a completed one, not mistaken for it",
      not (_timeout_dir / "turn_0001.events.jsonl").exists())


# --- what a codex call actually costs --------------------------------------------
# "One call per step" is the wrong unit: a call runs a tool loop, and each tool result
# is another request re-paying the prompt. And codex's usage is cumulative over the
# thread, so the arithmetic that looks obvious is quadratic.
from prolong_mc.codex_backend import request_stats, merge_stats


def _events(thread, tools, usage):
    lines = [{"type": "thread.started", "thread_id": thread}]
    for i in range(tools):
        lines.append({"type": "item.completed",
                      "item": {"id": f"i{i}", "type": "command_execution"}})
    lines.append({"type": "item.completed", "item": {"id": "m", "type": "agent_message"}})
    lines.append({"type": "turn.completed", "usage": {"input_tokens": usage,
                                                      "output_tokens": usage // 10}})
    return "\n".join(json.dumps(o) for o in lines)


two_tools = request_stats(_events("t1", 2, 40000))
check("a tool call is a request boundary, so two tools make three requests",
      two_tools["requests"] == 3, str(two_tools))
check("a call with no tools is one request", request_stats(_events("t1", 0, 10))["requests"] == 1)
check("agent messages are counted but are not the request unit",
      two_tools["agent_messages"] == 1 and two_tools["tool_calls"] == 2)

# turn_0001..0004 of m1-qwen38-prolong-0313-02bf report 40246, 88493, 146686, 242646
# input tokens for one resumed conversation: each number contains the ones before it.
resumed = [request_stats(_events("t1", 1, n)) for n in (40246, 88493, 146686)]
merged = merge_stats(resumed)
check("cumulative usage is taken once, not summed into a quadratic",
      merged["input_tokens"] == 146686, str(merged))
check("requests still add up across calls", merged["requests"] == 6, str(merged))
check("a session dropped on overflow starts its own counter",
      merge_stats(resumed + [request_stats(_events("t2", 0, 5000))])["input_tokens"]
      == 146686 + 5000)
check("threads are counted so a cold start is visible in the cost row",
      merge_stats(resumed + [request_stats(_events("t2", 0, 5000))])["threads"] == 2)
check("a transcript with no usage costs nothing rather than crashing",
      merge_stats([request_stats("")])["input_tokens"] == 0)


# --- overflow: the session must be dropped, not retried into ---------------------
from prolong_mc.codex_backend import is_overflow
check("overflow classifier catches the context-window message",
      is_overflow("BadRequest", "Your input exceeds the context window: maximum 272000 tokens"))
check("overflow classifier catches 'too long'", is_overflow("Error", "prompt is too long"))
check("overflow classifier ignores ordinary errors",
      not is_overflow("ToolError", "actions.json could not be written"))

ct2 = CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")
ct2.session_id = "1234abcd-0000-0000-0000-00000000ffff"
class _Proc:
    stdout = json.dumps({"type": "turn.failed",
                         "message": {"name": "BadRequest",
                                     "message": "context length exceeded"}}) + "\n"
    stderr = ""
    returncode = 1
import unittest.mock as _mock
with _mock.patch("prolong_mc.codex_backend.run_codex", return_value=_Proc()):
    res = ct2.run("hi")
check("overflow is reported to the caller", res["overflow"] is True)
check("overflow drops the session so the next turn cold-starts", ct2.session_id is None)
check("overflow reset is counted", ct2.overflow_resets == 1)


# --- ESC policy must not vary with the protocol, matching the baseline ----------
from prolong_mc.prompts import build_system_prompt
hint_on = build_system_prompt("t", 15, 40, 20, None, milestone_hint=True)
hint_off = build_system_prompt("t", 15, 40, 20, None, milestone_hint=False)
esc_on = [l for l in hint_on.splitlines() if "ESC=1" in l]
esc_off = [l for l in hint_off.splitlines() if "ESC=1" in l]
check("ESC wording is identical under both protocols", esc_on == esc_off, f"{esc_on} vs {esc_off}")
check("ESC wording keeps the baseline's 'keep working' clause",
      "keep working" in hint_off)

# The hint protocol: the baseline renders its verified-status section only when the
# hint is on, so PRO-LONG documents [MILESTONE] on exactly the same condition.
check("[MILESTONE] is documented only under the hint protocol",
      "[MILESTONE]" in hint_on and "[MILESTONE]" not in hint_off)

# An ESC refusal must annotate the log without erasing the plan it arrived alongside.
agent5 = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                      workspace=ws / "wsp5", milestone_hint=True)
agent5.codex.run = lambda prompt, images=(): {
    "ok": True, "error": None, "overflow": False, "message": "[PLAN]\nkeep going north",
    "actions_json": json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 4}]})}
agent5.load_system_prompt("t")
check("hint protocol reaches the analyzer's system prompt",
      "[MILESTONE]" in (ws / "wsp5" / "AGENTS.md").read_text())
for step in range(1, 5):
    agent5.get_action([frame], [], [], step, info={"player_pos": dict(pos, z=float(step))})
    agent5.on_esc_rejected(step=step)      # model insists it is done, every step
agent5.get_action([frame], [], [], 5, info={"player_pos": dict(pos, z=5.0)})
text5 = (ws / "wsp5" / "logs.txt").read_text()
check("repeated ESC refusals collapse to one note per section",
      text5.count("[NOTE] ESC was rejected") <= 4 and "[NOTE] ESC was rejected" in text5,
      f'got {text5.count("[NOTE] ESC was rejected")}')
check("the refusal note does not erase the analyzer's plan",
      "keep going north" in text5)
check("refusals are counted for the audit", agent5._esc_rejections == 4)

# The status is re-sent every step; the log must record the transition, not 150 copies.
agent6 = ProlongAgent(action_space=MinerRLActionSpace(), provider=None, model="stub",
                      workspace=ws / "wsp6", milestone_hint=True)
agent6.codex.run = lambda prompt, images=(): {
    "ok": True, "error": None, "overflow": False, "message": "[PLAN]\ngo",
    "actions_json": json.dumps({"actions": [{"action": {"forward": 1}, "repeat": 8}]})}
agent6.load_system_prompt("t")
NOT_YET = "The environment has NOT verified the task as complete yet."
DONE = "The environment HAS verified the task as complete."
for step in range(1, 7):
    agent6.get_action([frame], [], [], step, info={"player_pos": dict(pos, z=float(step))},
                      milestone_hint=NOT_YET if step < 4 else DONE)
text6 = (ws / "wsp6" / "logs.txt").read_text()
check("the unchanged status is logged once, not once per step",
      text6.count(NOT_YET) == 1, f"got {text6.count(NOT_YET)}")
check("the transition to verified-complete is logged the step it happens",
      text6.count(DONE) == 1, f"got {text6.count(DONE)}")

# --- the serving contract: assert the argv, not the script text --------------------
# Every property below changes what the model emits, so a regression here silently
# produces numbers that are not comparable to the ones already in the ledger. The
# check runs serve_vllm.sh with a stub interpreter that records its own argv, so it
# asserts what the server is actually launched with rather than what the script looks
# like it says.
import os, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent


def serve_argv(**env_overrides) -> list[str]:
    tmp = pathlib.Path(tempfile.mkdtemp())
    argv_file = tmp / "argv.txt"
    stub = tmp / "python-stub"
    stub.write_text(
        '#!/usr/bin/env bash\n'
        f'printf "%s\\n" "$@" >> "{argv_file}"\n'
        'exit 0\n'
    )
    stub.chmod(0o755)
    env = dict(
        os.environ,
        VLLM_PYTHON=str(stub),
        DISCOVERY_DIR=str(tmp / "servers"),
        ART_DIR=str(tmp),
        VLLM_READY_TIMEOUT="0",
        MINEEXPLORER_ROOT=str(ROOT),
        **{k: str(v) for k, v in env_overrides.items()},
    )
    # Exits non-zero: the stub is not a server, so readiness never arrives. The argv is
    # what is under test, and it is written before that.
    subprocess.run(["bash", str(ROOT / "scripts" / "serve_vllm.sh")],
                   env=env, capture_output=True, text=True, timeout=120)
    lines = argv_file.read_text().splitlines() if argv_file.exists() else []
    # Drop the pre-flight `-c import ...` dependency check; the server launch is last.
    return lines[lines.index("-m"):] if "-m" in lines else lines


def flag_value(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


argv = serve_argv()
check("serving: cudagraphs replace eager by default",
      "--enforce-eager" not in argv and "-cc.cudagraph_mode=FULL_DECODE_ONLY" in argv, " ".join(argv))
check("serving: compilation stays off so the Dynamo host-OOM cannot recur",
      "-cc.mode=none" in argv)
# Not a tuning knob: leaving vLLM's default of 1024 makes cudagraph capture refuse to
# start on this architecture, because every decode sequence holds a Mamba cache block.
check("serving: max_num_seqs is small enough for cudagraph capture to be possible",
      0 < int(flag_value(argv, "--max-num-seqs") or 0) <= 512,
      flag_value(argv, "--max-num-seqs"))
check("serving: tensor parallelism defaults to 2",
      flag_value(argv, "--tensor-parallel-size") == "2", flag_value(argv, "--tensor-parallel-size"))
# The cap has to clear what the model actually emits in the mode being served. Across the
# finished Qwen3.8 runs the model-authored items were p50 237 and p90 1933 tokens with 24
# over 4096, the largest a single 12,918-token message; a 4096 cap would have cut those
# mid-deliberation, and since the JSON follows the prose a truncated response yields no
# action at all. It still forecloses a repetition loop running to the 131k context end.
check("serving: the output cap clears the longest response observed with thinking on",
      json.loads(flag_value(argv, "--override-generation-config") or "{}").get("max_new_tokens") == 16384,
      flag_value(argv, "--override-generation-config"))
# Sampling is set once on the server because the codex arms send none of it. These are
# Qwen3.8's recipe for thinking mode, which is also what its shipped generation_config.json
# carries -- so this pins what was already in force rather than changing it, the point
# being that it is now pinned for both channels instead of one.
_gen = json.loads(flag_value(argv, "--override-generation-config") or "{}")
check("serving: sampling follows the model card's thinking recipe",
      (_gen.get("temperature"), _gen.get("top_p"), _gen.get("top_k")) == (1.0, 0.95, 20),
      json.dumps(_gen))
check("serving: the codex arms and the vLLM arm cannot end up on different sampling",
      _gen.get("temperature") == 1.0, json.dumps(_gen))
check("serving: presence_penalty is left unset, since only one arm could receive it",
      "presence_penalty" not in _gen, json.dumps(_gen))
# Reverses the earlier pin, on measurement rather than preference: with thinking off the
# default arm looped on `echo ok` 85 times inside one call and burned the client timeout,
# where the same arm with thinking on never exceeded 3 tool calls across 46. The damage was
# one-sided -- PRO-LONG was unaffected -- and a comparison whose baseline our own serving
# choice crippled is worse than no comparison. Untested confound: that measurement changed
# thinking and the sampling recipe together, and the card prescribes presence_penalty=1.5
# for the non-thinking mode specifically to stop repetition, which cannot be delivered here.
check("serving: thinking is pinned on in the chat template",
      json.loads(flag_value(argv, "--default-chat-template-kwargs") or "{}") == {"enable_thinking": True},
      flag_value(argv, "--default-chat-template-kwargs"))
# The one invariant spanning both files. The direct-vLLM arm is configured on the server
# and the codex arms are configured in effort_for, so nothing else stops a matrix from
# running its channel control with a different thinking setting than the cells it
# controls -- which is precisely the confound the channel axis exists to rule out. This
# check failed once, when the server was moved to thinking-on and effort_for was left
# pinned to "none".
_server_thinking = json.loads(
    flag_value(argv, "--default-chat-template-kwargs") or "{}").get("enable_thinking")
_codex_thinking = _effort_for("http://node:1/v1", "low") != "none"
check("serving: the codex arms and the direct-vLLM arm default to the same thinking setting",
      _server_thinking == _codex_thinking,
      f"server={_server_thinking} codex={_codex_thinking}")


def _runner_temperature(advert_temp, **env_overrides) -> str:
    """What the direct-vLLM runner would sample at, given a server advertising this.

    Exits non-zero -- the endpoints it contacts do not exist -- but the resolution is
    printed before them, which is why it was moved above the curls.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "servers").mkdir()
    (tmp / "servers" / "t.json").write_text(json.dumps(
        {"url": "http://x/v1", "max_model_len": 131072, "sampling": {"temperature": advert_temp}}))
    env = dict(os.environ, PYTHON_BIN="/bin/true", MODEL_SERVER="t",
               DISCOVERY_DIR=str(tmp / "servers"), ART_DIR=str(tmp / "art"),
               MC_SANDBOX_URL="http://127.0.0.1:1", QWEN_API_URL="http://127.0.0.1:1/v1",
               SCENES="0313", MINEEXPLORER_ROOT=str(ROOT),
               **{k: str(v) for k, v in env_overrides.items()})
    if "TEMPERATURE" not in env_overrides:
        # Or an ambient value would make the no-override case pass for the wrong reason.
        env.pop("TEMPERATURE", None)
    out = subprocess.run(["bash", str(ROOT / "scripts" / "run_qwen35_0313_0544.sh")],
                         env=env, capture_output=True, text=True, timeout=120).stdout
    for line in out.splitlines():
        if line.startswith("temperature <-"):
            return line.rsplit(":", 1)[1].strip()
    return ""


# The other half of the same trap the thinking check covers. --override-generation-config
# is a *default*, and VLLMProvider sends `temperature` on every request, where an explicit
# value wins -- so restating a temperature in the runner silently gave the direct arm a
# different one from the codex arms, on top of the server's top_p.
check("serving: the direct-vLLM arm samples at whatever the server advertises",
      _runner_temperature(1.0) == "1.0", _runner_temperature(1.0))
check("serving: an explicit TEMPERATURE still overrides the advert, for a probe",
      _runner_temperature(1.0, TEMPERATURE="0.3") == "", "advert was read despite an explicit value")
# The escape hatch has to keep working: if a cudagraph capture ever fails on a node,
# eager is how the run happens at all, and it must not need a mid-flight script edit.
eager_argv = serve_argv(VLLM_EAGER="1")
check("serving: VLLM_EAGER=1 still falls back to --enforce-eager",
      "--enforce-eager" in eager_argv and "-cc.mode=none" not in eager_argv, " ".join(eager_argv))
check("serving: the output cap is overridable for a deliberate probe",
      json.loads(flag_value(serve_argv(VLLM_MAX_OUTPUT_TOKENS="256"),
                            "--override-generation-config") or "{}").get("max_new_tokens") == 256)

print()
print(f"{'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
