"""Write every statistic in ../experiments/ANALYSIS_4hop_three_arms.md out as a data file.

`outputs/` is gitignored, so a number that only exists inside a prose document cannot be
re-checked without the 29 GB of episodes. This emits the computed statistics themselves --
machine-readable, one concern per file -- so the repository carries the results and not only
the code that made them. Same spirit as experiments/traj_analysis_4hop/summary.csv.

    python scripts/emit_stats_q35a.py [OUT]        # default experiments/stats_q35a

Files written:
  arm_summary.csv       one row per arm: TSR and MSR in every convention, loops, cost
  per_cell.csv          one row per cell: score, termination, loop metrics, ESC presses
  per_scene_shared.csv  the 20 shared scenes, arms side by side
  verb_success.csv      milestone success by verb -- the craft 0/109 finding
  prolong_retrieval.csv PRO-LONG's analyzer shell-command census, tail vs grep
  paired_tests.csv      per-pair W/L/T and the sign test on discordant pairs
"""
from __future__ import annotations

import csv
import glob
import json
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from loop_census import census, trace  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "experiments" / "stats_q35a"
ARMS = {
    "prolong": "outputs/q35a-prolong-codex-*/*/4-hop/*/result.json",
    "default": "outputs/q35a-default-vllm-append-only-*/*/4-hop/*/result.json",
    "hypothesis": "outputs/q35a-hypothesis-vllm-append-only-*/*/4-hop/*/result.json",
}
ESC = re.compile(r'"ESC":\s*1')
LOOPSAY = re.compile(r"circling loop|stuck in a loop|not making progress", re.I)
GUI = re.compile(r"(GUI limitation|no GUI|cannot open .{0,30}(interface|inventory|crafting)"
                 r"|Failed to (open|craft)|no (mouse|cursor|click))", re.I)
TURN = re.compile(r"\[codex\] turn (\d+) model=")
NOACT = re.compile(r"wrote no actions\.json")


def load() -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for arm, pat in ARMS.items():
        d = {}
        for res in glob.glob(str(ROOT / pat)):
            j = json.loads(Path(res).read_text())
            if "total_steps" not in j:
                continue
            tag = Path(res).parts[-5]
            lg = ROOT / "outputs" / f"log-{tag}.txt"
            txt = lg.read_text(errors="replace") if lg.exists() else ""
            c = census(trace(lg)) or {}
            d[j["scene_id"]] = dict(
                tag=tag, j=j, c=c,
                esc=len(ESC.findall(txt)),
                loopsay=len(LOOPSAY.findall(txt)),
                gui=len(GUI.findall(txt)),
                turns=len(TURN.findall(txt)),
                noact=len(NOACT.findall(txt)),
            )
        out[arm] = d
    return out


def w(name: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", newline="") as fh:
        cw = csv.writer(fh)
        cw.writerow(header)
        cw.writerows(rows)
    print(f"  {name}: {len(rows)} rows")


def classify(e: dict) -> str:
    c = e["c"]
    if e["esc"] >= 20:
        return "esc_deadlock"
    if c.get("frozen_max", 0) >= 20:
        return "navigation_freeze"
    if c.get("revisit", 0) >= 95:
        return "pacing_loop"
    return "clean"


def main() -> int:
    D = load()
    shared = sorted(set.intersection(*(set(D[a]) for a in D)))
    print(f"arms: " + ", ".join(f"{a} {len(D[a])}" for a in D) + f"; shared {len(shared)}")

    # --- per cell ------------------------------------------------------------------
    rows = []
    for arm in D:
        for scene, e in sorted(D[arm].items()):
            j, c = e["j"], e["c"]
            rows.append([
                arm, scene, e["tag"], j.get("prompt_layout", "legacy"),
                j["milestones_completed"], j["milestones_trackable"], j["milestones_total"],
                j["milestones_presatisfied"], j["all_milestones_done"],
                j["total_steps"], j["termination_reason"], scene in shared,
                f"{c.get('frozen', 0):.1f}", c.get("frozen_max", ""),
                f"{c.get('stalled', 0):.1f}", f"{c.get('revisit', 0):.1f}",
                f"{c.get('coverage', 0):.3f}",
                "" if c.get("tort") in (None, float("inf")) else f"{c['tort']:.2f}",
                e["esc"], e["loopsay"], e["gui"], e["turns"], e["noact"], classify(e),
            ])
    w("per_cell.csv",
      ["arm", "scene", "tag", "prompt_layout", "milestones_done", "milestones_trackable",
       "milestones_total", "milestones_presatisfied", "all_milestones_done", "steps",
       "termination", "in_shared_set", "frozen_pct", "frozen_max_run", "stalled_pct",
       "revisit_pct", "coverage", "tortuosity", "esc_presses", "loop_self_reports",
       "gui_limit_mentions", "analyzer_turns", "turns_without_action", "stuck_class"], rows)

    # --- per arm -------------------------------------------------------------------
    rows = []
    for arm in D:
        sub = [D[arm][s] for s in shared]
        n = len(sub)
        comp = sum(e["j"]["milestones_completed"] for e in sub)
        trk = sum(e["j"]["milestones_trackable"] for e in sub)
        tot = sum(e["j"]["milestones_total"] for e in sub)
        pre = sum(e["j"]["milestones_presatisfied"] for e in sub)
        tsr_s = sum(1 for e in sub if e["j"]["all_milestones_done"])
        tsr_a = sum(1 for e in sub if e["j"]["milestones_completed"]
                    == e["j"]["milestones_total"] - e["j"]["milestones_presatisfied"])
        cls = Counter(classify(e) for e in sub)
        med = lambda k: st.median([e["c"].get(k, 0) for e in sub])
        rows.append([
            arm, n, len(D[arm]),
            tsr_s, f"{100*tsr_s/n:.1f}", tsr_a, f"{100*tsr_a/n:.1f}",
            comp, trk, f"{100*comp/trk:.1f}", f"{100*comp/(tot-pre):.1f}",
            f"{100*(comp+pre)/tot:.1f}",
            cls["esc_deadlock"], cls["navigation_freeze"], cls["pacing_loop"], cls["clean"],
            f"{med('frozen'):.1f}", f"{med('stalled'):.1f}", f"{med('revisit'):.1f}",
            f"{med('coverage'):.2f}",
            sum(e["esc"] for e in sub), sum(1 for e in sub if e["loopsay"]),
        ])
    w("arm_summary.csv",
      ["arm", "shared_scenes", "cells_total", "tsr_strict_n", "tsr_strict_pct",
       "tsr_achievable_n", "tsr_achievable_pct", "msr_completed", "msr_trackable",
       "msr_strict_pct", "msr_ceiling_pct", "msr_msr_pct", "esc_deadlock_cells",
       "nav_freeze_cells", "pacing_cells", "clean_cells", "frozen_pct_median",
       "stalled_pct_median", "revisit_pct_median", "coverage_median", "esc_presses_total",
       "cells_self_reporting_loop"], rows)

    # --- shared scenes, arms side by side -------------------------------------------
    rows = []
    for s in shared:
        j0 = D["prolong"][s]["j"]
        rows.append([s, j0["milestones_trackable"], j0["milestones_presatisfied"]]
                    + [D[a][s]["j"]["milestones_completed"] for a in ("prolong", "default", "hypothesis")]
                    + [D[a][s]["j"]["termination_reason"] for a in ("prolong", "default", "hypothesis")]
                    + [classify(D[a][s]) for a in ("prolong", "default", "hypothesis")]
                    + ["|".join(m["milestone_id"] for m in j0["milestone_status"])])
    w("per_scene_shared.csv",
      ["scene", "trackable", "presatisfied", "prolong_ms", "default_ms", "hypothesis_ms",
       "prolong_end", "default_end", "hypothesis_end", "prolong_stuck", "default_stuck",
       "hypothesis_stuck", "milestone_ids"], rows)

    # --- verb census ----------------------------------------------------------------
    tab: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for arm in D:
        for e in D[arm].values():
            for m in e["j"]["milestone_status"]:
                if m["presatisfied_at_spawn"]:
                    continue
                v = m["milestone_id"].split("_")[0]
                tab[v][arm][1] += 1
                tab[v][arm][0] += int(m["completed"])
    rows = []
    for v in sorted(tab, key=lambda v: -sum(tab[v][a][1] for a in D)):
        r = [v, sum(tab[v][a][1] for a in D)]
        for a in ("prolong", "default", "hypothesis"):
            g, t = tab[v][a]
            r += [g, t, f"{100*g/t:.1f}" if t else ""]
        rows.append(r)
    w("verb_success.csv",
      ["verb", "n_all_arms", "prolong_done", "prolong_n", "prolong_pct",
       "default_done", "default_n", "default_pct",
       "hypothesis_done", "hypothesis_n", "hypothesis_pct"], rows)

    # --- PRO-LONG retrieval ----------------------------------------------------------
    verbs, cells_with_grep, per_cell_grep = Counter(), 0, []
    hits = misses = 0
    for aud in glob.glob(str(ROOT / "outputs/q35a-prolong-codex-*/*/4-hop/*/prolong_vision_audit.json")):
        try:
            src = json.loads(Path(aud).read_text())["vision_audit_source"]
        except Exception:
            continue
        if not src or not Path(src).exists():
            continue
        g = 0
        pending = {}
        for line in Path(src).open(errors="ignore"):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            pl = ev.get("payload") or ev
            t = pl.get("type")
            if t in ("function_call", "local_shell_call"):
                a = pl.get("arguments")
                if isinstance(a, str):
                    try:
                        a = json.loads(a)
                    except Exception:
                        a = {}
                if not isinstance(a, dict):
                    continue
                cmd = a.get("command") or a.get("cmd") or ""
                if isinstance(cmd, list):
                    cmd = " ".join(map(str, cmd))
                if not cmd:
                    continue
                if "grep" in cmd or cmd.strip().startswith("rg"):
                    verbs["grep/rg"] += 1
                    g += 1
                    pending[pl.get("call_id")] = True
                elif cmd.strip().startswith(("cat", "printf")) and "<<" in cmd:
                    verbs["heredoc write"] += 1
                elif cmd.strip().startswith("cat"):
                    verbs["cat (read back)"] += 1
                else:
                    verbs[(re.match(r"\s*([\w.-]+)", cmd) or [None, "?"])[1]] += 1
            elif t in ("function_call_output", "local_shell_call_output") and pl.get("call_id") in pending:
                out = pl.get("output") or ""
                if isinstance(out, dict):
                    out = json.dumps(out)
                body = out.split("Output:", 1)[1] if "Output:" in out else ""
                body = re.sub(r"^[=\s]*", "", body).strip()
                hits += bool(body)
                misses += not body
                del pending[pl["call_id"]]
        per_cell_grep.append(g)
        cells_with_grep += g > 0
    tot = sum(verbs.values())
    rows = [[k, v, f"{100*v/tot:.2f}"] for k, v in verbs.most_common()]
    rows.append(["--- cells that ever grep", f"{cells_with_grep}/{len(per_cell_grep)}", ""])
    rows.append(["--- median greps per cell", st.median(per_cell_grep) if per_cell_grep else 0, ""])
    rows.append(["--- grep calls returning content", hits, f"{100*hits/max(hits+misses,1):.1f}"])
    rows.append(["--- grep calls returning nothing", misses, ""])
    w("prolong_retrieval.csv", ["command", "count", "pct_of_commands"], rows)

    # --- paired sign tests ------------------------------------------------------------
    rows = []
    names = ("prolong", "default", "hypothesis")
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            win = sum(1 for s in shared if D[a][s]["j"]["milestones_completed"] > D[b][s]["j"]["milestones_completed"])
            loss = sum(1 for s in shared if D[a][s]["j"]["milestones_completed"] < D[b][s]["j"]["milestones_completed"])
            tie = len(shared) - win - loss
            n, k = win + loss, max(win, loss)
            p = min(1.0, 2 * sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n) if n else 1.0
            rows.append([a, b, win, loss, tie, n, f"{p:.4f}", "yes" if p < 0.05 else "no"])
    w("paired_tests.csv",
      ["arm_a", "arm_b", "a_wins", "a_losses", "ties", "discordant_pairs", "sign_test_p",
       "significant_at_05"], rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
