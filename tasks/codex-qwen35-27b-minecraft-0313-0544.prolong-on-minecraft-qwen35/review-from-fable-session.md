# Consolidated review — Fable session, 2026-08-16 (supersedes all earlier versions of this file)

Source: read-only review sessions by a separate Claude session (Fable 5) with dz.
Everything here is either a dz decision, a measured fact with its evidence path, or a
verified code-level finding. Items are ordered by how directly they affect the
numbers you will publish.

## Decisions from dz (settled, do not relitigate)

1. **TP=2, not TP=4.** TP=4 checks out technically (4×GH200/node, all head counts
   divide by 4) but 1N/4G queues too slowly on ghx4. TP=2 it is.
2. Forced vision for the PRO-LONG analyzer (landed — see §5).
3. Hint protocol for the matrix (landed).
4. **Every path gets the same 4096 output cap** — align with MineExplorer's own
   default (VLLMProvider caps at 4096 on main too). See §1b for the one place it
   can be set for the codex path.
5. **Thinking: align with MineExplorer main.** Main's contract is tolerate-and-strip
   (`extract_json_from_response` removes `<think>…</think>` first thing,
   `mc_agent/action_space.py:133` — present on main) with no server-side control;
   the branch's Qwen3.5 protocol served with `--reasoning off`. Pin
   `enable_thinking: false` server-side: it matches the observed Qwen3.8 behavior
   (no think output today), matches the 3.5 protocol, and prevents a silent flip on
   a future vLLM/template upgrade. The parser's strip stays as the second line of
   defense.
6. The codex-side anomalies (§1b: fallback metadata, multi-request steps) are to be
   investigated and fixed, not just documented.

## 1. URGENT — the queued TP=2 server (job 2958632) is still eager; add cudagraphs or it buys little

The run command sets only `VLLM_TP=2 VLLM_MAX_MODEL_LEN=131072`; `serve_vllm.sh`
still defaults `EAGER=1` → `--enforce-eager`. Measured on the live 131k server:

- Decode **~12.5 tok/s per request** (engine 25 tok/s across 2 running reqs);
  server log: "Enforce eager set, disabling torch.compile and CUDAGraphs".
- One baseline step (call_0056 of m1-default-0313-s3): input 36,679 tok (cached 0),
  output 1,381 tok, `reasoning_output_tokens: 0` (thinking is NOT the problem).
  Decode alone ≈ 110 s of the ~156 s step; prefill bursts at 2-4k tok/s are fine.
- Root cause is launch overhead: Grace (ARM) CPUs pay high per-kernel-launch cost,
  and a 64-layer hybrid model decoding at bs=1-2 in eager mode is launch-bound —
  exactly where CUDA graphs pay most. The serve_vllm.sh comment ("one request at a
  time, so CUDA graphs buy little") has it backwards. **Under eager, TP=2 adds ~2
  all-reduce launches per layer per token while shrinking per-kernel work — near-zero
  net gain.** Graphs first, TP second, same change.

**Fix** (avoids the compile host-OOM that motivated eager): replace `--enforce-eager`
with `-cc.mode=none -cc.cudagraph_mode=FULL_DECODE_ONLY`. This captures cudagraphs
over eager kernels with no Dynamo/Inductor pass, so the "Dynamo bytecode transform"
host-memory blowup cannot recur. Verified against the installed vLLM 0.27.1:
`CUDAGraphMode.FULL_DECODE_ONLY` exists (`vllm/config/compilation.py:62`) and is
vLLM's own fallback for attention that cannot do piecewise graphs (`:1409`).

Expected: graphs 2-4× (12 → 30-50 tok/s), TP=2 another ~1.5-1.8× → **~50-80 tok/s
per request**; the 1,381-tok decode drops 110 s → ~20-25 s, prefill roughly halves.
A 150-step baseline episode lands around 1.5 h against a 6 h walltime, which retires
finding 54's truncation asymmetry at the root. Keep the bad-node exclusions
(gh089, gh108, gh131) on the *server* job too — TP makes it interconnect-sensitive.

Two non-levers, so nobody reaches for them: prefix caching is auto-disabled for this
hybrid linear-attention architecture (recurrent state is not paged KV) — the 36.7k
re-prefill per step is a model-class property and grows with history, so budget
late-episode step time; FP8/speculative decoding would change the measured subject
mid-study (dz's call, not a serving tweak).

## 1b. Per-step output cap — the codex path has none (dz question, 2026-08-16)

Current state of max_tokens across the providers:
- `VLLMProvider.chat` defaults to **4096** and passes it to the server — the direct
  vLLM arm has a real per-step cap. (`BaseLLMProvider`'s 10240 is just the abstract
  signature; `OpenAIProvider` passes no cap; neither is in play now.)
- `CodexProvider`/`CodexTurn` — every current Qwen3.8 arm — **deliberately ignore
  max_tokens** (documented in the code), and codex 0.147 has no
  `max_output_tokens`-style config key (checked the binary), so the cap cannot be
  set client-side. vLLM's Responses path with max_tokens unset generates until EOS
  or the 131k context end.
- Observed outputs self-terminate at ~1.4k tok/step, so nothing has burned yet — but
  one degenerate repetition loop would write toward 131k at 12 tok/s: hours inside a
  single call, with the job looking alive. No invariant currently catches it.

Fix, one server-side line in the same change as graphs+TP=2:
`--override-generation-config '{"max_new_tokens": 4096}'` — flag verified in the
installed vLLM 0.27.1 (`engine/arg_utils.py:691,898`). Applies to every request,
matching the vLLM arm's 4096. Note it caps each internal codex request separately
(a turn's analysis request and its post-tool request each get 4096), which is ample
against the observed ~1.4k. (Key-name check redone against the REAL vendored binary
at `@openai/codex/node_modules/@openai/codex-linux-arm64/vendor/...` — the first
check accidentally hit a nonexistent path: `model_max_output_tokens` is confirmed
absent, so server-side really is the only place to cap Qwen. Hosted gpt-5.6 has no
cap lever at all; document that asymmetry rather than pretending parity.)

Thinking pin, same change (dz decision #5): vLLM 0.27.1 has
`--default-chat-template-kwargs` (JSON; `entrypoints/openai/cli_args.py:93`, and the
Responses path reads chat_template_kwargs in `responses/serving.py`). Serve with
`--default-chat-template-kwargs '{"enable_thinking": false}'` — verify the kwarg
name against Qwen3.8's actual template first (finding 38 says 3.8 also injects a
`reasoning_effort` instruction; render the template once with/without the kwarg and
diff). Codex sends no per-request template kwargs, so the server default governs.

Codex metadata fix (dz decision #6): the vendored binary DOES have a
`model_context_window` config key (7 hits in strings; `model_max_output_tokens`
does not exist). Add `-c model_context_window=131072` to BOTH `CodexProvider` and
`CodexTurn` arg builders — that is the direct fix for the per-turn "Model metadata
… not found, defaulting to fallback metadata" warning, and it makes codex's own
context accounting real instead of guessed.

**One consequence to check before trusting it for PRO-LONG**: the binary also
carries `model_auto_compact_token_limit` and auto-compact fallback prompts. With a
correct context window declared, codex may start auto-compacting the resumed
conversation as it approaches the limit — which would quietly change the PRO-LONG
memory story (upstream's stance, echoed in our overflow handler, is "Codex has no
native compaction; the session must be restarted", and the cold-start-on-overflow
path is what keeps logs.txt the memory of record). After setting the key, grep a
long episode's transcripts for compaction events: if codex compacts, decide
explicitly — either disable via `model_auto_compact_token_limit` (if it accepts
off/huge) to stay upstream-faithful, or re-document the arm as "codex-compacted
conversation + log". Do not let that choice happen by default.

Multi-request steps: do NOT strip codex's tools to force one request per step —
that would redefine the "model via the codex harness" arm mid-study. Instead count
model requests per step from the events transcripts (they are already saved) and
report request counts, not step counts, wherever per-call cost is compared.

Two side-findings from the same investigation:
- **"One call per step" undercounts the codex path**: call_0056 shows one step
  containing ≥2 model requests (an analysis message, then a bash `echo` the model
  used as a scratchpad, then the JSON) — each re-paying the full ~36.7k prefill.
  Worth remembering when comparing per-call costs across arms.
- codex logs `Model metadata for Qwen/Qwen3.8-27B not found. Defaulting to fallback
  metadata` on every turn — codex's assumptions about the model's context size come
  from a fallback and may affect its own truncation behavior. Record it; consider
  whether the served model name should match something codex knows.

Thinking status, stated precisely (dz asked): across all 60 calls of
m1-default-0313-s3 there are zero `<think>` tags, zero reasoning items, and
`reasoning_output_tokens: 0` — **thinking is off in the output**. The model does
spend ~2/3 of its ~1.4k output tokens on free-form deliberation prose before the
JSON, but that is style, not the thinking channel, and the volume is normal. What is
NOT verified is *why* thinking is off given Qwen3.8's template defaults it on
(finding 38) — likely a property of vLLM's template rendering on this path. If a
vLLM or template upgrade flips it back on, cost and behavior change suddenly; worth
one ledger line, and pinning it explicitly if a knob exists.

## 2. compare_runs.py — three small fixes

The TRUNCATED ledger rule already resolved the biggest issue here (the cap-40 probe
polluting pooled totals) — the symmetric inclusion rule and its stated-exclusion
principle are exactly right. Remaining:

- **"over N scene(s)" counts rows, not distinct scenes.** With seed replicates the
  prolong line reads "9/9 over 5 scene(s)" for what is 2 distinct scenes. Count
  distinct scenes, or relabel to "run(s)".
- **`view_image` counter double-counts.** `codex_backend.py` counts every event LINE
  containing `"view_image"`; a single call typically emits item.started AND
  item.completed → ~2× overcount. All observed values are 0 so far, so nothing is
  damaged yet — fix before the number is ever nonzero and quoted.
- **`channel()` reads scripts' CURRENT content to label historical runs.** A future
  edit to a runner script silently relabels old manifests. New runs are covered by
  result.json's `provider` field; for the handful of pre-`provider` runs, consider
  freezing their channel labels in RUN_LEDGER.txt instead of re-deriving.

## 3. Open port gaps — must land before any arm-C (ablation) run

Both verified against upstream at `/work/nvme/bdrx/dzhang5/PRO-LONG`:

- **stateless is prompt-only in the port.** Upstream deletes workspace files each
  turn, keeping only logs.txt + AGENTS.md (`codex_agent.py:449-460`); the port only
  rewords the prompt, so agent notes actually persist. (Keeping the codex session
  alive in stateless IS upstream behavior — do not "fix" that part.)
- **log_window is soft in the port.** Upstream's sandbox contains ONLY the truncated
  log copy; the port writes `logs_window.txt` NEXT TO the full `logs.txt`, which the
  model can still grep. Enforce (move the full log out of the visible workspace)
  before any window ablation.

## 4. Minor — prolong log fidelity

`describe_entry` logs the agent's RAW action dict, not the normalized wire dict:
camera yaw 270 executes as -90 but the log says 270, and unknown keys that were
ignored at parse time still appear in the log — the memory can claim actions that
never executed. Low priority; consider logging the normalized form (or both).

## 5. Verified working — no action needed

- All four fixes from the earlier handoff landed correctly and were re-reviewed
  line-by-line: frame attach (`-i` placed before `-m` so the variadic flag cannot
  swallow the resume session id; `codex exec resume -i` verified), overflow
  classifier + session reset (mirrors upstream `codex_agent.py:207-221`),
  `_last_entry` consumed after write (duplicate-section bug gone), stale workspace
  renamed to `.crashed` (resume pollution gone, evidence preserved).
- Vision audits confirm the mechanism live: `frames_attached == analyzer_turns`,
  `view_image_calls: 0`, `overflow_resets: 0` across all forced-vision runs.
- milestone_hint parity is clean: [MILESTONE] documented to the analyzer only under
  the hint protocol, mirroring the baseline's conditional context section; ESC
  refusals batched as one counted [NOTE] per section; status written on change only.
- result.json self-describes protocol/provider/agent_mode/max_steps — correct fix
  for the slug-guessing mislabels.
- `prolong_mc/selftest.py` passes (43 checks) under the project env.

## 6. Interpretation guardrails for the eventual writeup

- **Variance first**: two identical default runs differed by more than the two arms
  differ (finding 53). No claim rests on single seeds; every compared cell needs
  several seeds, and `--temperature` does not reach the codex path at all.
- **PRO-LONG's measured advantage is cost, not steps**: ~6× fewer model calls and
  ~10× smaller prompts (finding 55 retired the step-efficiency impression, which was
  a no-hint-protocol artifact). Report cost as cost, never smuggle it as capability.
- Truncated runs are excluded ONLY with the exclusion stated (the ledger's own rule):
  budgets bind the one-call-per-step arm first, so silent dropping would manufacture
  a PRO-LONG win.
- Every prolong score is reported next to its `prolong_vision_audit.json`; the
  vision-on-demand v3/v4 runs are their own arm and are never averaged in.
- 0802 is reported separately from 0313/0544 (finding 29: 0313's first hop needs
  0.56 blocks; 0802 needs ~4.5 blocks of real navigation).
