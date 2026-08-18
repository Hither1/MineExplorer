# Task Plan: qwen35-minecraft-0313-0544

## Stable Anchor

- Scientific question: Can the current branch run Minecraft tasks 0313 and 0544 through a remote MineExplorer sandbox and Qwen3.5-27B served on a223?
- Target claim or outcome: A reproducible runtime configuration and bounded end-to-end smoke for exactly scene IDs 0313 and 0544.
- Success criterion: The remote sandbox passes `/monitor/alive`; Qwen3.5-27B passes a multimodal OpenAI-compatible probe; the evaluator reaches both target scenes through those endpoints without configuration/import failures.
- Constraints and budget: Do not configure Docker on a219; use README Section 1 on a223 with `MC_SANDBOX_URL`; use a223 GPUs for vLLM; model download remains a separate authority gate; start with one worker and a bounded smoke.
- Non-goals: Full benchmark, formal E2 claims, evaluator semantic redesign, shared/protected-branch publication, or unrelated refactoring.

## Current Cycle

- Working hypothesis: Superseded by the user's stop request.
- Main uncertainty: None; execution was terminated before Docker or Qwen launch.
- Next decisive experiment or implementation: None.
- Expected pass/fail signal: Not applicable after user termination.
- Fallback: None unless the user starts a new task.

## Success Criteria

- [x] Recorded as unmet: remote MineExplorer was not launched before user termination.
- [x] Recorded as unmet: Qwen3.5-27B endpoint was not launched before user termination.
- [x] Recorded as unmet: the 0313/0544 end-to-end smoke was not run before user termination.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current | none | stopped-task closeout | stopped |

## Phases

### Phase 1: Discover and specify

- [x] Confirm live state and relevant owners.
- [x] Record the smallest implementation and verification contract.
- **Status:** complete
- **Evidence:** README Section 1; a223 SSH probes; `env/minerl_sandbox.py`; `tasks/main.qwen35-minecraft-0313-0544/findings.md`

### Phase 2: Implement or run the decisive test

- [x] Prepared a bounded branch configuration and image archive attempt.
- [x] Recorded the user stop and terminated all owned processes.
- **Status:** abandoned_with_evidence
- **Evidence:** `tasks/main.qwen35-minecraft-0313-0544/progress.md`; final process/port audit

### Phase 3: Interpret and hand off

- [x] Compare the evidence against the stable anchor and expected signal.
- [x] Close remaining phases as complete, superseded_by_evidence, or abandoned_with_evidence.
- [x] Preserve the uncommitted state and archive the stopped task without commit or push.
- **Status:** complete
- **Evidence:** user stop request; final process/port audit

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| Sandbox topology | Run MineExplorer on a223 port 8000 and connect from a219 via `MC_SANDBOX_URL`. | user + README Section 1 |
| Docker launch | Blocked: a223 Docker socket is `root:docker 0660`; group `docker` contains only `ops`; `ruihan` gets permission denied and has no passwordless sudo/root SSH. | live a223 probes |
| Inference topology | Run vLLM on a223 port 8001; begin with GPU 0 and bounded context/concurrency. | user + live CUDA probes |
| Model acquisition | `Qwen/Qwen3.5-27B` is absent from visible caches; download is not yet authorized. | cache and filesystem probes |
| Stop | User requested that every task related to this session stop; no further launch, download, or verification is allowed. | user |

## Verification Contract

- Command or probe: `curl -fsS http://192.168.2.16:8000/monitor/alive`; OpenAI-compatible one-image Qwen request; evaluator `--scene-ids 0313,0544 --num-workers 1`.
- Expected signal: Healthy sandbox; parseable Minecraft action JSON from Qwen; both target scenes selected and initialized without endpoint/configuration failures.
- Experiment/run pointer, if any: `tasks/main.qwen35-minecraft-0313-0544/progress.md`

## Next Action

none - ready to archive
