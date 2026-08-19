# Findings: fast-agent

| time (CST) | finding | evidence | confidence |
|---|---|---|---|
| 08:05 | Output anatomy of the c4h direct arms (7 cells each): default response 237 tokens = thought 74 + memory 118 + action 10 + ~35 JSON whitespace/fences; hypothesis 508 = thought 126 + memory 99 + action 5 + hypotheses 134 + plan 61 + ~83 structure. Memory identical to the previous step in 36% (default) / 28% (hypothesis) of steps and 99% similar in median; the hypothesis agent emits >= 1 hypothesis op on 99% of steps and repeats the plan verbatim for runs of steps. Compact JSON alone: 237 -> 208, 508 -> 414; without memory: 88 / 302. | outputs/log-c4h-{default,hypothesis}-vllm-*.txt, /tokenize on :8004 | high |
