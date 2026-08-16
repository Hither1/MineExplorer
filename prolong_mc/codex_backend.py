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
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from loguru import logger

_SESSION_RE = re.compile(r'"(?:thread_id|session_id)"\s*:\s*"([0-9a-fA-F-]{36})"')


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
        timeout: int = 1800,
        transcript_dir: Path | None = None,
    ) -> None:
        self.workspace = Path(workspace)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url
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
        self.view_image_calls = 0
        self.overflow_resets = 0

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
            "-c", f'model_reasoning_effort="{self.reasoning_effort}"',
            "-o", str(self.workspace / "last_message.txt"),
        ]
        if self.base_url:
            args += [
                "-c", "model_provider=local",
                "-c", 'model_providers.local.name="local"',
                "-c", f'model_providers.local.base_url="{self.base_url}"',
                "-c", 'model_providers.local.wire_api="responses"',
                "-c", 'model_providers.local.env_key="LOCAL_API_KEY"',
            ]
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

        images = [Path(p) for p in images if Path(p).exists()]
        args = self._args(images)
        self.images_attached += len(images)
        logger.info(
            f"[codex] turn {self.calls} model={self.model} "
            f"resume={'yes' if self.session_id else 'no'} images={len(images)}"
        )
        try:
            proc = subprocess.run(
                args, cwd=self.workspace, input=prompt, env=env,
                capture_output=True, text=True, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[codex] turn {self.calls} timed out after {self.timeout}s")
            return {"actions_json": None, "message": "", "ok": False, "error": "timeout"}

        if self.transcript_dir:
            stem = self.transcript_dir / f"turn_{self.calls:04d}"
            stem.with_suffix(".events.jsonl").write_text(proc.stdout, encoding="utf-8")
            stem.with_suffix(".prompt.txt").write_text(prompt, encoding="utf-8")
            if proc.stderr:
                stem.with_suffix(".stderr.txt").write_text(proc.stderr, encoding="utf-8")

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
            if '"view_image"' in line:
                self.view_image_calls += 1
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

    @staticmethod
    def extract_plan(message: str) -> str:
        """Pull the [PLAN] block the prompt asks for; fall back to the last lines."""
        match = re.search(r"\[PLAN\]\s*(.+)", message, re.DOTALL)
        if match:
            return match.group(1).strip()
        return message.strip()[-400:]
