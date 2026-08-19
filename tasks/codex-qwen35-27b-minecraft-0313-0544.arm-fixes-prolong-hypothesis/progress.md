# Progress: arm-fixes-prolong-hypothesis

- 2026-08-19 12:30 direction from dz: default fixed; audit prolong vs paper; optimize hypothesis.
- 12:35 fetched upstream PRO-LONG code + one Fable-5 release episode; measured our 14 prolong cells'
  tool use (0 python / 463 tail / 24 grep / 0 notes over 497 turns).
- 12:50 wrote experiments/PROLONG_FIDELITY_AUDIT.md.
- 13:00 landed prolong R2 (task-level) / R3 / R5 / R6; fixed the selftest's stale subprocess.run mocks
  (broken since run_codex landed); 167 checks pass.
- 13:02 branch merged by dz (speedup branches); re-read merged hypothesis_agent.py before patching.
- 13:20 landed hypothesis v2.0 + mc_agent/hypothesis_selftest.py (32 checks).
- 13:35 design doc + Chinese versions; task record; commit.
