# Findings

Record only findings that change a decision, hypothesis, implementation contract, or
interpretation. Link to exact code, run IDs, logs, artifacts, papers, or commits instead of
copying their full contents.

| date | finding | evidence | confidence | implication |
|---|---|---|---|---|
| 2026-08-18 | `find_rollout` was a stub, so every `prolong_vision_audit.json` reported view_image_calls=0 / image_attach_failures=0 as constants; real values for the five s0306 prolong seeds: 1 frame/turn, 0 attach failures, view_image 5/0/0/1/0, 0 compactions | rollouts under `~/.codex/runtime-home/sessions/2026/08/18/`; commit 33be080 | high | today's prolong runs were forced-vision as claimed; audits before 33be080 are not measurements |
| 2026-08-18 | the `codex` on PATH is a wrapper forcing CODEX_HOME=~/.codex/runtime-home; both codex arms carried the user's global AGENTS.md (9.3k chars) + ~40 skills (11k chars) in every request, and ran unsandboxed (`codex_sandboxed:false`) | rollout of s0306-prolong-codex-s2 turn 1; memory `codex-wrapper-forces-shared-codex-home` | high | s0306 runs of 2026-08-18 morning are a different arm from post-33be080 runs; do not pool without saying so |
| 2026-08-18 | default×codex with thinking off loops on `view_image`/PIL at the 20-frame steady state (69 requests / 420 s, ~25k tok each); a clean CODEX_HOME does not change it; 3-frame calls answer in ~37 s | probes 13:03 and 13:13 (scratchpad probe_default_codex, probe_clean_home) | high | arm dropped from this campaign (dz) |
| 2026-08-18 | vLLM 0.26 honours `max_new_tokens` (not `max_tokens`) in --override-generation-config and applies it to Responses too (`override_max_tokens`); `repetition_penalty` likewise | `vllm/config/model.py:1524`, `entrypoints/openai/responses/serving.py:197,434` | high | server-side 1024 cap for both channels; relaunched a227 13:49 with it |
| 2026-08-18 | codex_sandbox.sh works on helixon incl. plain-http proxying of the local model server: sandboxed prolong turn 15 s, resume 16 s, actions.json both, AGENTS.md msg 5.8k chars (no global instructions), ~10k input tok/request | scratchpad smoke_sbx rollout | high | campaign runs codex through the sandbox |
| 2026-08-18 | strict 4-hop set is 7 scenes: 0306 0726 0182 0311 0482 0603 0763 (depth 4, 0 free at spawn, action-space reachable, not satisfiable backwards); 5 of them score on inventory/voxel judges never exercised on this sandbox | `python scripts/screen_scenes.py --hops 4 --reachable --min-depth 4 --max-free 0 --no-backwards` | high | watch the first steps of those 5 for judge output |
| 2026-08-18 | 0311's `hunt_rabbit`/`hunt_donkey` are `count_in_box_at_most` and are pre-satisfied at spawn (mob count already ≤ max) in both arms, so the runner excludes them: 0311's ceiling is 2/4 for both arms | outputs/log-c4h-*-0311.txt "already satisfied at spawn"; bench_4hop7/0311 milestones.json | high | screen_scenes.satisfied_at_spawn only knows position rules; a static screen cannot see this — the runner's presatisfied check is the truth. Compare 0311 on its 2 position milestones |

