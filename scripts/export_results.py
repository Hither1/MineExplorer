"""Export every scored episode as one row: what task, whether it passed, under what settings.

The artifacts this reads from live on `/work/nvme` and do not outlive the allocation, while
the answer they contain is a few hundred rows. This writes that answer into the repository
so the campaign survives its storage.

Three sources are joined, because no single one carries a whole row:

  * `artifacts/runs/<id>/results/**/result.json` -- the outcome, and the settings
    `eval_benchmark.py` actually ran under (agent_mode, provider, caps) rather than the
    ones the launcher intended.
  * `.harness/runs/<id>/manifest.yaml` -- the job's own env prefix, which is where a
    setting is pinned when it must not depend on working-tree state, plus the code
    identity the run was submitted at.
  * `RUN_LEDGER.txt` -- whether the run is trustworthy at all, and how its model was
    served. A row without this is not interpretable: two scores taken under different
    servers answer different questions.

Usage: python scripts/export_results.py [-o experiments/results.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Settings worth a column. Read out of the job's env prefix rather than assumed, since the
# whole point of putting them there was that the script defaults could not be trusted.
ENV_KEYS = ("MODEL_ID", "AGENT_MODE", "MAX_STEPS", "SCENES", "CODEX_EFFORT", "CODEX_TIMEOUT",
            "MILESTONE_HINT", "MODEL_SERVER", "PROLONG_LOG_WINDOW", "PROLONG_STATELESS")


def manifest_fields(run_id: str) -> dict:
    path = ROOT / ".harness" / "runs" / run_id / "manifest.yaml"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        key, _, value = line.partition(":")
        if key.strip() in ("commit", "branch", "tier", "slurm_job_id", "walltime",
                           "command_shell_escaped", "purpose", "submitted_at", "dirty_files"):
            out[key.strip()] = value.strip().strip('"')
    return out


def env_from_command(command: str) -> dict:
    """Pull NAME=VALUE out of the job's `env` prefix.

    Values are shell-escaped in the manifest and some carry spaces (a JSON sampling
    fragment), so this matches only the keys asked for and stops at the next key.
    """
    found = {}
    for key in ENV_KEYS:
        m = re.search(rf"\b{key}=((?:[^ ]|(?<=\\) )*)", command)
        if m:
            found[key] = m.group(1).replace("\\", "")
    return found


def channel_from_runner(command: str) -> str:
    """Last resort for runs whose result.json predates the `provider` field.

    Which runner the job invoked is the channel, and it is the one fact about an old run
    that cannot have drifted: `run_codex_*` reaches the model through the Codex CLI,
    `run_qwen35_*` speaks to the server directly. Preferred over guessing from the slug,
    which named the model rather than the path to it.
    """
    if "run_codex_" in command:
        return "codex"
    if "run_qwen35_" in command:
        return "vllm"
    return ""


def task_text(scene: str) -> tuple[str, int]:
    meta = ROOT / "benchmark" / str(scene) / "multi-agent" / "metadata.json"
    if not meta.exists():
        return "", 0
    d = json.loads(meta.read_text())
    graph = d.get("reasoning_graph") or {}
    return d.get("task_text", "").strip().replace("\n", " "), len(graph.get("nodes") or [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default=str(ROOT / "experiments" / "results.csv"))
    args = ap.parse_args()

    import compare_runs as cr
    invalid, serving, channels = cr.load_invalid(), cr.load_serving(), cr.load_channels()

    def ledger(run_id: str, table: dict):
        # Prefix match, because ledger entries name a run without its trailing hash.
        for prefix, value in table.items():
            if run_id.startswith(prefix):
                return value
        return ""

    rows = []
    for path in sorted(ROOT.glob("artifacts/runs/*/results/*/*/*/result.json")):
        run_id = path.parts[len(ROOT.parts) + 2]
        d = json.loads(path.read_text())
        scene = str(d.get("scene_id") or "")
        man = manifest_fields(run_id)
        env = env_from_command(man.get("command_shell_escaped", ""))
        text, hops = task_text(scene)
        done, trackable = d.get("milestones_completed"), d.get("milestones_trackable")
        reason = ledger(run_id, invalid)
        rows.append({
            "run_id": run_id,
            "scene": scene,
            "task": text,
            "hops": hops,
            # `all_milestones_done` is the benchmark's own pass bit; the ratio is beside it
            # because a 3/4 is not a pass but is not a zero either.
            "passed": d.get("all_milestones_done"),
            "milestones_done": done,
            "milestones_trackable": trackable,
            "milestones_total": d.get("milestones_total"),
            "milestones_presatisfied": d.get("milestones_presatisfied"),
            "steps_used": d.get("total_steps"),
            "termination": d.get("termination_reason"),
            # result.json is authoritative for what ran; the env prefix fills the gaps in
            # the older runs, whose result schema predates these fields.
            "agent_mode": d.get("agent_mode") or env.get("AGENT_MODE", ""),
            "channel": (d.get("provider") or ledger(run_id, channels)
                        or channel_from_runner(man.get("command_shell_escaped", ""))),
            "model": d.get("model") or env.get("MODEL_ID", ""),
            "max_steps": d.get("max_steps") or env.get("MAX_STEPS", ""),
            "milestone_hint": d.get("milestone_hint", env.get("MILESTONE_HINT", "")),
            "codex_effort": env.get("CODEX_EFFORT", ""),
            "codex_timeout": env.get("CODEX_TIMEOUT", ""),
            "model_server": env.get("MODEL_SERVER", ""),
            "prolong_log_window": d.get("prolong_log_window", ""),
            "prolong_stateless": d.get("prolong_stateless", ""),
            "serving": ledger(run_id, serving),
            "trustworthy": not reason,
            "invalid_reason": reason,
            "commit": man.get("commit", ""),
            "slurm_job": man.get("slurm_job_id", ""),
            "submitted_at": man.get("submitted_at", ""),
        })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    good = [r for r in rows if r["trustworthy"]]
    print(f"{len(rows)} episodes -> {out}")
    print(f"  trustworthy: {len(good)}   passed: {sum(1 for r in good if r['passed'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
