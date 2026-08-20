# Progress: 4hop154-prolong-q35-q38

## 2026-08-20 11:50 — task opened, Phase 1 complete

Scope set by the user: all 154 paper-defined 4-hop scenes, `prolong:codex` only,
cap 1024 / thinking off / 300 steps, Qwen3.5 first, then the same on Qwen3.8.
Gated on a227 GPUs 2-7 being released by the other session's bcp/microvqa servers.
Second user instruction the same hour: do not push concurrency — that session shares
this runner. CONC stays at the verified 14.

Prep done (see findings.md 4):
- `bench_4hop154/_split/` — 154 one-scene benchmark dirs.
- `scripts/screen_scenes.py --split-to DIR` — materialises whatever the filter shows, so
  the scene set stays defined by one piece of code.
- `scripts/launch_4hop.sh` — `SPLIT_ROOT` knob; the split path was hardcoded to the seven.
- Verified: both checkpoints' k=3 run files, the a230 sandbox, the Qwen3.8 weights.

## Blocked on

a227 GPUs 2-7. Monitor armed; the release signal is the disappearance of the
`VLLM::Worker` PIDs on those six GPUs (currently 5136/5138/5140/5141 and 26960/26961).

## 2026-08-20 12:20 — plan replaced, and the frame asymmetry closed

User re-planned: **three arms on Qwen3.5 only**, in order `prolong:codex` ->
`hypothesis:vllm` -> `default:vllm`, **200 steps** (was 300). The Qwen3.8 rerun is dropped.
Same three servers for all three arms, so no swap and no re-wire-check between them.

Hyperparameter audit against `main` (user request): every shared knob already agreed —
`FRAME_BUFFER_SIZE=20`, `MAX_STEPS`, `--temperature 0.7`, `--loading-command-steps 20`,
`--milestone-hint` on, output cap 1024 (server, both wires verified), thinking off on both
channels (`enable_thinking:false` / `CODEX_LOCAL_EFFORT=none`, which `effort_for()` lets
override `--codex-effort low`), `max_images` unset for Qwen (only llama-3.2 is capped at 1),
prolong ablations off. Our branch changed none of them relative to `main`.

One knob did **not** agree and is now fixed (9fcd984, user chose to align): per-frame
resolution. `_png` wrote 640x360 while the direct arms' frames were halved to 320x180.
Both now go through `mc_agent.utils.downsample_pov`; `prolong_mc.selftest` asserts it at
640x360 and at the 128x128 reset frame. ALL PASS. Consequence: the prolong arm is no longer
byte-comparable to the recorded seven-scene campaigns, which ran at native resolution.

## Cost of the 200-step cap, measured

4 of the 35 milestones the recorded q35 seven-scene campaign earned were first reached
after step 200 (default 0182@216, hypothesis 0482@246, prolong 0603@253, prolong 0763@220),
so ~11% of earned milestones, and in that small sample it costs prolong most (2 of its 14).
All three arms share the cap, so the arm comparison is unaffected; the comparison to the
recorded 300-step seven is not.

## Estimate, 200 steps at MTP k=3, CONC=14

From the recorded q35 per-cell walls (full-300 cells): prolong 5.26, default 10.46,
hypothesis 13.97 s/step at k=1; k=3 factors 0.67 / 0.55 / 0.72 (README, EVAL_LATENCY §7.1).

| order | arm | per cell | cell-time | wall |
|---|---|---|---|---|
| 1 | prolong:codex | ~12 min | 30 h | ~2.1 h |
| 2 | hypothesis:vllm | ~34 min | 86 h | ~6.2 h |
| 3 | default:vllm | ~19 min | 50 h | ~3.5 h |
| | | | **166 h** | **~12-14 h** |

## Launch, ready to fire when GPUs 2-7 free

```bash
# 1. sandbox — only if /list_sessions shows nothing created today
# 2. servers on a227 (verify remote md5 first), then wire-check all three
ssh ruihan@192.168.2.20 'tmux new-session -d -s qwen35-s1-k3 "bash <qwen35-serve>/run/qwen35-s1-k3.sh"'   # s2, s3 likewise

# 3. the three arms, in order, one launcher each
SC="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {printf "%s ", $1}')"
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer
setsid nohup bash -c '
for arm in prolong:codex hypothesis:vllm default:vllm; do
  PREFIX=q35a MODEL=Qwen3.5-27B SPLIT_ROOT=bench_4hop154/_split \
  SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1" \
  ARMS="$arm" SCENES="'"$SC"'" MAX_STEPS=200 CONC=14 \
    bash scripts/launch_4hop.sh
done' > outputs/log-q35a-chain.txt 2>&1 &
```

Per-cell logs land in `outputs/log-q35a-<arm>-<channel>-<scene>.txt`; the launcher skips any
cell whose `result.json` exists, so a relaunch resumes.
