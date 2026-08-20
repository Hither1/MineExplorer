#!/usr/bin/env bash
# Wait for the a230 sandbox host to come back, then resume arms 2 and 3 where they stopped.
#
# a230 (192.168.2.22) went hard down at ~00:20 on 2026-08-21: no ICMP, no SSH, port 8000
# unreachable. Cells failed at /create_env and env.step with "No route to host". Everything
# already landed is intact -- prolong 154/154, hypothesis 27, default 37 -- and the 11 cells
# that wrote an error-schema result.json (no `total_steps`) were quarantined to
# outputs/_damaged_a230_outage/ so their scenes are re-runnable rather than silently skipped.
#
# Resumes at 9 slots per arm, the density that ran for 80 minutes without trouble. It does NOT
# restore the 3-slot boost that was live when the host went down: with no way to inspect a230's
# memory while it is unreachable, an increase from 18 to 21 sessions cannot be ruled out as a
# contributor, and re-applying it blind is not a risk worth taking to save half an hour.
set -uo pipefail
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer
say() { echo "[resume] $(date '+%m-%d %H:%M:%S') $*"; }
DEADLINE_EPOCH=$(date -d '2026-08-21 06:15:00' +%s)

say "waiting for 192.168.2.22:8000"
while :; do
  [ "$(date +%s)" -ge "$DEADLINE_EPOCH" ] && { say "deadline reached with a230 still down -- not resuming"; exit 1; }
  if python -c "
import urllib.request,json,sys
try:
    json.loads(urllib.request.urlopen('http://192.168.2.22:8000/list_sessions',timeout=10).read()); sys.exit(0)
except Exception: sys.exit(1)" 2>/dev/null; then
    say "a230 answers /list_sessions"; break
  fi
  sleep 30
done

# Two clean probes a minute apart, so a host still finishing its boot is not handed 18 sessions.
sleep 60
python -c "
import urllib.request,json,sys
d=json.loads(urllib.request.urlopen('http://192.168.2.22:8000/list_sessions',timeout=15).read())
print('  sessions on the recovered host:',len(d['sessions'])); sys.exit(0)" || { say "second probe failed -- not resuming"; exit 2; }

# The model servers live on a227 and were never affected, but a resume asserts its contract.
python - <<'PY' || { echo "[resume] server wire-check FAILED -- not resuming"; exit 3; }
import json,urllib.request,sys
bad=[]
for p in (8001,8002,8003,8004):
    try:
        r=urllib.request.Request(f"http://192.168.2.20:{p}/v1/chat/completions",
            data=json.dumps({"model":"Qwen3.5-27B","max_tokens":2048,
                "messages":[{"role":"user","content":"Count from 1 to 500, one number per line."}]}).encode(),
            headers={"Content-Type":"application/json"})
        d=json.loads(urllib.request.urlopen(r,timeout=120).read()); c=d["choices"][0]["message"]
        ok=d["usage"]["completion_tokens"]==1024 and d["choices"][0]["finish_reason"]=="length" \
           and "<think>" not in (c.get("content") or "") and not c.get("reasoning_content")
        print(f"  :{p} -> {'ok' if ok else 'BAD'}")
        if not ok: bad.append(p)
    except Exception as e:
        print(f"  :{p} FAILED {e}"); bad.append(p)
sys.exit(1 if bad else 0)
PY

SCENES="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {printf "%s ", $1}')"
[[ "$(echo "$SCENES" | wc -w)" -eq 154 ]] || { say "screen did not return 154 -- refusing"; exit 4; }
for arm in hypothesis:vllm default:vllm; do
  agent=${arm%%:*}
  PREFIX=q35a MODEL=Qwen3.5-27B SPLIT_ROOT=bench_4hop154/_split \
  SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1 http://192.168.2.20:8004/v1" \
  PROMPT_LAYOUT=append-only RESPONSE_STYLE=full \
  ARMS="$arm" SCENES="$SCENES" MAX_STEPS=200 CONC=9 \
    bash scripts/launch_4hop.sh > "outputs/log-q35a-launcher-${agent}-resume.txt" 2>&1 &
  say "relaunched $arm (CONC=9) pid $!"
  sleep 20
done
say "resumed; hypothesis $(find outputs -path '*q35a-hypothesis-vllm-append-only*' -name result.json | wc -l), default $(find outputs -path '*q35a-default-vllm-append-only*' -name result.json | wc -l)"
wait
