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
