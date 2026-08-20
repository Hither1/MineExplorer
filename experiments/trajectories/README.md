# Episode traces for the strict 4-hop campaigns

Two sets, in the same format:

- **the seven-scene campaigns** — 49 episodes: 28 on Qwen3.8-27B (4 arms) and 21 on
  Qwen3.5-27B (3 arms), same seven scenes, one seed each.
- **`q35a`, the 154-scene campaign** — 48 episodes, `hypothesis` arm only, Qwen3.5-27B.
  See [the section below](#the-q35a-hypothesis-episodes).

Written by `python scripts/export_4hop.py`; **derived, do not hand-edit** — re-run the
script after a campaign instead.

These are the readable part of the run. The cells themselves are ~29 GB under `outputs/`
(one episode video per cell, every frame PRO-LONG attached, every codex rollout) and stay
on the cluster filesystem; the per-cell path is in `4hop_cells.csv` if you need them.

```
<model>/<agent>-<channel>-<scene>.jsonl              the trace
<model>/<agent>-<channel>-<scene>.prolong_log.txt    PRO-LONG only: the agent's own episode log
<model>/<agent>-<channel>-<scene>.hypothesis.json    hypothesis only: the final DAG and plan
<model>/<cell-tag>.runner_log.txt                    q35a only: the raw runner log
```

## The trace

JSONL. Line 1 is `record: "meta"`; every other line is `record: "step"`, in step order.

**meta** — `campaign`, `model`, `agent_mode`, `channel`, `scene`, `hops`, the scene's
`task` text (the same text the agent is shown), then:

- `result`: `milestones_done` / `milestones_trackable`, `termination`
  (`max_steps` | `agent_esc` | `all_milestones`), `steps`, and `milestones` — the full
  per-milestone status including `frame_completed` (1-indexed from the first agent step,
  `-1` = never) and `presatisfied_at_spawn`.
- `settings`: what the cell ran under — 300 steps, temperature 0.7 / top_p 0.8 / top_k 20,
  a 1024-token server-side output cap, thinking off, hint protocol on, one seed,
  `codex_sandboxed`, and which server port served it.
- `cost`: wall seconds, `ceiling_hits`, and for the codex arms `analyzer_turns`,
  `wire_requests`, `input_tokens`, `output_tokens` (codex's own accounting, from the
  rollouts — the direct-vLLM arms send exactly one request per step, so their cost is the
  step count).

**step** — `step` (1-indexed), and:

- `pos` — the player's position and look angles *after* the action was applied.
- `rules` — `{milestone_id: [bool, ...]}`, one bool per rule of that milestone, as the
  checker saw it on this step. This is the trajectory's ground truth; a milestone
  completes when all of its rules pass.
- `completed` — present only on the step where a milestone first completed:
  `[{"milestone": id, "frame": n}]`.

For the arms that call the model once per step (`default`, `hypothesis`, either channel):

- `thought`, `action`, `memory` — parsed out of the model's reply. `action` is the action
  dict actually sent to the environment.
- `hypotheses`, `plan` — hypothesis agent only: the DAG update and the 3-step plan the
  model returned on this step. The DAG is advisory; it never overrides `action`.
- `attempt` — which JSON-parse attempt produced the reply (1 unless the first was
  malformed).
- `unparsed` — the reply, truncated to 500 characters, when it was not valid JSON. The
  agent stepped its no-op action instead. (A degenerate reply can be 1024 tokens of `!`,
  hence the truncation.)
- `ceiling: true` — the call ran to the provider's per-call ceiling and never returned, so
  there is no reply for this step and the agent stepped the no-op. Only `default × codex`
  has these: 748 of its 2100 steps.

For `prolong`, the model is not called per step — one analyzer turn writes a program that
covers many steps — so there is no `thought`/`action` per step. Instead:

- `analyzer_turn` — which turn's program produced this step.
- the turn's own reasoning is in the sibling `.prolong_log.txt`, which is the append-only
  log the agent reads and writes as its memory.

## Reading it

```python
import json
steps = [json.loads(l) for l in open("Qwen3.5-27B/default-vllm-0306.jsonl")]
meta, steps = steps[0], steps[1:]
# where did it get stuck?
[(s["step"], s["pos"]["x"], s["pos"]["z"]) for s in steps if s["step"] % 50 == 0]
# what did it believe at the step a milestone landed?
[s["thought"] for s in steps if "completed" in s]
```

`../4hop_cells.csv` is every episode as one row each, if you want the outcomes without
opening the traces.

## The `q35a` hypothesis episodes

48 episodes of the `hypothesis` arm on the 154-scene 4-hop set, Qwen3.5-27B, 200 steps.
Exported with

    python scripts/export_4hop.py --campaign q35a:Qwen3.5-27B --agent hypothesis \
        --trace-name tag --with-runner-log --no-csv

**The agent ran the set twice, and both runs are here.** Arm 2 launched on the `legacy`
prompt layout, was stopped when the prefix-cache diagnosis moved the direct arms to
`append-only`, and relaunched:

| files | layout | cells | covers the 20 scenes every arm shares |
|---|---|---|---|
| `q35a-hypothesis-vllm-<scene>.*` | legacy | 28 | yes, all 20 |
| `q35a-hypothesis-vllm-append-only-<scene>.*` | append-only | 20 | yes |

That pair is the reason to read these together rather than separately: on the shared 20
the legacy run scores 18/80 and the append-only run 14/80, so **the same agent's two runs
differ by exactly the margin that separates it from `default`** (18/80). The reading is
[`../ANALYSIS_hypothesis_vs_default.md`](../ANALYSIS_hypothesis_vs_default.md); the
statistics behind it are in [`../stats_hyp_vs_default/`](../stats_hyp_vs_default/).

Three things differ from the seven-scene traces:

- **Named by cell tag**, not by `<agent>-<channel>-<scene>` — the two runs differ only in
  prompt layout, so they collide under the older naming. The tag is the same string used
  in `outputs/`, in `4hop_cells.csv` and in the log filenames.
- **`settings` carries `prompt_layout` and `response_style`.** By this repo's rule anything
  but `legacy`/`full` is a different arm, so a trace has to say which it was. These runs
  are `full` style throughout; the layout is the axis that changes.
- **`.runner_log.txt` is included**: the raw loguru output for the cell, which the `.jsonl`
  is parsed from. Use it for what the trace drops — replies that failed to parse, the
  harness's own ESC-refusal and milestone warnings, and per-step timings. No frames are in
  it (image payloads are elided at log time), so it is plain text throughout.

`max_steps` is **200** here, not the 300 of the seven-scene campaigns; `4 of 35` milestones
in the earlier runs were first reached after step 200, so every q35a arm is measured below
its own ceiling.
