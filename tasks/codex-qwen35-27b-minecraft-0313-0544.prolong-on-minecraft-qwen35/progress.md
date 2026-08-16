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
