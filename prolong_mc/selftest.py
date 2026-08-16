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

print()
print(f"{'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
