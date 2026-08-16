# Review handoff: PRO-LONG arm must receive vision unconditionally

Source: read-only correctness review by a separate Claude session (Fable 5) with dz,
2026-08-16. dz has made the design decision below; the code changes are yours to land
(this session is under a no-code-changes constraint).

## Decision (from dz)

The PRO-LONG arm should be "baseline agent + PRO-LONG memory mechanism": the analyzer
must be handed the current observation unconditionally, the way the baseline is handed
its frame buffer every step. Vision-on-demand is not information-matched.

Evidence this matters: in `prolong-gpt56-v3` (run 557a), the analyzer completed 8 turns
/ 57 steps with **zero** `view_image` calls (`codex_turns/*.events.jsonl`). The arm
navigates purely on [STATE] coordinates while the baseline is forced 20 frames per
step. Whatever score that produces measures "blind Codex + numeric trace", not the
memory architecture — and the second 0313 milestone (tripwire, indoors) is essentially
unreachable blind.

Fidelity argument, for the paper: upstream PRO-LONG's log contains the *full
observation* — every board is rendered as text into logs.txt, and the `log_window=-1`
variant embeds the current board directly in the prompt (`codex_agent.py:298,430-438`).
In the Minecraft port the observation is pixels and [STATE] carries only position, so
making pixels optional is a fidelity downgrade relative to upstream, not an equivalent.
Attaching the current frame restores upstream's "analyzer always has the observation"
property; the on-demand image viewer then covers *history*, which is what upstream's
grep-the-log covers too.

## Verified implementation path

`codex exec -i <FILE>...` attaches images to the initial prompt, and — checked against
the vendored binary 0.147 — **`codex exec resume` also accepts `-i`** ("attach to the
prompt sent after resuming"). So both the first and resume paths can carry the frame
without giving up conversation continuity. Repeat `-i` once per file (avoids the
variadic-swallowing issue that db33e60 fixed; prompt stays on stdin).

Suggested shape:
- `CodexTurn.run(prompt, images: list[Path])`; ProlongAgent passes the newest saved
  frame (`frames/step_NNNN.png` already exists at decision time).
- Optionally attach all frames since the previous turn (bounded by step_cap, typically
  5–15) for closer parity with the baseline's 20-frame buffer; the single newest frame
  is the cheap minimum for the local-Qwen arm.
- Turn prompt: say the current view is attached; keep the [FRAME] markers for
  history-on-demand.
- Report attached-image and `view_image` counts per episode next to milestone scores,
  so the vision channel is auditable in the comparison.

Comparability: v3 (2956637) and v4 (2956638) in flight measure the vision-optional
variant. Either supersede them or keep them explicitly labeled as a "vision-on-demand"
ablation in the ledger; do not average them with forced-vision runs.

## Other confirmed gaps from the same review (in priority order)

1. **No context-overflow recovery.** Upstream detects overflow-class errors and resets
   `session_id = None` so the next turn cold-starts on logs.txt
   (`prolong_agent/agent/codex_agent.py:207-221`). The port
   (`prolong_mc/codex_backend.py`) retries the same overflowed session forever; after
   an overflow every remaining step burns 3 doomed calls + 10 s. Attaching images per
   turn (above) accelerates context growth, so this fix should land together with it.
   Local-Qwen arm is most exposed.
2. **Duplicate log sections after a failed refill.** `mc_agent/prolong_agent.py` never
   clears `_last_entry` when `_refill` fails, so every subsequent `get_action` before a
   successful refill re-appends the previous [ACTION] section (same action_num,
   moved≈0.00, fresh duplicate frame file). Clear `_last_entry` after writing it.
   Tell in an existing run: duplicated `Action N |` headers in logs.txt.
3. **Ablation arms are prompt-only, upstream enforces them.** Upstream stateless
   deletes workspace files each turn keeping only logs.txt+AGENTS.md
   (`codex_agent.py:449-460`); upstream log_window replaces logs.txt with the truncated
   copy so the full log is not readable. The port only edits wording and leaves full
   logs.txt (and notes) in the visible workspace. Do not run arm C before enforcing
   both. (Keeping the codex session alive in stateless *is* upstream behavior — don't
   "fix" that.)
4. **`--resume` reruns a crashed scene into the same deterministic dir**, appending a
   second episode to the old prolong logs.txt (AGENTS.md write-once also skips).
   Guard: before trusting any prolong result, check logs.txt has exactly one
   `INITIAL STATE`; consider wiping `prolong_workspace/` when result.json is absent.
