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

    with _mock.patch("subprocess.run", return_value=_Proc()):
        turn.run("hi")
    return turn.compactions


check("a compaction event is counted",
      _run_events([{"type": "thread.compacted", "usage": {}}]) == 1)
check("a model writing the word 'compact' is not a compaction",
      _run_events([{"type": "item.completed",
                    "item": {"type": "agent_message",
                             "text": "let me compact this plan"}}]) == 0)


# One view_image call emits two events. Counting lines counted it about twice, and
# this number is the evidence for whether a vision-on-demand analyzer ever looked.
def _view_image_calls(events) -> int:
    turn = _cb.CodexTurn(pathlib.Path(tempfile.mkdtemp()), model="m", codex_bin="/bin/true")

    class _Proc:
        stdout = "\n".join(json.dumps(e) for e in events) + "\n"
        stderr = ""
        returncode = 0

    with _mock.patch("subprocess.run", return_value=_Proc()):
        turn.run("hi")
    return turn.view_image_calls


one_call = [{"type": "item.started", "item": {"id": "i1", "type": "view_image",
                                              "path": "frames/step_0001.png"}},
            {"type": "item.completed", "item": {"id": "i1", "type": "view_image",
                                                "path": "frames/step_0001.png"}}]
check("one view_image call counts once, not once per event",
      _view_image_calls(one_call) == 1, f"got {_view_image_calls(one_call)}")
check("two view_image calls count twice", _view_image_calls(one_call * 2) == 2)


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
with _mock.patch("subprocess.run", return_value=_Proc()):
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
check("serving: tensor parallelism defaults to 2",
      flag_value(argv, "--tensor-parallel-size") == "2", flag_value(argv, "--tensor-parallel-size"))
check("serving: every arm gets the same 4096 output cap",
      json.loads(flag_value(argv, "--override-generation-config") or "{}").get("max_new_tokens") == 4096,
      flag_value(argv, "--override-generation-config"))
check("serving: thinking is pinned off in the chat template",
      json.loads(flag_value(argv, "--default-chat-template-kwargs") or "{}") == {"enable_thinking": False},
      flag_value(argv, "--default-chat-template-kwargs"))
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
