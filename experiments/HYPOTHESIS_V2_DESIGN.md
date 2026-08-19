# Hypothesis agent v2: make the graph do work

Companion to [BEHAVIOR_helixon_4hop.md](BEHAVIOR_helixon_4hop.md) (§3.3, §3.6, §5.6) and
[PROLONG_FIDELITY_AUDIT.md](PROLONG_FIDELITY_AUDIT.md). The `default` arm is the fixed
baseline and is not touched; `prolong` is being brought closer to its paper; `hypothesis`
is the method under development, and this file says what is wrong with it, what v2.0
changes (landed, unit-tested, not yet run against a model), what v2.1 would need a
decision for, and what to run first.

## 1. What the 4-hop trajectories say about the hypothesis agent

Fourteen cells (7 scenes × Qwen3.8 / Qwen3.5), 20 of 56 milestones against `default`'s 21:
the DAG changed nothing measurable, and the trajectories say why.

1. **The graph is a notebook, not a belief state.** Nodes are hop scaffolding (four per cell,
   created at step 1) plus motor-level claims ("there is a low block blocking forward
   movement", 0482) and restated goals; confidence is never checked against anything.
   0311 (Qwen3.8) `h12` "breaking tree trunks will clear a path" stayed at 0.65 through 46
   attack ticks with no progress. No cell shows an action the memory-only agent would not
   have taken.
2. **Goal completion is self-declared, and the declaration wins over the environment.**
   In q35-hypothesis-0603 the model marks `h4` "mined the quartz" confirmed at 1.0 (step
   98) and presses ESC; the harness refuses (nothing was mined — the carpet, stairs and
   quartz hops never fired) and `on_esc_rejected` demotes the goals to 0.5; **on step 99
   the model re-confirms h1–h4 at 1.0 and presses ESC again, and does so on every step to
   300** (202 refusals). Its stated reason: "the environment status explicitly states the
   task is NOT verified yet … I must re-issue ESC … assuming the verification system
   requires a specific trigger or delay". The memory string ("Mined white carpet (h2).
   Mined red nether brick stairs (h3). … Successfully mined the quartz block (h4)") is
   the lock, and the graph echoes it back as settled fact.
3. **Nothing bounds a test.** The plan is free text; nothing knows which hypothesis an
   action is testing or for how long, so a wrong mechanism belief runs until the model
   happens to change its mind (which, per 1, it does not).
4. Everything the direct arms share — no yaw, no inventory, no per-hop verification, the
   movement hint that cries wolf (BEHAVIOR §3.4), mining/aim blindness (§3.1) — the
   hypothesis agent shares, and its 320 ESC presses (default: 152) show the DAG made the
   completion error *stickier*.

## 2. Principle for v2

Turn the DAG from a notebook into **a belief state the harness can hold to account**:
every node has a kind; the kinds that can be checked are checked; what the environment
owns (goal completion) the model may not declare; and a belief that stops moving under
test is retired for it. The model still chooses every action — the graph is still
advisory about *what to do* — but it is no longer advisory about *what is true*.

## 3. v2.0 — landed (decision-free, no new information channel)

Files: `mc_agent/hypothesis.py`, `mc_agent/hypothesis_agent.py`,
`mc_agent/hypothesis_selftest.py` (32 checks, `python -m mc_agent.hypothesis_selftest`).
The `default` agent, `mc_agent/context.py` and `mc_agent/agent.py` are untouched; the
hypothesis prompt changed (by design), so `scripts/prompt_layout_check.py --golden` will
report the hypothesis cases as DIFFERENT — re-write the golden for them, and confirm the
default cases still read IDENTICAL.

| rule | what the harness does | targets |
|---|---|---|
| **kinds** | every hypothesis carries `kind ∈ {goal, location, mechanism, state, other}`; the first response's scaffolding is `goal` even if the model forgets the field; goals are listed first in the prompt | §1.1 — makes "what kind of claim is this" explicit so rules can act on it |
| **goals are confirmed by the environment** | a `confirmed` on a goal while the status line says NOT verified is reverted to `active`, confidence ≤ 0.9, with a `[harness]` evidence line saying why | §1.2 first half |
| **ESC gate + lock** | ESC while NOT verified is dropped before it reaches the game (the harness would refuse it anyway) and every goal the model *believed done* (confirmed or ≥ 0.5) plus any confirmed `state` claim is capped at 0.5 and **locked**; a locked node cannot be raised above 0.5 or confirmed until the environment verifies the task; the prompt shows "locked" on the node and a *Harness notices* section ("You tried to end the episode N times…; locked goals: h1, h2 — re-verify each physically, an item is mined only if it is in your hotbar/inventory") | §1.2 second half — the re-confirm-at-1.0 loop cannot happen; ESC spam costs nothing but the one dropped step |
| **test budget** | the reply names `testing: <id>`; a non-goal hypothesis under test for 25 steps (`TEST_BUDGET_STEPS`) with no confidence change (±0.05) is marked `stale`, the plan is cleared, and the prompt says so; a confidence change or a different id resets the clock; goals are exempt (searching for hop 2 for 40 steps is the job) | §1.3 — 46 attack ticks on a 0.65 belief becomes at most 25 |
| **no-hint protocol** | with no status line (`milestone_hint == ""`) nothing above fires and ESC passes through — the paper's protocol is unchanged | keeps the arm comparable under both protocols |
| **record** | `hypothesis_discipline.json` next to the graph: counts of reverted confirms, capped raises, dropped ESCs, lock events, budget stales, the locked set | so a v2 cell can be read next to its score |

Prompt: one shared block (`_HYP_DISCIPLINE`, both response styles) states the rules and
asks for `kind` and `testing`; the reply schema for the codex path (`hypothesis_reply_schema`)
accepts both. `on_esc_rejected` still exists (routes into the same lock) for a harness that
refuses ESC on its own grounds.

What v2.0 does **not** do: it does not tell the agent *which* goal is undone (only the
task-level bit exists), it does not read inventory or pose, and it does not change the
shared hints. Expected effect is therefore bounded: the 0603-type cell stops burning 200
steps on ESC and is told to re-verify, but whether it then *finds* the missing item
depends on §4.

## 4. v2.1 — grounding (needs a decision on information channels)

These make the kinds checkable and are where the real gain should be; each gives the
hypothesis arm information the `default` arm does not render, so each is a declared
method component, not a patch. The harness already has all of it in `info` /
`milestone_status`; the change is `_agent_extra` for the hypothesis mode plus rendering.

- **Pose-grounded `location` hypotheses.** A location claim carries a spawn-relative
  target or a bearing (`"at": [dx, dz]` or `"bearing": "west"`); the harness renders, from
  the true position and yaw, "h3: ~12 blocks away, bearing west; you face south (yaw 0) —
  turn +90 to face it". This is the compass fix (BEHAVIOR §3.2: all prolong 0311 cells and
  c4h-hyp went west for east) done inside the method, and it gives `location` nodes a
  ground-truth distance history the harness can score (approaching / receding). *Cost*:
  yaw + a bearing computation the baseline never sees.
- **Inventory-grounded `state` hypotheses.** "the carpet is in my hotbar" is checked
  against `info["inventory"]` and auto-confirmed/refuted with the count; the mining hops
  (16 of 42 cells die there) get the one fact they lack. *Cost*: inventory as text — the
  same parity question as PRO-LONG R1 (audit §5).
- **Per-hop verification for `goal` nodes.** With per-hop status the goal rule becomes
  exact: hop 1's node is confirmed by the harness the step it fires, and a refused ESC
  locks *only* the undone hops. This is a protocol change (BEHAVIOR §5.2) that would
  apply to every arm; it is the single most valuable channel and the one that most needs
  the user's call.

Recommendation: adopt all three for the hypothesis arm and name the arm
`hypothesis-v2` (kinds + discipline + grounding); if attribution to the DAG itself is
ever needed, run a `default+grounding` ablation later rather than withholding grounding
from the method now. Under this reading `default` stays the fixed baseline the user asked
for, and the comparison becomes method-vs-baseline rather than prompt-vs-prompt.

## 5. v2.2 — later

- **Hypothesis-driven programs**: a plan step as an action program with `repeat` (what
  gave PRO-LONG its hop-1 speed, BEHAVIOR §3.5), each program bound to the hypothesis it
  tests and its expected `[STATE]` signature; the harness ends the program early when the
  prediction fails. Bigger change (per-step interface), only after 4.
- **Compact style** for the v2 prompt (the branch's `--response-style compact` already
  covers the hypothesis agent; v2's rules are in the shared block, so it applies).

## 6. What to run first (when a server is free — every GPU carries an unrelated training job as of 2026-08-19)

`hypothesis` v2.0 vs the finished `hypothesis` cells, one seed, Qwen3.5-27B (the checkpoint
where the failure was loudest), scenes **0603, 0763, 0306**:

- 0603: `esc_dropped` > 0 and locks appear after the first ESC attempt; steps after that
  attempt are spent moving/checking, not pressing ESC (compare 202 ESC-only steps); watch
  whether the agent re-checks the hotbar or walks back to the carpet.
- 0763: the pickaxe/pen cell — does the goal rule keep "mined the fence" from being
  declared, and does the test budget retire the "attack from here" mechanism?
- 0306: the sanity cell (4/4 reachable) — no regression in hop counts or step-to-hop.

Success for v2.0 is behavioural (ESC spam gone, locks acted on, budgets firing), not a
score claim; the score question waits for v2.1 and seeds. Cost per cell ≈ 300 steps ×
~4–14 s.

## 7. Non-goals

The `default` agent and its prompt; the shared movement/camera hints; scene repairs
(BEHAVIOR §4); the prolong arm (see the audit). Nothing here changes what the paper's
no-hint protocol lets an agent do.
