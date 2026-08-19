"""Selftest for the hypothesis agent's discipline rules (experiments/HYPOTHESIS_V2_DESIGN.md).

    .venv/bin/python -m mc_agent.hypothesis_selftest

No model: a scripted provider plays the model, and the checks are the rules the harness
must hold the graph to -- goals are confirmed by the environment, a refused ESC locks the
goals the model believed done, a locked goal cannot be raised, a hypothesis under test
too long goes stale, ESC passes through under the no-hint protocol.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

from mc_agent.action_space import MinerRLActionSpace
from mc_agent.hypothesis_agent import HypothesisAgent, TEST_BUDGET_STEPS

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS  " if cond else "FAIL  ") + name + (f"  -- {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


NOT_YET = "The environment has NOT verified the task as complete yet. Do not end the episode (ESC) until it is."
DONE = "The environment HAS verified the task as complete. You may now end the episode by setting ESC=1."


class Scripted:
    """A provider that returns the next scripted reply; the last one repeats."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def chat(self, messages, **kwargs):
        self.prompts.append(messages[0]["content"][0]["text"])
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return json.dumps(reply)


def reply(action, hyps=None, plan=None, testing=None, thought="t", memory="m"):
    return {"thought": thought, "action": action, "memory_update": memory,
            "hypotheses": hyps or [], "plan": plan or [], "testing": testing}


frame = np.zeros((64, 64, 3), np.uint8)


def run(agent, provider, n, hint, start=1):
    out = []
    for step in range(start, start + n):
        _, action, _ = agent.get_action([frame], [], [], step, milestone_hint=hint)
        out.append(action)
    return out


# --- 1. goals: the environment confirms, not the model ------------------------------
chain = [
    {"id": "h1", "statement": "find the granite", "confidence": 0.3, "status": "active"},
    {"id": "h2", "statement": "find the brick wall", "confidence": 0.2, "status": "active", "depends_on": ["h1"]},
    {"id": "h3", "statement": "find the magenta banner", "confidence": 0.2, "status": "active", "depends_on": ["h2"]},
]
prov = Scripted([
    reply({"camera": [0, 30]}, hyps=chain),                                          # step 1: scaffold, no kind
    reply({"forward": 1}, hyps=[{"id": "h1", "status": "confirmed", "confidence": 1.0}]),  # step 2: self-confirms
    reply({"forward": 1}),                                                             # quiet
])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub")
agent.load_system_prompt("Find the granite, then the brick wall, then the magenta banner.")
run(agent, prov, 3, NOT_YET)
g = agent.graph.nodes
check("first-response scaffolding is typed as goals when the model omits kind",
      all(g[h].kind == "goal" for h in ("h1", "h2", "h3")), str({h: g[h].kind for h in g}))
check("a self-confirmed goal is reverted while the environment says NOT verified",
      g["h1"].status == "active" and g["h1"].confidence <= 0.9, f"{g['h1'].status} {g['h1'].confidence}")
check("the reversal is written into the node's evidence",
      any("only the environment confirms goals" in e for e in g["h1"].evidence), str(g["h1"].evidence))
check("the discipline counter says it happened", agent.discipline["goal_confirm_reverted"] == 1)
check("goals are listed first in the prompt summary",
      agent.graph.to_prompt_summary().splitlines()[0].startswith("- [h1] (goal"),
      agent.graph.to_prompt_summary())
check("the prompt documents the rules",
      "Goals are confirmed by the environment" in prov.prompts[-1] and '"testing"' in prov.prompts[-1])

# --- 2. ESC while NOT verified: dropped, goals the model believed done are locked --------
prov = Scripted([
    reply({"camera": [0, 30]}, hyps=[dict(h, kind="goal") for h in chain]),
    reply({"forward": 1}, hyps=[{"id": "h1", "confidence": 0.9}, {"id": "h2", "confidence": 0.85},
                                 {"id": "s1", "kind": "state", "statement": "the carpet is in my hotbar",
                                  "confidence": 1.0, "status": "confirmed"},
                                 {"id": "l1", "kind": "location", "statement": "the banner is west",
                                  "confidence": 0.9, "status": "confirmed"}]),
    reply({"ESC": 1}),                                                                # step 3: quits
    reply({"ESC": 1}, hyps=[{"id": "h1", "status": "confirmed", "confidence": 1.0},
                            {"id": "h2", "status": "confirmed", "confidence": 1.0}]),   # step 4: re-confirms + ESC
    reply({"forward": 1}),
])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub")
agent.load_system_prompt("t")
acts = run(agent, prov, 5, NOT_YET)
g = agent.graph.nodes
check("ESC is dropped while the environment says NOT verified", acts[2]["ESC"] == 0 and acts[3]["ESC"] == 0)
check("the drop is counted", agent.discipline["esc_dropped"] == 2, str(agent.discipline))
check("goals the model believed done are locked", {"h1", "h2"} <= agent._locked, str(agent._locked))
check("a goal it did not believe done is not locked", "h3" not in agent._locked)
check("a confirmed state claim about what it carries is locked too", "s1" in agent._locked)
check("a confirmed location belief is not a completion claim, so it is not locked",
      "l1" not in agent._locked and g["l1"].status == "confirmed")
check("locked goals are capped at 0.5", g["h1"].confidence <= 0.5 and g["h2"].confidence <= 0.5,
      f"{g['h1'].confidence} {g['h2'].confidence}")
check("re-confirming a locked goal on the next step does not stick",
      g["h1"].status == "active" and g["h1"].confidence <= 0.5, f"{g['h1'].status} {g['h1'].confidence}")
check("the cap on a locked raise is counted", agent.discipline["locked_raise_capped"] >= 2, str(agent.discipline))
check("the prompt shows the lock and the dropped ESCs",
      "locked" in prov.prompts[-1] and "each ESC was dropped" in prov.prompts[-1])
check("evidence is not spammed: one lock note per node",
      sum("locked until the environment" in e for e in g["h1"].evidence) == 1, str(g["h1"].evidence))

# --- 3. verification arrives: locks lift, ESC passes -----------------------------------
prov = Scripted([reply({"ESC": 1}, hyps=[{"id": "h1", "status": "confirmed", "confidence": 1.0}])])
agent2 = agent
agent2.provider = prov
acts = run(agent2, prov, 1, DONE, start=6)
check("once the environment verifies, ESC passes through", acts[0]["ESC"] == 1)
check("and the locks are lifted", not agent2._locked)
check("and a goal may be confirmed", agent2.graph.nodes["h1"].status == "confirmed")

# --- 4. no-hint protocol: the agent may end its own episode -----------------------------
prov = Scripted([reply({"ESC": 1}, hyps=[{"id": "h1", "kind": "goal", "statement": "x", "status": "confirmed",
                                          "confidence": 1.0}])])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub")
agent.load_system_prompt("t")
acts = run(agent, prov, 1, "")
check("no-hint protocol: ESC passes through", acts[0]["ESC"] == 1)
check("no-hint protocol: nothing is reverted or locked",
      agent.graph.nodes["h1"].status == "confirmed" and not agent._locked)

# --- 5. test budget: a hypothesis under test too long goes stale ------------------------
prov = Scripted([
    reply({"attack": 1}, hyps=[{"id": "m1", "kind": "mechanism", "statement": "attacking the trunk clears the path",
                                "confidence": 0.65, "status": "active"}], plan=["keep attacking"], testing="m1"),
    reply({"attack": 1}, testing="m1"),
])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub")
agent.load_system_prompt("t")
run(agent, prov, TEST_BUDGET_STEPS, NOT_YET)
check("under budget the hypothesis stays active", agent.graph.nodes["m1"].status == "active")
check("the prompt shows how long it has been under test", "under test for" in prov.prompts[-1])
run(agent, prov, 1, NOT_YET, start=TEST_BUDGET_STEPS + 1)
check("at the budget with no confidence change it goes stale",
      agent.graph.nodes["m1"].status == "stale", agent.graph.nodes["m1"].status)
check("and the plan is cleared", agent.current_plan == [])
check("and it is counted", agent.discipline["stale_by_budget"] == 1)

# a confidence change resets the clock
prov = Scripted([
    reply({"attack": 1}, hyps=[{"id": "m1", "kind": "mechanism", "statement": "s", "confidence": 0.6}], testing="m1"),
    reply({"attack": 1}, hyps=[{"id": "m1", "confidence": 0.4}], testing="m1"),
    reply({"attack": 1}, testing="m1"),
])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub")
agent.load_system_prompt("t")
run(agent, prov, TEST_BUDGET_STEPS + 1, NOT_YET)
check("a confidence change resets the budget clock", agent.graph.nodes["m1"].status == "active",
      agent.graph.nodes["m1"].status)

# goals are exempt: searching for a hop is the job, not perseveration
prov = Scripted([
    reply({"forward": 1}, hyps=[{"id": "h1", "kind": "goal", "statement": "find the banner", "confidence": 0.3}],
          testing="h1"),
    reply({"forward": 1}, testing="h1"),
])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub")
agent.load_system_prompt("t")
run(agent, prov, TEST_BUDGET_STEPS + 2, NOT_YET)
check("goals do not go stale under the budget", agent.graph.nodes["h1"].status == "active")

# --- 6. save_state writes the discipline record ------------------------------------------
out = Path(tempfile.mkdtemp())
agent.save_state(out)
disc = json.loads((out / "hypothesis_discipline.json").read_text())
check("save_state records the discipline counters",
      {"esc_dropped", "locked", "stale_by_budget", "test_budget_steps"} <= set(disc), str(disc))
graph = json.loads((out / "hypothesis_graph.json").read_text())
check("the saved graph carries kinds", graph["nodes"][0].get("kind") == "goal", str(graph["nodes"][0]))

# --- 7. compact style still formats with the new pieces -------------------------------------
prov = Scripted([reply({"forward": 1})])
agent = HypothesisAgent(MinerRLActionSpace(), prov, model="stub", response_style="compact",
                        prompt_layout="append-only")
agent.load_system_prompt("t")
run(agent, prov, 1, NOT_YET)
check("compact/append-only prompt renders with the discipline pieces",
      "Kinds, and what the harness enforces" in prov.prompts[-1])

print()
if FAILS:
    print("FAILURES:", ", ".join(FAILS))
    sys.exit(1)
print(f"all checks passed")
