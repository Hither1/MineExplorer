# Is our `prolong` arm the PRO-LONG of the paper? A fidelity audit

Companion to [BEHAVIOR_helixon_4hop.md](BEHAVIOR_helixon_4hop.md). That file found *what*
the three arms do on the strict 4-hop set. This one answers a narrower question the
findings raised: **does `mc_agent/prolong_agent.py` + `prolong_mc/` implement the idea of
PRO-LONG (Fox, Wang, Rosu, Dhingra — arXiv 2607.20064, code
github.com/alexisfox7/PRO-LONG, built for ARC-AGI-3), or something else that happens to
share its file names?** The upstream code (commit on `main` as of 2026-08-19, fetched to a
scratch dir) and one released Fable-5 episode (`release_logs/fable5/ar25/rep1`) were read
next to our port and next to the 14 finished prolong cells (`outputs/{c4h,q35}-prolong-codex-*`).

Verdict in one paragraph: **the harness contract is ported faithfully — actions.json,
plan queue, append-only log with the same separator, AGENTS.md system prompt, resumed
codex session with cold start on overflow, sandboxed tools including Python, the
log-window and stateless ablations — but the *mechanism the paper credits* is not
exercised, for three reasons that stack.** (1) The paper's log carries the full
observation as text after every action (a lossless 64×64 board); ours carries five numbers
(`pos`, `pitch`, `yaw`, `moved`) and a path to a PNG, so there is almost nothing in the log
worth parsing programmatically. (2) Three upstream mechanisms that make *progress* salient
and interrupt a stale plan are missing: `Score:` in every action header, queue flush +
re-analysis on score change, and the agent's own briefing written into the log. (3) With a
27B model the coding agent does not reach for the tools the paper's gains come from: over
497 analyzer turns there were **0 Python calls, 0 note files, 24 grep/sed/awk, 463 `tail`**,
and 70 turns wrote a plan without reading the log at all — against Python 60.6 % / log
parsing 20.3 % / workspace 19.1 % of tool calls in the paper (Table 3), and 45 Python calls
in 22 turns in the released Fable-5 episode. What our arm measured is therefore "a
plan-queue agent with a sliding text window and a resumed conversation", and its
advantage over the direct arms (26 vs 20–21 of 56 milestones) came from plan granularity,
not from programmatic memory. Section 5 lists the fixes in order; the first two need a
protocol decision because they change what the arm is told relative to the fixed baseline.

## 1. What PRO-LONG is, reduced to checkable mechanisms

From the paper (§Method, Tables 1–3, Appendix) and the upstream code:

| # | mechanism | where upstream does it |
|---|---|---|
| M1 | **Complete, structured log.** Every action appends a section: `Action N \| Level \| Attempt \| Plan Step i/T \| Score: S`, the agent's `[PLAN]`, `Tool Call: ACTIONx(...)`, and the **full observation as text** (`[POST-ACTION BOARD STATE]`, 64×64 chars) — 266 boards for 266 actions in the released episode. | `environment/runner.py:322-330, 488-513`; `swarm.py:58,280` (`log_post_board=True`) |
| M2 | **Coding agent told to parse the log programmatically**, with Read/Write/Edit/Bash/Grep/Glob and Python in a sandbox. Table 1: Read-only 23.1 % → +grep 27.2 % → +Python 38.3 % → +Write/Edit 41.2 % (GPT-5.5): *"increasing programmatic control over logs … lead[s] to improved performance"*. | `agent/prompts.py:52-58`; docker sandbox |
| M3 | **Persistent workspace** for notes/scripts. Table 2: clearing it costs PRO-LONG 0.5 pt but the no-log agent 4 pts — the log, not the notes, is the memory. | `codex_agent.py:449-460` (stateless deletes all but `logs.txt`, `AGENTS.md`) |
| M4 | **Plan queue**: `actions.json` = 1–15 actions; *"prefer short lists (1–2) when testing a new hypothesis … scale up for proven sequences"*; analyzer fires when the queue is empty; up to 5 retries with a nudge, then exponential back-off forever (never a silent no-op). | `prompts.py:74`; `runner.py:106-135, 270-296` |
| M5 | **Progress interrupts the plan.** `Score:` is in every header; a score change **flushes the remaining queue** and re-fires the analyzer; the game ends at `WIN`. | `action_queue.py:55-62`; `runner.py:113-114, 313, 335-375` |
| M6 | **The agent's analyses live in the log.** The briefing text is written once as a `[PLAN]` block and the 2–3-sentence plan is repeated in **every** action section until the next analysis (*"your own prior analyses"* is part of the log's definition). | `game_state.py:26-62`; `runner.py:457-458, 497-508` |
| M7 | **One codex session per game**, `codex exec resume` on every later turn; overflow → drop the session, cold-start on `logs.txt`; codex has no compaction. | `codex_agent.py:207-221, 381-406, 476-486` |
| M8 | **Ablations**: `--log-window N` copies a truncated log into the sandbox (the full log is not there), `--log-window -1` = *no log, current board in the prompt* (the paper's "No-Log" control), `--workspace stateless`. | `base.py:33-51`; `codex_agent.py:295-333, 336-380, 417-424, 449-460` |
| M9 | **The paper's comparison** is PRO-LONG vs the *same coding agent* with the board in-prompt and no log (+18.0 pp avg), and vs published harnesses on cost (4.2–5.8× fewer tokens). | paper §Results |
| M10 | **Regime**: frontier models (GPT-5.5, Opus 4.6, Fable 5), lossless textual observations, and gains concentrated on games *"where the current board does not fully determine the game dynamics"*; minimal gain where it does (ft09). | paper §Analysis, Fig. 3 |

Reference episode for "what a competent agent does with this": Fable 5 on ar25 (rep1),
22 analyzer calls, 64 bash calls = **45 Python, 14 cat/head/wc, 5 grep**, plus `notes.md`
written once and edited 6 times; the notes contain a coordinate-level model of the board
and the plans cite it.

## 2. Mechanism-by-mechanism: upstream vs. our port vs. what the 14 cells show

| # | upstream | our port | evidence in our runs | verdict |
|---|---|---|---|---|
| M1 log content | full observation as text after every action | `[STATE] pos=(x,y,z) pitch yaw moved` + `[FRAME] frames/step_N.png`; no inventory, hotbar, held item, health, water, or block under crosshair, although `info` carries inventory (the `inventory_has` rules score from it) | the analyzer `tail`s 10–30 lines (median 20 = the last 2–3 sections) and reads pixels from the one attached frame; the 16/42 cells that die on a mining hop never know what is in hand (BEHAVIOR §3.1) | **domain-forced deviation, but under-ported**: what *is* text-representable in `info` is not logged. Fix R1. |
| M1 header | `Score:` and `Plan Step i/T` in every header | `Action N \| Step S`; tick index inside the Tool Call line; **no progress field** | `[MILESTONE]` appears twice in a 300-action log (c4h-0306: line 17 "NOT verified", line 387 "HAS verified"); no cell ever grepped it (3 turns in q35 mention it) | **missing**. Fix R2. |
| M5 flush on progress | score change flushes the queue, analyzer re-fires immediately; game ends at WIN | no flush; `[MILESTONE]` written on change only; episode ends only on the agent's ESC | c4h-0306 completed 4/4 at step 52 and drained plans to step 300 (21 more analyzer turns); the "HAS verified" line was ~10 sections above the `tail -20` of the next turn (step 63) and never read | **missing**. Fix R2. |
| M6 analyses in the log | briefing once + `[PLAN]` repeated every section | only the `[PLAN]` block (or the last 400 chars) once, in the next section (`prolong_agent.py:_refill`, `log.py:write_action`) | reasoning persists only in the resumed conversation; after an overflow reset it is gone; `grep PLAN` yields 2–3-sentence plans (BEHAVIOR §3.6) | **missing, cheap**. Fix R3. |
| M2 tools | Read/Write/Edit/Bash/Grep/Glob + Python; "parse programmatically" | same tool surface (`exec_command`, `apply_patch`, `view_image`), Python asserted in the sandbox (`sandbox_selftest.py:230-236`); prompt says "parse it programmatically" | **0 python, 0 notes, 24 grep/sed/awk, 463 tail, 10 cat/head, 503 `cat > actions.json`, 6 view_image over 497 turns; 70 turns (63 Qwen3.5) wrote a plan without opening the log** | faithful surface, **unused mechanism** (see §3) |
| M3 workspace | notes/scripts accumulate | same (persist; stateless deletes) | 0 files in 14 workspaces besides `AGENTS.md`, `logs.txt`, `actions.json`, `last_message.txt` | faithful, unused |
| M4 queue | 1–15 actions, 1 tick each; 5 retries + back-off | 1–15 entries × `repeat` ≤ 20, ≤ 40 ticks/plan; 3 retries then a **no-op step** | steps/turn 11.1 (Qwen3.8) and 5.8 (Qwen3.5); repeat=20 sprint programs overshoot 4-block targets (BEHAVIOR §3.5) | adaptation is right for Minecraft; retry semantics differ (minor, R6) |
| M7 session | resume; overflow → cold start | same, plus a compaction counter that must stay 0 (`prolong_vision_audit.json`) | overflow_resets 0, compactions 0 in all 14 cells | **faithful** |
| M8 ablations | window copy in a separate sandbox; `-1` = No-Log control; stateless | window/stateless enforced via `EpisodeLog.publish` (record dir vs. visible dir); **no `-1` No-Log mode** | not run in these campaigns | faithful for 0/N/stateless; **the paper's control arm is missing** (R5) |
| M9 comparison | same agent ± log | `prolong×codex` vs `default×vllm` (different agent loop, different channel; `default×codex` stalls at any frame count) | — | **not the paper's comparison**; R5 makes it available |
| observation to the analyzer | none beyond the log (text) | current frame attached to every turn (`-i`), earlier frames on disk | frames_attached == turns in all cells; view_image 6/497 | deliberate deviation (finding #30), justified: the observation is pixels |
| system prompt | ~30 lines, "briefing then [PLAN]", "prefer 1–2 when testing" | same skeleton + the baseline's action reference and ESC paragraph verbatim; `[MILESTONE]` documented only under the hint protocol | — | faithful in structure; ESC/verification wording is our protocol, not the paper's |
| sandbox | docker, `danger-full-access`, egress allow-list | bwrap, `workspace-write`, per-episode `CODEX_HOME`, `SAFE_CODEX_FLAGS` (no web, no connectors, no sub-agents) | selftest 43 checks | faithful in threat model, stricter |
| M10 regime | frontier coding agents, textual boards, history-dependent dynamics | Qwen3.5/3.8-27B, pixels + 5 numbers, tasks whose next action is mostly determined by the current view and position | the arm's failures are mining/aim, compass, false completion (BEHAVIOR §3.1–3.3), none of which is a retrieval failure | **outside the paper's regime** on all three axes; §4 |

## 3. Why the mechanism has nothing to bite on here (diagnosis)

1. **The log is not the observation.** In ARC the board *is* the world and it is lossless
   text; the paper's whole argument is that a coding agent can search a complete textual
   history better than a context window can hold it. Our log's information per action is
   `pos/pitch/yaw/moved`; the world is in `frames/*.png`, which is not greppable, and the
   analyzer looked at old frames 6 times in 497 turns. A `tail -20` reproduces everything
   the log has to say about the recent past, so `tail` is the *rational* tool here — the
   agents were not lazy, the log was thin. This is the same fact as finding #30 (the arm
   was navigating blind) seen from the other side: after forced vision, pixels do the
   perceiving and the log only does the odometry.
2. **The parts of `info` that are text were left out on purpose.** The port was designed
   to hold information equal to the baseline (task plan, "arm B adds no information"), so
   inventory/hotbar/held-item — which the baseline can only read off pixels — were not
   logged. That was the right call for a *single-variable* comparison against `default`;
   it is the wrong call for *fidelity*, whose premise is "log everything the environment
   returns, as text". The two goals conflict and only the user can rank them (§5, decision).
3. **Nothing in the log says "you made progress" or "you are done".** The paper's agent
   sees `Score:` on every line it tails, and the runner cuts a plan short the moment the
   score moves. Ours buries a task-level yes/no in a `[MILESTONE]` line that changes twice
   per episode, and lets a 40-tick program finish after the environment has verified
   completion. Per-hop progress is not written anywhere (the harness has it in
   `milestone_status`, but no arm receives it — BEHAVIOR §5.2).
4. **The model.** Qwen3.5-27B on the same prompt wrote plans without reading the log in
   63 of 320 turns and replanned every 5.8 steps; Qwen3.8 read the tail every turn. Neither
   wrote a script or a note. The paper's ablation says notes are dispensable *for its
   models*; whether a 27B model would benefit from being made to write them is untested.
   The hosted gpt-5.6 arm exists (task findings #19, #34) and is the way to separate "port"
   from "model": on 0313/0802 it solved 3/3 under no-hint, but it has not run on the
   4-hop set.

## 4. What this means for the claim

- The prolong arm's lead on the 4-hop set (26/56 vs 21 and 20) is real as an observation
  but it is not evidence *for programmatic memory*: the mechanism was not used. BEHAVIOR
  §3.5 attributes the lead to plan granularity (hop-1 median step 10.5 vs 29.5/17.5) and
  to making fewer per-tick decisions that can go wrong; the same section shows the cost
  (overshoot, pacing).
- A faithful port would not fix the arm's dominant failures. Mining/aim (16/42 cells),
  compass errors (all prolong 0311 cells went west), and false completion are perception,
  mechanics and calibration problems that no amount of log search recovers. What fidelity
  *would* buy is bounded: R2 removes the wasted post-completion steps and gives hop
  progress; R1 gives the mining hops the one fact (what is in hand) they lack; R3 makes the
  memory survive an overflow.
- The paper-faithful comparison for a "does PRO-LONG's memory help on MineExplorer" claim
  is `prolong` vs `prolong --log-window -1` (same codex agent, same frame, no log) — R5 —
  not `prolong×codex` vs `default×vllm`, which changes the agent loop, the channel and the
  frame count at once. The current pairing answers "does our plan-queue codex arm beat the
  20-frame vLLM baseline", which is a fine question but a different one.

## 5. Recommended changes, in order

Each is small; the tests are 1–2 scenes × 1 seed once a server is up (every GPU carries an unrelated training job as of 2026-08-19 12:40, so nothing below
has been run against a model).
**Landed in this commit, covered by `prolong_mc/selftest.py` (167 checks):** R2 in its
task-level form, R3, R5 and R6. R1, per-hop R2 and R7 wait for the decisions named.

- **R1 — log the whole text-representable observation** in `[STATE]` (upstream M1):
  hotbar contents with the selected slot and held item, inventory as `name:count`, and the
  per-action inventory delta (`+1 white_carpet`), plus health/food/in-water if `info` has
  them. *Fidelity gain: this is the "board".* *Cost: breaks information parity with
  `default`, which only sees the hotbar in pixels — a decision, not a patch.* Test: 0763,
  0603 — does the analyzer select the pickaxe slot before its first mining program, and
  does the mined carpet show up in its next plan?
- **R2 — make progress salient and interrupting** (upstream M5): put the verification
  state in **every** action header (`| Verified: 2/4` under the hint protocol; per-hop ids
  if the protocol allows it, else the task-level yes/no we already give), and **flush the
  queue and re-fire the analyzer when it changes**. The task-level version is
  decision-free (it is the same bit the arm already receives, written where `tail` sees
  it); the per-hop version is the same protocol decision as BEHAVIOR §5.2. Test: c4h-0306
  should ESC within a turn of step 52 instead of at 300; hop counts should not fall.
  *Landed (task-level):* header `Action N | Step S | Plan Step i/T | Verified: yes/no`
  (`prolong_mc/log.py`), flush + re-plan on change (`ProlongAgent.get_action`),
  `plan_flushes` in `prolong_vision_audit.json`, marker documented in the system prompt.
- **R3 — write the briefing into the log once and the `[PLAN]` into every section**
  (upstream M6, `consume_hint_block`). Decision-free. Test: `grep -c PLAN logs.txt` ≈
  action count; a cold start after a forced overflow still knows what it concluded.
  *Landed:* `EpisodeLog.set_plan(plan, briefing)`, `CodexTurn.split_briefing`.
- **R4 — do not do the parsing for the agent.** BEHAVIOR §5.5 suggested a runner-side
  parsed summary of the last N `[STATE]` lines in every prompt. That is an *assist* the
  paper does not give (the paper's agent computes such things itself, and Table 1 credits
  the computing); if it is added it should be named as a departure (`prolong-assisted`)
  and never pooled with the faithful arm. Recommendation: hold it until R1–R3 and R5 have
  been measured.
- **R5 — port the paper's No-Log control** (`--prolong-log-window -1`, upstream M8/M9): no
  `logs.txt`; the current `[STATE]` line and the current frame in the prompt; workspace
  persists; same codex session semantics. Then the memory-architecture effect is
  `prolong` − `prolong-nolog` within one channel and one model — the paper's own contrast —
  and `default×vllm` stays what it is, an external baseline. Cheap: the frame is already
  attached, `-1` is a prompt-and-publish switch. *Landed:* `SYSTEM_PROMPT_NOLOG` +
  `NOLOG_*_PROMPT` (`prolong_mc/prompts.py`), `EpisodeLog.publish(window=-1)` removes
  the log and every frame but the current one, `ProlongAgent._state_text` carries
  `[STATE]`, `Verified:`, action count and last action into the prompt.
- **R6 — retry semantics**: five nudged attempts instead of three, then the existing
  no-op tick (upstream M4 backs off forever, which would hang an episode here). *Landed:*
  `analyzer_retries=5`.
- **R7 — one gpt-5.6 (hosted) prolong run on the seven scenes** as the capability
  ceiling: if it uses Python/grep/notes and reads the `[MILESTONE]` line, the gap is the
  model; if it also `tail`s and never parses, the log is the problem. Cost: API dollars
  and 150 KB/s egress (text only, fine); a decision.
- Keep as they are (verified faithful or justified): session/resume/overflow handling,
  sandbox and tool surface, ablation enforcement, forced current frame, `repeat`/step cap,
  the ESC/verification wording (a protocol choice made deliberately in finding #28).

Not recommended: dropping the codex channel or reimplementing the loop against
`/v1/chat/completions` (task-plan fallback). The channel is faithful; the thinness of the
log and the model's habits are the findings, and R1–R5 address them inside the same harness.

## 6. Numbers behind §2–3 (how they were obtained)

Tool profile: every `item.completed`/`command_execution` event in
`outputs/{c4h,q35}-prolong-codex-*/**/codex_turns/turn_*.events.jsonl` (timeouts excluded),
classified by regex (`python|python3` → python; `grep|rg|sed|awk`; `tail`; `head|cat|wc`;
a heredoc/echo/tee into `actions.json` → write). 497 turns, 1001 commands: write 503, tail
463, head/cat 10, grep/sed/awk 24, ls 1, python 0. `tail -N` sizes: N=10 60×, 15 79×,
20 126×, 25 38×, 30 112×, 40 29×, ≥50 19×. Turns with no read of the log: 70 (c4h 7,
q35 63). Workspace files from `prolong_workspace_files.txt`; view_image and overflow
counts from `prolong_vision_audit.json`. Upstream episode profile from
`release_logs/fable5/ar25/rep1/logs_analyzer.txt` (`[TOOL USE: …]` blocks) and
`workspace/notes.md`. Paper figures quoted from arXiv 2607.20064v2 (Tables 1–3, §Method).
