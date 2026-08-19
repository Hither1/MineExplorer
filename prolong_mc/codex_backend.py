"""Drive one PRO-LONG turn through the Codex CLI.

This implements upstream's contract -- a persistent workspace, AGENTS.md carrying the
system prompt, a turn prompt pointing at logs.txt, `actions.json` as the only output
that matters, and `codex exec resume` for conversation continuity -- but it is our
code, not a fork of `prolong_agent/agent/codex_agent.py`.

That file is 770 lines, and the majority of it is Docker orchestration, ARC prompt
assembly and OpenAI price tables, none of which survives here: DeltaAI has no usable
container runtime, the prompts are replaced wholesale, and a subscription model
reports no per-token price. What remains after removing those is roughly what follows.
Deviations from upstream worth naming: no container (Codex's own bubblewrap sandbox
via `-s workspace-write` covers the same threat model), and subscription auth instead
of the required CODEX_API_KEY.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from loguru import logger

_SESSION_RE = re.compile(r'"(?:thread_id|session_id)"\s*:\s*"([0-9a-fA-F-]{36})"')
# Compaction announces itself in a type-ish field, never in prose, so this cannot be
# tripped by a model that happens to write the word. See `_metadata_args` for why a
# single hit matters.
_COMPACTION_RE = re.compile(r'"(?:type|kind|action_trigger)"\s*:\s*"[^"]*compact', re.I)

# What codex should believe about a locally served model. Codex has no catalog entry
# for it -- every turn logs `Model metadata for <name> not found. Defaulting to
# fallback metadata` -- so without this its context accounting is a guess.
#
# Two things this is NOT. It does not silence that warning: the warning is emitted by
# the catalog lookup on the model *name*, and it still appears verbatim with
# `-c model_context_window=131072` set (measured against a no-config baseline and
# against `-m gpt-5.6-sol`, which is in the catalog and warns not at all). Silencing it
# needs `model_catalog_json`, whose schema is an undocumented nested struct that would
# break every run on a codex upgrade -- not worth buying a quieter log with. And it is
# not applied to hosted models, where codex's own metadata is right and ours would be
# a guess overriding a fact.
DEFAULT_CONTEXT_WINDOW = int(os.environ.get("CODEX_MODEL_CONTEXT_WINDOW", 131072))


def effort_for(base_url: str | None, effort: str) -> str:
    """The reasoning effort to send, which on a local server is the thinking switch.

    `--default-chat-template-kwargs '{"enable_thinking": false}'` does not reach the
    codex arms. vLLM synthesises `enable_thinking = (effort != "none")` from a Responses
    request's `reasoning.effort` and merges it as `defaults | request`
    (`responses/protocol.py:329-330`, `renderers/params.py:99-115`), so the request wins
    and the server's pin is overridden by every codex turn.

    Measured, not inferred. Codex puts `reasoning: {"effort": ..., "summary": "auto"}` on
    the wire verbatim and sends no `chat_template_kwargs` of its own, so effort is the
    only lever it has. Rendering Qwen3.8's pinned template shows what each value buys:
    with thinking enabled the generation prompt ends with a bare `<think>` and the system
    message gains "Reasoning effort is set to <effort>"; with `none` it ends with an
    already-closed `<think></think>` and no effort instruction -- byte-identical to what
    the server pin produces for the direct-vLLM arm, which is the alignment dz asked for.

    This also names what the finished Qwen3.8 runs were really doing: thinking was ON for
    all of them. The absence of `<think>` in their output is because the tag sits in the
    prompt, and the "free-form deliberation before the JSON" was the thinking channel
    without a label.

    Hosted models keep the caller's effort: there the field means what codex means by it,
    and nothing downstream reinterprets it as a template switch.

    **The invariant this function exists to hold: the codex arms and the direct-vLLM arm
    must agree about thinking.** They are configured from opposite ends -- the server's
    `--default-chat-template-kwargs` governs the direct arm, this value governs the codex
    arms -- so nothing but care keeps them together, and a matrix whose channel control
    differs in thinking cannot separate the agent axis from the channel axis.

    So a local server gets the caller's effort through, and thinking is on for both by
    default, matching `scripts/serve_vllm.sh`. Turning it off is one variable changed on
    two sides: `CODEX_LOCAL_EFFORT=none` here and `VLLM_CHAT_TEMPLATE_KWARGS` there.
    Setting one without the other is the bug this note is about; `selftest.py` asserts the
    two defaults agree.

    Both settings are worth having because the choice has a measured cost. With thinking
    off the default arm looped on `echo ok` 85 times inside one call and burned the client
    timeout -- 6 of 13 calls returned nothing on the 0313 diagnostic -- where the same arm
    with thinking on never exceeded 3 tool calls across 46, and PRO-LONG was unaffected
    either way. That measurement changed thinking and the sampling recipe together, so it
    does not yet say which is responsible; separating them needs both switches reachable
    from a run's environment rather than from an edit.
    """
    if not base_url:
        return effort
    return os.environ.get("CODEX_LOCAL_EFFORT", effort)


def _metadata_args(context_window: int) -> list[str]:
    """Codex config for a model codex has never heard of.

    `model_auto_compact_token_limit` is the load-bearing one. The vendored binary
    carries auto-compaction and its fallback prompts, and telling codex the real
    context window is exactly what would let it start compacting a long resumed
    conversation as it fills. That would quietly replace PRO-LONG's memory story:
    upstream's stance, which our overflow handler mirrors, is that codex has no
    compaction and an overflowed session must cold-start, which is what keeps logs.txt
    the memory of record. Set the trigger above the window so the server's own context
    limit -- and the cold start that follows it -- always arrives first.

    The direction of that comparison is inferred, not documented, so it is not trusted
    on its own: `CodexTurn` counts compaction events in the transcripts and reports
    them in the vision audit, and a nonzero count means this argument is wrong and the
    arm needs re-describing rather than quietly re-running.
    """
    return [
        "-c", f"model_context_window={context_window}",
        "-c", f"model_auto_compact_token_limit={context_window * 8}",
    ]


# What the model is allowed to hold in its hands, fixed here rather than left to codex's
# defaults. Measured on codex-cli 0.147.0 (2026-08-17) on the sibling mllm-search port,
# same subscription account: without these the tool list carried `web__run` -- and the
# model used it to fetch a Wikipedia article -- plus ~250 account-level
# `mcp__codex_apps__*` connectors (github, gmail, slack, google_drive, hugging_face, ...)
# and the sub-agent tools (`spawn_agent`, ...). All of them run server-side or in the
# codex process itself, so no local sandbox is on their path; only config is.
#
# This matters more here than the filesystem does. A scene's milestones are
# `position_near_with_facing` against coordinates that sit in
# `benchmark/<scene>/multi-agent/metadata.json`, and a connector that can fetch a repo --
# or a web search against a public benchmark -- is a way to those coordinates that never
# touches this host's filesystem.
#
#   web_search          default "cached": OpenAI's web index.
#   features.apps       account connectors; the docs say their "traffic [is] not
#                       controlled by sandboxed-command network proxy".
#   agents.enabled      the sub-agent tools. `--disable multi_agent` does NOT remove
#                       them (measured); this key does. Off so one analyzer turn is one
#                       thread and `request_stats` means what it says.
#   plugins/remote      the plugin catalog and its `request_plugin_install` tool.
#   image/goals         server-side image generation and goal state; off so the nested
#                       tool list is exactly EXPECTED_NESTED_TOOLS and a new default
#                       cannot slip in unnoticed.
SAFE_CODEX_FLAGS: tuple[str, ...] = (
    "-c", 'web_search="disabled"',
    "-c", "features.apps=false",
    "-c", "apps._default.enabled=false",
    "-c", "agents.enabled=false",
    "-c", "features.remote_plugin=false",
    "-c", "features.plugins=false",
    "-c", "features.image_generation=false",
    "-c", "features.goals=false",
)

EXPECTED_NESTED_TOOLS: frozenset[str] = frozenset({
    "apply_patch", "exec_command", "update_plan", "view_image", "write_stdin",
})


class SandboxViolation(RuntimeError):
    """A turn reached a capability the arm is defined not to have.

    Raised, not recorded: a web search or a connector call means the configuration in
    force is not the one the results claim, and the episode that follows it is
    contaminated -- the result sits in the resumed conversation and in whatever the
    agent wrote into its workspace.
    """


# A tool result is what makes codex send the model another request, so these are what
# turn one call into several. Named rather than inferred, so an unfamiliar item type is
# undercounted visibly instead of inflating the count silently.
_TOOL_ITEM_TYPES = frozenset({
    "command_execution", "view_image", "file_change", "patch_apply",
    "mcp_tool_call", "web_search", "todo_list",
})


def request_stats(events: str) -> dict[str, int]:
    """What one arm's calls actually cost, read off the saved event stream.

    "One call per step" is the wrong unit for the codex arms. A single turn runs an
    agentic loop: the model answers, calls a tool, and is asked again with the result
    appended -- turn_0003 of the m1-qwen38-prolong-0313 run is three requests (two bash
    calls plus the closing message) re-paying a ~46k-token prompt each time. Comparing
    per-call cost across arms without this counts a codex turn as one request and
    understates it by however many tools the model reached for.

    The alternative -- stripping codex's tools so a step is one request -- would redefine
    the arm mid-study, so this measures the harness that is actually being run.

    requests = one per tool result plus the one that closes each turn. Token totals come
    from codex's own `turn.completed` usage, so they are its accounting, not our estimate
    -- but that usage is CUMULATIVE over the thread: across one prolong episode it reads
    40k, 88k, 147k, 243k for turns 1-4 of the same resumed conversation. Adding those up
    is quadratic, and it is not a subtle error: summed naively, one 57-turn run claimed
    659M input tokens. So usage is returned per thread, to be maxed and only then summed
    (`merge_stats`); a session dropped after an overflow starts a new thread and its own
    counter, which is exactly the boundary the totals should respect.
    """
    out: dict[str, Any] = dict(turns=0, requests=0, tool_calls=0, agent_messages=0,
                               usage_by_thread={},
                               # Must all stay 0; see SAFE_CODEX_FLAGS.
                               web_searches=0, mcp_tool_calls=0, subthreads=0)
    thread = ""
    for line in events.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "thread.started":
            new_thread = event.get("thread_id") or ""
            if thread and new_thread and new_thread != thread:
                # A second thread inside one `codex exec` is a spawned sub-agent.
                out["subthreads"] += 1
            thread = new_thread
        elif kind == "item.completed":
            item_type = (event.get("item") or {}).get("type")
            if item_type in _TOOL_ITEM_TYPES:
                out["tool_calls"] += 1
            elif item_type == "agent_message":
                out["agent_messages"] += 1
            if item_type == "web_search":
                out["web_searches"] += 1
            elif item_type == "mcp_tool_call":
                out["mcp_tool_calls"] += 1
        elif kind == "turn.completed":
            out["turns"] += 1
            usage = event.get("usage") or {}
            seen = out["usage_by_thread"].setdefault(
                thread, dict(input_tokens=0, cached_input_tokens=0, output_tokens=0))
            for key in seen:
                seen[key] = max(seen[key], int(usage.get(key) or 0))
    out["requests"] = out["tool_calls"] + out["turns"]
    return out


def merge_stats(parts: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Total up per-call stats without double-counting codex's cumulative usage.

    Counts add; token usage is the per-thread maximum, summed across threads, because
    every turn of a resumed thread reports the whole thread's usage so far.
    """
    total = dict(turns=0, requests=0, tool_calls=0, agent_messages=0,
                 input_tokens=0, cached_input_tokens=0, output_tokens=0, threads=0,
                 web_searches=0, mcp_tool_calls=0, subthreads=0)
    per_thread: dict[str, dict[str, int]] = {}
    for part in parts:
        for key in ("turns", "requests", "tool_calls", "agent_messages",
                    "web_searches", "mcp_tool_calls", "subthreads"):
            total[key] += int(part.get(key) or 0)
        for thread, usage in (part.get("usage_by_thread") or {}).items():
            seen = per_thread.setdefault(
                thread, dict(input_tokens=0, cached_input_tokens=0, output_tokens=0))
            for key in seen:
                seen[key] = max(seen[key], int(usage.get(key) or 0))
    for usage in per_thread.values():
        for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
            total[key] += usage[key]
    total["threads"] = len(per_thread)
    return total


def is_overflow(name: str, text: str) -> bool:
    """Does this Codex error mean the model's context window is full?

    Mirrors upstream's classifier (`codex_agent.py:207-212`). Codex has no native
    compaction, so an overflowed session stays overflowed: every later turn on the
    same session id fails the same way. The only recovery is a cold start, which is
    cheap here because `logs.txt` -- not the conversation -- is the memory.
    """
    lname, lmsg = name.lower(), text.lower()
    return (
        "overflow" in lname
        or "too long" in lmsg
        or ("context" in lmsg and ("length" in lmsg or "limit" in lmsg or "window" in lmsg))
        or ("maximum" in lmsg and "tokens" in lmsg)
    )


# Codex 0.147 runs the model's tools inside a `exec` code-mode cell, and the `--json`
# event stream reports only *shell* commands (`command_execution`). A nested
# `tools.view_image(...)` -- which is how the model looks at a frame -- never appears
# there at all. Measured on the sibling mllm-search port's runs/cal_sbx/microvqa: 0 events mentioning view_image, while
# the conversation shows 20 calls returning 60 images.
#
# So the vision audit reads the rollout instead. That is the conversation as codex stored
# it, it is per-episode now that each episode has its own CODEX_HOME, and it is the only
# place two things are recorded:
#
#   view_image calls        what the model chose to look at
#   "could not read the     an `-i` attachment that did not land. This is the failure the
#    local image"           audit exists to catch: the run still scores, the counter still
#                           says images_attached=N, and the arm has silently become
#                           vision-on-demand instead of the forced-vision arm it claims.
_ROLLOUT_VIEW_IMAGE = re.compile(r"view_image")
_ROLLOUT_ATTACH_FAIL = re.compile(r"could not read the local image", re.I)


def scan_rollout(path: Path) -> dict[str, int]:
    """Count what the transcripts cannot show: nested vision calls and failed attachments."""
    out = {"view_image_calls": 0, "image_attach_failures": 0}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        # Two shapes, depending on how codex ran the tool: nested inside a code-mode
        # `exec` cell it is a `custom_tool_call` mentioning view_image (the sibling
        # port's runs); called directly it is a `function_call` named view_image (every
        # helixon run of 2026-08-18 -- the first version counted only the former and
        # read 0 against rollouts that held the call).
        if '"custom_tool_call"' in line:
            out["view_image_calls"] += len(_ROLLOUT_VIEW_IMAGE.findall(line))
        elif '"function_call"' in line and re.search(r'"name":\s*"view_image"', line):
            out["view_image_calls"] += 1
        if _ROLLOUT_ATTACH_FAIL.search(line):
            out["image_attach_failures"] += 1
    return out


def find_rollout(codex_home: Path | None, workspace: Path, session_id: str | None) -> Path | None:
    """The rollout file for this session, under whichever home the wrapper gave codex.

    Codex writes `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<session_id>.jsonl`.
    Which home that was depends on the wrapper in front of codex, and none of them is
    visible from here, so every candidate is searched in order of specificity:

      1. `codex_home` given to CodexTurn, then $CODEX_HOME -- what the runner asked for;
      2. $CODEX_EPISODE_HOME, then `<workspace>.codexhome` -- what `codex_sandbox.sh`
         gives codex, regardless of what the runner asked for (it --clearenvs);
      3. `~/.codex/runtime-home`, then `~/.codex` -- what the `codex` on PATH forces on
         this cluster (a wrapper that overrides CODEX_HOME), and codex's own default.

    The first version of this function returned None unconditionally, which made every
    vision audit report zeros and log "no rollout found" while the rollouts sat under
    the wrapper's home. Found 2026-08-18.
    """
    if not session_id:
        return None
    workspace = Path(workspace)
    home = Path(os.environ.get("HOME", "~")).expanduser()
    candidates: list[Path] = []
    for cand in (
        codex_home,
        os.environ.get("CODEX_HOME"),
        os.environ.get("CODEX_EPISODE_HOME"),
        workspace.with_name(workspace.name + ".codexhome"),
        home / ".codex" / "runtime-home",
        home / ".codex",
    ):
        if cand:
            cand = Path(cand)
            if cand not in candidates:
                candidates.append(cand)
    for cand in candidates:
        sessions = cand / "sessions"
        if not sessions.is_dir():
            continue
        hits = sorted(sessions.glob(f"*/*/*/rollout-*-{session_id}.jsonl"))
        if hits:
            return hits[-1]
    return None


def run_codex(
    args: Sequence[str], *, cwd: Path | str, prompt: str, env: dict[str, str] | None,
    timeout: float,
) -> subprocess.CompletedProcess:
    """`subprocess.run(capture_output=True, text=True)` that kills the whole process
    group on timeout.

    `subprocess.run` kills only its direct child. Here that child is a launcher -- the
    `codex` on PATH is a bash wrapper that execs node, which spawns the native codex
    binary; `codex_sandbox.sh` is bash around bwrap -- so on a timeout the process
    that is actually talking to the model survives as an orphan and keeps looping.
    Measured 2026-08-18: a default×codex call timed out at 420 s and its native codex
    was still issuing requests eight minutes later. Codex is started in its own
    session and the group is killed, so a timeout ends the requests as well as the
    wait. Raises `subprocess.TimeoutExpired` carrying the partial stdout/stderr, like
    `subprocess.run` does.
    """
    proc = subprocess.Popen(
        list(args), cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(list(args), timeout, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(list(args), proc.returncode, stdout, stderr)


class CodexTurn:
    def __init__(
        self,
        workspace: Path,
        *,
        model: str,
        reasoning_effort: str = "low",
        base_url: str | None = None,
        codex_bin: str | None = None,
        codex_home: Path | None = None,
        # See CodexProvider: the same ceiling, read from the same place, so a run that
        # bounds one arm's stalls bounds the other's identically.
        timeout: int = int(os.environ.get("CODEX_TIMEOUT", 1800)),
        transcript_dir: Path | None = None,
        context_window: int | None = None,
    ) -> None:
        # Absolute, always. Codex runs with cwd == this directory, so every path derived
        # from it -- `-o last_message.txt`, the `-i` frames -- is handed to codex relative
        # to *its* cwd. The sibling mllm-search port measured a relative workspace losing
        # every attached frame and every last_message.txt, silently.
        self.workspace = Path(workspace).resolve()
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url
        self.context_window = context_window or DEFAULT_CONTEXT_WINDOW
        self.codex_bin = codex_bin or os.environ.get("CODEX_BIN", "codex")
        self.codex_home = Path(codex_home) if codex_home else None
        self.timeout = timeout
        self.transcript_dir = Path(transcript_dir) if transcript_dir else None
        if self.transcript_dir:
            self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.session_id: str | None = None
        self.calls = 0
        # Audited in the comparison: an arm's score is only interpretable next to how
        # much vision it actually received.
        self.images_attached = 0
        # Read off the rollout at audit time, not from the event stream, which does not
        # carry them. See scan_rollout.
        self.view_image_calls = 0
        self.image_attach_failures = 0
        self.overflow_resets = 0
        # Must stay 0. A nonzero count means codex compacted the conversation, so the
        # arm is no longer "PRO-LONG memory + a cold start on overflow" and cannot be
        # averaged with the runs that were.
        self.compactions = 0

    def write_system_prompt(self, text: str) -> None:
        """Upstream puts the system prompt in AGENTS.md, which Codex discovers from
        the working directory. Written once; rewriting it mid-episode would change
        the agent's instructions underneath it."""
        agents_md = self.workspace / "AGENTS.md"
        if not agents_md.exists():
            agents_md.write_text(text, encoding="utf-8")

    def _args(
        self, images: Sequence[Path] = (), prompt_on_stdin: bool = True
    ) -> list[str]:
        args = [
            self.codex_bin, "exec",
            "--json", "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
        ]
        # Before -m, not after the last flag: -i/--image is variadic, so anything
        # positional that follows it is read as one more image path. On the resume
        # path that positional is the session id, and losing it would silently turn
        # every turn into a cold start. A non-variadic flag terminates the list.
        for image in images:
            args += ["-i", str(image)]
        args += [
            "-m", self.model,
            "-c", f'model_reasoning_effort="{effort_for(self.base_url, self.reasoning_effort)}"',
            "-o", str(self.workspace / "last_message.txt"),
        ]
        if self.base_url:
            args += [
                "-c", "model_provider=local",
                "-c", 'model_providers.local.name="local"',
                "-c", f'model_providers.local.base_url="{self.base_url}"',
                "-c", 'model_providers.local.wire_api="responses"',
                "-c", 'model_providers.local.env_key="LOCAL_API_KEY"',
            ] + _metadata_args(self.context_window)
        # workspace-write, not upstream's danger-full-access: writes stay in the
        # workspace and the agent's own commands get no network, so it cannot reach
        # the Minecraft sandbox and drive the world behind the runner's back.
        #
        # Set through -c rather than -s because `codex exec resume` rejects -s
        # ("unexpected argument '-s' found") while accepting the same config
        # override. Upstream hits this too and works around it by bypassing the
        # sandbox entirely on resume; that would leave every turn after the first
        # unconfined, so the config form is used on both paths instead.
        args += ["-c", 'sandbox_mode="workspace-write"']
        args += list(SAFE_CODEX_FLAGS)
        if self.session_id:
            # Documented order: codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]
            args = args[:2] + ["resume"] + args[2:] + [self.session_id]
        if prompt_on_stdin:
            args.append("-")
        return args

    def run(self, prompt: str, images: Sequence[Path] = ()) -> dict[str, Any]:
        """Execute one turn. Returns {"actions_json", "message", "ok", "error"}.

        `images` are attached to this turn's prompt unconditionally -- on the resume
        path too, which `codex exec resume -i` supports. Upstream's log carries the
        full observation as text; here the observation is pixels, so attaching the
        current frame is what keeps the analyzer as informed as upstream's is, and as
        informed as the baseline agent it is compared against.
        """
        self.calls += 1
        for stale in ("actions.json", "last_message.txt"):
            (self.workspace / stale).unlink(missing_ok=True)

        env = os.environ.copy()
        if self.codex_home:
            env["CODEX_HOME"] = str(self.codex_home)
        env.setdefault("LOCAL_API_KEY", "EMPTY")

        # Absolute, and present. Codex resolves `-i` against ITS cwd -- the workspace --
        # so a relative path that exists for the runner does not exist for codex, and the
        # only trace is a line in the conversation that the event stream never shows. The
        # sibling mllm-search port lost all 20 attachments of a run that way. Raise rather
        # than filter: an arm that quietly stops attaching frames is a different arm, and
        # this one is compared against a baseline that gets 20 frames every step.
        images = [Path(p) for p in images]
        relative = [p for p in images if not p.is_absolute()]
        if relative:
            raise ValueError(
                f"attachments must be absolute paths; codex resolves -i against its own "
                f"cwd ({self.workspace}), not the runner's: {relative}"
            )
        missing = [p for p in images if not p.exists()]
        if missing:
            logger.error(
                f"[codex] turn {self.calls + 1}: {len(missing)} attachment(s) do not "
                f"exist and will not be sent: {missing}"
            )
        images = [p for p in images if p.exists()]
        args = self._args(images)
        self.images_attached += len(images)
        logger.info(
            f"[codex] turn {self.calls} model={self.model} "
            f"resume={'yes' if self.session_id else 'no'} images={len(images)}"
        )
        try:
            proc = run_codex(
                args, cwd=self.workspace, prompt=prompt, env=env, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as expired:
            # Keep what the turn had already emitted. Written after `run` returned, the
            # transcript was missing for exactly the turns worth reading -- a stall's
            # last event is what distinguishes hanging in a tool from hanging on the
            # wire, and without it the only evidence a timeout leaves is its duration.
            partial = expired.stdout or ""
            if isinstance(partial, bytes):
                partial = partial.decode(errors="replace")
            if self.transcript_dir:
                # Composed, not `with_suffix`: that replaces `.timeout` rather than
                # extending it, and the partial would land under the name a completed
                # turn uses.
                stem = f"turn_{self.calls:04d}.timeout"
                (self.transcript_dir / f"{stem}.events.jsonl").write_text(partial, encoding="utf-8")
                (self.transcript_dir / f"{stem}.prompt.txt").write_text(prompt, encoding="utf-8")
            logger.error(
                f"[codex] turn {self.calls} timed out after {self.timeout}s; "
                f"{len(partial.splitlines())} events kept"
            )
            return {"actions_json": None, "message": "", "ok": False, "error": "timeout"}

        stats = request_stats(proc.stdout)
        violated = {k: stats[k] for k in ("web_searches", "mcp_tool_calls", "subthreads") if stats[k]}
        if self.transcript_dir:
            stem = self.transcript_dir / f"turn_{self.calls:04d}"
            stem.with_suffix(".events.jsonl").write_text(proc.stdout, encoding="utf-8")
            stem.with_suffix(".prompt.txt").write_text(prompt, encoding="utf-8")
            if proc.stderr:
                stem.with_suffix(".stderr.txt").write_text(proc.stderr, encoding="utf-8")

        if violated:
            raise SandboxViolation(
                f"codex turn {self.calls} used capabilities this arm must not have: "
                f"{violated}. The tool surface in force is not the one SAFE_CODEX_FLAGS "
                f"describes; see the transcript under {self.transcript_dir}."
            )

        # Keep the thread id so the next turn resumes rather than restarting cold.
        if self.session_id is None:
            match = _SESSION_RE.search(proc.stdout)
            if match:
                self.session_id = match.group(1)
                logger.info(f"[codex] session {self.session_id}")

        errors = []
        overflowed = False
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except Exception:
                continue
            # No view_image counting here. "Every observed value is 0" was not a
            # measurement, it was the counter: codex 0.147 runs the model's tools inside
            # an `exec` cell and this stream reports only shell commands, so a nested
            # `tools.view_image(...)` never appears. `vision_audit()` reads the rollout.
            # Finding #30 -- "the analyzer opened none across 8 turns" -- rests on this
            # counter and has to be re-checked against those runs' rollouts before it is
            # quoted again.
            if _COMPACTION_RE.search(line):
                self.compactions += 1
                logger.error(
                    f"[codex] turn {self.calls} shows a compaction event; the "
                    f"conversation is no longer the one this arm claims to run: {line[:200]}"
                )
            if event.get("type") in ("error", "turn.failed"):
                raw = event.get("message") or event.get("error") or ""
                if isinstance(raw, dict):
                    name, text = raw.get("name", "CodexError"), raw.get("message", str(raw))
                else:
                    name, text = "CodexError", str(raw)
                errors.append(text)
                overflowed = overflowed or is_overflow(name, text)

        if overflowed and self.session_id:
            # Drop the thread rather than retry into it. Everything the next turn
            # needs is in logs.txt and the workspace; only the conversation is lost.
            logger.error(
                f"[codex] turn {self.calls} overflowed the context window; "
                f"discarding session {self.session_id} so the next turn cold-starts"
            )
            self.session_id = None
            self.overflow_resets += 1

        actions_path = self.workspace / "actions.json"
        actions_json = actions_path.read_text(encoding="utf-8") if actions_path.exists() else None
        message_path = self.workspace / "last_message.txt"
        message = message_path.read_text(encoding="utf-8").strip() if message_path.exists() else ""

        if actions_json is None:
            logger.warning(
                f"[codex] turn {self.calls} wrote no actions.json (rc={proc.returncode}); "
                f"{errors[-1] if errors else proc.stderr.strip()[:200]}"
            )
        return {
            "actions_json": actions_json,
            "message": message,
            "ok": actions_json is not None,
            "error": errors[-1] if errors else None,
            "overflow": overflowed,
        }

    def vision_audit(self) -> dict[str, Any]:
        """What the model actually saw, read from the rollout rather than the events.

        `image_attach_failures` must be 0. Nonzero means `-i` did not land, so the
        episode ran vision-on-demand -- the arm the campaign relabelled v3/v4 as -- while
        reporting itself as the forced-vision arm.
        """
        rollout = find_rollout(self.codex_home, self.workspace, self.session_id)
        if rollout is not None:
            counts = scan_rollout(rollout)
            self.view_image_calls = counts["view_image_calls"]
            self.image_attach_failures = counts["image_attach_failures"]
            if self.image_attach_failures:
                logger.error(
                    f"[codex] {self.image_attach_failures} attachment(s) never reached "
                    f"the model (\"could not read the local image\" in {rollout}); this "
                    f"episode ran vision-on-demand, not forced vision"
                )
        elif self.images_attached:
            logger.warning(
                f"[codex] no rollout found for session {self.session_id}; the vision "
                f"audit is unverified for this episode"
            )
        return {
            "frames_attached": self.images_attached,
            "view_image_calls": self.view_image_calls,
            "image_attach_failures": self.image_attach_failures,
            "vision_audit_source": str(rollout) if rollout else None,
        }

    @staticmethod
    def extract_plan(message: str) -> str:
        """Pull the [PLAN] block the prompt asks for; fall back to the last lines."""
        return CodexTurn.split_briefing(message)[1]

    @staticmethod
    def split_briefing(message: str) -> tuple[str, str]:
        """(briefing, plan): the text before the [PLAN] marker and the block after it,
        as upstream splits its `hint`/`plan` pair (`codex_agent.py:677-681`). Without a
        marker the whole message is the plan's stand-in (last 400 chars) and there is
        no briefing."""
        text = (message or "").strip()
        match = re.search(r"\[PLAN\]\s*(.+)", text, re.DOTALL)
        if match:
            return text[: match.start()].strip(), match.group(1).strip()
        return "", text[-400:]
