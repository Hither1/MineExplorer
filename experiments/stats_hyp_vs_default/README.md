# `hypothesis` vs `default` on 4-hop — the computed statistics

Qwen3.5-27B, campaign `q35a`, the 20 scenes every run covers. Regenerate with:

    python scripts/hyp_vs_default.py [OUT]      # default experiments/stats_hyp_vs_default

The prose reading is [`../ANALYSIS_hypothesis_vs_default.md`](../ANALYSIS_hypothesis_vs_default.md).
`outputs/` is gitignored, so these files are the statistics themselves.

**Four runs, and the fourth is the point.** The hypothesis agent ran the 4-hop set twice in this
campaign — `legacy` (28 cells, stopped when the prefix-cache diagnosis moved the direct arms) and
`append-only` (20 cells). Both cover all 20 shared scenes, so the same agent's run-to-run spread
can be measured against the gap it is being asked to explain. It is the same size.

| file | rows | what it holds |
|---|---|---|
| `report.md` | — | the four sections as the script prints them |
| `paired_scores.csv` | 6 | one row per arm pair: sums, mean per-scene difference, W-L-T, sign test |
| `geometry.csv` | 147 | one row per (run, position milestone): closest approach, best facing while inside the radius, and `why` it was missed — `never_near` or `near_never_faced` |
| `behaviour.csv` | 60 | one row per (run, scene): action mix, ESC actions, reply size, yaw swept, blocks walked |
| `discipline.csv` | 48 | one row per hypothesis cell-run: the agent's own counters (reverted goal confirmations, dropped ESC, staleness) plus the final graph's kind/status census |

## Column notes that matter

**`why` in `geometry.csv`.** `position_near_with_facing` reads no frame and no agent claim: it
fires when the player is inside `max_distance` of a spawn-relative coordinate and yaw is within
`facing_tolerance/2` (`benchmark_gen/utils.py:84`). So an unearned find_* milestone splits into a
navigation failure (`never_near`) and a camera failure (`near_never_faced`), and the split is
computed from the runner log's own `player_pos` line, not from anything the model said.

**`goal_confirm_reverted` in `discipline.csv`** counts the times the model marked a task goal
`confirmed` while the environment status said NOT verified — 653 over 48 cell-runs. It is an
instrument that only exists in the hypothesis arm, so it documents that arm's belief error but
cannot compare it to `default`. The comparable measure is `esc_actions` in `behaviour.csv`.

**ESC cross-check.** `behaviour.csv` counts ESC from the actions parsed out of the runner log;
`discipline.csv` counts them from the agent's own `hypothesis_discipline.json`. They agree
exactly (296 append-only, 53 legacy, over the shared 20), which is the check that the log parse
recovers every step.
