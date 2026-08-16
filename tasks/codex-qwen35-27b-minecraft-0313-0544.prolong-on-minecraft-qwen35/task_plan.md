# Task Plan: prolong-on-minecraft-qwen35

Port the PRO-LONG programmatic-memory harness (github.com/alexisfox7/PRO-LONG,
arXiv 2607.20064) onto the native aarch64 MineExplorer sandbox, driven by the local
Qwen3.5-27B through the Codex CLI.

## Stable Anchor

- Scientific question: does PRO-LONG's programmatic memory — one append-only `logs.txt`
  the agent greps/parses itself, instead of a fixed sliding frame buffer — improve
  multi-hop performance on an *embodied, visual* benchmark, or is the gain specific to
  ARC-AGI-3's losslessly-textual grid boards?
- Target claim: on MineExplorer scenes, with model, information and scorer held fixed,
  PRO-LONG's memory architecture changes milestone completion by a measurable margin
  relative to the current `deque(maxlen=20)` frame-buffer agent.
- Success criterion: both arms run to completion on the same scenes under the same
  paper protocol (`MILESTONE_HINT=0`), scored by the *same* `MilestoneChecker.check(info)`,
  with per-arm milestone counts and token/wall-clock cost recorded.
- Constraints: DeltaAI aarch64/GH200, no Docker, single local Qwen3.5-27B behind
  `transformers serve` (no prefix caching), `ghx4` partition, budget for this phase
  E0/E1 only.
- Non-goals: reproducing PRO-LONG's ARC-AGI-3 numbers; ARC API access; training or
  fine-tuning; multi-seed statistical claims; any hosted-model comparison.

## Current Cycle

- Working hypothesis: the Codex CLI can be pointed at the local Qwen3.5-27B via a
  custom `model_provider`, and Codex's agent loop is functional enough on a 27B model to
  produce a valid `actions.json` each turn.
- Main uncertainty: **R1** — whether `codex exec` completes a tool-using turn against
  `transformers serve` + Qwen3.5-27B at all. Everything downstream is wasted if not.
- Next decisive experiment: gate test G1 (below) — `codex exec` writing one file, then
  one `actions.json`, against the local server on a `ghx4` node.
- Expected pass/fail signal: `last_message.txt` written and a well-formed
  `{"actions": [...]}` parsed by `BaseAgent._parse_actions_json_text`.
- Fallback: bypass the Codex CLI and reimplement the PRO-LONG *loop* (log + grep/bash
  tools + actions.json) directly against `/v1/chat/completions`, keeping the memory
  architecture and dropping the CLI. Costs the "same harness" claim, keeps the science.

## Design Decision: what goes into the log

Both scenes score exclusively on `position_near_with_facing` (0313: targets
`(0,2,5)` d≤5 and `(0,1,10)` d≤4; 0544: `(8,1,8)` d≤8 and `(5,0,8)`), i.e. *be within
N blocks of a coordinate and face it within 60°*. Nothing in the rule requires seeing
anything. So the log's information content decides what is actually being measured.

| arm | log content | comparable to baseline? | what it measures |
|---|---|---|---|
| **B (headline)** | frames as files + `player_pos`/pitch + movement deltas + actions + agent notes — exactly the information the current baseline prompt already carries | **yes**, single variable = memory architecture | does programmatic memory help an embodied VLM agent |
| **A (ablation)** | B + `VoxelsCallback` 15³ block list (`{"type","x","y","z"}`) | no — new ground truth | upper bound: memory + symbolic world state |
| **C** | B + `--log-window 25` and `--log-window -1` | yes | PRO-LONG's own ablation axis, transferred |

Run B first. A is diagnostic only and must never be reported as a MineExplorer score.
Note that position/pitch is *already* in the baseline prompt (`_camera_state_hint`,
`_movement_state_hint`), so arm B adds no information — only a different way to hold it.

## Success Criteria

- [ ] G1 passes: Codex CLI drives local Qwen3.5-27B to a valid `actions.json`.
- [ ] `prolong-mc` runs scene 0313 end to end and produces a milestone count from the
      unmodified `MilestoneChecker`.
- [ ] Arm B vs. current baseline on 0313+0544, same protocol, both numbers recorded
      with wall-clock and token cost.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current | none | final synthesis | active |
| W1 serving | primary | implement | current | none | Codex→Qwen provider config | pending |
| W3 adapter | primary | implement | current | G1 | `MineExplorerEnv` + log format | pending |

## Phases

### Phase 1: Feasibility gate (G1)

- [ ] Write `~/.codex/config.toml`-free `-c` overrides: `model_provider=local`,
      `model_providers.local.base_url=http://127.0.0.1:30000/v1`, `wire_api="chat"`,
      `env_key`. (`--ignore-user-config` in PRO-LONG's args means `-c` is the only route.)
- [ ] On a `ghx4` node with the Qwen server up: `codex exec` a trivial file-write, then
      a PRO-LONG-shaped prompt that must produce `actions.json`.
- [ ] Record: does it complete, how many internal LLM calls, seconds per turn, tokens.
- **Status:** pending
- **Evidence:** none

### Phase 2: Port (only if G1 passes)

- [ ] **W2 de-Docker** `codex_agent.py`: replace the `docker run` argv with a direct
      `codex exec` in the workspace dir (`cwd=sandbox`, host paths for `-o`), keep
      `--json --skip-git-repo-check --ignore-user-config`, add the provider `-c` flags.
- [ ] **W3 env adapter** `MineExplorerEnv(BaseEnv)` over `env/minerl_sandbox.py`,
      replacing `arcagi3.py`. `reset/step -> (obs, reward, done)`.
- [ ] **W4 log format** replacing `game_state.render_board`: per step append action,
      resulting position/pitch, movement delta, and `frames/step_NNNN.png`. The agent
      reaches frames with Codex's `view_image` tool — a good fit for PRO-LONG's thesis
      (grep the text trace, selectively re-view the pixels). Cap images per turn.
- [ ] **W5 action vocabulary**: `actions.json` entries become MineExplorer action dicts
      validated by `mc_agent/action_space.py`, plus `{"action": {...}, "repeat": N}` so
      one plan can cover many env ticks. Cap total env steps per plan.
- [ ] **W6 runner**: strip ARC level/attempt/scorecard bookkeeping from `runner.py`;
      keep the queue + analyzer-fire loop; score `MilestoneChecker.check(info)` every
      env step exactly as `eval_benchmark.py` does; terminate on ESC or `MAX_STEPS`.
- [ ] **W7 harness**: `scripts/run_prolong_minecraft.sh` under
      `scripts/with_minecraft_arm64.sh`, launched through `scripts/launch.sh`.
- **Status:** pending
- **Evidence:** none

### Phase 3: Measure and interpret

- [ ] E1 pilot: scene 0313, `MAX_STEPS=60`, to measure seconds/analyzer-call and
      internal-call count before committing to a full run.
- [ ] E1 arm B vs. baseline on 0313 + 0544, `MILESTONE_HINT=0`, `MAX_STEPS=300`.
- [ ] Interpret against the anchor; one seed, so no capability claim.
- **Status:** pending
- **Evidence:** none

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| Docker sandbox | Dropped. Unavailable on DeltaAI (established in the arm64 task). Codex runs natively with `-s danger-full-access` in a scratch workspace. | prior task findings 1-5 |
| Model wire | `transformers serve` exposes `/v1/chat/completions` *with* `tools`/`tool_calls` parsing and `/v1/responses`. Not a blocker on paper; unproven in practice. | `transformers/cli/serving/chat_completion.py:157,264-284` |
| Codex features | Native aarch64 binary has `model_providers`, `wire_api`, `base_url`, `env_key`, `view_image`. | `strings` on the vendored binary, codex-cli 0.147.0 |
| `voxels` | Present as an info key but **empty** — `VoxelsCallback` is not registered by our server. Enabling it is a one-line change but moves us to arm A. | `scripts/minecraft_arm64/mc_server.py:196-229` |
| Prefix caching | None in `transformers serve`. Every internal Codex call re-prefills the whole growing log. Primary cost risk. | design constraint |

## Verification Contract

- Command or probe: G1 — `codex exec --json -c model_provider=local ... "write /workspace/actions.json with {\"actions\":[...]}"`
- Expected signal: exit 0, `last_message.txt` present, `_parse_actions_json_text` returns a non-empty list.
- Experiment/run pointer, if any: `[none yet]`

## Next Action

Run gate test G1 on a `ghx4` node.
