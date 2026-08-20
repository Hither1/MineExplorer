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

## Launch commands, ready to paste

```bash
# 1. sandbox — only if /list_sessions shows nothing created today
ssh ruihan@192.168.2.22 ...   # scripts/start_minecraft_podman.sh, see README

# 2. servers on a227 (verify remote md5 first — a stale NFS view burned wave 1 once)
ssh ruihan@192.168.2.20 'tmux new-session -d -s qwen35-s1-k3 "bash <qwen35-serve>/run/qwen35-s1-k3.sh"'
#   ... s2-k3, s3-k3; ~10 min to load; then wire-check: served name at 131072,
#   a chat completion stops at 1024 with finish_reason length and no <think>,
#   one parsed tool_calls entry.

# 3. the campaign
PREFIX=q35a MODEL=Qwen3.5-27B \
SPLIT_ROOT=bench_4hop154/_split \
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1" \
ARMS="prolong:codex" \
SCENES="$(python scripts/screen_scenes.py --hops 4 --split-to bench_4hop154/_split | sed -n 's/^SCENES="\(.*\)"$/\1/p')" \
MAX_STEPS=300 CONC=14 \
  setsid nohup bash scripts/launch_4hop.sh > outputs/log-q35a-launcher.txt 2>&1 &

# 4. same again with PREFIX=q38a MODEL=Qwen3.8-27B after swapping the servers
```
