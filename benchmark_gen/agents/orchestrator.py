"""
agents/orchestrator.py

AutoGen-Based Multi-Agent Benchmark Orchestrator
=================================================

Replaces the hand-rolled orchestrator with a proper AutoGen GroupChat so that
agents collaborate from round 1 with real multi-turn conversation.

Architecture
------------
Five ConversableAgents + one UserProxyAgent (Orchestrator):

  Orchestrator (UserProxy)   – drives the conversation, injects tasks/tools
  TaskSelectorAgent          – picks k atomic tasks, builds DAG
  SceneDesignerAgent         – designs Minecraft scene, uses sandbox tools
  MilestoneAgent             – designs rule-based milestones, uses sandbox
  CommonSenseAgent           – checks for Minecraft-specific knowledge issues
  ValidatorAgent             – validates DAG + milestones, uses sandbox

Conversation flow (GroupChat with custom speaker selector):
  Round 0 (Init):
    Orchestrator → TaskSelectorAgent: "Select k tasks from candidates"
    TaskSelectorAgent → ALL: task list + DAG
    SceneDesignerAgent → ALL: scene design (calls sandbox tool, then reports)
    CommonSenseAgent → ALL: early feedback on sandbox report
    MilestoneAgent → ALL: final milestones JSON (direct, no inquiry)
  Round 1..N (Debate):
    CommonSenseAgent → ALL: inspection report + critiques
    ValidatorAgent → ALL: validation report + critiques
    TaskSelectorAgent → ALL: revisions (if any)
    SceneDesignerAgent → ALL: revisions (if any)
    MilestoneAgent → ALL: revisions (if any)
  Termination:
    Orchestrator detects JSON convergence; extracts final outputs.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# AutoGen import (pyautogen / autogen-agentchat)
# ---------------------------------------------------------------------------
try:
    import autogen
    from autogen import ConversableAgent, GroupChat, GroupChatManager, UserProxyAgent
except ImportError as _e:
    raise ImportError(
        "AutoGen is required. Install with: pip install pyautogen\n"
        f"Original error: {_e}"
    )

from ..utils import (
    extract_json_object,
    validate_scene_design,
    validate_reasoning_graph,
    validate_milestones,
    parse_task_selection,
    save_fallback_response,
    save_benchmark_sample,
    render_reasoning_graph,
)
from .sandbox_tools import (
    SandboxHandle,
    setup_sandbox,
    lazy_setup_sandbox,
    LazyMCBenchSandboxEnv,
    lazy_setup_sandbox,
    LazyMCBenchSandboxEnv,
    close_sandbox,
    execute_commands,
    take_screenshot,
    make_execute_commands_tool,
    make_screenshot_tool,
    make_agent_action_tool,
    make_run_agent_tool,
    make_preview_scene_tool,
    _PREVIEW_MAX_STEPS,
)

# Agent system prompts
from .task_selector_agent import SYSTEM_PROMPT as _TASK_SELECTOR_SYS
from .scene_designer_agent import SYSTEM_PROMPT as _SCENE_DESIGNER_SYS
from .milestone_agent import SYSTEM_PROMPT as _MILESTONE_SYS
from .commonsense_agent import SYSTEM_PROMPT as _COMMONSENSE_SYS, query_minecraft_wiki, make_wiki_tools
from .validator_agent import SYSTEM_PROMPT as _VALIDATOR_SYS

AGENTS_DIR = Path(__file__).resolve().parent           # benchmark_gen/agents/
BENCHMARK_GEN_DIR = AGENTS_DIR.parent                  # benchmark_gen/
FALLBACK_DIR = BENCHMARK_GEN_DIR / "fallback"

# ---------------------------------------------------------------------------
# Conversation order constants (module-level so _run_groupchat can reference them)
# ---------------------------------------------------------------------------

# Init phase: fixed order of agent turns from the very first message
INIT_ORDER: List[str] = [
    "TaskSelectorAgent",   # 0: select tasks + build DAG
    "SceneDesignerAgent",  # 1: design scene + call preview_scene_in_sandbox
    "SceneDesignerAgent",  # 2: report sandbox findings & propose revisions to team
    "CommonSenseAgent",    # 3: react to sandbox report (early feedback)
    "MilestoneAgent",      # 4: output final milestones directly (NO questions first)
]

# Debate phase: repeated N times after the init phase
DEBATE_ORDER: List[str] = [
    "CommonSenseAgent",    # 0: inspect
    "ValidatorAgent",      # 1: validate graph
    "ValidatorAgent",      # 2: validate milestones
    "TaskSelectorAgent",   # 3: revise (if needed)
    "SceneDesignerAgent",  # 4: revise scene (may call preview_scene_in_sandbox again)
    "SceneDesignerAgent",  # 5: report revised sandbox findings
    "MilestoneAgent",      # 6: revise milestones based on revised scene
    "CommonSenseAgent",    # 7: re-inspect
    "ValidatorAgent",      # 8: re-validate
]


# ---------------------------------------------------------------------------
# Tool call logging wrapper
# ---------------------------------------------------------------------------

class _LoggingToolWrapper:
    """
    Wraps a sandbox tool function to intercept every call and record:
      - tool name
      - call arguments
      - returned image paths (saved_paths)
      - base64 images (for multimodal injection)
      - timestamp
      - caller agent name (best-effort from thread context)

    All records are appended to a shared ``tool_call_log`` list.

    The __call__ method returns a human-readable text summary so the LLM can
    understand what happened, while also storing the full image data in the
    log record for later multimodal injection into the conversation.
    """

    def __init__(
        self,
        name: str,
        fn,
        tool_call_log: List[Dict],
        log_dir: str,
        agent_name: str = "unknown",
        visual_log: Optional[List[Dict]] = None,
        tool_use_dir: Optional[str] = None,
        call_counter: Optional[List[int]] = None,
    ):
        self.name = name
        self._fn = fn
        self._log = tool_call_log
        self._log_dir = log_dir
        self._agent_name = agent_name
        # visual_log: shared list for image injection into conversation
        self._visual_log = visual_log if visual_log is not None else []
        # tool_use_dir: staging dir for per-call tool_use/ subfolders
        self._tool_use_dir = tool_use_dir
        # call_counter: shared mutable counter [int] across all wrappers
        self._call_counter = call_counter if call_counter is not None else [0]
        # Preserve function signature metadata for AutoGen introspection
        import functools
        functools.update_wrapper(self, fn)

    def __call__(self, *args, **kwargs):
        import datetime as _dt
        ts = _dt.datetime.now().isoformat(timespec="seconds")

        # Build a serialisable args record (skip non-serialisable objects)
        safe_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                safe_kwargs[k] = v
            else:
                safe_kwargs[k] = repr(v)

        result = self._fn(*args, **kwargs)

        # ── Extract image data from result ───────────────────────────────
        # Collect (perspective_name, b64_png, saved_path) tuples
        image_entries: List[Dict] = []  # [{"perspective": str, "b64": str, "path": str}]
        image_paths: List[str] = []

        if isinstance(result, dict):
            saved_paths = result.get("saved_paths", {})
            # Map perspective → saved path
            path_map: Dict[str, str] = {}
            if isinstance(saved_paths, dict):
                path_map = {k: v for k, v in saved_paths.items() if v}
            elif isinstance(saved_paths, list):
                path_map = {f"frame_{i}": p for i, p in enumerate(saved_paths) if p}

            # Per-perspective base64 data (execute_commands returns these at top level)
            _KNOWN_PERSPECTIVES = {
                "first_person", "overhead", "inventory",
                "north", "south", "east", "west"
            }
            for key in list(result.keys()):
                if key in _KNOWN_PERSPECTIVES and isinstance(result[key], str) and len(result[key]) > 64:
                    b64 = result[key]
                    saved_path = path_map.get(key, "")
                    image_entries.append({"perspective": key, "b64": b64, "path": saved_path})
                    if saved_path:
                        image_paths.append(saved_path)

            # Handle preview_scene_in_sandbox result (all_frames list)
            all_frames = result.get("all_frames", [])
            if all_frames and not image_entries:
                for frame in all_frames:
                    b64 = frame.get("b64", "")
                    path = frame.get("path", "")
                    label = frame.get("label", "frame")
                    if isinstance(b64, str) and len(b64) > 64:
                        image_entries.append({"perspective": label, "b64": b64, "path": path})
                        if path:
                            image_paths.append(path)

            # Also handle execute_agent_action / run_agent_episode
            if not image_entries:
                frames_b64 = result.get("frames_b64", [])
                for i, b64 in enumerate(frames_b64):
                    if isinstance(b64, str) and len(b64) > 64:
                        sp = path_map.get(f"frame_{i}", "")
                        image_entries.append({"perspective": f"frame_{i}", "b64": b64, "path": sp})
                        if sp:
                            image_paths.append(sp)
                # steps from run_agent_episode
                for step in result.get("steps", []):
                    if isinstance(step, dict):
                        b64 = step.get("frame_b64", "")
                        sp = step.get("saved_path", "")
                        if isinstance(b64, str) and len(b64) > 64:
                            image_entries.append({
                                "perspective": f"agent_step_{step.get('step_idx', '?')}",
                                "b64": b64,
                                "path": sp,
                            })
                            if sp:
                                image_paths.append(sp)

        elif isinstance(result, str) and result.endswith(".png"):
            image_paths = [result]

        # ── Build text summary for the LLM (tool result content) ─────────
        text_summary = _build_tool_result_summary(
            tool_name=self.name,
            kwargs=safe_kwargs,
            image_entries=image_entries,
            image_paths=image_paths,
            raw_result=result,
        )

        # ── Assign global call index ─────────────────────────────────────
        self._call_counter[0] += 1
        call_idx = self._call_counter[0]

        # ── Record in tool_call_log ──────────────────────────────────────
        record = {
            "call_idx": call_idx,
            "timestamp": ts,
            "agent": self._agent_name,
            "tool": self.name,
            "kwargs": safe_kwargs,
            "image_paths": image_paths,
            "image_entries": [
                {"perspective": e["perspective"], "path": e["path"]}
                for e in image_entries
            ],
            "text_summary": text_summary,
            "tool_use_subdir": None,  # filled in below if tool_use_dir is set
        }

        # ── Write tool_use/ per-call subfolder ───────────────────────────
        # Each call gets its own numbered subdirectory:
        #   tool_use/001_SceneDesignerAgent_execute_minecraft_commands_143022/
        # Inside: call_info.json + copies of all screenshot files.
        tool_use_subdir_rel: Optional[str] = None
        if self._tool_use_dir:
            try:
                import shutil as _shutil

                # Build subfolder name: NNN_Agent_Tool_HHMMSS
                time_part = ts.replace("T", "_").replace(":", "")[-6:]  # HHMMSS
                tool_short = self.name.replace("execute_minecraft_commands", "exec_cmds")\
                                      .replace("execute_agent_action", "agent_action")\
                                      .replace("run_agent_episode", "run_agent")\
                                      .replace("take_screenshot", "screenshot")
                subdir_name = f"{call_idx:03d}_{self._agent_name}_{tool_short}_{time_part}"
                subdir_path = Path(self._tool_use_dir) / subdir_name
                subdir_path.mkdir(parents=True, exist_ok=True)

                # Copy screenshot files into the subdir
                copied_files: List[str] = []
                for img_path in image_paths:
                    if img_path and Path(img_path).is_file():
                        dest = subdir_path / Path(img_path).name
                        # Avoid duplicate names
                        if dest.exists():
                            stem, suf = dest.stem, dest.suffix
                            i = 1
                            while dest.exists():
                                dest = subdir_path / f"{stem}_{i}{suf}"
                                i += 1
                        try:
                            _shutil.copy2(img_path, dest)
                            copied_files.append(str(dest))
                        except Exception as _ce:
                            print(f"  [ToolUse] copy failed: {img_path} → {dest}: {_ce}")

                # Build call_info.json
                call_info = {
                    "call_idx": call_idx,
                    "timestamp": ts,
                    "agent": self._agent_name,
                    "tool": self.name,
                    "arguments": safe_kwargs,
                    "text_summary": text_summary,
                    "screenshots": [
                        {
                            "perspective": e["perspective"],
                            "file": Path(cp).name,
                            "original_path": ip,
                        }
                        for e, ip, cp in zip(
                            image_entries,
                            image_paths,
                            copied_files if copied_files else [""] * len(image_entries),
                        )
                    ] if image_entries else [],
                    "num_images": len(image_entries),
                }
                call_info_path = subdir_path / "call_info.json"
                with open(call_info_path, "w", encoding="utf-8") as _f:
                    json.dump(call_info, _f, indent=2, ensure_ascii=False)

                tool_use_subdir_rel = subdir_name
                record["tool_use_subdir"] = subdir_name
                print(f"  [ToolUse] {subdir_name}/ ({len(copied_files)} images)")
            except Exception as _tue:
                print(f"  [ToolUse] subfolder creation failed: {_tue}")

        self._log.append(record)

        # ── Record in visual_log (for multimodal injection) ───────────────
        if image_entries:
            self._visual_log.append({
                "timestamp": ts,
                "agent": self._agent_name,
                "tool": self.name,
                "image_entries": image_entries,
                "text_summary": text_summary,
                "tool_use_subdir": tool_use_subdir_rel,
            })

        # Print a concise log line
        images_str = ", ".join(
            f"{e['perspective']}={Path(e['path']).name if e['path'] else 'no-file'}"
            for e in image_entries
        ) if image_entries else "none"
        print(f"  [ToolLog] {ts} | {self._agent_name} → {self.name} | images: [{images_str}]")

        # ── Return text summary so AutoGen injects it as tool result text ─
        # The actual images are injected separately by _VisualToolAgent
        return text_summary


def _build_tool_result_summary(
    tool_name: str,
    kwargs: Dict,
    image_entries: List[Dict],
    image_paths: List[str],
    raw_result: Any,
) -> str:
    """
    Build a human-readable text summary of a tool call result.
    This is what the LLM sees as the tool result content.
    The images themselves are injected separately as multimodal messages.
    """
    lines = [f"## Tool Result: {tool_name}"]

    if tool_name == "execute_minecraft_commands":
        cmds = kwargs.get("commands", [])
        perspectives = kwargs.get("perspectives", [])
        lines.append(f"\n**Commands executed** ({len(cmds)} total):")
        for cmd in cmds[:10]:  # show first 10
            lines.append(f"  - `{cmd}`")
        if len(cmds) > 10:
            lines.append(f"  ... and {len(cmds)-10} more commands")

        lines.append(f"\n**Screenshots captured** ({len(image_entries)} perspectives):")
        for entry in image_entries:
            persp = entry["perspective"]
            path = entry["path"]
            fname = Path(path).name if path else "(no file)"
            lines.append(f"  - `{persp}`: saved as `{fname}`")

        if image_entries:
            lines.append(
                f"\n**IMAGES ATTACHED**: {len(image_entries)} screenshot(s) follow this message "
                "as inline images. Please examine them carefully to verify the scene layout."
            )
        else:
            lines.append("\n**WARNING**: No screenshots were captured. Check sandbox connectivity.")

    elif tool_name == "take_screenshot":
        if image_paths:
            fname = Path(image_paths[0]).name if image_paths[0] else "(no file)"
            lines.append(f"\n**Screenshot captured**: `{fname}`")
            lines.append("\n**IMAGE ATTACHED**: The screenshot follows as an inline image.")
        else:
            lines.append("\n**Result**: Base64 PNG captured (see attached image).")

    elif tool_name == "preview_scene_in_sandbox":
        total_steps  = raw_result.get("total_steps", 0)
        saved_dir    = raw_result.get("saved_dir", "")
        n_explore    = len(raw_result.get("explore_frames", []))
        has_initial  = bool(raw_result.get("initial_frame", {}).get("b64"))
        cmds_executed = raw_result.get("commands_executed", 0)
        lines.append(
            f"\n**Scene preview completed** (eval_benchmark.py-style): "
            f"{cmds_executed} commands executed, "
            f"{'1 initial frame + ' if has_initial else ''}"
            f"{total_steps} exploration steps ({n_explore} explore frames)."
        )
        if image_entries:
            lines.append(
                f"\n**IMAGES ATTACHED**: {len(image_entries)} frame(s) follow as inline images. "
                "First image = initial scene view (after commands settle). "
                "Remaining images = AI agent's first-person exploration frames "
                "(each with a thought + action from the DefaultAgent). "
                "Please examine them carefully — describe the scene layout, "
                "identify any issues, and propose revisions if needed."
            )
        else:
            lines.append("\n**WARNING**: No frames were captured. Check sandbox connectivity.")

    elif tool_name == "run_agent_episode":
        total_steps = raw_result.get("total_steps", 0) if isinstance(raw_result, dict) else 0
        lines.append(f"\n**Agent episode completed**: {total_steps} steps executed.")
        if image_entries:
            lines.append(f"\n**FRAMES ATTACHED**: {len(image_entries)} frame(s) follow as images.")

    elif tool_name == "execute_agent_action":
        n_frames = len(image_entries)
        lines.append(f"\n**Action executed**: {n_frames} frame(s) captured.")
        if image_entries:
            lines.append("\n**FRAMES ATTACHED**: Follow as inline images.")

    else:
        # Generic fallback
        if image_entries:
            lines.append(f"\n**Images**: {len(image_entries)} image(s) captured and attached.")
        elif isinstance(raw_result, str):
            lines.append(f"\nResult: {raw_result[:500]}")
        elif isinstance(raw_result, dict):
            # Summarise dict without base64 blobs
            summary = {k: v for k, v in raw_result.items()
                       if k not in ("saved_paths",) and not (isinstance(v, str) and len(v) > 200)}
            lines.append(f"\nResult summary: {json.dumps(summary, ensure_ascii=False)[:500]}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ImageAwareConversableAgent — injects images after tool calls
# ---------------------------------------------------------------------------

class _VisualToolAgent(ConversableAgent):
    """
    A ConversableAgent subclass that, after executing a tool call, injects
    the resulting screenshots as multimodal messages (image_url) directly
    into the agent's conversation history.

    This allows the LLM to actually *see* the Minecraft screenshots when
    it generates its next reply.

    The injected messages are also appended to a shared ``visual_message_log``
    list so they appear in the saved conversation record.

    ── Injection timing ────────────────────────────────────────────────────────
    Images are NOT injected inside execute_function (which is called from
    generate_tool_calls_reply BEFORE the tool-result message is appended to
    oai_messages).  Injecting there would insert a "user" role message between
    the "assistant (tool_calls)" message and the "tool (result)" message,
    breaking the strict ordering required by the OpenAI API and causing:

        BadRequestError 400: tool_call_id did not have response messages

    Instead we use a **deferred injection** strategy:
      1. execute_function just records the visual_log watermark.
      2. generate_tool_calls_reply calls super() (which internally calls
         execute_function), records pending image entries, then returns the
         tool-result dict — no injection yet.
      3. generate_oai_reply is called when the agent is *asked to speak next*.
         At this point the tool-result message is already in oai_messages.
         We prepend the pending image messages right before calling the LLM so
         the model sees images in the correct position.
    """

    def __init__(
        self,
        *args,
        visual_log: Optional[List[Dict]] = None,
        visual_message_log: Optional[List[Dict]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # Shared log of all visual tool outputs — maintained by _LoggingToolWrapper
        self._visual_log: List[Dict] = visual_log if visual_log is not None else []
        self._visual_message_log: List[Dict] = (
            visual_message_log if visual_message_log is not None else []
        )
        # Pending image entries waiting to be injected on the next generate_oai_reply call
        self._pending_image_entries: List[Dict] = []

        # ── Patch reply_func_list so our generate_oai_reply override is called ─
        # AutoGen registers ConversableAgent.generate_oai_reply (unbound parent
        # class function) in _reply_func_list during __init__.  When AutoGen later
        # calls reply_func(self, ...) it invokes the *parent* implementation directly,
        # bypassing our subclass override entirely.  We fix this by replacing the
        # entry with a reference to THIS class's generate_oai_reply so that the
        # Bedrock-Claude assistant-prefill guard actually fires.
        from autogen import ConversableAgent as _CA
        for entry in self._reply_func_list:
            if entry.get("reply_func") is _CA.generate_oai_reply:
                entry["reply_func"] = _VisualToolAgent.generate_oai_reply
                break

    def execute_function(self, func_call, call_id=None, verbose=False):
        """
        Execute the tool and record visual_log watermark.
        Image injection is deferred to generate_oai_reply (see class docstring).
        """
        prev_len = len(self._visual_log)

        # AutoGen 0.2.x: execute_function(func_call, verbose)  — no call_id param.
        # AutoGen 0.3+/0.4+: execute_function(func_call, call_id, verbose).
        # Use inspect to stay compatible with both versions.
        import inspect as _inspect
        _base_sig = _inspect.signature(super().execute_function)
        if "call_id" in _base_sig.parameters:
            success, result = super().execute_function(func_call, call_id=call_id, verbose=verbose)
        else:
            success, result = super().execute_function(func_call, verbose=verbose)

        # Collect new image entries from the visual_log and store them as pending.
        # Actual injection into oai_messages happens in generate_oai_reply (deferred).
        new_entries = self._visual_log[prev_len:]
        for entry in new_entries:
            images = entry.get("image_entries", [])
            if images:
                self._pending_image_entries.append(entry)

        return success, result

    def generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender=None,
        config=None,
    ) -> Tuple[bool, Any]:
        """
        Generate a reply via OpenAI, first injecting any pending sandbox images.

        The tool-result message has already been appended to oai_messages by the
        time this method is called, so inserting image messages here does NOT
        break the tool_calls → tool ordering required by the OpenAI API.
        """
        # ── Flush pending images into oai_messages ───────────────────────
        if self._pending_image_entries:
            pending = list(self._pending_image_entries)
            self._pending_image_entries.clear()

            for entry in pending:
                images = entry.get("image_entries", [])
                if not images:
                    continue
                # For preview_scene_in_sandbox, subsample frames to avoid 413 errors.
                # Keep: initial frame + up to MAX_PREVIEW_FRAMES evenly-spaced steps.
                images = _subsample_preview_frames(images, entry.get("tool", ""))
                multimodal_content = _build_multimodal_content(
                    images, entry.get("text_summary", "")
                )
                if not multimodal_content:
                    continue

                injected_msg = {
                    "role": "user",
                    "content": multimodal_content,
                    "name": "SandboxVision",
                }

                # Inject into this agent's message lists (keyed by sender)
                for sender_key in list(self._oai_messages.keys()):
                    self._oai_messages[sender_key].append(injected_msg)

                # Record in shared visual message log
                log_entry = {
                    "from": "SandboxVision",
                    "role": "user",
                    "content": _summarise_multimodal_for_log(multimodal_content),
                    "image_paths": [e["path"] for e in images if e.get("path")],
                    "timestamp": entry.get("timestamp", ""),
                    "tool": entry.get("tool", ""),
                    "agent": entry.get("agent", ""),
                }
                self._visual_message_log.append(log_entry)

                persp_list = [e["perspective"] for e in images]
                print(
                    f"  [Vision] Injected {len(images)} images into {self.name} context: "
                    f"{persp_list}"
                )

        # ── Bedrock Claude "assistant prefill" guard ─────────────────────
        # Bedrock Claude rejects requests where the last message has role='assistant'
        # (it treats that as "assistant prefill" and returns HTTP 400).
        # This can happen when the same agent is called multiple times in a row
        # (tool-call intercept returns the same speaker for consecutive turns) and
        # the previous turn ended with the agent's own text reply (role=assistant).
        # Solution: if the messages list ends with an assistant message, append a
        # minimal user acknowledgement so the conversation ends with a user turn.
        #
        # NOTE: AutoGen passes messages=None here; we must resolve it ourselves
        # before checking, then pass the resolved list to super() so the guard
        # actually fires.
        if messages is None and sender is not None:
            messages = self._oai_messages.get(sender)
        if messages and messages[-1].get("role") == "assistant":
            messages = list(messages) + [{
                "role": "user",
                "content": "Please continue.",
                "name": "Orchestrator",
            }]
            print(
                f"  [Vision] Inserted ack user-msg for {self.name} "
                "to satisfy Bedrock Claude 'no assistant prefill' constraint."
            )

        # ── Image history pruning guard (avoid 413 Request Entity Too Large) ──
        # Each sandbox preview injects 20+ large base64 PNG images.  After
        # multiple tool calls the accumulated images can easily exceed the
        # proxy/gateway request-body size limit (typically 10-50 MB).
        # Strategy: keep the images only in the *most recent* SandboxVision
        # message; replace images in all earlier SandboxVision messages with a
        # compact text placeholder so the context is preserved without the bulk.
        if messages:
            messages = _prune_old_vision_images(messages)

        # ── Rate-limit retry loop ────────────────────────────────────────
        # If the upstream API returns HTTP 429 (rate limit exceeded) we wait
        # 60 seconds and retry rather than crashing the whole generation run.
        import time as _time
        _max_retries = 10
        _retry_wait  = 60  # seconds
        for _attempt in range(1, _max_retries + 1):
            try:
                return super().generate_oai_reply(messages=messages, sender=sender, config=config)
            except Exception as _exc:
                _exc_str = str(_exc)
                # Check for rate-limit indicators (HTTP 429 or explicit message)
                _is_rate_limit = (
                    "429" in _exc_str
                    or "rate limit" in _exc_str.lower()
                    or "RateLimitError" in type(_exc).__name__
                    or "每分钟请求次数超过限制" in _exc_str
                )
                if _is_rate_limit and _attempt < _max_retries:
                    print(
                        f"  [RateLimit] {self.name} hit rate limit (attempt {_attempt}/{_max_retries}). "
                        f"Waiting {_retry_wait}s before retry..."
                    )
                    _time.sleep(_retry_wait)
                    continue
                # Non-rate-limit error or last attempt — re-raise
                raise


def _build_multimodal_content(
    image_entries: List[Dict],
    text_summary: str = "",
) -> List[Dict]:
    """
    Build an OpenAI-style multimodal content list from image entries.

    Each entry: {"perspective": str, "b64": str, "path": str}
    Returns a list of content parts: [{"type": "text", ...}, {"type": "image_url", ...}, ...]
    """
    parts: List[Dict] = []

    # Opening text
    if text_summary:
        parts.append({"type": "text", "text": text_summary})
    else:
        parts.append({"type": "text", "text": "Sandbox tool executed. Screenshots below:"})

    for entry in image_entries:
        persp = entry.get("perspective", "view")
        b64 = entry.get("b64", "")
        path = entry.get("path", "")
        fname = Path(path).name if path else "screenshot.png"

        if not b64 or len(b64) < 64:
            continue

        # Label for this image
        parts.append({"type": "text", "text": f"\n--- Perspective: {persp} ({fname}) ---"})

        # Embed as data URI
        # Use "low" detail to keep request payload small (avoids 413 errors).
        # Low-detail images are ~85 tokens each vs ~1000+ for high-detail.
        parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "low",
            },
        })

    return parts if len(parts) > 1 else []  # at least one image required


def _summarise_multimodal_for_log(content: List[Dict]) -> str:
    """
    Produce a concise text summary of a multimodal content list for storing
    in the conversation log (avoids saving huge base64 blobs).
    """
    parts = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "")
            if len(text) > 200:
                text = text[:200] + "..."
            parts.append(text)
        elif item.get("type") == "image_url":
            url = item.get("image_url", {}).get("url", "")
            if url.startswith("data:image"):
                parts.append("[IMAGE: base64 PNG embedded]")
            else:
                parts.append(f"[IMAGE: {url}]")
    return " ".join(parts)


# Maximum number of frames to inject per preview_scene_in_sandbox call.
# 21 frames at high-detail easily exceeds 10 MB; 6 frames at low-detail is ~300 KB.
MAX_PREVIEW_FRAMES = 6


def _subsample_preview_frames(
    image_entries: List[Dict],
    tool_name: str,
) -> List[Dict]:
    """
    For ``preview_scene_in_sandbox`` calls that produce many exploration frames,
    subsample down to at most MAX_PREVIEW_FRAMES to keep the request payload
    within proxy limits (avoids 413 Request Entity Too Large).

    Strategy:
    - Always keep the first entry (typically the ``initial`` frame showing the
      scene immediately after commands settle — the most informative view).
    - From the remaining exploration steps, pick MAX_PREVIEW_FRAMES-1 frames
      spread evenly across the sequence so the agent sees a representative
      sample of the exploration rather than only the first few steps.

    For all other tools (execute_minecraft_commands, execute_agent_action, etc.)
    the full frame list is returned unchanged because those tools only produce
    a small number of frames anyway (typically 1-4).
    """
    if tool_name != "preview_scene_in_sandbox":
        return image_entries

    if len(image_entries) <= MAX_PREVIEW_FRAMES:
        return image_entries

    # Always keep the first frame (initial scene view)
    first = [image_entries[0]]
    rest = image_entries[1:]

    # Pick MAX_PREVIEW_FRAMES-1 evenly-spaced frames from the exploration steps
    n_want = MAX_PREVIEW_FRAMES - 1
    if len(rest) <= n_want:
        sampled = rest
    else:
        indices = [int(round(i * (len(rest) - 1) / (n_want - 1))) for i in range(n_want)]
        # Deduplicate while preserving order
        seen = set()
        sampled = []
        for idx in indices:
            if idx not in seen:
                seen.add(idx)
                sampled.append(rest[idx])

    result = first + sampled
    print(
        f"  [Vision] Subsampled preview frames: {len(image_entries)} → {len(result)} "
        f"(initial + {len(sampled)} of {len(rest)} explore steps)"
    )
    return result


def _prune_old_vision_images(messages: List[Dict]) -> List[Dict]:
    """
    To avoid 413 Request Entity Too Large errors caused by accumulated base64
    PNG images across multiple sandbox preview tool calls, this function strips
    inline image data from all but the most recent SandboxVision message.

    Strategy:
    - Find all messages that came from "SandboxVision" (name="SandboxVision")
      and contain multimodal content (list with image_url entries).
    - Keep images intact only in the LAST such message.
    - For all earlier SandboxVision image messages, replace the content with a
      compact text-only summary so the agent still has context about what was
      observed, without the heavy base64 payload.

    Non-SandboxVision messages are left completely untouched.
    """
    # Identify indices of SandboxVision messages that carry images
    vision_indices = []
    for i, msg in enumerate(messages):
        if msg.get("name") != "SandboxVision":
            continue
        content = msg.get("content", "")
        if not isinstance(content, list):
            continue
        has_image = any(
            part.get("type") == "image_url"
            for part in content
            if isinstance(part, dict)
        )
        if has_image:
            vision_indices.append(i)

    if len(vision_indices) <= 1:
        # 0 or 1 image message – nothing to prune
        return messages

    # Prune all but the last one
    indices_to_prune = set(vision_indices[:-1])
    pruned = []
    pruned_count = 0
    for i, msg in enumerate(messages):
        if i not in indices_to_prune:
            pruned.append(msg)
            continue
        # Replace image parts with a text summary
        content = msg.get("content", [])
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        image_count = sum(
            1 for part in content
            if isinstance(part, dict) and part.get("type") == "image_url"
        )
        summary = " ".join(t for t in text_parts if t).strip()
        if not summary:
            summary = "Sandbox tool executed."
        replacement_text = (
            f"[Earlier sandbox preview – {image_count} image(s) pruned to save context space. "
            f"Summary: {summary}]"
        )
        pruned.append({**msg, "content": replacement_text})
        pruned_count += 1

    if pruned_count:
        print(
            f"  [Vision] Pruned images from {pruned_count} older SandboxVision message(s) "
            f"to avoid 413 payload limit (kept latest {len(vision_indices) - pruned_count} batch)."
        )
    return pruned


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_llm_config(
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """Build AutoGen llm_config dict for OpenAI-compatible endpoints.

    Strips common router prefixes (``openai/``, ``litellm/``, ``azure/``) from
    *model* so the raw model name is forwarded to the API endpoint.  These
    prefixes are sometimes added by the caller for LiteLLM routing but are not
    accepted by direct OpenAI-compatible servers.
    """
    for _prefix in ("openai/", "litellm/", "azure/"):
        if model.startswith(_prefix):
            model = model[len(_prefix):]
            break
    return {
        "config_list": [
            {
                "model": model,
                "api_key": api_key,
                "base_url": base_url,
                "api_type": "openai",
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": 600,
    }


def _extract_final_json_block(text: str, key: str) -> Optional[Dict]:
    """Find last occurrence of a JSON block containing `key`."""
    matches = list(re.finditer(r"\{", text))
    for m in reversed(matches):
        candidate = text[m.start():]
        obj = extract_json_object(candidate)
        if isinstance(obj, dict) and key in obj:
            return obj
    return None


# ---------------------------------------------------------------------------
# Sandbox screenshot → message content helper
# ---------------------------------------------------------------------------

def _b64_image_message(b64: str, caption: str = "") -> List[Dict]:
    """Build a multimodal message content list with an image."""
    content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        }
    ]
    if caption:
        content.append({"type": "text", "text": caption})
    return content


# ---------------------------------------------------------------------------
# BenchmarkOrchestrator
# ---------------------------------------------------------------------------

class BenchmarkOrchestrator:
    """
    AutoGen-based multi-agent orchestrator for MCBench generation.

    Key changes from previous version:
    - Uses AutoGen GroupChat for all agent communication (real multi-agent).
    - Sandbox tools (execute_commands, screenshot, agent_run) are injected as
      AutoGen tool functions into the relevant agents.
    - All 5 agents talk to each other from round 0 (not sequentially gated).
    - Sandbox is shared across agents via a SandboxHandle passed through tool closures.
    """

    def __init__(
        self,
        api_model: str,
        api_key: str,
        api_base_url: str,
        enable_wiki: bool = True,
        max_debate_rounds: int = 2,
        temperature_task_selector: float = 0.7,
        temperature_scene_designer: float = 0.7,
        temperature_milestone: float = 0.2,
        temperature_commonsense: float = 0.3,
        temperature_validator: float = 0.2,
        max_retries: int = 2,
        sandbox_tmp_dir: str = "/tmp/mcbench_sandbox",
        verbose: bool = True,
    ):
        self.api_model = api_model
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.enable_wiki = enable_wiki
        self.max_debate_rounds = max_debate_rounds
        self.temperatures = {
            "task_selector": temperature_task_selector,
            "scene_designer": temperature_scene_designer,
            "milestone": temperature_milestone,
            "commonsense": temperature_commonsense,
            "validator": temperature_validator,
        }
        self.max_retries = max_retries
        self.sandbox_tmp_dir = sandbox_tmp_dir
        self.verbose = verbose

        # Sandbox handle (shared across agents per sample)
        self._sandbox: Optional[SandboxHandle] = None

    # ------------------------------------------------------------------
    # Sandbox lifecycle
    # ------------------------------------------------------------------

    def _start_sandbox(self, sample_idx: int) -> Optional[SandboxHandle]:
        """Create a lazy SandboxHandle for this sample.

        The sandbox resource is NOT allocated here.  Instead, a
        ``LazyMCBenchSandboxEnv`` is created which only holds the pssdk
        credentials.  The actual ``sandbox_start + create_env`` call happens
        the first time SceneDesignerAgent calls ``preview_scene_in_sandbox``
        (or ``execute_minecraft_commands``) and passes a ``commands`` list.

        This matches the user's requirement:
          1. Tools are registered (sandbox not yet started).
          2. When the agent decides to call the tool with correct commands,
             the sandbox is created and create_env is called in one step.

        If credentials are not available, returns None and the workflow
        proceeds without sandbox tools.
        """
        tmp = os.path.join(self.sandbox_tmp_dir, f"sample_{sample_idx:04d}")
        os.makedirs(tmp, exist_ok=True)
        try:
            print("  [Sandbox] Creating lazy sandbox handle (sandbox NOT yet started)...")
            handle = lazy_setup_sandbox(tmp_dir=tmp)
            print("  [Sandbox] Lazy sandbox handle ready – will start on first tool call.")
            return handle
        except Exception as e:
            print(f"  [Sandbox] Failed to create lazy sandbox handle: {e}. Continuing without sandbox.")
            return None

    def _stop_sandbox(self) -> None:
        if self._sandbox is not None:
            try:
                close_sandbox(self._sandbox)
            except Exception:
                pass
            self._sandbox = None

    # ------------------------------------------------------------------
    # Post-chat scene capture (using live sandbox, no MinecraftSim needed)
    # ------------------------------------------------------------------

    def _capture_final_scene_views(
        self,
        result: Dict[str, Any],
        snap_dir: str,
    ) -> Dict[str, Any]:
        """
        After the GroupChat finishes, while the sandbox is still alive,
        re-execute the designed scene commands and capture multi-perspective
        screenshots (first_person + overhead + cardinal views).

        These are stored in ``<snap_dir>/scene_map/`` and their paths are
        added to ``result["scene_map_paths"]`` so callers can copy them
        into the final output directory.

        This lets the user always see what the scene looks like even when
        MinecraftSim / the 'mcu' conda environment is unavailable.
        """
        if self._sandbox is None:
            return result

        # For lazy handles: only proceed if the sandbox has actually been started
        # (i.e., the agent called preview_scene_in_sandbox at least once).
        lazy_env = self._sandbox.get("env")
        if isinstance(lazy_env, LazyMCBenchSandboxEnv) and not lazy_env._ready:
            self._log(
                "Lazy sandbox was never initialised (agent did not call preview tool). "
                "Skipping post-chat scene map capture."
            )
            return result

        scene_design = result.get("scene_design") or {}
        commands = scene_design.get("commands", [])
        if not commands:
            return result

        map_dir = os.path.join(snap_dir, "scene_map")
        os.makedirs(map_dir, exist_ok=True)

        self._log("Capturing final scene views via sandbox...")
        try:
            snap = execute_commands(
                handle=self._sandbox,
                commands=commands,
                wait_steps_per_cmd=3,
                settle_steps=2,
                perspectives=["first_person", "overhead"],
                save_dir=map_dir,
            )
            saved = snap.get("saved_paths", {})
            paths = {k: v for k, v in saved.items() if v}
            result["scene_map_paths"] = paths
            self._log(
                f"Scene map captured: {list(paths.keys())} → {map_dir}"
            )
            for persp, path in paths.items():
                print(f"  [SCENE_MAP] {persp}: {path}")
        except Exception as e:
            self._log(f"Scene map capture failed: {e}")

        return result

    # ------------------------------------------------------------------
    # LLM config builders
    # ------------------------------------------------------------------

    def _llm_config(self, role: str) -> Dict[str, Any]:
        return _build_llm_config(
            model=self.api_model,
            api_key=self.api_key,
            base_url=self.api_base_url,
            temperature=self.temperatures[role],
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_sample(
        self,
        candidate_tasks: List[str],
        k: int,
        sample_idx: int = 0,
        render_out_dir: Optional[str] = None,
        log_dir: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Run multi-agent AutoGen GroupChat to generate one benchmark sample.

        Args:
            candidate_tasks: Pool of atomic task names to choose from.
            k:               Number of tasks to select.
            sample_idx:      Index for this sample (used in directory names).
            render_out_dir:  If set, render scene graph images to this directory.
            log_dir:         If set, save agent dialogue logs and tool-call images here.
                             Defaults to ``render_out_dir`` when not specified.

        Returns final result dict or None on failure.
        """
        self._log(f"=== Sample {sample_idx}: k={k}, candidates={len(candidate_tasks)} ===")

        # Start sandbox (shared by all agents)
        self._sandbox = self._start_sandbox(sample_idx)
        sandbox_tmp = os.path.join(
            self.sandbox_tmp_dir, f"sample_{sample_idx:04d}"
        ) if self._sandbox else None

        try:
            result = self._run_groupchat(
                candidate_tasks=candidate_tasks,
                k=k,
                sample_idx=sample_idx,
                render_out_dir=render_out_dir,
                sandbox_tmp=sandbox_tmp,
                log_dir=log_dir or render_out_dir,
            )

            # ── Post-chat: capture final scene map while sandbox is still live ──
            # Capture first_person + overhead views of the fully-built scene so
            # the user can always see what the designed scene looks like, without
            # requiring MinecraftSim / mcu environment.
            if result is not None and self._sandbox is not None:
                scene_snap_dir = log_dir or render_out_dir or sandbox_tmp
                if scene_snap_dir:
                    result = self._capture_final_scene_views(
                        result, scene_snap_dir
                    )

            return result
        finally:
            self._stop_sandbox()

    # ------------------------------------------------------------------
    # GroupChat construction and execution
    # ------------------------------------------------------------------

    def _run_groupchat(
        self,
        candidate_tasks: List[str],
        k: int,
        sample_idx: int,
        render_out_dir: Optional[str],
        sandbox_tmp: Optional[str],
        log_dir: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build agents, run GroupChat, extract result."""

        # ── Shared tool-call log ─────────────────────────────────────────
        # Shared list that all _LoggingToolWrapper instances append records to.
        tool_call_log: List[Dict] = []
        # visual_log: shared list where wrappers record image data for injection
        visual_log: List[Dict] = []
        # visual_message_log: records all injected multimodal messages for conversation log
        visual_message_log: List[Dict] = []

        # Determine where to save tool-call screenshots
        # (prefer log_dir / sandbox_tmp / tmp_dir fallback)
        tool_log_dir = (
            log_dir
            or sandbox_tmp
            or os.path.join(self.sandbox_tmp_dir, f"sample_{sample_idx:04d}")
        )
        os.makedirs(tool_log_dir, exist_ok=True)

        # tool_use/ staging directory: each tool call gets its own numbered subfolder here.
        # After successful generation it is moved into <scene_id>/tool_use/ by save_benchmark_sample.
        tool_use_staging_dir = os.path.join(tool_log_dir, "tool_use")
        os.makedirs(tool_use_staging_dir, exist_ok=True)

        # Shared call counter — mutable int wrapped in a list so all wrappers share one counter.
        shared_call_counter: List[int] = [0]

        # ── Build tool functions (sandbox-aware) ────────────────────────
        tools_scene: List[Dict] = []
        tools_milestone: List[Dict] = []
        tools_validator: List[Dict] = []

        if self._sandbox is not None:
            # Build AutoGen-compatible tool specs
            # Pass tool_log_dir so every screenshot is saved under
            # <tool_log_dir>/logs/<tool_name>_<ts>/ automatically.
            _cmd_tool_raw = make_execute_commands_tool(self._sandbox, default_log_dir=tool_log_dir)
            _shot_tool_raw = make_screenshot_tool(self._sandbox, default_log_dir=tool_log_dir)
            _act_tool_raw = make_agent_action_tool(self._sandbox, default_log_dir=tool_log_dir)
            _run_tool_raw = make_run_agent_tool(self._sandbox, default_log_dir=tool_log_dir, agent_model=self.api_model)
            _preview_tool_raw = make_preview_scene_tool(
                self._sandbox,
                default_log_dir=tool_log_dir,
                agent_model=self.api_model,  # use same model as orchestrator (e.g. "openai/gpt-5.1")
            )

            # ── Create ONE shared wrapper per tool ──────────────────────────
            # Using separate per-agent wrappers caused "Function X not found"
            # errors when the speaker selector handed the turn to an agent that
            # didn't have the tool registered in its own function_map.
            # A single shared instance is registered into EVERY agent that should
            # have access to that tool, so whichever agent is selected by the
            # GroupChat speaker can always execute the function.
            # The agent_label is set to "[auto]" — the actual caller's name is
            # logged by the _LoggingToolWrapper based on who triggered the call.
            def _wrap_shared(name: str, fn):
                return _LoggingToolWrapper(
                    name, fn, tool_call_log, tool_log_dir, "[auto]",
                    visual_log=visual_log,
                    tool_use_dir=tool_use_staging_dir,
                    call_counter=shared_call_counter,
                )

            # Shared callable instances — registered into multiple agents below
            _cmd_shared     = _wrap_shared("execute_minecraft_commands", _cmd_tool_raw)
            _shot_shared    = _wrap_shared("take_screenshot",             _shot_tool_raw)
            _act_shared     = _wrap_shared("execute_agent_action",        _act_tool_raw)
            _run_shared     = _wrap_shared("run_agent_episode",            _run_tool_raw)
            _preview_shared = _wrap_shared("preview_scene_in_sandbox",    _preview_tool_raw)

            # Aliases (kept for clarity in tools_* lists below)
            _cmd_scene     = _cmd_shared
            _shot_scene    = _shot_shared
            _act_scene     = _act_shared
            _run_scene     = _run_shared
            _preview_scene = _preview_shared
            _cmd_mile   = _cmd_shared
            _shot_mile  = _shot_shared
            _act_mile   = _act_shared
            _run_mile   = _run_shared
            _cmd_val    = _cmd_shared
            _shot_val   = _shot_shared
            _act_val    = _act_shared
            _run_val    = _run_shared

            # Register as autogen function tools (name + description + callable)
            tools_scene = [
                {
                    "name": "preview_scene_in_sandbox",
                    "description": (
                        "**PRIMARY SCENE VERIFICATION TOOL** — Build the scene in the live sandbox "
                        "(mirrors eval_benchmark.py exactly): create_env(commands) → reset() → "
                        "loading_steps noop steps to settle → save initial frame → "
                        "DefaultAgent explores for up to max_walk_steps steps autonomously "
                        "(get_action → env.step loop, identical to eval_benchmark.py). "
                        "No extra spectator screenshots or teleports — the agent sees only what "
                        "a real player sees and decides autonomously where to walk and look. "
                        "All frames are injected as inline images for you to examine. "
                        f"Args: commands (list[str] — scene build /commands, required), "
                        f"explore_prompt (str — task description for the agent; defaults to generic "
                        "scene-observation prompt), "
                        f"max_walk_steps (int ≤ {_PREVIEW_MAX_STEPS}, default {_PREVIEW_MAX_STEPS}), "
                        "loading_steps (int — noop steps after reset to let commands settle, default 20). "
                        "Returns: initial_frame (one frame after settle), explore_frames (per-step "
                        "with thought + action), all_frames, total_steps, saved_dir, commands_executed."
                    ),
                    "function": _preview_scene,
                },
                {
                    "name": "execute_minecraft_commands",
                    "description": (
                        "Execute Minecraft /commands (e.g. /fill, /setblock, /summon) in the live "
                        "sandbox and receive screenshots. "
                        "Args: commands (list[str]), perspectives (list: first_person|overhead|"
                        "inventory|north|south|east|west — use all cardinal directions for full docs). "
                        "Returns dict with base64 PNG per perspective and saved_paths."
                    ),
                    "function": _cmd_scene,
                },
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the current Minecraft view. Returns base64 PNG.",
                    "function": _shot_scene,
                },
                {
                    "name": "execute_agent_action",
                    "description": (
                        "Execute a single MinerRL player action in the sandbox and observe the result. "
                        "Use this to physically navigate the scene you designed — walk forward/back, "
                        "look around, mine blocks, or interact with objects. "
                        "Args: action (dict with keys: forward|back|left|right|jump|attack|use|sneak|"
                        "sprint|camera=[pitch_delta,yaw_delta]|chat='/command', all default 0), "
                        "repeat (int, number of steps). "
                        "Returns dict with frames_b64 (list of base64 PNG), saved_paths (list of paths), "
                        "last_frame_b64 (final frame as base64 PNG). "
                        "Example — walk forward 5 steps: "
                        "{\"action\": {\"forward\": 1}, \"repeat\": 5}"
                    ),
                    "function": _act_scene,
                },
                {
                    "name": "run_agent_episode",
                    "description": (
                        "Run an AI agent for up to max_steps steps in the current scene. "
                        "Use this to verify whether the designed scene actually allows a player to "
                        "complete the intended tasks. The agent will attempt the task autonomously and "
                        "return per-step observations and screenshots. "
                        "Args: task_text (str — describe the task in plain English), "
                        "max_steps (int, default 10). "
                        "Returns dict with steps (list of {thought, action_text, frame_b64, step_idx}), "
                        "final_frame_b64, total_steps."
                    ),
                    "function": _run_scene,
                },
            ]
            tools_milestone = [
                {
                    "name": "execute_minecraft_commands",
                    "description": (
                        "Execute Minecraft /commands and receive screenshots. "
                        "Args: commands (list[str]), perspectives (list: first_person|overhead|"
                        "inventory|north|south|east|west). "
                        "Returns dict with base64 PNG per perspective and saved_paths."
                    ),
                    "function": _cmd_mile,
                },
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the current Minecraft view. Returns base64 PNG.",
                    "function": _shot_mile,
                },
                {
                    "name": "execute_agent_action",
                    "description": (
                        "Execute a single MinerRL player action in the sandbox and observe the result. "
                        "Use this to physically walk to specific coordinates, look around, or interact "
                        "with objects to verify milestone spatial conditions. "
                        "Args: action (dict with keys: forward|back|left|right|jump|attack|use|sneak|"
                        "sprint|camera=[pitch_delta,yaw_delta]|chat='/command', all default 0), "
                        "repeat (int, number of steps). "
                        "Returns dict with frames_b64 (list of base64 PNG), saved_paths (list), "
                        "last_frame_b64 (final frame). "
                        "Example — walk forward 5 steps: "
                        "{\"action\": {\"forward\": 1}, \"repeat\": 5}"
                    ),
                    "function": _act_mile,
                },
                {
                    "name": "run_agent_episode",
                    "description": (
                        "Run an AI agent in the sandbox for up to max_steps steps. "
                        "Useful to verify a task is completable and observe milestone transitions. "
                        "Args: task_text (str), max_steps (int). Returns steps + final_frame_b64."
                    ),
                    "function": _run_mile,
                },
            ]
            tools_validator = [
                {
                    "name": "execute_minecraft_commands",
                    "description": (
                        "Execute Minecraft /commands and receive screenshots. "
                        "Args: commands (list[str]), perspectives (list: first_person|overhead|"
                        "inventory|north|south|east|west). "
                        "Returns dict with base64 PNG per perspective and saved_paths."
                    ),
                    "function": _cmd_val,
                },
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the current Minecraft view. Returns base64 PNG.",
                    "function": _shot_val,
                },
                {
                    "name": "execute_agent_action",
                    "description": (
                        "Execute a single MinerRL player action in the sandbox and observe the result. "
                        "Walk to coordinates, interact with objects, or check positions for validation. "
                        "Args: action (dict with keys: forward|back|left|right|jump|attack|use|sneak|"
                        "sprint|camera=[pitch_delta,yaw_delta]|chat='/command', all default 0), "
                        "repeat (int, number of steps). "
                        "Returns dict with frames_b64 (list of base64 PNG), saved_paths (list), "
                        "last_frame_b64 (final frame)."
                    ),
                    "function": _act_val,
                },
                {
                    "name": "run_agent_episode",
                    "description": (
                        "Run an AI agent for up to max_steps steps for end-to-end validation. "
                        "Args: task_text (str), max_steps (int). Returns steps + final_frame_b64."
                    ),
                    "function": _run_val,
                },
            ]

        # ── System prompts ───────────────────────────────────────────────
        task_selector_sys = self._build_task_selector_system()
        scene_designer_sys = self._build_scene_designer_system(tools_scene)
        milestone_sys = self._build_milestone_system(tools_milestone)
        commonsense_sys = self._build_commonsense_system()
        validator_sys = self._build_validator_system(tools_validator)

        # ── Create ConversableAgents ─────────────────────────────────────
        # Total scheduled turns per agent across the whole conversation:
        # INIT_ORDER has 5 steps + DEBATE_ORDER has 9 steps per round.
        # SceneDesignerAgent gets up to 2 turns in INIT + 2 per debate round.
        # MilestoneAgent gets 1 turn in INIT + 1 per debate round (direct output, no inquiry).
        # Each substep can consume at most a few extra tool turns on top of the
        # agent's own text reply.  SceneDesignerAgent and ValidatorAgent (sandbox/move
        # tools) are capped at 1 extra turn each; all other agents at 5 extra turns.
        # Use the larger cap (5) for the headroom formula to stay safe.
        _total_substeps = len(INIT_ORDER) + self.max_debate_rounds * len(DEBATE_ORDER)
        _agent_max_reply = _total_substeps * (5 + 1) + 10

        task_selector = _VisualToolAgent(
            name="TaskSelectorAgent",
            system_message=task_selector_sys,
            llm_config=self._llm_config("task_selector"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=_agent_max_reply,
            visual_log=visual_log,
            visual_message_log=visual_message_log,
        )

        # SceneDesignerAgent uses _VisualToolAgent so that sandbox screenshots
        # are injected as multimodal messages after each tool call.
        scene_designer = _VisualToolAgent(
            name="SceneDesignerAgent",
            system_message=scene_designer_sys,
            llm_config=self._llm_config("scene_designer"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=_agent_max_reply,
            visual_log=visual_log,
            visual_message_log=visual_message_log,
        )
        # Register sandbox tools for SceneDesigner
        if tools_scene:
            self._register_tools(scene_designer, tools_scene)

        # MilestoneAgent also uses _VisualToolAgent (has execute_minecraft_commands tool)
        milestone_agent = _VisualToolAgent(
            name="MilestoneAgent",
            system_message=milestone_sys,
            llm_config=self._llm_config("milestone"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=_agent_max_reply,
            visual_log=visual_log,
            visual_message_log=visual_message_log,
        )
        if tools_milestone:
            self._register_tools(milestone_agent, tools_milestone)

        # CommonSenseAgent uses _VisualToolAgent so it can receive sandbox images
        # injected by other agents' tool calls.  We register ALL four sandbox tools
        # here so that the LLM never sees "Function X not found" when it tries to use
        # a tool it has witnessed other agents use successfully in the shared GroupChat
        # history.  The system prompt lists exactly these four tools.
        tools_commonsense: List[Dict] = []
        if self._sandbox is not None:
            tools_commonsense = [
                {
                    "name": "preview_scene_in_sandbox",
                    "description": (
                        "Build the scene in the live sandbox and explore it: "
                        "create_env(commands) → reset() → DefaultAgent explores autonomously. "
                        "Args: commands (list[str] — scene build /commands, required), "
                        "explore_prompt (str — task description for the agent), "
                        f"max_walk_steps (int ≤ {_PREVIEW_MAX_STEPS}, default {_PREVIEW_MAX_STEPS}), "
                        "loading_steps (int — noop steps after reset, default 20). "
                        "Returns: initial_frame, explore_frames, all_frames, total_steps, saved_dir, commands_executed."
                    ),
                    "function": _preview_shared,
                },
                {
                    "name": "execute_minecraft_commands",
                    "description": (
                        "Execute Minecraft /commands and receive screenshots. "
                        "Args: commands (list[str]), perspectives (list: first_person|overhead|"
                        "inventory|north|south|east|west). "
                        "Returns dict with base64 PNG per perspective and saved_paths."
                    ),
                    "function": _cmd_shared,
                },
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the current Minecraft view. Returns base64 PNG.",
                    "function": _shot_shared,
                },
                {
                    "name": "execute_agent_action",
                    "description": (
                        "Execute a single MinerRL player action in the sandbox and observe the result. "
                        "Args: action (dict with keys: forward|back|left|right|jump|attack|use|sneak|"
                        "sprint|camera=[pitch_delta,yaw_delta]|chat='/command', all default 0), "
                        "repeat (int, number of steps). "
                        "Returns dict with frames_b64 (list of base64 PNG), saved_paths (list), "
                        "last_frame_b64 (final frame)."
                    ),
                    "function": _act_shared,
                },
                {
                    "name": "run_agent_episode",
                    "description": (
                        "Run an AI agent for up to max_steps steps in the current scene. "
                        "Args: task_text (str), max_steps (int). Returns steps + final_frame_b64."
                    ),
                    "function": _run_shared,
                },
            ]

        commonsense_agent = _VisualToolAgent(
            name="CommonSenseAgent",
            system_message=commonsense_sys,
            llm_config=self._llm_config("commonsense"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=_agent_max_reply,
            visual_log=visual_log,
            visual_message_log=visual_message_log,
        )
        # Register local wiki tools
        if self.enable_wiki:
            self._register_tools(commonsense_agent, make_wiki_tools())
        # Register sandbox tools (basic subset) so the model never gets "Function not found"
        if tools_commonsense:
            self._register_tools(commonsense_agent, tools_commonsense)

        # ValidatorAgent uses _VisualToolAgent (has execute_minecraft_commands tool)
        validator_agent = _VisualToolAgent(
            name="ValidatorAgent",
            system_message=validator_sys,
            llm_config=self._llm_config("validator"),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=_agent_max_reply,
            visual_log=visual_log,
            visual_message_log=visual_message_log,
        )
        if tools_validator:
            self._register_tools(validator_agent, tools_validator)

        # Orchestrator (UserProxy – drives conversation, no LLM)
        # max_consecutive_auto_reply=1 so it can reply once to kick off the chat,
        # then stops.  Termination is handled by max_round being exhausted OR by
        # the speaker-selector entering "done" and returning None.
        orchestrator = UserProxyAgent(
            name="Orchestrator",
            system_message=(
                "You are the benchmark generation orchestrator. "
                "You initiate tasks and collect final outputs. "
                "Do NOT add new instructions – just observe and terminate."
            ),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
            code_execution_config=False,
            # Never terminate based on message content – rely on max_round / speaker selector
            is_termination_msg=lambda msg: False,
        )

        # ── GroupChat setup ──────────────────────────────────────────────
        # max_round: each substep can consume at most a few extra tool turns.
        # SceneDesignerAgent/ValidatorAgent are capped at 1; others at 5.
        # Use the larger cap (5) for the formula so there is always enough room.
        # This ensures MilestoneAgent always gets its turn.
        _total_substeps = len(INIT_ORDER) + self.max_debate_rounds * len(DEBATE_ORDER)
        max_round = _total_substeps * (5 + 1) + 20

        groupchat = GroupChat(
            agents=[orchestrator, task_selector, scene_designer,
                    milestone_agent, commonsense_agent, validator_agent],
            messages=[],
            max_round=max_round,
            speaker_selection_method=self._make_speaker_selector(
                max_debate_rounds=self.max_debate_rounds,
            ),
            allow_repeat_speaker=True,
        )
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self._llm_config("task_selector"),  # manager uses same LLM for routing
        )

        # ── Kick off conversation ────────────────────────────────────────
        candidate_list_str = "\n".join(
            f"  {i+1}. {t}" for i, t in enumerate(candidate_tasks)
        )
        init_msg = self._build_init_message(candidate_tasks, k, candidate_list_str)

        self._log("Starting GroupChat...")
        orchestrator.initiate_chat(
            manager,
            message=init_msg,
            clear_history=True,
        )

        # ── Extract results from conversation history ────────────────────
        return self._extract_result(
            groupchat.messages,
            candidate_tasks,
            sample_idx,
            tool_call_log=tool_call_log,
            visual_message_log=visual_message_log,
        )

    # ------------------------------------------------------------------
    # Tool registration helper
    # ------------------------------------------------------------------

    @staticmethod
    def _build_tool_schemas(tools: List[Dict]) -> List[Dict]:
        """
        Convert our internal tool list into OpenAI function-calling schema dicts.

        We use pre-defined schemas for the four known sandbox tools so that the
        LLM receives well-typed parameter descriptions.  Any unknown tool falls
        back to an automatic inspect-based schema.
        """
        # Pre-defined schemas for the four sandbox tools used in MCBench
        _KNOWN_SCHEMAS: Dict[str, Dict] = {
            "execute_minecraft_commands": {
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of Minecraft slash-commands to execute, "
                            "e.g. [\"/fill ~0 ~0 ~0 ~5 ~3 ~5 oak_planks\"]"
                        ),
                    },
                    "perspectives": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["first_person", "overhead", "inventory",
                                     "north", "south", "east", "west"],
                        },
                        "description": (
                            "Which perspectives to capture after the commands. "
                            "Use all cardinal directions for a full map view."
                        ),
                    },
                },
                "required": ["commands"],
            },
            "take_screenshot": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "execute_agent_action": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "object",
                        "description": (
                            "MinerRL action dict. Keys: forward, back, left, right, "
                            "jump, attack, use, sneak, sprint (all 0/1), "
                            "camera=[pitch_delta, yaw_delta], chat='/command'. "
                            "Example walk forward: {\"forward\": 1}"
                        ),
                    },
                    "repeat": {
                        "type": "integer",
                        "description": "Number of steps to repeat the action (default 1).",
                    },
                },
                "required": ["action"],
            },
            "run_agent_episode": {
                "type": "object",
                "properties": {
                    "task_text": {
                        "type": "string",
                        "description": "Plain-English description of the task for the AI agent.",
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "Maximum number of steps to run (default 10).",
                    },
                },
                "required": ["task_text"],
            },
            # ── Wiki tools (used by CommonSenseAgent) ────────────────────────
            "wiki_list_categories": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "wiki_list_keys": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Wiki database to list. One of: "
                            "blocks, items, mobs, biomes, effects, "
                            "enchantments, structures."
                        ),
                    },
                },
                "required": ["category"],
            },
            "wiki_lookup": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Wiki database to query. One of: "
                            "blocks, items, mobs, biomes, effects, "
                            "enchantments, structures."
                        ),
                    },
                    "names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of exact object names to look up "
                            "(as returned by wiki_list_keys)."
                        ),
                    },
                },
                "required": ["category", "names"],
            },
            # ── Sandbox tools ─────────────────────────────────────────────────
            "preview_scene_in_sandbox": {
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of Minecraft /commands to build the scene "
                            "(e.g. /fill, /setblock, /summon, /give, /effect). "
                            "Scene is rebuilt via create_env, then the agent explores it."
                        ),
                    },
                    "explore_prompt": {
                        "type": "string",
                        "description": (
                            "Optional task description for the exploration agent. "
                            "Defaults to a generic scene-observation prompt. "
                            "Example: 'Walk to the lake and verify its borders'."
                        ),
                    },
                    "max_walk_steps": {
                        "type": "integer",
                        "description": (
                            f"Number of AI-agent exploration steps (hard cap: {_PREVIEW_MAX_STEPS}, "
                            f"default {_PREVIEW_MAX_STEPS})."
                        ),
                    },
                    "loading_steps": {
                        "type": "integer",
                        "description": (
                            "Noop steps after reset to let init commands settle (default 20, "
                            "same as eval_benchmark.py --loading-command-steps)."
                        ),
                    },
                },
                "required": ["commands"],
            },
        }

        import inspect
        schemas = []
        for tool in tools:
            fn   = tool["function"]
            name = tool["name"]
            desc = tool.get("description", "")

            if name in _KNOWN_SCHEMAS:
                params = _KNOWN_SCHEMAS[name]
            else:
                # Auto-build schema from function signature (best-effort)
                # If fn is a _LoggingToolWrapper, inspect the wrapped function
                raw_fn = getattr(fn, "_fn", fn)
                try:
                    sig  = inspect.signature(raw_fn)
                except (ValueError, TypeError):
                    sig = inspect.signature(fn)
                props: Dict[str, Any] = {}
                required: List[str]   = []
                for pname, param in sig.parameters.items():
                    if pname in ("self",):
                        continue
                    if param.kind in (
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    ):
                        continue
                    ann = param.annotation
                    if ann is int:
                        ptype = "integer"
                    elif ann is float:
                        ptype = "number"
                    elif ann is bool:
                        ptype = "boolean"
                    elif ann is str:
                        ptype = "string"
                    else:
                        ptype = "object"
                    props[pname] = {"type": ptype, "description": pname}
                    if param.default is inspect.Parameter.empty:
                        required.append(pname)
                params = {"type": "object", "properties": props, "required": required}

            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": params,
                },
            }
            schemas.append(schema)
        return schemas

    @staticmethod
    def _register_tools(agent: ConversableAgent, tools: List[Dict]) -> None:
        """
        Register sandbox tool functions into an AutoGen agent (v0.2.x compatible).

        Two things must happen for function calling to work:
          1. agent.register_function()     — maps name → callable for execution
          2. agent.update_tool_signature() — tells the LLM which functions it can call

        Without (2) the LLM never emits tool_call messages; it just writes
        JSON-looking text in its reply instead.
        """
        schemas = BenchmarkOrchestrator._build_tool_schemas(tools)

        for tool, schema in zip(tools, schemas):
            # 1. Register execution callable
            agent.register_function(
                function_map={tool["name"]: tool["function"]}
            )
            # Verify it landed in the function_map
            if tool["name"] not in (agent._function_map or {}):
                raise RuntimeError(
                    f"register_function succeeded but '{tool['name']}' is still missing "
                    f"from {agent.name}._function_map. "
                    f"Registered keys: {list((agent._function_map or {}).keys())}"
                )
            print(f"  [Orchestrator] Registered function '{tool['name']}' into {agent.name}")

            # 2. Register tool schema via the official AutoGen API (works for 0.2.x)
            try:
                agent.update_tool_signature(schema, is_remove=False)
                print(
                    f"  [Orchestrator] Registered tool schema '{tool['name']}' "
                    f"into {agent.name}"
                )
            except Exception as e:
                # Fallback: directly mutate llm_config["tools"] (older autogen builds)
                print(
                    f"  [Orchestrator] update_tool_signature failed for '{tool['name']}': {e}. "
                    "Falling back to direct llm_config mutation."
                )
                try:
                    lc = agent.llm_config
                    existing = lc.get("tools") or [] if hasattr(lc, "get") else []
                    existing_names = {
                        s["function"]["name"] for s in existing
                        if isinstance(s, dict) and "function" in s
                    }
                    if schema["function"]["name"] not in existing_names:
                        lc["tools"] = list(existing) + [schema]
                except Exception as _e2:
                    print(f"  [Orchestrator] Fallback also failed: {_e2}")

    # ------------------------------------------------------------------
    # Custom speaker selector (state-machine style)
    # ------------------------------------------------------------------

    def _make_speaker_selector(self, max_debate_rounds: int):
        """
        Returns a speaker_selection_method callable.

        The conversation flows through a fixed sequence:
          INIT: Orchestrator (init msg) → TaskSelector → SceneDesigner → Milestone
                → SceneDesigner (respond) → Milestone (finalise)
          DEBATE × N: CommonSense → Validator → Validator → TaskSelector → SceneDesigner
                      → Milestone → CommonSense (re-check) → Validator (re-validate)
          DONE: return None → GroupChat terminates naturally

        Returning None from the selector causes AutoGen GroupChat to stop the
        conversation without requiring any agent to post a termination message.
        """
        # Per-agent cap on extra tool-call/result turns within a single substep.
        # Agents that call scene-rendering or movement tools are capped tightly (1)
        # to prevent long sandbox loops that starve later agents.
        # Wiki-query agents and others get a slightly higher cap (5).
        _TOOL_TURN_LIMIT: dict = {
            "SceneDesignerAgent": 2,
            "ValidatorAgent":     2,
        }
        _TOOL_TURN_LIMIT_DEFAULT = 5

        state = {
            "phase": "init",
            "substep": 0,
            "debate_round": 0,
            "tool_turns_this_substep": 0,   # counts same-speaker extra turns consumed
        }
        # INIT_ORDER and DEBATE_ORDER are module-level constants (defined at top of file)

        def _last_message_needs_same_speaker(groupchat: GroupChat) -> bool:
            """Return True when the last GroupChat message requires the SAME speaker again.

            Two cases:
            1. role='tool' / tool_responses:  The tool has already executed and returned
               its result.  The originating agent must get one more turn to write a
               human-readable reply that references the tool output.

            2. role='assistant' with tool_calls:  AutoGen 0.2 emits the tool_calls
               message from generate_reply and then immediately calls
               generate_tool_calls_reply on the SAME agent to execute the functions.
               In the GroupChat run_chat loop the tool_calls assistant message is
               appended first; the next generate_reply call on the *same* agent handles
               execution.  If our custom selector hands control to a DIFFERENT agent at
               this point, that agent sees an unresolved tool_calls message in its
               oai_messages and tries to execute it via its own _function_map —
               which fails with "Function not found" if the tool is not registered there.
            """
            msgs = groupchat.messages
            if not msgs:
                return False
            last = msgs[-1]
            # Case 1: tool result already appended
            if last.get("role") == "tool" or bool(last.get("tool_responses")):
                return True
            # Case 2: pending tool_calls request (assistant message with tool_calls list)
            if last.get("role") == "assistant" and bool(last.get("tool_calls")):
                return True
            return False

        def selector(last_speaker, groupchat: GroupChat):
            agents_by_name = {a.name: a for a in groupchat.agents}

            phase = state["phase"]

            # ── DONE ─────────────────────────────────────────────────────
            # Returning None terminates the GroupChat cleanly.
            if phase == "done":
                return None

            # ── Tool-call / Tool-result intercept ────────────────────────
            # If the last GroupChat message is either:
            #   • a pending tool_calls request (the agent hasn't executed it yet), OR
            #   • a tool result (the agent needs to summarise the result)
            # … then return the SAME speaker so it can handle its own tool calls
            # and write its final text reply before we advance to the next step.
            #
            # Safety valve: if the same agent has already consumed _MAX_TOOL_TURNS_PER_SUBSTEP
            # extra turns at the current substep, forcibly advance rather than allowing it
            # to loop indefinitely (e.g. SceneDesignerAgent calling preview repeatedly).
            if _last_message_needs_same_speaker(groupchat):
                _limit = _TOOL_TURN_LIMIT.get(
                    last_speaker.name, _TOOL_TURN_LIMIT_DEFAULT
                )
                if state["tool_turns_this_substep"] < _limit:
                    state["tool_turns_this_substep"] += 1
                    print(
                        f"  [Speaker] Tool call/result detected – giving {last_speaker.name} "
                        f"an extra turn ({state['tool_turns_this_substep']}/{_limit}) "
                        "(substep not advanced)"
                    )
                    return last_speaker
                else:
                    print(
                        f"  [Speaker] ⚠️  {last_speaker.name} reached tool-turn limit "
                        f"({_limit}) at substep {state['substep']-1} – "
                        "forcing substep advance to unblock next agent."
                    )

            # ── INIT phase ───────────────────────────────────────────────
            if phase == "init":
                step = state["substep"]
                if step < len(INIT_ORDER):
                    next_name = INIT_ORDER[step]
                    state["substep"] += 1
                    state["tool_turns_this_substep"] = 0   # reset per-substep counter
                    print(f"  [Speaker] INIT step {step} → {next_name}")
                    return agents_by_name.get(next_name)
                else:
                    if max_debate_rounds > 0:
                        # Transition to debate – substep=1 because we are
                        # already returning DEBATE_ORDER[0] right now.
                        state["phase"] = "debate"
                        state["substep"] = 1
                        state["debate_round"] = 1
                        state["tool_turns_this_substep"] = 0
                        print(f"  [Speaker] → DEBATE round 1")
                        return agents_by_name.get(DEBATE_ORDER[0])
                    else:
                        # No debate rounds requested – finish directly
                        state["phase"] = "done"
                        print("  [Speaker] → DONE (no debate rounds)")
                        return None

            # ── DEBATE phase ─────────────────────────────────────────────
            if phase == "debate":
                step = state["substep"]
                if step < len(DEBATE_ORDER):
                    next_name = DEBATE_ORDER[step]
                    state["substep"] += 1
                    state["tool_turns_this_substep"] = 0   # reset per-substep counter
                    print(f"  [Speaker] DEBATE round {state['debate_round']} step {step} → {next_name}")
                    return agents_by_name.get(next_name)
                else:
                    # End of one debate round
                    next_round = state["debate_round"] + 1
                    if next_round > max_debate_rounds:
                        # All debate rounds complete – terminate
                        state["phase"] = "done"
                        print("  [Speaker] → DONE (all debate rounds complete)")
                        return None
                    else:
                        state["debate_round"] = next_round
                        # substep=1: we are already returning DEBATE_ORDER[0]
                        state["substep"] = 1
                        state["tool_turns_this_substep"] = 0
                        print(f"  [Speaker] → DEBATE round {next_round}")
                        return agents_by_name.get(DEBATE_ORDER[0])

            # Fallback – should not be reached
            return None

        return selector

    # ------------------------------------------------------------------
    # Initial message
    # ------------------------------------------------------------------

    def _build_init_message(
        self,
        candidate_tasks: List[str],
        k: int,
        candidate_list_str: str,
    ) -> str:
        sandbox_note = (
            "\n\n## Sandbox Preview — MANDATORY for SceneDesignerAgent\n\n"
            "SceneDesignerAgent has access to the **`preview_scene_in_sandbox`** function tool.\n\n"
            "### ⚠️ HOW TO CALL THE TOOL — CRITICAL\n"
            "You MUST call `preview_scene_in_sandbox` using the **native function call mechanism**.\n"
            "This means your model emits a `tool_calls` message — NOT a JSON text block.\n\n"
            "**WRONG** (do NOT do this — it is just text and executes nothing):\n"
            "```\n"
            "{\"tool_name\": \"preview_scene_in_sandbox\", \"arguments\": {...}}\n"
            "```\n\n"
            "**CORRECT**: Simply decide to call the tool. Your message should be a brief note\n"
            "like *\"Calling preview_scene_in_sandbox now with the agreed commands.\"* followed\n"
            "by the actual function invocation that your model runtime handles automatically.\n\n"
            "The tool will (identical to eval_benchmark.py's _run_benchmark):\n"
            "  1. Rebuild the scene: create_env(commands=[...]).\n"
            "  2. reset() → 20 noop steps to let commands settle → save ONE initial frame.\n"
            "  3. Run a DefaultAgent for up to 20 steps autonomously:\n"
            "     agent.get_action(frame_buffer, thoughts, actions) → env.step → save frame.\n"
            "     The agent decides where to walk and look — goal is OBSERVATION.\n"
            "  4. Inject the initial frame + all per-step exploration frames as inline images.\n\n"
            "After the tool call completes, the images appear in the conversation.\n"
            "In your NEXT turn describe what you actually observed in those images.\n"
            "**Never fabricate screenshot descriptions** before calling the tool.\n"
        )

        # If sandbox startup failed, add a fallback note so agents can still proceed
        if self._sandbox is None:
            sandbox_note += (
                "\n> **Note**: The sandbox failed to start for this run. "
                "SceneDesignerAgent should design the scene based on Minecraft knowledge "
                "and mark screenshot observations as unavailable.\n"
            )

        scene_designer_turn_note = (
            "\n   **SceneDesignerAgent — CRITICAL for TURN 1**: After reading TaskSelectorAgent's\n"
            "   output, design the scene in your mind, then **IMMEDIATELY call the\n"
            "   `preview_scene_in_sandbox` function tool** with all your commands.\n"
            "   YOUR FIRST MESSAGE MUST BE SHORT — just 1-2 sentences saying you are calling the\n"
            "   tool, then immediately emit the native function call.\n"
            "   ⛔ DO NOT output a full JSON block with `screenshot_observations` in your first turn.\n"
            "   ⛔ DO NOT write `{\"tool_name\": ...}` — that is plain text and does nothing.\n"
            "   ✅ The correct pattern: short text → native function call (your model handles this).\n"
        )

        return f"""
# MCBench Multi-Agent Benchmark Generation — START

You are participating in a **multi-agent collaborative workflow** to generate a
high-quality Minecraft multi-hop benchmark sample.

## Your Roles
- **TaskSelectorAgent**: Select {k} atomic tasks and build a dependency DAG.
- **SceneDesignerAgent**: Design the Minecraft scene. You have sandbox tools including
  `preview_scene_in_sandbox` to build the scene, run an AI exploration agent through it
  (up to 20 steps, same loop as eval_benchmark.py), and share visual findings with all agents.
- **MilestoneAgent**: Design rule-based milestone completion criteria. You have
  sandbox tools to verify spatial coordinates.
- **CommonSenseAgent**: Check for Minecraft-specific knowledge bottlenecks and
  respond to SceneDesigner's sandbox findings.
- **ValidatorAgent**: Validate the dependency graph and milestone rules. You have
  sandbox tools to verify scene state.{sandbox_note}

## Candidate Tasks ({len(candidate_tasks)} total, select {k})
{candidate_list_str}

## Conversation Flow
1. **TaskSelectorAgent** selects {k} tasks and outputs the dependency DAG.
2. **SceneDesignerAgent** designs the scene and calls `preview_scene_in_sandbox` as a
   **function call** (not JSON text) with the commands you just designed. The sandbox
   builds the scene, captures screenshots, and walks through it up to 20 steps.{scene_designer_turn_note}
3. **SceneDesignerAgent** (2nd turn) reports sandbox observations: what it actually saw in each
   frame, any issues found, and proposals for the team. (Only describe images you received.)
4. **CommonSenseAgent** reacts to the sandbox report with early common-sense feedback.
5. **MilestoneAgent** — **IMMEDIATELY outputs the final milestone rules JSON** based on all
   information above. **DO NOT ask questions first.** Read SceneDesignerAgent's scene report
   carefully — it contains all coordinates and spatial layout needed. Output the complete
   `{{"milestones": [...]}}` JSON block in this single turn.
6. Debate rounds follow: CommonSense → Validator → Validator → TaskSelector →
   SceneDesigner (function call + report) → Milestone → CommonSense → Validator.

## Instructions for TaskSelectorAgent
Please start by selecting exactly {k} tasks from the candidates above.
Output a JSON block with:
```json
{{
  "selected_tasks": ["task_a", "task_b", ...],
  "selection_reasoning": "...",
  "dependency_graph": {{
    "nodes": ["task_a", "task_b", ...],
    "edges": [{{"from": "task_a", "to": "task_b", "reason": "..."}}]
  }}
}}
```

Begin!
""".strip()

    # ------------------------------------------------------------------
    # System prompt builders
    # ------------------------------------------------------------------

    def _build_task_selector_system(self) -> str:
        # Use the agent module's SYSTEM_PROMPT (already contains full instructions)
        return _TASK_SELECTOR_SYS

    def _build_scene_designer_system(self, tools: List[Dict]) -> str:
        """Build SceneDesigner system prompt, appending sandbox tool descriptions if available."""
        base = _SCENE_DESIGNER_SYS
        if not tools:
            return base + (
                "\n\n## Sandbox Tools\n"
                "No sandbox is connected for this run. Design the scene based on your knowledge\n"
                "of Minecraft; you will not be able to call preview tools."
            )
        tool_desc = (
            "\n\n## Available Sandbox Tools (registered as native function calls)\n\n"
            "The following tools are registered as **real function-call tools** in your runtime.\n"
            "To use them, issue a function call — do NOT write `{\"tool_name\": ...}` in your message.\n\n"
            + "\n".join(f"- **`{t['name']}`**: {t['description']}" for t in tools)
            + "\n\n"
            "### Workflow reminder for SceneDesignerAgent\n"
            "1. After TaskSelectorAgent outputs the tasks, design your scene commands.\n"
            "2. **Immediately call `preview_scene_in_sandbox`** as a function call with all your commands.\n"
            "   - Your message body can be brief: just say you are calling the preview tool.\n"
            "   - Do NOT write out `{\"tool_name\": \"preview_scene_in_sandbox\", ...}` in your message.\n"
            "3. After the tool result arrives (images injected), describe what you saw in the next message.\n"
            "4. During debate, call the tool again whenever the team revises the commands.\n"
        )
        return base + tool_desc

    def _build_milestone_system(self, tools: List[Dict]) -> str:
        """Build MilestoneAgent system prompt, appending sandbox tool descriptions if available."""
        base = _MILESTONE_SYS
        if not tools:
            return base
        tool_desc = "\n\n## Available Sandbox Tools (injected by Orchestrator)\n" + "\n".join(
            f"- **{t['name']}**: {t['description']}" for t in tools
        )
        return base + tool_desc

    def _build_commonsense_system(self) -> str:
        """Build CommonSenseAgent system prompt."""
        base = _COMMONSENSE_SYS
        if not self.enable_wiki:
            base = base + "\n\nNote: Minecraft wiki queries are disabled for this run."
        if self._sandbox is not None:
            base = base + (
                "\n\n## Available Sandbox Tools\n"
                "You also have access to the following sandbox tools registered as native function calls:\n"
                "- **`execute_minecraft_commands`**: Execute /commands and capture screenshots.\n"
                "- **`take_screenshot`**: Capture the current view.\n"
                "- **`execute_agent_action`**: Move the player (forward/turn/jump/etc.).\n"
                "- **`run_agent_episode`**: Run an AI agent for N steps to verify task completability.\n\n"
                "Call these tools using the **native function call mechanism** — NOT by writing JSON text.\n"
                "Only call sandbox tools when you need to visually verify something that "
                "cannot be determined from Minecraft knowledge alone."
            )
        return base

    def _build_validator_system(self, tools: List[Dict]) -> str:
        """Build ValidatorAgent system prompt, appending sandbox tool descriptions if available."""
        base = _VALIDATOR_SYS
        if not tools:
            return base
        tool_desc = "\n\n## Available Sandbox Tools (injected by Orchestrator)\n" + "\n".join(
            f"- **{t['name']}**: {t['description']}" for t in tools
        )
        return base + tool_desc

    # ------------------------------------------------------------------
    # Result extraction from conversation history
    # ------------------------------------------------------------------

    def _extract_result(
        self,
        messages: List[Dict[str, Any]],
        candidate_tasks: List[str],
        sample_idx: int,
        tool_call_log: Optional[List[Dict]] = None,
        visual_message_log: Optional[List[Dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse the GroupChat message history to extract the final benchmark outputs.
        Looks for the most recent valid JSON block from each agent.

        visual_message_log: list of injected multimodal image messages from _VisualToolAgent.
        These are interleaved into full_conversation_log at the correct position
        (after the corresponding tool call message) so the conversation record shows
        the images in context.
        """
        self._log("Extracting results from conversation history...")

        # Organise messages by agent name
        # Skip tool-call / tool-result messages so that {"tool_name": ...,
        # "arguments": ...} payloads are never mistaken for JSON outputs from
        # the agents (e.g. milestone JSON).
        _TOOL_ROLES = {"tool", "function"}
        by_agent: Dict[str, List[str]] = {}
        debate_log: List[Dict[str, Any]] = []
        for msg in messages:
            msg_role = msg.get("role", "")

            # Skip raw tool-result messages (role="tool" / "function")
            if msg_role in _TOOL_ROLES:
                continue

            # Skip assistant messages that contain tool_calls (no text content
            # to parse, only a structured tool invocation).
            if msg_role == "assistant" and msg.get("tool_calls"):
                continue

            sender = msg.get("name") or msg_role or "unknown"
            content = msg.get("content") or ""
            # content may be a list (multimodal) — convert for text-based indexing
            if isinstance(content, list):
                # flatten text parts for by_agent text search
                text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                content_str = " ".join(text_parts)
            else:
                content_str = content

            # Also skip if the text itself looks like a raw tool-call JSON
            # (e.g. AutoGen sometimes stores them as string content)
            if content_str.strip().startswith("{") and '"tool_name"' in content_str:
                continue

            by_agent.setdefault(sender, []).append(content_str)
            debate_log.append({
                "from": sender,
                "content": content_str[:500],  # truncate for log
                "timestamp": msg.get("timestamp", ""),
            })

        # Full conversation log (all messages, untruncated)
        # We interleave visual_message_log entries so images appear inline.
        full_conversation_log: List[Dict[str, Any]] = []
        visual_idx = 0
        visual_entries = visual_message_log or []

        for msg in messages:
            sender = msg.get("name") or msg.get("role", "unknown")
            content = msg.get("content") or ""

            # Build text-safe content for log
            if isinstance(content, list):
                text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                log_content = " ".join(text_parts)
            else:
                log_content = content

            full_conversation_log.append({
                "from": sender,
                "content": log_content,
                "timestamp": msg.get("timestamp", ""),
                "role": msg.get("role", ""),
            })

            # After a tool-result message, inject any visual messages whose timestamp
            # matches (best-effort: insert all pending visual entries after each tool msg)
            msg_role = msg.get("role", "")
            if msg_role in ("tool", "function") and visual_idx < len(visual_entries):
                # Insert the next visual entry right after this tool message
                vis_entry = visual_entries[visual_idx]
                full_conversation_log.append({
                    "from": vis_entry.get("from", "SandboxVision"),
                    "content": vis_entry.get("content", ""),
                    "role": "user",
                    "timestamp": vis_entry.get("timestamp", ""),
                    "image_paths": vis_entry.get("image_paths", []),
                    "tool": vis_entry.get("tool", ""),
                    "injected_images": True,
                })
                visual_idx += 1

        # Append any remaining visual entries at the end
        while visual_idx < len(visual_entries):
            vis_entry = visual_entries[visual_idx]
            full_conversation_log.append({
                "from": vis_entry.get("from", "SandboxVision"),
                "content": vis_entry.get("content", ""),
                "timestamp": vis_entry.get("timestamp", ""),
                "image_paths": vis_entry.get("image_paths", []),
                "tool": vis_entry.get("tool", ""),
                "injected_images": True,
            })
            visual_idx += 1

        n_visual = len(visual_entries)
        if n_visual:
            self._log(f"Conversation log includes {n_visual} injected visual messages.")
        # ── Task selection ───────────────────────────────────────────────
        selected_tasks, selection_reasoning, dependency_graph = None, "", None
        for text in reversed(by_agent.get("TaskSelectorAgent", [])):
            obj = extract_json_object(text)
            if not obj:
                continue
            # Initial selection
            if "selected_tasks" in obj and isinstance(obj["selected_tasks"], list):
                selected_tasks = obj["selected_tasks"]
                selection_reasoning = obj.get("selection_reasoning", "")
            # Possible revision
            if "revised_tasks" in obj and isinstance(obj["revised_tasks"], list):
                selected_tasks = obj["revised_tasks"]
            # DAG
            if validate_reasoning_graph(obj.get("dependency_graph")):
                dependency_graph = obj["dependency_graph"]
            elif validate_reasoning_graph(obj.get("revised_graph")):
                dependency_graph = obj["revised_graph"]
            elif validate_reasoning_graph(obj):
                dependency_graph = obj
            if selected_tasks:
                break
        # Actual injection into oai_messages happens in generate_oai_reply (deferred).
        if not selected_tasks:
            self._log("Could not extract selected_tasks from conversation.")
            return {
                "partial": True,
                "failure_reason": "Could not extract selected_tasks from conversation.",
                "selected_tasks": [],
                "scene_design": None,
                "milestones": None,
                "full_conversation_log": full_conversation_log,
                "tool_call_log": tool_call_log or [],
                "visual_message_log": visual_message_log or [],
                "debate_log": debate_log,
                "agent_states": {
                    "conversation_turns": len(messages),
                    "sample_idx": sample_idx,
                },
            }

        # ── Scene design ─────────────────────────────────────────────────
        scene_design = None
        sandbox_findings_log: List[str] = []  # collect all sandbox_findings from SceneDesigner

        def _try_extract_scene(texts_iter):
            """Scan an iterable of text strings (most-recent-first) for a valid scene_design."""
            nonlocal sandbox_findings_log
            for text in texts_iter:
                obj = extract_json_object(text)
                if not obj:
                    # Still collect sandbox_findings from plain-text reports
                    if "sandbox_findings" in text or "preview_scene_in_sandbox" in text:
                        sandbox_findings_log.append(text[:800])
                    continue
                # Collect sandbox_findings from revision responses
                if isinstance(obj, dict):
                    findings = obj.get("sandbox_findings", "")
                    if findings:
                        sandbox_findings_log.append(str(findings)[:800])
                    proposal = obj.get("proposal_for_team", "")
                    if proposal:
                        sandbox_findings_log.append(f"[Proposal for team] {proposal}"[:800])
                # Look for revised_scene wrapper
                if "revised_scene" in obj and validate_scene_design(obj["revised_scene"]):
                    result = obj["revised_scene"]
                    if not result.get("screenshot_observations") and sandbox_findings_log:
                        result["screenshot_observations"] = sandbox_findings_log[0]
                    return result
                if validate_scene_design(obj):
                    return obj
            return None

        # Primary: look in SceneDesignerAgent messages (most authoritative source)
        scene_design = _try_extract_scene(reversed(by_agent.get("SceneDesignerAgent", [])))

        # Fallback: scan ALL agents' messages in reverse-chronological order
        # (the last valid scene_design in the conversation is the most refined version)
        if scene_design is None:
            self._log(
                "scene_design not found in SceneDesignerAgent messages — "
                "scanning all agents for a fallback scene_design..."
            )
            # Reconstruct chronological order from raw messages, then reverse
            all_agent_texts = []
            for msg in messages:
                role = msg.get("role", "")
                if role in ("tool", "function"):
                    continue
                if role == "assistant" and msg.get("tool_calls"):
                    continue
                content = msg.get("content") or ""
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
                if content.strip():
                    all_agent_texts.append(content)
            scene_design = _try_extract_scene(reversed(all_agent_texts))

        if scene_design is None:
            self._log("Could not extract valid scene_design from conversation.")
            return {
                "partial": True,
                "failure_reason": "Could not extract valid scene_design from conversation.",
                "selected_tasks": selected_tasks,
                "selection_reasoning": selection_reasoning,
                "reasoning_graph": dependency_graph,
                "scene_design": None,
                "milestones": None,
                "full_conversation_log": full_conversation_log,
                "tool_call_log": tool_call_log or [],
                "visual_message_log": visual_message_log or [],
                "debate_log": debate_log,
                "sandbox_findings_log": sandbox_findings_log,
                "agent_states": {
                    "conversation_turns": len(messages),
                    "visual_messages": len(visual_message_log or []),
                    "sample_idx": sample_idx,
                    "sandbox_preview_calls": sum(
                        1 for r in (tool_call_log or [])
                        if r.get("tool") == "preview_scene_in_sandbox"
                    ),
                },
            }

        ordered_tasks = scene_design.get("atomic_tasks_ordered", selected_tasks)

        # ── Milestones ───────────────────────────────────────────────────
        milestones = None
        milestone_texts = by_agent.get("MilestoneAgent", [])
        self._log(f"MilestoneAgent produced {len(milestone_texts)} messages.")
        for i, text in enumerate(reversed(milestone_texts)):
            obj = extract_json_object(text)
            if not obj:
                self._log(f"  Milestone msg[{i}]: no JSON found.")
                continue
            # Revision wrapper
            if "revised_milestones" in obj:
                cand = obj["revised_milestones"]
                ok = validate_milestones(cand, ordered_tasks)
                self._log(f"  Milestone msg[{i}]: revised_milestones present, valid={ok}")
                if ok:
                    milestones = cand
                    break
                else:
                    # Log why validation failed (task count mismatch etc.)
                    m_list = cand.get("milestones", []) if isinstance(cand, dict) else []
                    self._log(
                        f"    revised_milestones invalid: "
                        f"got {len(m_list)} milestones, expected {len(ordered_tasks)} tasks. "
                        f"tasks={ordered_tasks}"
                    )
            ok = validate_milestones(obj, ordered_tasks)
            self._log(f"  Milestone msg[{i}]: direct validate={ok}")
            if ok:
                milestones = obj
                break
            else:
                m_list = obj.get("milestones", []) if isinstance(obj, dict) else []
                self._log(
                    f"    direct invalid: got {len(m_list)} milestones, "
                    f"expected {len(ordered_tasks)} tasks. "
                    f"keys={list(obj.keys()) if isinstance(obj, dict) else 'not-a-dict'}"
                )

        if milestones is None:
            failure_reason = (
                "Could not extract valid milestones from conversation. "
                f"ordered_tasks={ordered_tasks}"
            )
            self._log(failure_reason)
            # ── Fallback: save conversation history for debugging ─────────
            save_fallback_response(
                str(FALLBACK_DIR),
                sample_idx,
                "milestones",
                json.dumps(
                    [{"from": m.get("from"), "content": m.get("content", "")[:800]}
                     for m in full_conversation_log],
                    ensure_ascii=False,
                ),
                attempt=1,
                validation_error=f"ordered_tasks={ordered_tasks}",
            )
            return {
                "partial": True,
                "failure_reason": failure_reason,
                "selected_tasks": selected_tasks,
                "selection_reasoning": selection_reasoning,
                "scene_design": scene_design,
                "reasoning_graph": dependency_graph,
                "milestones": None,
                "debate_log": debate_log,
                "full_conversation_log": full_conversation_log,
                "tool_call_log": tool_call_log or [],
                "visual_message_log": visual_message_log or [],
                "sandbox_findings_log": sandbox_findings_log,
                "agent_states": {
                    "conversation_turns": len(messages),
                    "visual_messages": len(visual_message_log or []),
                    "sample_idx": sample_idx,
                    "sandbox_preview_calls": sum(
                        1 for r in (tool_call_log or [])
                        if r.get("tool") == "preview_scene_in_sandbox"
                    ),
                },
            }

        self._log(
            f"Extraction OK — tasks={selected_tasks}, "
            f"scene={scene_design.get('scene_name')}, "
            f"milestones={len(milestones.get('milestones', []))}"
        )

        return {
            "selected_tasks": selected_tasks,
            "selection_reasoning": selection_reasoning,
            "scene_design": scene_design,
            "reasoning_graph": dependency_graph,
            "milestones": milestones,
            "debate_log": debate_log,
            "full_conversation_log": full_conversation_log,
            "tool_call_log": tool_call_log or [],
            "visual_message_log": visual_message_log or [],
            "sandbox_findings_log": sandbox_findings_log,
            "agent_states": {
                "conversation_turns": len(messages),
                "visual_messages": len(visual_message_log or []),
                "sample_idx": sample_idx,
                "sandbox_preview_calls": sum(
                    1 for r in (tool_call_log or [])
                    if r.get("tool") == "preview_scene_in_sandbox"
                ),
            },
        }

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[Orchestrator] {msg}")
