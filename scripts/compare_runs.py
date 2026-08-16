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
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# One definition of what a codex call costs, shared with the runner that produces the
# transcripts this reads.
from prolong_mc.codex_backend import merge_stats, request_stats  # noqa: E402


def label(run_id: str, drifted: list[str] | None = None) -> tuple[str, str, str]:
    """(agent, model, path) inferred from the run slug the launcher recorded."""
    r = run_id.lower()
    agent = "prolong" if "prolong" in r else "hypothesis" if "hypothesis" in r else "default"
    model = "gpt-5.6" if "gpt56" in r else "Qwen3.5-27B"
    return agent, model, channel(run_id, drifted)


def channel(run_id: str, drifted: list[str] | None = None) -> str:
    """Which channel reached the model, for runs predating the recorded `provider`.

    Guessing this from the slug was wrong in the way that matters: a run named
    `m1-qwen38-default-0313-s2` contains neither "codex" nor "vllm", so the guess
    called it plain-vLLM when every one of those runs went through the Codex CLI.
    That mislabel turned the central comparison -- PRO-LONG against its baseline --
    into an apparent agent-vs-channel difference. The launcher records the actual
    command, so read it instead.

    Which *copy* of the script is read decides whether that answer stays true. Reading
    the live `scripts/` labels a year-old manifest with today's code: edit a runner and
    every historical run silently relabels, with nothing in the output to say so. Runs
    launched through `snapshot_exec.sh` carry the scripts they actually ran, so read
    those; a frozen `CHANNEL:` line in RUN_LEDGER.txt covers the handful that predate
    the snapshot; and the live-script fallback now reports itself through *drifted*
    instead of passing as a fact.
    """
    frozen = load_channels().get(run_id)
    if frozen:
        return frozen
    manifest = ROOT / ".harness" / "runs" / run_id / "manifest.yaml"
    if manifest.exists():
        cmd = manifest.read_text(errors="replace")
        # The command names a runner script rather than the flags themselves, so the
        # answer lives one level down, in the script it invoked.
        snapshot = ROOT / "artifacts" / "runs" / run_id / "script-snapshot"
        texts, from_snapshot = [cmd], False
        for name in re.findall(r"scripts/[\w./-]+\.sh", cmd):
            snapped = snapshot / Path(name).name
            if snapped.exists():
                texts.append(snapped.read_text(errors="replace"))
                from_snapshot = True
            elif (ROOT / name).exists():
                texts.append((ROOT / name).read_text(errors="replace"))
                if drifted is not None and run_id not in drifted:
                    drifted.append(run_id)
        joined = "\n".join(texts)
        if "--use-codex" in joined:
            return "codex"
        if "--use-vllm" in joined:
            return "vllm"
        if from_snapshot:
            return "?"
    r = run_id.lower()
    if drifted is not None and run_id not in drifted:
        drifted.append(run_id)
    if "vllm" in r:
        return "vllm"
    if "codex" in r or "prolong" in r:
        return "codex"
    return "?"


@lru_cache(maxsize=1)
def _ledger_entries() -> tuple[tuple[str, str], ...]:
    # Tracked, not under artifacts/: which runs are trustworthy is a research
    # judgement that has to survive an artifacts/ wipe and travel with the code.
    path = ROOT / "RUN_LEDGER.txt"
    if not path.exists():
        return ()
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        prefix, _, reason = line.partition("  ")
        out.append((prefix.strip(), reason.strip()))
    return tuple(out)


def scene_cost(scene_dir: Path) -> dict[str, int]:
    """Add up what one scene's codex calls cost, from the transcripts it already saved.

    Both codex paths write their event streams next to the result: `codex_turns/` for
    the PRO-LONG analyzer, `codex_calls/` for the per-step provider. Neither is one
    request per call -- see `request_stats` -- so this is the only honest denominator
    for a per-call cost comparison. Runs with no transcripts (the plain vLLM arm) return
    zeros and are reported as blank rather than as cheap.
    """
    parts = []
    for sub in ("codex_turns", "codex_calls"):
        for events in sorted((scene_dir / sub).glob("*.events.jsonl")):
            try:
                parts.append(request_stats(events.read_text(errors="replace")))
            except OSError:
                continue
    return merge_stats(parts)


def arm_label(agent: str, d: dict) -> str:
    """Suffix the agent label with the ablation the run recorded, if any.

    PRO-LONG's ablations are the arm the headline prolong runs are compared *against*,
    so pooling them under one "prolong" label would average an arm with its own control.
    The ledger already forces this for the vision-on-demand variant; these two are the
    same case, except that the run now says so itself instead of needing a ledger line.
    """
    if d.get("prolong_stateless"):
        agent = f"{agent}-sl"
    if d.get("prolong_log_window") is not None:
        agent = f"{agent}-w{d['prolong_log_window']}"
    return agent


def load_invalid() -> dict[str, str]:
    """Runs whose numbers exist but do not measure what they claim.

    A reason beginning `VARIANT:` marks the other case: the numbers are sound but
    they belong to a different arm than the run was launched as. Those are reported,
    under their own label, rather than dropped -- dropping them would quietly discard
    a real ablation.

    `CHANNEL:` lines are not verdicts about a run and are kept out of this dict
    entirely. Leaving them in would exclude the very runs they exist to label, and --
    because a prefix match returns the first hit -- could hide a real invalidation
    behind a bookkeeping line further up the file.
    """
    return {p: r for p, r in _ledger_entries()
            if not r.startswith(("CHANNEL:", "SERVING:"))}


@lru_cache(maxsize=1)
def load_channels() -> dict[str, str]:
    """Channel labels frozen for runs that predate both `provider` and the snapshots.

    Format: `<run-id-prefix>  CHANNEL: codex`. Exact run ids, not prefixes, because a
    label is only trustworthy for the run someone actually checked.
    """
    return {p: r.split(":", 1)[1].strip()
            for p, r in _ledger_entries() if r.startswith("CHANNEL:")}


@lru_cache(maxsize=1)
def load_serving() -> dict[str, str]:
    """How a run's model was served, where that differs from the current configuration.

    Format: `<run-id-prefix>  SERVING: think-on`. The serving configuration decides what
    the model emits -- an output cap, and whether the chat template opens a thinking
    block -- so two scores taken under different servers answer slightly different
    questions. This axis joins the protocol in the pooling key rather than excluding the
    runs: they measured something real, just not the thing the next runs will measure.
    """
    return {p: r.split(":", 1)[1].strip()
            for p, r in _ledger_entries() if r.startswith("SERVING:")}


def main() -> int:
    invalid = load_invalid()
    skipped: list[tuple[str, str]] = []
    # Runs whose channel could only be read off today's scripts. Named rather than
    # counted, because the fix is one CHANNEL: line each in RUN_LEDGER.txt.
    drifted: list[str] = []
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
        agent, model, path = label(run_id, drifted)
        # Prefer what the run recorded over what its slug implies: result.json now
        # carries agent_mode and model, and a slug is a label someone typed once.
        if d.get("agent_mode"):
            agent = d["agent_mode"]
        agent = arm_label(agent, d)
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
        # Serving configuration rides in the same column, and therefore in the same
        # pooling key: a score taken with thinking on and no output cap is not the same
        # measurement as one taken with both pinned, however identical the arm is.
        served = next((t for p, t in load_serving().items() if run_id.startswith(p)), None)
        if served:
            proto = f"{proto}/{served}"
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
            "cost": scene_cost(f.parent),
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

    print(f"{'agent':11s} {'model':14s} {'path':6s} {'proto':16s} {'scene':6s} "
          f"{'steps':>5s} {'term':15s} {'score':>6s}  milestones hit")
    print("-" * 108)
    for r in sorted(rows, key=lambda r: (r["proto"], r["scene"], r["agent"],
                                         r["model"], r["path"])):
        print(f"{r['agent']:11s} {r['model']:14s} {r['path']:6s} {r['proto']:16s} "
              f"{r['scene']:6s} {r['steps']:5d} {r['term']:15s} "
              f"{r['done']:2d}/{r['track']:<3d}  {','.join(r['hits']) or '-'}")

    audited = [r for r in rows if r["audit"]]
    if audited:
        print()
        print("PRO-LONG analyzer audit (a score is only readable next to the vision "
              "that produced it):")
        print(f"  {'run':44s} {'scene':6s} {'turns':>5s} {'frames':>6s} "
              f"{'view_image':>10s} {'overflow':>8s} {'compact':>7s} {'esc_rej':>7s}")
        for r in sorted(audited, key=lambda r: (r["scene"], r["run"])):
            a = r["audit"]
            # compact must read 0. Anything else means codex rewrote the conversation,
            # so that row is not the memory architecture the column header claims.
            print(f"  {r['run'][:44]:44s} {r['scene']:6s} "
                  f"{a.get('analyzer_turns', 0):5d} {a.get('frames_attached', 0):6d} "
                  f"{a.get('view_image_calls', 0):10d} "
                  f"{a.get('overflow_resets', 0):8d} {a.get('compactions', 0):7d} "
                  f"{a.get('esc_rejections', 0):7d}")

    costed = [r for r in rows if r["cost"].get("requests")]
    if costed:
        print()
        print("cost, in model requests rather than agent steps (a codex call runs a tool "
              "loop, so one call is several requests, each re-paying the prompt):")
        print(f"  {'run':44s} {'scene':6s} {'steps':>5s} {'calls':>5s} {'reqs':>5s} "
              f"{'req/call':>8s} {'req/step':>8s} {'in_tok':>10s} {'out_tok':>8s}")
        for r in sorted(costed, key=lambda r: (r["agent"], r["scene"], r["run"])):
            c = r["cost"]
            calls, reqs, steps = c["turns"], c["requests"], r["steps"]
            print(f"  {r['run'][:44]:44s} {r['scene']:6s} {steps:5d} {calls:5d} {reqs:5d} "
                  f"{reqs / calls if calls else 0:8.2f} {reqs / steps if steps else 0:8.2f} "
                  f"{c['input_tokens']:10d} {c['output_tokens']:8d}")
        print("  the plain vLLM arm saves no transcripts and is absent here, not cheap.")

    if drifted:
        print()
        print(f"{len(drifted)} run(s) had no recorded provider and no script snapshot, so "
              f"their channel was read off today's scripts and can change under a future "
              f"edit. Freeze each with a `<run-id>  CHANNEL: codex|vllm` line in "
              f"RUN_LEDGER.txt:")
        for run_id in drifted:
            print(f"  {run_id}")

    print()
    print("per-configuration totals (scenes pooled, read with the caveat above):")
    agg: dict[tuple, list] = {}
    for r in rows:
        # Protocol is part of the key: without the hint an arm ends its own episode,
        # so pooling the two would average a navigation score with a quitting score.
        k = (r["proto"], r["agent"], r["model"], r["path"])
        a = agg.setdefault(k, [0, 0, 0, set()])
        a[0] += r["done"]; a[1] += r["track"]; a[2] += 1; a[3].add(r["scene"])
    for (proto, agent, model, path), (done, track, n, scenes) in sorted(agg.items()):
        pct = f"{100 * done / track:.0f}%" if track else "n/a"
        # Runs and scenes are different denominators and were being reported as one:
        # with replicates, five runs over two scenes printed as "5 scene(s)", which
        # reads as breadth of coverage when it is repetition. Both, always, so neither
        # can be mistaken for the other.
        print(f"  {proto:16s} {agent:11s} {model:14s} {path:6s}  "
              f"{done}/{track} ({pct}) over {n} run(s) on {len(scenes)} scene(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
