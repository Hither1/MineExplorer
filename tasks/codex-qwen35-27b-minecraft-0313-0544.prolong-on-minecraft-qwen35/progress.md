# Progress: prolong-on-minecraft-qwen35

## 2026-08-15 — task opened, design specified, nothing executed

- Read PRO-LONG end to end (3.1k LoC) at `acbdbf3`; clone kept in the session scratchpad,
  not vendored into this repo yet.
- Established the port surface (findings 1-3) and the two hard constraints:
  no Docker on DeltaAI, and both scenes score purely on position+facing (finding 6).
- Specified arms B (headline, information-matched to the baseline), A (voxels, diagnostic
  only), C (PRO-LONG's own log-window ablation).
- No code written, no GPU time spent. Phase 1 gate test G1 not yet run.
- Predecessor task `…rebuild-minecraft-sandbox-arm64` supplies the sandbox and the
  baseline number to compare against: `Milestones 1/4 (25.0%)` on 0313+0544 under
  `MILESTONE_HINT=0 MAX_STEPS=300`, run `20260815-210755-qwen35-0313-0544-scored-33ea`.

## 2026-08-15 — G1 gate: three interface bugs, then a clean split verdict

Four attempts, each blocked by a different interface detail rather than by the model:

| run | job | outcome |
|---|---|---|
| v1 `…-gate-1d37` | 2956208 | `wire_api = "chat"` no longer supported by codex 0.147 |
| v2 `…-v2-42ef` | 2956224 | 422 on `client_metadata`; model never consulted |
| v3 `…-v3-30c4` | 2956251 | **operator error, not a result** — see below |
| v4 `…-v4-5b52` | 2956276 | rerun of v3, in flight |

Fixes landed along the way: `scripts/serve_qwen_for_codex.py` (drop-and-log unknown
request fields), model id read back from `/v1/models`, `-s workspace-write` per the
isolation decision, and `< /dev/null` so batch stdin is not appended to the prompt.

**v3 was my mistake.** I edited the gate script while the job was executing it, believing
`mv` to be atomic. `/tmp` is local xfs and the repo is on NFS, so the cross-filesystem
`mv` was `open(O_TRUNC)` + copy on the *same inode* the running bash had open; bash's read
offset landed in rewritten content and the script ended silently at exit 0. Evidence: the
server log shows exactly one `/health 200` and no `/v1/models` at all. Rule going forward:
never modify a script a Slurm job is running — copy it, or wait.

**Hosted reference arm passes both gates** (finding 19), which is the useful outcome of the
evening: the de-Dockered codex invocation, the bubblewrap sandbox and the oracle are all
verified, so the local arm now tests only the model and the local wire.

## 2026-08-16 — the matrix, four self-inflicted defects, and the vision fix

The PRO-LONG port runs as an agent mode inside `eval_benchmark.py` (`--agent-mode prolong`),
so the episode loop, the frame buffer, `MilestoneChecker` and the video are the baseline's;
only the memory mechanism differs. The matrix under test is
{Qwen3.5-27B, gpt-5.6} × {vLLM, codex} × {default, hypothesis, prolong} × {0313, 0544, 0802}.

**Four defects tonight, all of which produced healthy-looking runs.** Listed in
findings 26–28 and 30; the operational lesson is that each was invisible from the
outside and each was caught by an invariant, not by reading logs:

- variadic `--image` swallowed the prompt → 73 no-op steps
- `codex exec resume` rejects `-s` → 55 analyzer turns, one plan
- shared-node port collision → scored against another job's un-shimmed server
- PRO-LONG ESC wording differed from the baseline's → episodes ended at step 17

Three of these were mine, and two came from the same habit: editing files that running
jobs were reading. `scripts/snapshot_exec.sh` now copies the whole `scripts/` directory
into the run's artifact dir and execs the copy, so a live edit cannot reach a running
job and the exact code that ran sits beside its results. Its own first version copied a
single file and killed a run whose script called a sibling — fixed, with the copy
guarded by a marker so the nested invocation cannot overwrite the file bash is reading.

**The vision fix (finding 30).** The analyzer now gets the current frame every turn,
including on resume. Landed with the overflow-recovery gap (finding 32), the duplicate
log section after a failed refill, and a guard that moves a crashed scene's workspace
aside instead of appending a second episode to its append-only log. 63 selftest checks.

**Open decision for dz — the Qwen arm quits (finding 31).** Qwen presses ESC within
1–13 steps in every default/hypothesis cell, so those cells cannot measure memory
architecture at all; PRO-LONG's plan queue happens to shield it, which biases the
comparison in PRO-LONG's favour for the wrong reason. Three options, none free:

1. Report as-is. Honest, but the Qwen half of the matrix answers nothing about memory.
2. Ignore agent ESC entirely and always run to `max_steps`. No oracle leakage,
   symmetric across arms, scoring is unaffected (milestones are checked from `info`
   every step). Costs a full 300 steps per episode.
3. Enable `--milestone-hint`, which rejects premature ESC. Cheapest, but it feeds the
   agent ground truth and changes the prompt for every arm.

My recommendation is (2): it is the only one that leaks nothing and treats both models
identically. It needs dz's call because it changes the protocol.

### Runs in flight at handoff

| cell | run id | note |
|---|---|---|
| prolong gpt-5.6 forced-vision 0313/0544 | `20260816-003135-…-01e3` | the arm the paper claims |
| prolong Qwen forced-vision 0313/0544 | `20260816-003144-…-1758` | |
| prolong gpt-5.6 forced-vision 0802 | `20260816-003158-…-1638` | 0802 is the sharp scene (finding 29) |
| prolong Qwen forced-vision 0802 | `20260816-003200-…-6c31` | |
| Qwen default via codex 0313/0544 | `20260816-003512-…-5d44` | third attempt; v1 edited mid-run, v2 lost its sibling script |
| prolong v3/v4, 0802 prolong ×2 | earlier ids | vision-on-demand ablation, labelled in `RUN_LEDGER.txt` |

`RUN_LEDGER.txt` (moved out of the ignored `artifacts/` tree) is the authority on which
runs may be compared; `scripts/compare_runs.py` reads it and reports VARIANT rows under
their own label instead of dropping them.

## 2026-08-16 (early hours) — serving layer rebuilt, matrix held

dz's calls this session, in order: use the hint protocol; kill the affected queued
jobs; **stop running the matrix until the serving layer is verified** ("不要一次跑很多
但是又有各种系统性问题得不偿失"); serve with vLLM rather than transformers; and
**test Qwen3.8-27B, not 3.5**.

All 14 queued hint-protocol cells are cancelled. Two no-hint runs finish out.

### Why the serving layer had to change

Each evaluation job ran its own `transformers serve`: 52 GB of weights per job, no
paged KV cache, and a shim so the Codex CLI's requests were accepted at all. It
produced finding 37 — a PRO-LONG run losing 7 of 15 analyzer turns to allocator
fragmentation, not capacity.

vLLM 0.27.1 replaces it: aarch64 wheel, `Qwen3_5ForConditionalGeneration` in its
registry (the architecture *both* 3.5 and 3.8 declare), and a native Responses API —
the one codex speaks. sglang 0.5.10 is installed here too and its
`/v1/chat/completions` handles Minecraft frames correctly, but its `/v1/responses`
echoed structured content blocks back as literal Python dicts, so it cannot drive
codex. It stays as a fallback for the plain-VLM arms.

New pieces: `scripts/serve_vllm.sh` (one long-lived server that verifies what it
serves before advertising, and removes only its own advert) and
`scripts/use_model_server.sh` (resolves the advert, then asks the server what it
actually holds — a URL resolving is not the same as the right model answering, which
is exactly how two runs were scored against a stranger's process).

### Verification ladder before any matrix

Nothing scales until each rung passes, because tonight's pattern is that a
systematic fault looks healthy from outside:

1. server advertises, `/v1/models` reports Qwen3.8-27B — job `2957109`
2. `chat/completions` answers text, and answers with a Minecraft frame attached
3. G1 gate: codex drives it through `/v1/responses` and writes a valid `actions.json`
4. one 40-step default episode on 0313, hint protocol, end to end
5. one 40-step PRO-LONG episode
6. only then the matrix, staged rather than fanned out

### Also fixed

`BACKEND` is a name the research harness itself exports (finding 39). The Qwen3.8
gate was launched with `BACKEND=local` and silently ran the *hosted* gpt-5.6 arm
while reporting PASS. Renamed `GATE_BACKEND`. An env-propagation probe confirms the
transport is fine — `MILESTONE_HINT` and friends do reach the job — so the matrix's
protocol flags were never at risk.

### Discovery layer verified before the server exists (2026-08-16 ~02:00)

`use_model_server.sh` exercised against the live sglang server on gh056:8002, no GPU
needed, all five paths behaving:

| case | result |
|---|---|
| live server, model matches | URL on stdout, rc=0 |
| caller expects a different model | refused |
| advert points at a dead port | refused ("stale file from job …?") |
| advert lies about what the server holds | refused |
| no advert at all | refused after the wait |

The fourth case is the one that cost two runs tonight — a readiness endpoint
answering from a stranger's process. It now fails closed. Cross-node reachability is
confirmed by the same test (login node → gh056).
