"""Collate every finished scene result into one comparison table.

Reads result.json wherever eval_benchmark wrote it and labels each run by the three
axes that actually vary: agent architecture, model, and how the model is reached.
Milestones are reported per scene rather than pooled, because the scenes differ
sharply in how much they demand -- 0313's first hop needs 0.56 blocks of movement
while 0802's single milestone needs ~4.5 -- so a pooled percentage hides the signal.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def label(run_id: str) -> tuple[str, str, str]:
    """(agent, model, path) inferred from the run slug the launcher recorded."""
    r = run_id.lower()
    agent = "prolong" if "prolong" in r else "hypothesis" if "hypothesis" in r else "default"
    model = "gpt-5.6" if "gpt56" in r else "Qwen3.5-27B"
    return agent, model, channel(run_id)


def channel(run_id: str) -> str:
    """Which channel reached the model, for runs predating the recorded `provider`.

    Guessing this from the slug was wrong in the way that matters: a run named
    `m1-qwen38-default-0313-s2` contains neither "codex" nor "vllm", so the guess
    called it plain-vLLM when every one of those runs went through the Codex CLI.
    That mislabel turned the central comparison -- PRO-LONG against its baseline --
    into an apparent agent-vs-channel difference. The launcher records the actual
    command, so read it instead.
    """
    manifest = ROOT / ".harness" / "runs" / run_id / "manifest.yaml"
    if manifest.exists():
        cmd = manifest.read_text(errors="replace")
        # The command names a runner script rather than the flags themselves, so the
        # answer lives one level down, in the script it invoked.
        texts = [cmd]
        for name in re.findall(r"scripts/[\w./-]+\.sh", cmd):
            path = ROOT / name
            if path.exists():
                texts.append(path.read_text(errors="replace"))
        joined = "\n".join(texts)
        if "--use-codex" in joined:
            return "codex"
        if "--use-vllm" in joined:
            return "vllm"
    r = run_id.lower()
    if "vllm" in r:
        return "vllm"
    if "codex" in r or "prolong" in r:
        return "codex"
    return "?"


def load_invalid() -> dict[str, str]:
    """Runs whose numbers exist but do not measure what they claim.

    A reason beginning `VARIANT:` marks the other case: the numbers are sound but
    they belong to a different arm than the run was launched as. Those are reported,
    under their own label, rather than dropped -- dropping them would quietly discard
    a real ablation.
    """
    # Tracked, not under artifacts/: which runs are trustworthy is a research
    # judgement that has to survive an artifacts/ wipe and travel with the code.
    path = ROOT / "RUN_LEDGER.txt"
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        prefix, _, reason = line.partition("  ")
        out[prefix.strip()] = reason.strip()
    return out


def main() -> int:
    invalid = load_invalid()
    skipped: list[tuple[str, str]] = []
    rows = []
    for f in sorted(ROOT.glob("artifacts/runs/*/results/*/*/*/result.json")):
        run_id = f.parts[len(ROOT.parts) + 2]
        bad = next((r for p, r in invalid.items() if run_id.startswith(p)), None)
        # A protocol difference is not a defect: it is a second axis. Reported with
        # the protocol in its own column instead of being dropped.
        if bad and bad.startswith("PROTOCOL:"):
            bad = None
        if bad and not bad.startswith("VARIANT:"):
            if (run_id, bad) not in skipped:
                skipped.append((run_id, bad))
            continue
        scene = f.parent.name
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        agent, model, path = label(run_id)
        # Prefer what the run recorded over what its slug implies: result.json now
        # carries agent_mode and model, and a slug is a label someone typed once.
        if d.get("agent_mode"):
            agent = d["agent_mode"]
        if d.get("model"):
            model = d["model"].split("@")[0].replace("Qwen/", "")
        if d.get("provider"):
            path = d["provider"]
        if bad:
            # Its own configuration key, so it never averages with the arm it was
            # launched as. `vod` = the analyzer had to ask for pixels.
            agent = f"{agent}-vod"
        ms = d.get("milestone_status", [])
        hits = [m["milestone_id"] for m in ms if m.get("completed")]
        # Results written before the flag existed are all from the no-hint protocol.
        proto = "hint" if d.get("milestone_hint") else "no-hint"
        # How much vision and how much analysis produced this score. A PRO-LONG number
        # is not interpretable without it: the same agent scores differently blind.
        audit_path = f.parent / "prolong_vision_audit.json"
        audit = {}
        if audit_path.exists():
            try:
                audit = json.loads(audit_path.read_text())
            except Exception:
                audit = {}
        rows.append({
            "run": run_id, "scene": scene, "agent": agent, "model": model, "path": path,
            "proto": proto, "cap": d.get("max_steps", 0), "audit": audit,
            "steps": d.get("total_steps", 0), "term": d.get("termination_reason", ""),
            "done": d.get("milestones_completed", 0),
            "track": d.get("milestones_trackable", 0),
            "hits": hits,
        })

    if skipped:
        print(f"excluded {len(skipped)} invalidated run(s):")
        for run_id, reason in skipped:
            print(f"  {run_id[:44]:44s} {reason}")
        print()
    if not rows:
        print("no valid results yet")
        return 0

    print(f"{'agent':11s} {'model':14s} {'path':6s} {'proto':8s} {'scene':6s} "
          f"{'steps':>5s} {'term':15s} {'score':>6s}  milestones hit")
    print("-" * 108)
    for r in sorted(rows, key=lambda r: (r["proto"], r["scene"], r["agent"],
                                         r["model"], r["path"])):
        print(f"{r['agent']:11s} {r['model']:14s} {r['path']:6s} {r['proto']:8s} "
              f"{r['scene']:6s} {r['steps']:5d} {r['term']:15s} "
              f"{r['done']:2d}/{r['track']:<3d}  {','.join(r['hits']) or '-'}")

    audited = [r for r in rows if r["audit"]]
    if audited:
        print()
        print("PRO-LONG analyzer audit (a score is only readable next to the vision "
              "that produced it):")
        print(f"  {'run':44s} {'scene':6s} {'turns':>5s} {'frames':>6s} "
              f"{'view_image':>10s} {'overflow':>8s} {'esc_rej':>7s}")
        for r in sorted(audited, key=lambda r: (r["scene"], r["run"])):
            a = r["audit"]
            print(f"  {r['run'][:44]:44s} {r['scene']:6s} "
                  f"{a.get('analyzer_turns', 0):5d} {a.get('frames_attached', 0):6d} "
                  f"{a.get('view_image_calls', 0):10d} "
                  f"{a.get('overflow_resets', 0):8d} {a.get('esc_rejections', 0):7d}")

    print()
    print("per-configuration totals (scenes pooled, read with the caveat above):")
    agg: dict[tuple, list[int]] = {}
    for r in rows:
        # Protocol is part of the key: without the hint an arm ends its own episode,
        # so pooling the two would average a navigation score with a quitting score.
        k = (r["proto"], r["agent"], r["model"], r["path"])
        a = agg.setdefault(k, [0, 0, 0])
        a[0] += r["done"]; a[1] += r["track"]; a[2] += 1
    for (proto, agent, model, path), (done, track, n) in sorted(agg.items()):
        pct = f"{100 * done / track:.0f}%" if track else "n/a"
        print(f"  {proto:8s} {agent:11s} {model:14s} {path:6s}  "
              f"{done}/{track} ({pct}) over {n} scene(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
