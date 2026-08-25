from __future__ import annotations

import json
import os
import sys
import time
import signal
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

_ROOT_DIR = Path(__file__).resolve().parent
_BENCHMARK_GEN = _ROOT_DIR / "benchmark_gen"

if str(_ROOT_DIR) not in sys.path:
    sys.path.append(str(_ROOT_DIR))

from env.minerl_sandbox import MineRLSandboxEnv
from env.render import RenderWrapper
from mc_agent import (
    DefaultAgent, MinerRLActionSpace, OpenAIProvider, VLLMProvider, CodexProvider, DefaultContextBuilder,
    HypothesisAgent, HypothesisContextBuilder,
)
from mc_agent.context import PROMPT_LAYOUTS, RESPONSE_STYLES, default_reply_schema

AGENT_MODES = ("default", "hypothesis", "prolong", "worldmodel")

FRAME_BUFFER_SIZE = 20
# --prompt-layout append-only: the frame buffer grows by one frame per step and is rebased
# (oldest FRAME_WINDOW_REBASE frames dropped) only when it reaches FRAME_BUFFER_SIZE +
# FRAME_WINDOW_REBASE, so the window is 20-29 frames and the request prefix is unchanged on
# 9 steps out of 10. The other layouts keep the sliding 20-frame window.
FRAME_WINDOW_REBASE = 10
MAX_STEPS = 300
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
AGENT_API_BASE = os.getenv("AGENT_API_BASE", "")
if not AGENT_API_KEY:
    raise ValueError("AGENT_API_KEY not found. Please set it in .env or environment")
if not AGENT_API_BASE:
    raise ValueError("AGENT_API_BASE not found. Please set it in .env or environment")

app = typer.Typer(help="Evaluate benchmark scenarios")


class MineRLBenchmarkEnv(MineRLSandboxEnv):
    """MineRLSandboxEnv that builds the scene from a benchmark metadata.json."""

    def __init__(self, metadata_path: str, use_friday: bool = False,
                 obs_size: list[int] | None = None):
        meta_path = Path(metadata_path)
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found: {meta_path}")
        with open(meta_path, "r", encoding="utf-8") as f:
            self._metadata = json.load(f)
        # The screenshot resolution the server renders observations at. 128x128 is the
        # protocol every existing arm ran under; the worldmodel arm asks for the full
        # 640x360 render because its memory mechanism files frames away to be re-read.
        self._obs_size = list(obs_size) if obs_size else [128, 128]
        self._parse_metadata()
        super().__init__(env_id=self._scene_name, use_friday=use_friday)

    def _parse_metadata(self) -> None:
        self._commands_list = self._metadata.get("commands", [])
        self._task_text = self._metadata.get("task_text", "")
        self._scene_name = self._metadata.get("scene_name", "benchmark_scene")
        logger.info(f"[BenchmarkEnv] scene={self._scene_name} commands={len(self._commands_list)}")
        logger.info(f"[BenchmarkEnv] task: {self._task_text[:100]}")

    def _init_remote_env(self) -> None:
        logger.info(f"Sending /create_env with {len(self._commands_list)} commands "
                    f"(obs_size={self._obs_size})...")
        response = self.create_env(
            env='MinecraftSim',
            obs_size=self._obs_size,
            render_size=[640, 360],
            seed=0,
            record=False,
            record_path='./output/',
            yaml_config=None,
            commands=self._commands_list,
            task_text=self._task_text,
            call_timeout=120,
        )
        if response.get("status") != 0:
            raise RuntimeError(f"create_env failed: {response.get('msg')}")
        self.task = response.get("task_text", "") or self._task_text
        logger.success(f"Benchmark environment created: {self.task[:80]}")
        time.sleep(10)


try:
    if str(_BENCHMARK_GEN) not in sys.path:
        sys.path.append(str(_BENCHMARK_GEN))
    from benchmark_gen.milestone_checker import MilestoneChecker
    _HAS_MILESTONE_CHECKER = True
except ImportError:
    _HAS_MILESTONE_CHECKER = False

    class MilestoneChecker:
        def __init__(self, milestones): self._milestones = milestones
        def reset(self, info): pass
        def check(self, info): return []
        def summary(self): return "no milestone checker"
        def augment_action_with_queries(self, action, info): return action
        def num_completed(self): return 0
        def num_trackable(self): return 0
        def all_done(self): return False

        @classmethod
        def from_metadata(cls, path): return cls([])


_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("\n[INTERRUPT] Shutdown requested, finishing current step and closing sandbox...")


def _camera_state_hint(info: dict) -> str:
    """Ground-truth camera pitch from the environment, so the agent doesn't
    have to rely solely on visually noticing it has pitched to an extreme
    (observed failure mode: repeating the same camera move several steps in
    a row drives pitch into the +-90 clamp, after which every frame is blank
    sky/ground, which some models keep misreading as unrelated scenery
    instead of recognizing they're stuck)."""
    pos = info.get("player_pos") or {}
    pitch = pos.get("pitch")
    if pitch is None:
        return ""
    if pitch >= 80:
        note = "you are looking almost straight DOWN at the ground"
    elif pitch <= -80:
        note = "you are looking almost straight UP at the sky"
    elif pitch >= 40:
        note = "you are looking steeply downward"
    elif pitch <= -40:
        note = "you are looking steeply upward"
    else:
        note = "roughly level"
    return f"pitch={pitch:.0f} degrees ({note})."


def _movement_state_hint(
    info: dict,
    spawn_xz: tuple[float, float] | None,
    pos_history: "deque[tuple[float, float]]",
) -> str:
    """Ground-truth horizontal displacement from the environment, so the
    agent doesn't have to infer from subtle frame-to-frame visual similarity
    whether its last action (or last several actions) actually covered new
    ground.

    Observed failure modes this targets (see MineExplorer hypothesis-agent
    debugging session): (a) the model issues 'left'/'right' (these STRAFE
    sideways, they do not change facing) while narrating "turning to scan a
    new direction", never actually rotating; (b) the model pairs a large
    camera yaw turn with forward movement on every single tick, which -
    exactly as this file's own system prompt warns - walks in a closed loop
    while every individual frame still looks like "new" forest; (c) the
    agent gets physically wedged against terrain (a 1-block ledge, a wall)
    and its position freezes for tens of steps while it keeps narrating
    "N consecutive scans, environment unchanged" as if still moving. In all
    three cases the model's own account of its progress silently diverges
    from the server-reported player_pos, and nothing before this hint ever
    surfaced that divergence back into the prompt. Before this hint existed,
    the model had no numeric access to its own coordinates at all (only
    pixels + camera pitch + milestone hint), so it also had no way to reason
    about real distance/direction independent of its own narrative.
    """
    pos = info.get("player_pos") or {}
    x, z = pos.get("x"), pos.get("z")
    if x is None or z is None:
        return ""

    had_history = len(pos_history) > 0
    tick_delta = 0.0
    if had_history:
        px, pz = pos_history[-1]
        tick_delta = ((x - px) ** 2 + (z - pz) ** 2) ** 0.5

    pos_history.append((x, z))
    if not had_history:
        # First call (spawn): nothing has moved yet because no action has
        # been taken, so there's nothing meaningful to report.
        return ""

    parts = []

    if tick_delta < 0.05:
        parts.append(
            f"You have NOT moved since your last action (still at x={x:.1f}, z={z:.1f}). "
            f"Your last action did not change your position at all - you are likely "
            f"blocked by terrain (a wall, fence, one-block ledge), or you used "
            f"'left'/'right' (these STRAFE sideways - they do NOT change your facing "
            f"direction; only 'camera' turns you) without any 'forward'/'camera' change "
            f"that would actually move you. Try 'jump' combined with 'forward', try "
            f"'back' to un-wedge yourself, or issue a 'camera' yaw turn before your next "
            f"forward move - do not just repeat the same action again."
        )
    else:
        parts.append(f"moved {tick_delta:.2f} blocks since last step (now x={x:.1f}, z={z:.1f}).")

    if len(pos_history) == pos_history.maxlen:
        ox, oz = pos_history[0]
        window_net = ((x - ox) ** 2 + (z - oz) ** 2) ** 0.5
        if window_net < 1.0:
            parts.append(
                f"WARNING: over your last {pos_history.maxlen} steps you have net-moved "
                f"only {window_net:.2f} blocks (from x={ox:.1f},z={oz:.1f} to x={x:.1f},"
                f"z={z:.1f}) even though you took action every step. Even if each frame "
                f"looked slightly different, you are circling back on yourself, not "
                f"covering new ground - this is what happens when you turn and move in "
                f"the same tick, repeatedly. Stop and do ONE full turn (camera only, "
                f"forward=0), then move in a straight line (forward=1, camera=[0,0]) for "
                f"several steps before turning again."
            )

    if spawn_xz is not None:
        sx, sz = spawn_xz
        spawn_dist = ((x - sx) ** 2 + (z - sz) ** 2) ** 0.5
        parts.append(
            f"You are {spawn_dist:.1f} blocks from your spawn point (spawn was "
            f"x={sx:.1f}, z={sz:.1f}). Use this real number, not a step count, to judge "
            f"how much ground you've actually covered - a high step count with a small "
            f"spawn distance means you have been going in circles, not exploring."
        )

    return " ".join(parts)


def _run_benchmark(
    *,
    metadata_path: str,
    model: str,
    output_dir: Path,
    loading_command_steps: int,
    max_steps: int,
    use_vllm: bool = False,
    vllm_url: str = "http://localhost:8000/v1",
    use_codex: bool = False,
    codex_effort: str = "xhigh",
    codex_base_url: str = "",
    frame_size: int = FRAME_BUFFER_SIZE,
    use_friday: bool = False,
    temperature: float = 0.7,
    use_milestone_hint: bool = True,
    agent_mode: str = "default",
    prolong_log_window: Optional[int] = None,
    prolong_stateless: bool = False,
    prompt_layout: str = "legacy",
    response_style: str = "full",
    codex_output_schema: bool = False,
) -> Dict[str, Any]:
    """Run one benchmark scenario and save results."""
    global _shutdown_requested

    # Argument checks first: past this point a sandbox session exists, and a combination
    # rejected after that leaks it on the sandbox server.
    if agent_mode not in AGENT_MODES:
        raise ValueError(f"agent_mode must be one of {AGENT_MODES}, got {agent_mode!r}")
    if prompt_layout not in PROMPT_LAYOUTS:
        raise ValueError(f"prompt_layout must be one of {PROMPT_LAYOUTS}, got {prompt_layout!r}")
    if agent_mode in ("prolong", "worldmodel") and prompt_layout != "legacy":
        # PRO-LONG builds its own prompt (prolong_mc); the layouts describe the default and
        # hypothesis agents' request only.
        raise ValueError(f"--prompt-layout applies to --agent-mode default/hypothesis, not {agent_mode}")
    if response_style not in RESPONSE_STYLES:
        raise ValueError(f"response_style must be one of {RESPONSE_STYLES}, got {response_style!r}")
    if agent_mode in ("prolong", "worldmodel") and response_style != "full":
        raise ValueError(f"--response-style applies to --agent-mode default/hypothesis, not {agent_mode}")
    if codex_output_schema and not use_codex:
        # It is a codex CLI flag; the direct channel already gets valid JSON every time.
        raise ValueError("--codex-output-schema applies to --use-codex runs only")
    if codex_output_schema and agent_mode in ("prolong", "worldmodel"):
        # PRO-LONG's reply is its own contract (prolong_mc writes the analyzer's format and
        # parses it), and it logged zero parse failures on the c4h campaign. Constraining it
        # would change the method's output surface for no measured gain.
        raise ValueError(f"--codex-output-schema applies to --agent-mode default/hypothesis, not {agent_mode}")

    meta_path = Path(metadata_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)

    scene_id = meta_path.parent.parent.name
    task_desc = metadata_dict.get("task_text", f"Complete the Minecraft task for {scene_id}.")
    safe_model = model.replace("/", "_")

    if _HAS_MILESTONE_CHECKER:
        try:
            checker = MilestoneChecker.from_metadata(metadata_path)
            logger.info(f"Loaded {len(checker._milestones)} milestones")
        except Exception as e:
            logger.warning(f"Could not load milestones: {e}")
            checker = MilestoneChecker([])
    else:
        checker = MilestoneChecker([])

    # The worldmodel arm's memory files frames away to be re-read, so it asks the server
    # for the full 640x360 render as its observation; every other arm keeps the 128x128
    # protocol its finished runs were produced under. WM_OBS_SIZE=WxH overrides.
    _wm_obs: Optional[list] = None
    if agent_mode == "worldmodel":
        try:
            _wm_obs = [int(v) for v in os.environ.get("WM_OBS_SIZE", "640x360").split("x")]
            assert len(_wm_obs) == 2
        except (ValueError, AssertionError):
            logger.warning(f"bad WM_OBS_SIZE={os.environ.get('WM_OBS_SIZE')!r}; using 640x360")
            _wm_obs = [640, 360]
    _base_env = MineRLBenchmarkEnv(metadata_path=metadata_path, use_friday=use_friday,
                                   obs_size=_wm_obs)
    if use_codex:
        # Every call's prompt and event stream lands under the scene's own output
        # directory, so a Codex run is inspectable the same way episode.mp4 is.
        if codex_output_schema:
            # The reply contract of the agent that is about to run, so the constrained
            # final message is exactly what its prompt asks for.
            from mc_agent.hypothesis_agent import hypothesis_reply_schema
            _schema = (hypothesis_reply_schema(response_style) if agent_mode == "hypothesis"
                       else default_reply_schema(response_style))
        else:
            _schema = None
        _provider = CodexProvider(
            model_name=model,
            reasoning_effort=codex_effort,
            transcript_dir=str(output_dir / "codex_calls"),
            base_url=codex_base_url or None,
            output_schema=_schema,
        )
    elif use_vllm:
        _provider = VLLMProvider(model_name=model, base_url=vllm_url, temperature=temperature)
    else:
        _provider = OpenAIProvider(AGENT_API_KEY, AGENT_API_BASE, model, temperature=temperature)
    if agent_mode == "prolong":
        # Same env, same loop, same scorer as the baseline; only the memory
        # mechanism differs. Codex is the model channel, so the provider above is
        # constructed but unused.
        from mc_agent.prolong_agent import ProlongAgent
        agent = ProlongAgent(
            action_space=MinerRLActionSpace(),
            provider=_provider,
            model=model,
            workspace=output_dir / "prolong_workspace",
            transcript_dir=output_dir / "codex_turns",
            reasoning_effort=codex_effort,
            base_url=codex_base_url or None,
            codex_home=os.environ.get("CODEX_HOME"),
            # The baseline only renders its "Environment-verified task status" section
            # under this protocol; PRO-LONG documents its [MILESTONE] marker on the
            # same condition, so neither arm is told about a signal the other lacks.
            milestone_hint=use_milestone_hint,
            # PRO-LONG's own ablations, off unless asked for. Both are enforced in the
            # directory the analyzer works in rather than described to it, so these are
            # arm C, not a differently worded arm B.
            log_window=prolong_log_window,
            stateless=prolong_stateless,
        )
    elif agent_mode == "worldmodel":
        # Same env, same loop, same scorer as the baseline; the memory architecture is
        # the dual-turn act/induction loop ported from MCU-AgentBeats. Codex is the
        # model channel (the mechanism is a workspace the model greps and writes).
        from mc_agent.worldmodel_agent import WorldModelAgent
        agent = WorldModelAgent(
            action_space=MinerRLActionSpace(),
            provider=_provider,
            model=model,
            workspace=output_dir / "worldmodel_workspace",
            # The scene's milestone spec, for the checklist the prompt renders; the
            # per-step verification bits arrive via _agent_extra["milestones"].
            milestones_spec=list(getattr(checker, "_milestones", [])),
            transcript_dir=output_dir / "codex_turns",
            reasoning_effort=codex_effort,
            base_url=codex_base_url or None,
            codex_home=os.environ.get("CODEX_HOME"),
            induction_every=int(os.environ.get("WM_INDUCTION_EVERY", "60")),
            max_steps=max_steps,
        )
    elif agent_mode == "hypothesis":
        agent = HypothesisAgent(
            action_space=MinerRLActionSpace(),
            provider=_provider,
            context_builder_class=HypothesisContextBuilder,
            model=model,
            prompt_layout=prompt_layout,
            response_style=response_style,
        )
    else:
        agent = DefaultAgent(
            action_space=MinerRLActionSpace(),
            provider=_provider,
            context_builder_class=DefaultContextBuilder,
            model=model,
            prompt_layout=prompt_layout,
            response_style=response_style,
        )

    run_id = f"{safe_model}_{scene_id}"

    output_dir.mkdir(parents=True, exist_ok=True)
    result_save_path = output_dir / "result.json"

    env = RenderWrapper(_base_env, save_messages=True, save_path=str(output_dir))

    if prompt_layout == "append-only":
        frame_buffer: deque = deque()  # rebased by _push_frame, not sliding
    else:
        frame_buffer = deque(maxlen=frame_size)

    def _push_frame(pov) -> None:
        frame_buffer.append(pov)
        if prompt_layout == "append-only":
            while len(frame_buffer) >= frame_size + FRAME_WINDOW_REBASE:
                for _ in range(FRAME_WINDOW_REBASE):
                    frame_buffer.popleft()

    thought_history: List[str] = []
    action_history: List[Dict] = []
    _frame_completed: Dict[str, Optional[int]] = {}
    _presatisfied_ids: set = set()
    _frame_offset: int = 0
    _all_done_logged: bool = False
    long_term_memory: str = ""
    termination_reason: str = "max_steps"
    milestone_hint: str = (
        "The environment has not verified the task as complete yet." if use_milestone_hint else ""
    )
    _spawn_xz: Optional[tuple] = None
    _pos_history: "deque[tuple[float, float]]" = deque(maxlen=8)

    original_sigint_handler = signal.signal(signal.SIGINT, _signal_handler)

    try:
        has_loading = loading_command_steps > 0
        obs, info = env.reset(save_frame=not has_loading)
        _push_frame(obs["pov"])

        for step in range(loading_command_steps):
            if _shutdown_requested:
                logger.info(f"[{run_id}] Shutdown requested during loading, exiting...")
                break
            logger.info(f"[{run_id}] Loading command step {step + 1}/{loading_command_steps}")
            _, noop_action = agent.get_default_action(is_call_failed=False)
            obs, reward, terminated, truncated, info = env.step(
                noop_action, save_frame=(step + 1 == loading_command_steps)
            )

        logger.info(f"[{run_id}] Minecraft commands loaded.")

        if not info.get("player_pos"):
            _, noop_action = agent.get_default_action(is_call_failed=False)
            obs, reward, terminated, truncated, info = env.step(noop_action, save_frame=True)
            _push_frame(obs["pov"])

        logger.debug(
            f"[{run_id}] Pre-reset info keys={list(info.keys())} "
            f"player_pos={info.get('player_pos')!r}"
        )
        if not info.get("player_pos"):
            logger.warning(
                f"[{run_id}] Server info has no usable 'player_pos' key "
                f"(info keys={list(info.keys())}); spawn will default to (0,0,0)."
            )
        else:
            _spawn_pos = info["player_pos"]
            _spawn_xz = (_spawn_pos.get("x"), _spawn_pos.get("z"))

        checker.reset(info)
        agent.load_system_prompt(task_desc)

        # Record the frame count right after the loading phase so that
        # frame_completed values are reported relative to the agent's first
        # real action step (frame 1 = first agent step).
        _frame_offset: int = env.frame_count

        # Perform a baseline check immediately after reset to identify any
        # milestones whose rules are already satisfied at spawn (before the
        # agent takes any action).  These are treated as "pre-satisfied" and
        # will NOT be counted as completed — they are excluded via a blocklist
        # so that _frame_completed is only set when the agent genuinely
        # triggers the condition during gameplay.
        _baseline_check = checker.check(info)
        _presatisfied_ids: set = set()
        for _bms in _baseline_check:
            if _bms.get("completed") and not _bms.get("no_milestone"):
                _presatisfied_ids.add(_bms["milestone_id"])
                logger.warning(
                    f"[{run_id}] Milestone '{_bms['milestone_id']}' already satisfied at spawn "
                    f"(will NOT be counted as completed by the agent)."
                )
        # Reset the checker state so those pre-satisfied flags don't persist
        checker.reset(info)

        # Milestones that actually count toward completion (excludes
        # decorative/no-rule milestones). Computed once here so both the
        # per-step ground-truth hint and the final summary use the same set.
        trackable_mids = {
            ms.get("milestone_id", "")
            for ms in checker._milestones
            if len(ms.get("rules", [])) > 0
        }

        step_error: Optional[str] = None
        step = -1
        # The checker's latest verdicts, handed to the worldmodel agent each step as its
        # ledger's only verification source. Empty until the first post-step check runs
        # (nothing is verified at step 0 by construction).
        milestone_status: List[dict] = []

        for step in range(max_steps):
            if _shutdown_requested:
                logger.info(f"[{run_id}] Shutdown requested, exiting after step {step}...")
                step_error = "interrupted_by_user"
                termination_reason = "interrupted"
                break

            logger.info(f"[{run_id}] --- Step {step + 1}/{max_steps} ---")

            try:
                # ProlongAgent writes its own [STATE] lines, so it needs the raw
                # info the hints are derived from; the other agents do not accept it.
                # WorldModelAgent additionally receives the checker's status list --
                # its ledger never re-scores the scene itself.
                if agent_mode == "prolong":
                    _agent_extra = {"info": info}
                elif agent_mode == "worldmodel":
                    # presatisfied rides along because the checker's completed bit
                    # keeps latching True for spawn-satisfied milestones the final
                    # score will never credit; the agent's ledger must not bank them.
                    _agent_extra = {"info": info, "milestones": milestone_status,
                                    "presatisfied": _presatisfied_ids}
                else:
                    _agent_extra = {}
                thought, action, memory_update = agent.get_action(
                    list(frame_buffer), list(thought_history), list(action_history), step + 1,
                    long_term_memory=long_term_memory,
                    milestone_hint=milestone_hint,
                    camera_hint=_camera_state_hint(info),
                    movement_hint=_movement_state_hint(info, _spawn_xz, _pos_history),
                    **_agent_extra,
                )
            except Exception as agent_err:
                logger.error(f"[{run_id}] Agent call failed: {agent_err}. Retrying in 10s...")
                time.sleep(10)
                continue

            if action is None:
                logger.warning(f"[{run_id}] Agent failed to provide action. Retrying in 10s...")
                time.sleep(10)
                continue

            if memory_update and memory_update.strip():
                long_term_memory = memory_update.strip()

            thought_history.append(thought)
            action_history.append(action)

            try:
                augmented_action = checker.augment_action_with_queries(action, info)
                obs, reward, terminated, truncated, info = env.step(augmented_action)
            except Exception as env_err:
                logger.error(f"[{run_id}] env.step failed: {env_err}. Retrying in 10s...")
                time.sleep(10)
                continue

            _push_frame(obs["pov"])

            milestone_status = checker.check(info)
            logger.debug(
                f"[{run_id}] step={step + 1} player_pos={info.get('player_pos')!r} "
                f"rules_passed={[(ms['milestone_id'], ms.get('rules_passed')) for ms in milestone_status]}"
            )
            for ms in milestone_status:
                mid = ms["milestone_id"]
                # Skip milestones that were already satisfied at spawn
                if mid in _presatisfied_ids:
                    continue
                if ms.get("completed") and mid not in _frame_completed:
                    # frame_completed is 1-indexed from the first agent step
                    _frame_completed[mid] = env.frame_count - _frame_offset
                    logger.success(f"[{run_id}] Milestone '{mid}' completed at step {step + 1} (frame {_frame_completed[mid]})")

            _remaining_mids = [
                mid for mid in trackable_mids
                if mid not in _presatisfied_ids and mid not in _frame_completed
            ]

            # The remote sandbox does not reliably end the episode when the
            # agent presses ESC (observed: agent can emit ESC=1 for hundreds
            # of consecutive steps with server-reported `done` staying False).
            # Enforce the documented contract ("set ESC=1 to end the episode",
            # see mc_agent/context.py) on the client side as a safety net.
            agent_requested_stop = bool(action.get("ESC"))

            # Guard against a common failure mode: the agent visually
            # hallucinates success and presses ESC before the milestone
            # checker has actually verified the task, ending the episode
            # early with steps still available. If we already told the
            # agent (via milestone_hint) that completion is unverified,
            # don't honor a premature ESC — ignore it and keep the episode
            # running so the agent gets a chance to actually finish the
            # task. Only applies when the ground-truth hint is enabled.
            if agent_requested_stop and use_milestone_hint and _remaining_mids:
                logger.warning(
                    f"[{run_id}] step={step + 1} Agent requested ESC but milestone(s) "
                    f"{_remaining_mids} are not yet verified complete — ignoring premature "
                    f"stop, episode continues."
                )
                agent_requested_stop = False
                if hasattr(agent, "on_esc_rejected"):
                    try:
                        agent.on_esc_rejected(step=step + 1)
                    except Exception as hook_err:
                        logger.warning(f"[{run_id}] agent.on_esc_rejected() raised: {hook_err}")

            done = terminated or truncated or agent_requested_stop

            if done:
                if agent_requested_stop and not (terminated or truncated):
                    termination_reason = "agent_esc"
                elif terminated:
                    termination_reason = "env_terminated"
                elif truncated:
                    termination_reason = "env_truncated"

            # Ground-truth completion signal shown to the agent next step, so
            # it doesn't have to rely solely on visually judging whether its
            # last action worked (a common failure mode: hallucinating
            # success and pressing ESC before the milestone is actually met).
            # Disabled when use_milestone_hint=False to match the paper's
            # protocol, where the agent gets no such signal.
            if use_milestone_hint:
                if _remaining_mids:
                    milestone_hint = "The environment has NOT verified the task as complete yet. Do not end the episode (ESC) until it is."
                else:
                    milestone_hint = "The environment HAS verified the task as complete. You may now end the episode by setting ESC=1."

            if not _all_done_logged and checker.num_completed() > 0 and checker.all_done():
                _all_done_logged = True
                logger.success(f"[{run_id}] All milestones completed at step {step + 1}!")

            if (step + 1) % 10 == 0:
                env.save_video_checkpoint()

            if done:
                logger.success(f"[{run_id}] Episode finished ({termination_reason}).")
                break

    except KeyboardInterrupt:
        logger.warning(f"[{run_id}] KeyboardInterrupt received, shutting down...")
        step_error = "interrupted_by_user"
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)
        logger.info(f"[{run_id}] Closing sandbox environment...")
        try:
            env.close()
            logger.success(f"[{run_id}] Sandbox closed successfully")
        except Exception as close_err:
            logger.warning(f"[{run_id}] env.close() raised: {close_err}")

    if hasattr(agent, "save_state"):
        try:
            agent.save_state(output_dir)
        except Exception as save_err:
            logger.warning(f"[{run_id}] agent.save_state() raised: {save_err}")

    final_status = []
    for ms in checker._milestones:
        mid = ms.get("milestone_id", "")
        completed_frame = _frame_completed.get(mid)
        presatisfied = mid in _presatisfied_ids
        final_status.append({
            "milestone_id": mid,
            "task": ms.get("task", ""),
            # A milestone is only "completed" if the agent triggered it during
            # gameplay (frame_completed recorded) and it was not already
            # satisfied at spawn.
            "completed": completed_frame is not None and not presatisfied,
            "frame_completed": completed_frame if (completed_frame is not None and not presatisfied) else -1,
            # Extra diagnostic field so callers can see which milestones were
            # already satisfied before the agent started.
            "presatisfied_at_spawn": presatisfied,
        })

    # Compute milestones_completed / all_milestones_done using only the
    # corrected _frame_completed dict (excludes pre-satisfied milestones).
    corrected_completed = sum(
        1 for mid in trackable_mids
        if mid in _frame_completed and mid not in _presatisfied_ids
    )
    corrected_trackable = len(trackable_mids)
    corrected_all_done = (
        corrected_trackable > 0
        and corrected_completed == corrected_trackable
    )

    total_steps = step + 1 if step >= 0 else 0
    summary: Dict[str, Any] = {
        "run_id": run_id,
        "model": model,
        "scene_id": scene_id,
        "mode": "multi-agent",
        "metadata_path": str(meta_path),
        # Which protocol produced this number. Scores taken with and without the hint
        # are not comparable -- without it an arm can end its own episode on a
        # hallucinated success, and one model did so within three steps -- so the
        # result has to say which one it is rather than leaving it to a run slug.
        "agent_mode": agent_mode,
        # How the model was reached, recorded rather than inferred from the run slug.
        # The slug-based guess mislabelled codex-driven runs as plain-vLLM ones purely
        # because the word "codex" was absent from a name someone typed once.
        "provider": "codex" if use_codex else ("vllm" if use_vllm else "openai"),
        # Whether this run was sandboxed, recorded rather than assumed. It changes what
        # the agent *is* -- what it can read, what it can reach, which tools codex hands
        # the model -- and not merely where it runs, so a score taken with it must not be
        # pooled with one taken without.
        **({"codex_bin": os.environ.get("CODEX_BIN", "codex"),
            "codex_sandboxed": os.path.basename(
                os.environ.get("CODEX_BIN", "codex")) == "codex_sandbox.sh"}
           if use_codex else {}),
        "milestone_hint": use_milestone_hint,
        # How the request was laid out for the server (see PROMPT_LAYOUTS). Anything but
        # "legacy" changes what the model reads -- and, for append-only, the frame window --
        # so it is a different arm and must not be pooled with a legacy run.
        "prompt_layout": prompt_layout,
        # What the model was asked to write back (see RESPONSE_STYLES). "compact" changes
        # the instructions and what is re-emitted per step, so it too is a different arm.
        "response_style": response_style,
        # Whether the codex channel's final message was constrained to the agent's reply
        # schema (`codex exec --output-schema`). Changes what the model emits, so it is
        # part of the arm.
        **({"codex_output_schema": codex_output_schema} if use_codex else {}),
        "max_steps": max_steps,
        # Which PRO-LONG arm this is. Recorded only where it means something, and
        # recorded at all because an ablated run pooled with the headline prolong runs
        # would average an arm against the arm it exists to be compared with.
        **({"prolong_log_window": prolong_log_window,
            "prolong_stateless": prolong_stateless} if agent_mode == "prolong" else {}),
        "total_steps": total_steps,
        "termination_reason": termination_reason,
        "milestones_completed": corrected_completed,
        "milestones_trackable": corrected_trackable,
        "milestones_total": len(checker._milestones),
        "milestones_presatisfied": len(_presatisfied_ids),
        "all_milestones_done": corrected_all_done,
        "milestone_status": final_status,
    }
    if step_error:
        summary["error"] = step_error

    with open(result_save_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.success(f"[{run_id}] Result saved -> {result_save_path}")

    return summary


def _hop_folder_name(meta_path: str) -> str:
    """Derive the '<N>-hop' folder name from a scene's atomic task count."""
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)
    n_hops = len(metadata_dict.get("atomic_tasks_ordered", []))
    return f"{n_hops}-hop" if n_hops > 0 else "unknown-hop"


def _worker_eval(worker_args: dict) -> dict:
    import signal as _signal
    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)

    _root = Path(__file__).resolve().parent
    sys.path.append(str(_root))

    return _run_benchmark(
        metadata_path=worker_args["metadata_path"],
        model=worker_args["model"],
        output_dir=Path(worker_args["output_dir"]),
        loading_command_steps=worker_args["loading_command_steps"],
        max_steps=worker_args["max_steps"],
        use_vllm=worker_args.get("use_vllm", False),
        vllm_url=worker_args.get("vllm_url", "http://localhost:8000/v1"),
        use_codex=worker_args.get("use_codex", False),
        codex_effort=worker_args.get("codex_effort", "xhigh"),
        codex_base_url=worker_args.get("codex_base_url", ""),
        frame_size=worker_args.get("frame_size", FRAME_BUFFER_SIZE),
        use_friday=worker_args.get("use_friday", False),
        temperature=worker_args.get("temperature", 0.7),
        use_milestone_hint=worker_args.get("use_milestone_hint", True),
        agent_mode=worker_args.get("agent_mode", "default"),
        prolong_log_window=worker_args.get("prolong_log_window"),
        prolong_stateless=worker_args.get("prolong_stateless", False),
        prompt_layout=worker_args.get("prompt_layout", "legacy"),
        response_style=worker_args.get("response_style", "full"),
        codex_output_schema=worker_args.get("codex_output_schema", False),
    )


@app.command(name="run")
def eval_benchmark(
    model: str = typer.Option(..., "--model", "-m", help="LLM model name"),
    benchmark_dir: str = typer.Option("benchmark_shuffled", "--benchmark-dir", "-b",
                                      help="Path to benchmark directory"),
    output_dir: str = typer.Option("outputs", "--output-dir", "-o",
                                   help="Output directory"),
    loading_command_steps: int = typer.Option(20, "--loading-command-steps",
                                              help="No-op steps after reset"),
    max_steps: int = typer.Option(MAX_STEPS, "--max-steps",
                                  help="Maximum agent steps per episode"),
    resume: bool = typer.Option(False, "--resume",
                                help="Resume evaluation (skip completed)"),
    use_vllm: bool = typer.Option(False, "--use-vllm",
                                  help="Use local vLLM server"),
    vllm_url: str = typer.Option("http://localhost:8000/v1", "--vllm-url",
                                 help="vLLM server URL"),
    use_codex: bool = typer.Option(False, "--use-codex",
                                   help="Drive the model through the Codex CLI (subscription auth, no API key)"),
    codex_effort: str = typer.Option("xhigh", "--codex-effort",
                                     help="Reasoning effort for --use-codex"),
    codex_base_url: str = typer.Option("", "--codex-base-url",
                                       help="Point --use-codex at a local OpenAI-compatible server instead of the account's hosted models"),
    num_workers: int = typer.Option(1, "--num-workers", "-n",
                                    help="Number of parallel workers"),
    limit: Optional[int] = typer.Option(None, "--limit",
                                        help="Limit number of scenarios to evaluate"),
    use_friday: bool = typer.Option(False, "--use-friday",
                                    help="Use Friday platform sandbox instead of local Docker"),
    temperature: float = typer.Option(0.7, "--temperature", "-t",
                                      help="LLM sampling temperature"),
    shard_index: int = typer.Option(0, "--shard-index",
                                    help="This job's shard index (0-based) for splitting a "
                                         "benchmark-dir across a SLURM array; e.g. pass "
                                         "$SLURM_ARRAY_TASK_ID. Scenes are assigned round-robin "
                                         "(shard_index::shard_count), so every shard's output "
                                         "can share the same --output-dir without collisions."),
    shard_count: int = typer.Option(1, "--shard-count",
                                    help="Total number of shards (array size), e.g. "
                                         "$SLURM_ARRAY_TASK_COUNT. Must be >= 1."),
    milestone_hint: bool = typer.Option(True, "--milestone-hint/--no-milestone-hint",
                                        help="Feed the agent a per-step ground-truth signal for "
                                             "whether the environment has verified the task "
                                             "complete. The paper's protocol has no such signal "
                                             "(--no-milestone-hint matches it)."),
    agent_mode: str = typer.Option("default", "--agent-mode",
                                   help="Agent implementation to use: 'default' (the current "
                                        "LLM-only agent, unchanged) or 'hypothesis' (adds an "
                                        "explicit hypothesis DAG + short-horizon plan on top; "
                                        "see mc_agent/hypothesis_agent.py). Defaults to 'default' "
                                        "so existing invocations behave exactly as before."),
    prolong_log_window: Optional[int] = typer.Option(None, "--prolong-log-window",
                                                     help="PRO-LONG's log-window ablation "
                                                          "(--agent-mode prolong only): 0 keeps the "
                                                          "initial state plus the latest action "
                                                          "section, N keeps the last N, -1 is the "
                                                          "paper's No-Log control (no logs.txt; the "
                                                          "current state and frame travel in the "
                                                          "prompt). Enforced -- the analyzer's "
                                                          "directory holds the truncated log and "
                                                          "the frames it names, and nothing else "
                                                          "of the history."),
    prolong_stateless: bool = typer.Option(False, "--prolong-stateless",
                                           help="PRO-LONG's stateless ablation (--agent-mode prolong "
                                                "only): everything the analyzer writes is deleted "
                                                "each turn, leaving logs.txt and AGENTS.md. The "
                                                "Codex conversation itself stays alive, which is "
                                                "upstream's behaviour."),
    prompt_layout: str = typer.Option("legacy", "--prompt-layout",
                                      help="How the default/hypothesis agents lay out each request "
                                           "for the server's prefix cache: 'legacy' (today's prompt, "
                                           "byte for byte), 'static-first' (state after the frames, "
                                           "instruction block caches), 'append-only' (also an "
                                           "append-only frame window of 20-29 frames, so the frames "
                                           "cache too). Not 'legacy' = a different arm; recorded in "
                                           "result.json. See PROMPT_LAYOUTS in mc_agent/context.py."),
    response_style: str = typer.Option("full", "--response-style",
                                       help="What the default/hypothesis agents ask the model to write "
                                            "back: 'full' (today's protocol: pretty-printed JSON, the "
                                            "whole memory / hypotheses / plan every step) or 'compact' "
                                            "(one line; 1-3 sentence thought; memory_update, hypotheses "
                                            "and plan only on steps where they change). Not 'full' = a "
                                            "different arm; recorded in result.json. See RESPONSE_STYLES "
                                            "in mc_agent/context.py."),
    codex_output_schema: bool = typer.Option(False, "--codex-output-schema",
                                             help="Codex channel only (default/hypothesis agents): "
                                                  "constrain codex's output to the agent's reply schema via "
                                                  "`codex exec --output-schema`. NOTE: codex applies the "
                                                  "constraint to every assistant turn, so the model can no "
                                                  "longer call tools (measured) -- this makes the arm "
                                                  "single-shot, which is a change of arm, not a reliability "
                                                  "switch. It fixes the 46-of-2266 prose answers the c4h "
                                                  "default x codex arm had to retry; it does nothing for the "
                                                  "748 ceiling timeouts. Recorded in result.json."),
):
    """Evaluate all benchmark scenarios in benchmark_dir."""
    logger.info(f"--- Starting evaluation (model={model}) ---")

    if agent_mode not in AGENT_MODES:
        raise ValueError(f"--agent-mode must be one of {AGENT_MODES}, got {agent_mode!r}")
    if prompt_layout not in PROMPT_LAYOUTS:
        raise ValueError(f"--prompt-layout must be one of {PROMPT_LAYOUTS}, got {prompt_layout!r}")
    if response_style not in RESPONSE_STYLES:
        raise ValueError(f"--response-style must be one of {RESPONSE_STYLES}, got {response_style!r}")
    if codex_output_schema and not use_codex:
        raise ValueError("--codex-output-schema applies to --use-codex runs only")
    if shard_count < 1:
        raise ValueError(f"--shard-count must be >= 1, got {shard_count}")
    if not (0 <= shard_index < shard_count):
        raise ValueError(f"--shard-index must be in [0, {shard_count}), got {shard_index}")

    bench_path = Path(benchmark_dir)
    out_root = Path(output_dir) / model.replace("/", "_")

    if not bench_path.exists():
        raise FileNotFoundError(f"Benchmark directory not found: {bench_path}")

    metadata_entries: List[tuple] = []
    for scene_dir in sorted(d for d in bench_path.iterdir() if d.is_dir() and not d.name.startswith("_")):
        meta_path = scene_dir / "multi-agent" / "metadata.json"
        if meta_path.exists():
            metadata_entries.append((scene_dir.name, str(meta_path)))

    if not metadata_entries:
        logger.warning(f"No metadata.json found under {bench_path}")
        return

    if shard_count > 1:
        total_before_shard = len(metadata_entries)
        metadata_entries = metadata_entries[shard_index::shard_count]
        logger.info(
            f"Shard {shard_index}/{shard_count}: {len(metadata_entries)} of "
            f"{total_before_shard} scenario(s) assigned to this job"
        )

    if limit and limit > 0:
        metadata_entries = metadata_entries[:limit]

    logger.info(f"Found {len(metadata_entries)} scenario(s) to evaluate")

    pending: List[tuple] = []
    all_results: List[Dict[str, Any]] = []

    for scene_num, meta_path in metadata_entries:
        scene_out_dir = out_root / _hop_folder_name(meta_path) / scene_num
        result_path = scene_out_dir / "result.json"

        if resume and result_path.exists():
            logger.info(f"[SKIP] {scene_num} - result.json exists")
            with open(result_path, "r", encoding="utf-8") as f:
                all_results.append(json.load(f))
        else:
            pending.append((scene_num, meta_path))

    logger.info(f"Scenarios to run: {len(pending)} (skipped: {len(metadata_entries) - len(pending)})")

    def _make_error_summary(scene_num, e):
        return {
            "run_id": f"{model}_{scene_num}",
            "model": model,
            "scene_id": scene_num,
            "mode": "multi-agent",
            "error": str(e),
            "milestones_completed": 0,
            "milestones_trackable": 0,
            "all_milestones_done": False,
        }

    if num_workers <= 1:
        for idx, (scene_num, meta_path) in enumerate(pending):
            scene_out_dir = out_root / _hop_folder_name(meta_path) / scene_num
            result_path = scene_out_dir / "result.json"

            logger.info(f"\n{'='*60}")
            logger.info(f"[{idx+1}/{len(pending)}] {scene_num}")

            try:
                summary = _run_benchmark(
                    metadata_path=meta_path,
                    model=model,
                    output_dir=scene_out_dir,
                    loading_command_steps=loading_command_steps,
                    max_steps=max_steps,
                    use_vllm=use_vllm,
                    vllm_url=vllm_url,
                    use_codex=use_codex,
                    codex_effort=codex_effort,
                    codex_base_url=codex_base_url,
                    use_friday=use_friday,
                    temperature=temperature,
                    use_milestone_hint=milestone_hint,
                    agent_mode=agent_mode,
                    prolong_log_window=prolong_log_window,
                    prolong_stateless=prolong_stateless,
                    prompt_layout=prompt_layout,
                    response_style=response_style,
                    codex_output_schema=codex_output_schema,
                )
            except Exception as e:
                logger.error(f"[ERROR] {scene_num}: {e}")
                summary = _make_error_summary(scene_num, e)
                scene_out_dir.mkdir(parents=True, exist_ok=True)
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)

            all_results.append(summary)

            task_icon = "✅" if summary.get("all_milestones_done") else "❌"
            logger.info(f"Result: {task_icon} | milestones {summary.get('milestones_completed', 0)}/{summary.get('milestones_trackable', 0)}")

    else:
        import multiprocessing as _mp

        effective_workers = min(num_workers, len(pending))
        mp_ctx = _mp.get_context("spawn")

        remaining = list(pending)
        batch_num = 0

        while remaining:
            batch = remaining[:effective_workers]
            remaining = remaining[effective_workers:]
            batch_num += 1

            logger.info(f"\n[Batch {batch_num}] Launching {len(batch)} worker(s)")

            batch_jobs: List[Dict[str, Any]] = []
            for scene_num, meta_path in batch:
                scene_out_dir = out_root / _hop_folder_name(meta_path) / scene_num
                scene_out_dir.mkdir(parents=True, exist_ok=True)
                batch_jobs.append({
                    "metadata_path": str(meta_path),
                    "model": model,
                    "output_dir": str(scene_out_dir),
                    "loading_command_steps": loading_command_steps,
                    "max_steps": max_steps,
                    "use_vllm": use_vllm,
                    "vllm_url": vllm_url,
                    "use_codex": use_codex,
                    "codex_effort": codex_effort,
                    "codex_base_url": codex_base_url,
                    "use_friday": use_friday,
                    "temperature": temperature,
                    "use_milestone_hint": milestone_hint,
                    "agent_mode": agent_mode,
                    "prolong_log_window": prolong_log_window,
                    "prolong_stateless": prolong_stateless,
                    "prompt_layout": prompt_layout,
                    "response_style": response_style,
                    "codex_output_schema": codex_output_schema,
                    "_scene_num": scene_num,
                })

            with ProcessPoolExecutor(max_workers=len(batch_jobs), mp_context=mp_ctx) as pool:
                futures = {pool.submit(_worker_eval, job): job for job in batch_jobs}
                for future in as_completed(futures):
                    job = futures[future]
                    scene_num = job["_scene_num"]
                    try:
                        summary = future.result()
                        all_results.append(summary)
                        task_icon = "✅" if summary.get("all_milestones_done") else "❌"
                        logger.info(f"[DONE] {scene_num} {task_icon} | milestones {summary.get('milestones_completed', 0)}/{summary.get('milestones_trackable', 0)}")
                    except Exception as exc:
                        logger.error(f"[ERROR] {scene_num}: {exc}")
                        summary = _make_error_summary(scene_num, exc)
                        all_results.append(summary)

    total = len(all_results)
    done = sum(1 for r in all_results if r.get("all_milestones_done"))
    ms_done = sum(r.get("milestones_completed", 0) for r in all_results)
    ms_total = sum(r.get("milestones_trackable", 0) for r in all_results)

    logger.info(f"\n{'='*60}")
    logger.info("EVALUATION COMPLETE")
    logger.info("-" * 60)
    task_rate = done / total * 100 if total > 0 else 0.0
    ms_rate = ms_done / ms_total * 100 if ms_total > 0 else 0.0
    logger.info(f"Scenes: {total} | Tasks: {done}/{total} ({task_rate:.1f}%) | Milestones: {ms_done}/{ms_total} ({ms_rate:.1f}%)")
    logger.info(f"{'='*60}")

    # Each shard writes its own summary file to avoid concurrent array tasks
    # clobbering a single shared eval_summary.json; merge them afterward.
    summary_name = "eval_summary.json" if shard_count == 1 else f"eval_summary.shard{shard_index}.json"
    agg_path = out_root / summary_name
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump({
            "model": model,
            "benchmark": str(bench_path),
            "total": total,
            "done": done,
            "ms_done": ms_done,
            "ms_total": ms_total,
            "task_success_rate": task_rate,
            "milestone_success_rate": ms_rate,
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)
    logger.success(f"Aggregated summary -> {agg_path}")


if __name__ == "__main__":
    app()
