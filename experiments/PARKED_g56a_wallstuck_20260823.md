# g56a arm-1 wall-stuck cells, parked 2026-08-23 ~01:40

Hosted resumed-session latency grows past the 1500s ceiling once the session
is deep enough; these cells entered a timeout-retry loop that cannot reach 200
steps (each timed-out call still burns the full resume payload server-side).
Killed at the recorded step; partial trajectories remain in outputs/. Scenes
count as NOT run for any rerun (no result.json). Policy decision pending:
truncate-and-score / stateless rerun / drop.

| cell | age_h | step | milestones | timeouts |
|------|-------|------|------------|----------|
| 0073 | 25 | 87 | 1/4 | 88 |
| 0267 | 15 | 86 | 0/4 | 14 |
| 0093 | 23 | 97 | 2/4 | 81 |
| 0232 | 16 | 103 | 3/4 | 16 |
| 0294 | 13 | 73 | 2/4 | 12 |
| 0274 | 15 | 81 | 1/4 | 13 |
| 0097 | 23 | 60 | 0/4 | 82 |
| 0078 | 23 | 113 | 1/4 | 84 |
| 0295 | 12 | 83 | 2/4 | 10 |
| 0239 | 16 | 128 | 2/4 | 16 |
| 0184 | 18 | 80 | 1/4 | 21 |
| 0058 | 25 | 120 | 2/4 | 88 |
| 0140 | 18 | 88 | 0/4 | 20 |
| 0130 | 20 | 91 | 2/4 | 43 |
| 0242 | 16 | 67 | 0/4 | 32 |
| 0106 | 22 | 105 | 0/4 | 40 |
| 0168 | 18 | 132 | 1/4 | 19 |
| 0280 | 13 | 110 | 1/4 | 12 |
