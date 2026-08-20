# `q35a` statistics — the computed results, as data

Qwen3.5-27B, 4-hop, 2026-08-20/21. Regenerate with:

    python scripts/emit_stats_q35a.py [OUT]      # default experiments/stats_q35a

`outputs/` is gitignored — ~29 GB of episode video, frames and codex rollouts — so a number
that lives only inside a prose document cannot be re-checked without the storage volume. These
files are the statistics themselves. The prose reading of them is
[`../ANALYSIS_4hop_three_arms.md`](../ANALYSIS_4hop_three_arms.md); the protocol and headline
table are in [`../RESULTS_4hop154_q35a.md`](../RESULTS_4hop154_q35a.md); the per-cell record in
the campaign-wide format is `../4hop_cells.csv`.

**Coverage.** prolong 154/154; default 33/154 and hypothesis 20/154, both stopped by the a230
sandbox outage at 00:20 on 08-21. Every cross-arm figure is on the **20 scenes all three
share**, and 20 scenes is a pilot.

| file | rows | what it holds |
|---|---|---|
| `arm_summary.csv` | 3 | one row per arm: TSR and MSR in every convention, the stuck-class counts, medians for frozen / stalled / revisit / coverage |
| `per_cell.csv` | 207 | one row per cell: score, termination, all loop metrics, ESC presses, self-reported loops, GUI-limit mentions, analyzer turns |
| `per_scene_shared.csv` | 20 | the shared scenes with all three arms side by side, plus each arm's stuck class and the scene's milestone ids |
| `verb_success.csv` | 23 | milestone success by verb — this is where `craft` 0/109 lives |
| `prolong_retrieval.csv` | 18 | PRO-LONG's analyzer shell-command census: heredoc writes vs `tail` vs `grep`, grep hit rate |
| `paired_tests.csv` | 3 | per-pair W/L/T and the sign test on discordant pairs |

## Column notes that matter

**Three MSR conventions, because `trackable` is not a ceiling.** `msr_strict_pct` is
`completed / trackable` as the harness records it; `trackable` counts spawn-satisfied
milestones, and `eval_benchmark.py` never puts one in `completed`, so they sit in the
denominator unreachably. `msr_ceiling_pct` divides by `total - presatisfied` instead;
`msr_msr_pct` counts a spawn-satisfied milestone as met. On a matched set all three order the
arms identically.

**Two TSR conventions, for the same reason.** `tsr_strict_n` is `all_milestones_done` as
recorded, which any scene with a spawn-satisfied milestone can never earn.
`tsr_achievable_n` asks whether the agent got everything it could.

**`stuck_class`** in `per_cell.csv` is one of:

- `esc_deadlock` — ≥20 `ESC` presses. `eval_benchmark.py:541-566` refuses a premature ESC and
  offers no alternative, so the agent re-presses until the step budget ends. This is a harness
  behaviour, not an agent failure, and it is the worst freeze in both direct arms.
- `navigation_freeze` — ≥20 consecutive byte-identical poses, not ESC-driven.
- `pacing_loop` — ≥95 % of steps on already-visited blocks without freezing.
- `clean` — none of the above. Note that "clean" cells still spend ~78 % of steps moving
  <0.25 blocks; the classes only pick out the extremes.

**`turns_without_action`** (prolong only) counts analyzer turns that wrote no `actions.json`,
the 1024-token truncation loop. 2,342 of 7,594 campaign-wide, concentrated in 3 cells.

## What is not here

`per_cell.csv` covers everything derivable from `result.json` plus the runner log. Reproducing
the loop and retrieval columns from scratch needs what stayed on the storage volume:
`outputs/log-q35a-*.txt` (65 MB) and, for the PRO-LONG command census,
`outputs/q35a-prolong-codex-*/…/prolong_workspace.codexhome/` (1.3 GB).
