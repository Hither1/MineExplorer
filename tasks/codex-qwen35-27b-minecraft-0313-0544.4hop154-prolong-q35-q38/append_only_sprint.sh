#!/usr/bin/env bash
# Arms 2 and 3 on the append-only layout, four servers, both arms in parallel, deadline 06:15.
#
# What changed and why (user decision, 2026-08-20 22:5x, deadline 07:00):
#   * `PROMPT_LAYOUT=append-only`. The formal `legacy` layout slides a fixed 20-frame window,
#     so the request prefix changes at the first image every step and the measured prefix-cache
#     hit rate was 0.0 / 0.7 / 1.4 %: every step re-prefills 20 frames. append-only moves the
#     reusable prefix to 94-96 % (repo: hypothesis 13.7 -> 7.6 s/step, default 7.3 -> 4.6).
#     It is a DIFFERENT ARM by this repo's own rule -- own tag suffix, never pooled with legacy
#     cells -- because it also changes what the model reads: state after the frames, window
#     20-29 instead of a fixed 20. The 28 legacy hypothesis cells already on disk stay as a
#     small legacy sample; they are not part of this table.
#   * A fourth server on GPUs 0,1 (:8004). Those GPUs freed themselves when `qwen35-auto3`
#     ended; nothing of the user's was killed for this.
#   * Both arms run AT THE SAME TIME, 9 slots each, walking the identical scene order. A
#     deadline needs a matched set at an arbitrary stopping time, and running them in parallel
#     means the common prefix grows steadily instead of arm 3 starting from zero at 03:00.
#   * The prolong arm is untouched: layout knobs never reach it (run_cell.sh drops them), so
#     its 154 legacy cells stand and cover whatever subset this produces.
#
#   setsid nohup bash tasks/<task>/append_only_sprint.sh > outputs/log-q35a-sprint.txt 2>&1 &
set -uo pipefail
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer

PREFIX=q35a; MODEL=Qwen3.5-27B; MAX_STEPS=200
SPLIT_ROOT=bench_4hop154/_split
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1 http://192.168.2.20:8004/v1"
CONC_PER_ARM=9           # 18 total against 4 servers = 4.5 cells/server, the density measured today
HARD_STOP="06:15"
SCENES="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {printf "%s ", $1}')"
[[ "$(echo "$SCENES" | wc -w)" -eq 154 ]] || { echo "[sprint] scene screen did not return 154 -- refusing"; exit 2; }

say() { echo "[sprint] $(date '+%m-%d %H:%M:%S') $*"; }
past() { [[ "$(date +%H%M)" -ge "${1/:/}" && "$(date +%H)" -lt 12 ]]; }

# --- wait for the fourth server, then wire-check all four -------------------------------
say "waiting for :8004 to serve $MODEL"
for i in $(seq 1 120); do
  python - <<'PY' && break
import json,urllib.request,sys
try:
    r=json.loads(urllib.request.urlopen("http://192.168.2.20:8004/v1/models",timeout=5).read())
    sys.exit(0 if "Qwen3.5-27B" in [m["id"] for m in r.get("data",[])] else 1)
except Exception: sys.exit(1)
PY
  sleep 15
done
say "wire-checking all four servers (cap 1024, thinking off, tool parser)"
python - <<'PY' || { echo "[sprint] wire-check FAILED -- refusing to launch"; exit 3; }
import json,urllib.request,sys
def post(u,b):
    r=urllib.request.Request(u,data=json.dumps(b).encode(),headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r,timeout=120).read())
bad=[]
for p in (8001,8002,8003,8004):
    base=f"http://192.168.2.20:{p}/v1"
    try:
        d=post(f"{base}/chat/completions",{"model":"Qwen3.5-27B","max_tokens":2048,
              "messages":[{"role":"user","content":"Count from 1 to 500, one number per line."}]})
        c=d["choices"][0]["message"]
        cap=d["usage"]["completion_tokens"]; fin=d["choices"][0]["finish_reason"]
        ok = cap==1024 and fin=="length" and "<think>" not in (c.get("content") or "") and not c.get("reasoning_content")
        print(f"  :{p} cap={cap} finish={fin} think={'<think>' in (c.get('content') or '')} -> {'ok' if ok else 'BAD'}")
        if not ok: bad.append(p)
    except Exception as e:
        print(f"  :{p} FAILED {e}"); bad.append(p)
sys.exit(1 if bad else 0)
PY
say "all four servers pass"

# --- both arms, in parallel, same scene order -------------------------------------------
for arm in hypothesis:vllm default:vllm; do
  agent=${arm%%:*}
  PREFIX=$PREFIX MODEL=$MODEL SPLIT_ROOT=$SPLIT_ROOT SERVERS="$SERVERS" \
  PROMPT_LAYOUT=append-only RESPONSE_STYLE=full \
  ARMS="$arm" SCENES="$SCENES" MAX_STEPS=$MAX_STEPS CONC=$CONC_PER_ARM \
    bash scripts/launch_4hop.sh > "outputs/log-${PREFIX}-launcher-${agent}-ao.txt" 2>&1 &
  say "launched $arm (append-only, CONC=$CONC_PER_ARM) pid $!"
  sleep 20
done

# --- watchdog: stop in time to write the table ------------------------------------------
while :; do
  h=$(find outputs -path '*q35a-hypothesis-vllm-append-only*' -name result.json 2>/dev/null | wc -l)
  d=$(find outputs -path '*q35a-default-vllm-append-only*'    -name result.json 2>/dev/null | wc -l)
  if past "$HARD_STOP"; then
    say "deadline $HARD_STOP: hypothesis $h, default $d -- stopping launchers"
    for pid in $(pgrep -f '^bash scripts/launch_4hop\.sh$'); do kill "$pid" 2>/dev/null; done
    break
  fi
  if [[ "$h" -ge 154 && "$d" -ge 154 ]]; then say "both arms finished all 154"; break; fi
  if ! pgrep -f '^bash scripts/launch_4hop\.sh$' >/dev/null; then say "both launchers exited"; break; fi
  sleep 120
done

say "final: hypothesis $(find outputs -path '*hypothesis-vllm-append-only*' -name result.json | wc -l), default $(find outputs -path '*default-vllm-append-only*' -name result.json | wc -l)"
python scripts/summarize_4hop.py --prefix "$PREFIX" --model "$MODEL" --md > "outputs/${PREFIX}-summary.md" 2>&1
say "summary at outputs/${PREFIX}-summary.md"
