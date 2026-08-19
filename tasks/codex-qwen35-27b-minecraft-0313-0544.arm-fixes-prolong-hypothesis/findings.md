# Findings: arm-fixes-prolong-hypothesis

| # | date | finding | evidence | confidence | implication |
|---|---|---|---|---|---|
| 1 | 2026-08-19 | The prolong port is faithful in contract but the paper's mechanism is unused: 0 python, 0 notes, 24 grep, 463 tail over 497 turns; 70 turns wrote a plan without reading the log. Paper: python 60.6 % / log parsing 20.3 % / workspace 19.1 %; Fable-5 release episode: 45 python in 22 turns + notes.md. | events.jsonl of the 14 cells; upstream release_logs | high | The arm measured a plan-queue agent with a sliding text window; its lead is granularity, not memory. |
| 2 | 2026-08-19 | Three upstream progress mechanisms were missing: `Score:` per header, queue flush on score change, briefing in the log. c4h-0306 completed at step 52 and ran plans to 300 (21 more turns). | logs.txt line 387 vs turn 6 `tail -20` | high | Landed as R2 (task-level) + R3; per-hop needs the protocol decision. |
| 3 | 2026-08-19 | The paper's control (same agent, no log) did not exist in the port; `default×codex` stalls. | prompts.py had no -1 mode | high | Landed `--prolong-log-window -1`. |
| 4 | 2026-08-19 | q35-hypothesis-0603: after the ESC refusal at step 98 the model re-confirmed h1–h4 at 1.0 on every step 99–300 and pressed ESC 202 times, rationalising the NOT-verified line as "a trigger or delay". | outputs/log-q35-hypothesis-vllm-0603.txt | high | Goal confirmation must be environment-owned and locked after a refused ESC — v2.0. |
| 5 | 2026-08-19 | prolong_mc/selftest.py had been failing since run_codex replaced subprocess.run (KeyError at the provider argv check, hiding 8 later failures). | selftest run 13:00 | high | Mocks retargeted; run the selftest after every backend change. |
