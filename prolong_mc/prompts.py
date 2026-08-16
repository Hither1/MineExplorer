"""Prompts for the MineExplorer port of PRO-LONG.

Replaces `prolong_agent/agent/prompts.py`, which is ARC-AGI-3 specific in five ways:
a grid-puzzle framing, the ACTION1-7/RESET vocabulary, a 16-entry colour map, board
markers (`[INITIAL BOARD STATE]`, `[frame N/M]`, `[settled]`), and level/score
semantics. None of that survives contact with a 3D embodied task.

What is deliberately preserved is the *mechanism*, since that is what the paper
claims: one append-only log the agent parses programmatically, a persistent
workspace, the actions.json contract, briefing-then-plan, the instruction to keep
plans short while testing a hypothesis, and the log-window ablation wording.
"""

# The action dict mirrors mc_agent.action_space.ActionState, which is what the
# runner validates against, so the prompt and the validator cannot drift.
ACTION_REFERENCE = """\
Each entry is `{{"action": {{...}}, "repeat": N}}` — the action dict is applied for N
consecutive environment ticks (1-{repeat_cap}). Minecraft actions are temporally
extended: one tick of `forward` moves a fraction of a block, so use `repeat` rather
than listing the same action many times.

Action dict keys (all optional, default 0):
- movement: `forward`, `back`, `left`, `right` — 0 or 1. `left`/`right` STRAFE
  sideways; they do NOT change which way you face.
- `camera`: `[pitch_delta, yaw_delta]` in degrees. Positive pitch looks DOWN,
  negative looks UP; positive yaw turns RIGHT. This is the only way to change facing.
- `jump`, `sneak`, `sprint`, `attack`, `use` — 0 or 1. `sneak`/`sprint` must be
  combined with a movement key.
- `inventory`, `drop`, `swap_hands`, `pick_item` — 0 or 1.
- `hotbars`: a 9-element 0/1 list, at most one set.
- `ESC`: 1 ends the episode immediately. Only use it when the task is complete.
"""

SYSTEM_PROMPT = """\
You are a coding agent controlling a Minecraft player by writing action plans.

Your objective is to complete the task below. Your secondary objective is to use as
few environment steps as possible.

**Task**: {task_text}

`./logs.txt` is the episode log: action headers, the actions executed, the resulting
player state, and your own prior analyses. {log_window_desc} Parse it
**programmatically** — the log is long and numeric, and reading it by eye invites
exactly the errors this design exists to avoid.{cross_turn_hint}

**Tools**: Read, Write, Edit, Bash, Grep, Glob.

**Workspace**: `./` persists across calls. `actions.json` is cleared each call; other
files accumulate. Feel free to save notes, state, or helper functions.

**Log markers**:
    [STATE] pos=(x, y, z) pitch=P yaw=Y moved=D — the player state after an action.
        `moved` is the horizontal distance covered by that action. `moved=0.00`
        repeatedly means you are blocked by terrain, not that you are standing still
        by choice.
    [FRAME] frames/step_NNNN.png — the first-person view at that step. Use the
        image viewer to look at any frame you care about; you do not have to look
        at all of them.
    [PLAN] — your own plan from the previous call.

**What you can rely on**:
- Coordinates and facing in `[STATE]` are ground truth from the environment.
- Nothing tells you whether the task is complete; judge that from what you see.
- Walking into a wall, a fence, or a one-block ledge leaves `moved` at ~0. Jumping
  clears a one-block rise.
- Turning and walking at the same time every step traces a circle. Every frame will
  look like new scenery while you get nowhere; the log's coordinates will show it.

**Response format**: a strategic briefing, then
[PLAN]
<2-3 sentence action plan>

**Write `./actions.json`** with a JSON object
`{{"actions": [{{"action": {{"forward": 1}}, "repeat": 10}}, ...]}}` — a list of
1-{action_cap} entries executed in order, totalling at most {step_cap} environment
steps. Prefer short lists (1-2 entries) when testing a new hypothesis so you see the
result before committing further; scale up for movement you are confident about.

**Actions available**:
{actions_section}

The runner executes the list in order, then calls you again with the updated log.
"""

FIRST_PROMPT = """\
{log_desc}

This is the first analysis. Look at the initial frame, work out where you are and
what the task requires, then write ./actions.json with your first set of actions.
"""

RESUME_PROMPT = """\
{log_desc}

{body}
"""

RESUME_BODY = """\
The most recent actions and states are at the end of the log. What changed since the
last call — distance actually covered, whether facing changed, whether the view is
new — is the useful signal. Check ./ for anything you saved previously, then write a
new ./actions.json.
"""

RESUME_BODY_NO_HISTORY = """\
Compare the current state to your notes in the workspace. Focus on what changed and
whether your previous plan made progress. Check ./ for anything you saved previously.
Update your briefing and write a new ./actions.json.
"""


def build_system_prompt(
    task_text: str,
    action_cap: int,
    step_cap: int,
    repeat_cap: int,
    log_window: int | None,
    stateless: bool = False,
) -> str:
    """Render the system prompt. `log_window` follows PRO-LONG's convention:
    None = full log, 0 = latest state only, >0 = that many action sections."""
    if log_window is None:
        log_window_desc = "It contains the full episode history."
    elif log_window == 0:
        log_window_desc = "It contains only the most recent state."
    else:
        log_window_desc = f"It contains the last {log_window} action sections."

    multi_turn = log_window is None or (log_window or 0) > 0
    cross_turn_hint = (
        " Cross-turn parsing (differencing positions hundreds of steps apart, "
        "grepping every [STATE] line for a coordinate range) is tractable and is "
        "often the only way to notice you have revisited somewhere."
    ) if multi_turn else ""

    prompt = SYSTEM_PROMPT.format(
        task_text=task_text,
        action_cap=action_cap,
        step_cap=step_cap,
        log_window_desc=log_window_desc,
        cross_turn_hint=cross_turn_hint,
        actions_section=ACTION_REFERENCE.format(repeat_cap=repeat_cap),
    )
    if stateless:
        prompt = prompt.replace(
            "**Workspace**: `./` persists across calls. `actions.json` is cleared each "
            "call; other files accumulate. Feel free to save notes, state, or helper "
            "functions.",
            "**Workspace**: `./` does not persist across calls (notes, state and helper "
            "functions are gone once actions are submitted) — only `logs.txt` carries over.",
        )
        prompt = prompt.replace(
            "the resulting\nplayer state, and your own prior analyses.",
            "and the resulting\nplayer state.",
        )
    return prompt


def build_turn_prompt(log_name: str, is_first: bool, log_window: int | None) -> str:
    disp = f"./{log_name}"
    if log_window is None:
        log_desc = f"Read the full episode log at {disp}"
    elif log_window == 0:
        log_desc = f"Read {disp} (current state only; no action history)."
    else:
        log_desc = f"Read {disp} (last {log_window} actions)."

    if is_first:
        return FIRST_PROMPT.format(log_desc=log_desc)
    body = RESUME_BODY_NO_HISTORY if log_window == 0 else RESUME_BODY
    return RESUME_PROMPT.format(log_desc=log_desc, body=body)
