# Findings: 4hop154-prolong-q35-q38

## 1. The paper's "4-hop" is 154 scenes, and `benchmark/` is exactly the released set

arXiv 2605.30931 §2.2: hop count = |V_tau|, the number of atomic tasks the selector picks
("select k compatible tasks, where k corresponds to the target hop number"), not the DAG's
depth. §3: 1,039 generated, **813 human-validated**. Table 2 multi-agent valid rates
89.04/84.39/68.72/65.53 x the generated 292/301/211/235 = **260/254/145/154 = 813**, which
is the node-count histogram of `benchmark/` byte for byte. So `--hops 4` = 154 = the paper's
4-hop set. Our stricter screens (`--min-depth 4` -> 53, `--reachable` -> 77, all four -> 7)
are ours alone; the paper has none of them. Confidence: high (arithmetic identity).

Open question for the authors: §2.2 puts `a_craft` in "the executable action space", but this
harness has no cursor/click, so the 77 scenes with craft/trade/smelt verbs cannot be
completed here. Either their runner can craft or their 4-hop numbers carry the same floor.

## 2. Timing base for the estimate

PRO-LONG on Qwen3.5, cap 1024, thinking off, 300 steps, k=1, 3 servers, CONC=14 —
the 6 cells that ran the full 300 steps: 8, 10, 16, 34, 36, 54 min (mean 26.3, sd 18.0,
se 7.4). Source: `experiments/4hop_cells.csv` + log timestamps of `outputs/log-q35-*.txt`.
154 cells => 68 h cell-time (49-86) => **4.8 h wall at CONC=14** (3.5-6.2); k=3 cuts ~32%
(EVAL_LATENCY §7.1: turn 16-20 s -> 10-13 s, arm is ~95% decode). Qwen3.8 is slower on the
same arm (full-300 cells mean ~35 min) => ~6-7 h. Confidence: medium — all 6 sampled cells
are position-tier; the other 147 are inventory / voxel-count and unmeasured.

## 3. Live cluster state, 2026-08-20 11:44

- a227 all 8 GPUs busy, all `ruihan`: four TP=2 vLLM servers, tmux `qwen35-t1` (GPUs 2,3
  :8010), `qwen35-t2b` (4,5 :8011), `qwen35-t3` (6,7 :8012), `qwen35-t4` (0,1 :8013).
  These serve **thinking ON, temp 0.6, cap 4096** — the other session's bcp/microvqa
  contract, not ours. GPU 0 also carries chenxi's 3 GB dplm job.
- SSH to a227 works as `ruihan@192.168.2.20`; the `a227` / FQDN name is publickey-denied.
- The other session's cells run from `.../Collab/mllm-search` (2 `run_cell.sh`, ~24 `codex`,
  ~48 `bwrap`, 7 h 27 m elapsed) on **this** runner host a218. a218: 255 cores, load ~27,
  1 TB RAM, so there is headroom, but the process budget is shared.
- a230 sandbox up at 192.168.2.22:8000, 8 sessions all created 2026-08-19 — stale leftovers,
  nothing from today, so a restart before launch costs the other session nothing. Re-check
  immediately before restarting.

## 4. Prep verified

- `bench_4hop154/_split/` built: 154 one-scene dirs, each a byte-identical copy of
  `benchmark/<scene>/multi-agent/` (checked against the existing seven).
- `qwen35-s{1,2,3}-k3.sh` and `qwen38-s{1,2,3}-k3.sh` all carry the campaign contract:
  TP=2 on GPUs 2,3 / 4,5 / 6,7, ports 8001-8003, `max_new_tokens 1024`, temp 0.7 / top_p 0.8
  / top_k 20, `enable_thinking:false`, prefix caching, MTP k=3, `--max-num-seqs 64`,
  `qwen3_xml` tool parser.
- Qwen3.8-27B weights present locally (52 G, `/datapool/data3/storage/ruihan/models/`).

## PRO-LONG burns 31 % of its model calls on a truncation loop -- cost, not validity

**Evidence.** Across arm 1's 154 cells: 7,594 analyzer turns, of which **2,342 (30.8 %) wrote
no `actions.json` (rc=1)**, the error dominated by
`{"error":{"message":"Unterminated string starting at: line 1 column 9 ...`. The plan JSON is
being cut mid-string, codex fails to parse it, no action is emitted, the turn is retried, and
the next reply is truncated the same way. The cause is our own serving contract: the plan
exceeds the server's 1024-token `max_new_tokens`.

**It is concentrated, not endemic.** 11/154 cells see the error at all; three cells account
for essentially all of it -- 0326 (910/914 turns wasted), 0133 (865/869), 0016 (556/569).
Those three cost **12 cell-h, 18 % of the arm**, and 31 % of its model calls.

**No detectable score effect.** The three looping cells score 4/12 = 33.3 % ceiling-corrected
against 181/552 = 32.8 % for the other 151. n=3 cannot prove absence, but there is no evidence
the loop depressed arm 1's 185/616 and no reason to caveat the headline number for it.

**What it does change: the cost model.** prolong's per-cell wall is 25.6 min with the loop and
**21.3 min without it**; a 1+2+3-hop campaign for all three arms goes 718 -> 671 cell-h
(2.0 -> 1.9 days). Small, because the waste is 18 % of one arm.

**Fix, for after the campaign** (not during -- it would split the arm): bound the plan, or
detect N consecutive unparsable turns and fall back to a single action instead of retrying
forever. Related but distinct: the direct arms' `content: None` -> `UnboundLocalError` at
`mc_agent/action_space.py:244`, same family (an empty/truncated completion is not handled as a
named parse error), seen once tonight and recovered by retry.
