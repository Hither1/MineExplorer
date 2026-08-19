from __future__ import annotations
from dataclasses import dataclass
from io import StringIO
from typing_extensions import Self


# How the per-step request is laid out. This exists because of the serving side, not the
# agent: vLLM's prefix cache reuses KV blocks (800 tokens on the hybrid Qwen3.5/3.8 servers)
# only for a prefix identical to an earlier request. In `legacy` the memory and hints sit
# between the goal and the instructions, so a memory rewrite invalidates everything after it
# and consecutive steps share ~140 tokens -- measured 2026-08-19, zero cache blocks per step.
#   legacy       -- today's prompt, byte for byte: [intro+goal, state, instructions][frames].
#   static-first -- the same text with the state moved out of the instruction block and
#                   appended after the frames: [intro+goal, instructions][frames][state].
#                   The instruction block is now identical every step and caches; the
#                   20-frame window still slides, so the frames do not.
#   append-only  -- static-first, plus captions that do not name the frame's position in the
#                   window ("Frame [Step 37]" instead of "Frame 3 (total frame num is 20)
#                   [Step 37]"), so that with an append-only frame buffer (eval_benchmark.py
#                   rebases it every FRAME_WINDOW_REBASE steps instead of sliding by one)
#                   every frame but the newest is a cache hit too.
# The two non-legacy layouts change what the model reads (order, and for append-only the
# window size), so a run taken with them is a different arm and result.json records it.
PROMPT_LAYOUTS = ("legacy", "static-first", "append-only")

# What the model is asked to write back. Orthogonal to the layout: the layout is about the
# prefill (what the cache can reuse), the style is about the decode (how many tokens the step
# waits for). Measured on the c4h campaign (2026-08-19): the default agent's 237-token reply
# is 74 thought + 118 memory + 10 action + ~35 pretty-printing, and the memory is identical to
# the previous step's in 36% of steps and 99% similar in median; the hypothesis agent's
# 508-token reply repeats hypothesis ops and the plan verbatim for runs of steps.
#   full     -- today's protocol, byte for byte: pretty-printed JSON, the FULL memory rewritten
#               every step, hypotheses/plan every step.
#   compact  -- the same fields with the same meaning, but the reply is one line of JSON, the
#               thought is 1-3 sentences, and memory_update / hypotheses / plan are sent only
#               on steps where they change (an absent key means "unchanged"; the runner and
#               HypothesisAgent already treat an empty memory_update / hypotheses / plan as
#               "keep"). What the model maintains is unchanged; what it re-emits is not.
RESPONSE_STYLES = ("full", "compact")

STATE_BLOCK_HEADER = "\n**Current state for this step:**"


class DefaultContextBuilder:
    def __init__(self) -> None:
        self.buffer = StringIO()

    def build(self) -> str:
        return self.buffer.getvalue()

    @classmethod
    def next_step(
        cls,
        images_idx: int,
        total_images_length: int,
        frame_step: int | None = None,
        hist_action: dict | None = None,
        hist_thought: str | None = None,
        layout: str = "legacy",
    ) -> Self:
        builder = cls()
        if frame_step:
            step_info = f"[Step {frame_step}]"
        else:
            step_info = ""

        if layout == "append-only":
            # No window-relative index or count: the caption must stay byte-identical as the
            # frame ages through the window, or the cached prefix breaks at the first frame.
            builder.buffer.write(f"Frame {step_info}:" if step_info else "Frame:")
        else:
            builder.buffer.write(f"Frame {images_idx} (total frame num is {total_images_length}){step_info}:")

        # frame_buffer[i] corresponds to the observation at step frame_step
        # If frame_step > 1, then this obs came from executing action at step (frame_step-1)
        if frame_step is None or frame_step == 1:
            builder.buffer.write("\n  (Initial observation, no prior action)")
        elif frame_step > 1:
            if hist_action and hist_thought:
                key_actions = {k: v for k, v in hist_action.items() if v != 0 and k != "camera"}
                if hist_action.get("camera") != [0, 0]:
                    key_actions["camera"] = hist_action["camera"]
                builder.buffer.write(f"\n  Previous decision: \"{hist_thought}\"\n  Action taken: {key_actions}")
            else:
                builder.buffer.write("\n  (History not available)")

        return builder

    @classmethod
    def _memory_section(
        cls,
        long_term_memory: str = "",
        style: str = "full",
        memory_step: int | None = None,
        current_step: int | None = None,
    ) -> str:
        """The memory as the model sees it. `full`: the memory if there is one, else nothing (the
        model rewrites it every step anyway). `compact`: always a line -- an empty memory is asked
        for outright, and a written one carries the step it was last rewritten at, so the model
        can see it is stale (it is only sent when the model decides to change it), and after
        MEMORY_REWRITE_DUE steps without a rewrite the line asks for one. Measured 2026-08-19: with
        the section simply absent when empty, a compact default cell went 54 steps and three
        milestones without ever writing a memory."""
        mem = long_term_memory.strip() if long_term_memory else ""
        if style != "compact":
            return MEMORY_SECTION_TEMPLATE.format(long_term_memory=mem) if mem else ""
        if not mem:
            return COMPACT_MEMORY_EMPTY_TEMPLATE
        if memory_step is not None and current_step is not None:
            age = current_step - memory_step
            when = f"at step {memory_step}"
            due = (f"; it has not been rewritten for {age} steps - rewrite it this step"
                   if age >= MEMORY_REWRITE_DUE else "")
        else:
            when, due = "earlier", ""
        return COMPACT_MEMORY_SECTION_TEMPLATE.format(long_term_memory=mem, when=when, due=due)

    @classmethod
    def _state_sections(
        cls,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
        style: str = "full",
        memory_step: int | None = None,
        current_step: int | None = None,
    ) -> dict[str, str]:
        """The per-step sections, rendered from the same templates whichever layout uses them."""
        return {
            "memory_section": cls._memory_section(long_term_memory, style, memory_step, current_step),
            "milestone_section": (
                MILESTONE_SECTION_TEMPLATE.format(milestone_hint=milestone_hint.strip())
                if milestone_hint and milestone_hint.strip() else ""),
            "camera_section": (
                CAMERA_SECTION_TEMPLATE.format(camera_hint=camera_hint.strip())
                if camera_hint and camera_hint.strip() else ""),
            "movement_section": (
                MOVEMENT_SECTION_TEMPLATE.format(movement_hint=movement_hint.strip())
                if movement_hint and movement_hint.strip() else ""),
        }

    @classmethod
    def system_prompt(
        cls,
        task_desc: str,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
        layout: str = "legacy",
        style: str = "full",
        memory_step: int | None = None,
        current_step: int | None = None,
    ) -> Self:
        TASK_SUFFIX = "end the episode by setting the 'ESC' action to 1."
        goal_desc = f"{task_desc}, {TASK_SUFFIX}"

        builder = cls()
        if layout == "legacy":
            sections = cls._state_sections(long_term_memory, milestone_hint, camera_hint, movement_hint,
                                           style, memory_step, current_step)
        else:
            # The state goes into state_block() after the frames; what is left here is the same
            # text every step, which is the point.
            sections = dict(memory_section="", milestone_section="", camera_section="", movement_section="")
        template = BASE_PROMPT if style == "full" else BASE_PROMPT_COMPACT
        text = template.format(goal_desc=goal_desc, **sections)
        if layout == "append-only":
            text = text.replace(APPEND_ONLY_WINDOW_PHRASE[0], APPEND_ONLY_WINDOW_PHRASE[1])
        builder.buffer.write(text)
        return builder

    @classmethod
    def state_block(
        cls,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
        style: str = "full",
        memory_step: int | None = None,
        current_step: int | None = None,
    ) -> str:
        """The per-step state as one text part, for the non-legacy layouts (empty if nothing to say)."""
        sections = cls._state_sections(long_term_memory, milestone_hint, camera_hint, movement_hint,
                                       style, memory_step, current_step)
        body = "".join(sections.values())
        return STATE_BLOCK_HEADER + body if body else ""


# What the append-only layout says about the window instead of "the last 20 frames" (the
# window is FRAME_BUFFER_SIZE..FRAME_BUFFER_SIZE+FRAME_WINDOW_REBASE-1 frames there).
APPEND_ONLY_WINDOW_PHRASE = (
    "a sequence of the last 20 frames from your point of view",
    "a sequence of your most recent frames (20 to 29 of them, oldest first) from your point of view",
)


MEMORY_SECTION_TEMPLATE = """
**Your Long-Term Memory (accumulated across all previous steps):**
{long_term_memory}
"""

# The compact style's memory line (see _memory_section). A compact reply carries the memory only
# when the model changes it, so the line must say when it was last written and ask for it when it
# is missing or has gone MEMORY_REWRITE_DUE steps without a rewrite.
MEMORY_REWRITE_DUE = 20

COMPACT_MEMORY_EMPTY_TEMPLATE = """
**Your Long-Term Memory:** empty - write it this step (send "memory_update").
"""

COMPACT_MEMORY_SECTION_TEMPLATE = """
**Your Long-Term Memory (last rewritten {when}; rewrite it whenever it no longer records everything you have found, completed or ruled out{due}):**
{long_term_memory}
"""

MILESTONE_SECTION_TEMPLATE = """
**Environment-verified task status:** {milestone_hint}
"""

CAMERA_SECTION_TEMPLATE = """
**Environment-reported camera state:** {camera_hint}
"""

MOVEMENT_SECTION_TEMPLATE = """
**Environment-reported position (ground truth - trust this over your own step-count narrative):** {movement_hint}
"""

# The default agent's prompt, in pieces so that the two response styles share every piece
# they have in common (BASE_PROMPT, the `full` style, is the concatenation the campaign has
# always used -- byte for byte, see scripts/prompt_layout_check.py --golden).
_DEFAULT_HEADER = """
You are an expert Minecraft player embodied as an AI agent. Your mission is to survive and thrive.
{goal_desc}
{memory_section}
{milestone_section}
{camera_section}
{movement_section}
You will be given a recent history of your thoughts and a sequence of the last 20 frames from your point of view. Based on this full context, you must decide on your next thought, action, and memory update.
"""

_DEFAULT_THOUGHT_PROCESS_FULL = """
**Your Thought Process:**
1.  Review your long-term memory (if any). What important facts have you accumulated?
2.  Analyze the past thoughts. What was your most recent plan? Are you still following it?
3.  Analyze the sequence of images. Do you see movement? Have you turned? What is new in your view?
4.  Formulate a new, concise thought. Your thought should describe your immediate plan or observation.
5.  Based on your thought, decide the single next action to take.
6.  Update your long-term memory: rewrite it as a concise, updated summary that incorporates new key findings. Keep it under 200 words. Focus on: locations visited, objects found, failed attempts, current progress toward the goal.
"""

_DEFAULT_THOUGHT_PROCESS_COMPACT = """
**Your Thought Process:**
1.  Review your long-term memory (if any). What important facts have you accumulated?
2.  Analyze the past thoughts. What was your most recent plan? Are you still following it?
3.  Analyze the sequence of images. Do you see movement? Have you turned? What is new in your view?
4.  Formulate a new, concise thought: 1-3 sentences on what you conclude and what you will do next. Do not restate the memory, the hint lines or the frame captions - they are already in front of you.
5.  Based on your thought, decide the single next action to take.
6.  Your long-term memory is what survives beyond the frames you can see, so keep it complete: write it on your first step, and rewrite it in FULL (a concise summary under 200 words: locations visited, objects found, failed attempts, current progress toward the goal) whenever it no longer records everything important - a landmark or object found, a sub-goal completed, a direction or attempt that failed, a change of plan - and whenever the memory line above says it is due. On the other steps do not send it.
"""

_DEFAULT_ACTION_REFERENCE = """
**Available Actions:**
Your actions are controlled by a JSON object. Available keys:
- "ESC": 0 or 1, press ESC to end episode (usually 0)
- "attack": 0 or 1, attack/mine blocks
- "back": 0 or 1, move backward
- "camera": [pitch_delta, yaw_delta] in degrees (e.g., [0, 45] to look right, [-20, 0] to look up).
  **IMPORTANT**: this is a RELATIVE change added to your CURRENT camera angle, not an absolute target -
  repeating the same camera move across several steps keeps rotating further in that direction. Pitch is
  clamped to [-90 (straight up), 90 (straight down)]; if you keep pushing pitch the same direction it will
  get stuck at the clamp and you'll not be looking at anything useful. Trust the "Environment-reported
  camera state" line above over your own visual read - if it says you're pitched far from 0, issue a
  camera move of the opposite sign before trying to interpret what you see.
- "drop": 0 or 1, drop current item
- "forward": 0 or 1, move forward
- "jump": 0 or 1, jump
- "left": 0 or 1, strafe left
- "right": 0 or 1, strafe right
- "sneak": 0 or 1, sneak/crouch
- "sprint": 0 or 1, sprint (MUCH FASTER movement - use this when exploring!)
- "use": 0 or 1, use item or place block
- "inventory": 0 or 1, open/close inventory
- "hotbar.1" to "hotbar.9": 0 or 1, select hotbar slots
- "pickItem", "swapHands": other actions

**Action Value Rules:**
- Most actions: 0 = don't do, 1 = do it
- "camera": continuous values [pitch, yaw] in degrees
- **IMPORTANT**: You only need to specify actions you want to perform (value = 1 or non-zero)
- Omitted keys automatically default to 0 (no action)
- This keeps your responses concise

**Movement Tips for Efficient Exploration:**
- **USE SPRINT!** Combine "forward": 1 with "sprint": 1 for FAST movement when exploring open areas
- **Turn, then move - don't do both every step.** A camera yaw change and "forward" fire in the same
  in-game tick, so pairing a large yaw turn (e.g. 90 degrees) with "forward" on every single step turns
  your path into a tight loop instead of a straight line - each step points you in a new direction before
  you've gone anywhere in the last one. If you want to change direction, spend one step turning
  (camera yaw only, forward=0), then spend several subsequent steps moving straight (forward=1,
  camera=[0,0]) before turning again. Use the **Environment-reported position** line above (not your
  own step count or visual impression) to confirm you're actually covering new ground - it will tell
  you explicitly if your last action didn't move you, or if you've been circling in place.
- Use "jump": 1 with forward movement to navigate obstacles
- Use camera to look around before deciding where to move
- Combine actions efficiently (e.g., sprint + forward + jump for speed over terrain)
"""

_DEFAULT_RESPONSE_FULL = """
**RESPONSE FORMAT:**
Your response **MUST** be valid JSON with exactly THREE keys: "thought", "action", and "memory_update".
- "thought": your current reasoning and plan (string)
- "action": the action JSON object
- "memory_update": updated long-term memory summarizing everything important so far (string, max 200 words). Write the FULL updated memory, not just the delta.

**Examples:**

Example 1 - Fast exploration (USE THIS OFTEN!):
```json
{{
  "thought": "I need to cover ground quickly to find a cave. I will sprint forward.",
  "action": {{
    "forward": 1,
    "sprint": 1
  }},
  "memory_update": "Step 1: Spawned in a forest biome. No cave visible yet. Started exploring north."
}}
```

Example 2 - Updating memory with new findings:
```json
{{
  "thought": "I found the jukebox inside the stone hut. Moving toward it.",
  "action": {{
    "forward": 1
  }},
  "memory_update": "Spawned near a stone hut. Explored east side - found crafting table and chest. Found jukebox inside stone hut at north side. Currently approaching jukebox."
}}
```

Example 3 - Recording a failed attempt:
```json
{{
  "thought": "The path north is blocked by lava. I should try going east instead.",
  "action": {{
    "right": 1,
    "sprint": 1
  }},
  "memory_update": "Spawned in desert. North path blocked by lava pool - cannot pass. East direction looks open. West has sand dunes. Target object not yet found."
}}
```

**Remember**: Always use sprint when moving forward in open areas to explore efficiently! Always update memory_update with the FULL current memory (not just new info).
"""

_DEFAULT_RESPONSE_COMPACT = """
**RESPONSE FORMAT:**
Your response **MUST** be exactly one JSON object on a single line - no line breaks, no indentation, no text before or after it - with the keys "thought" and "action", plus "memory_update" on the steps where the memory is written or changes.
- "thought": your concise reasoning and plan (string, 1-3 sentences)
- "action": the action JSON object (only the keys you set; omitted keys are 0)
- "memory_update": the FULL long-term memory (string, max 200 words). Send it on your first step and whenever the memory changes (or the memory line says it is due), and then send the whole memory, never just the delta. Leave the key out on the other steps: no key means "memory unchanged".

**Examples:**

Example 1 - First step: the memory is empty, so it is written:
{{"thought": "Nothing found yet; I will scan the surroundings before choosing a direction.", "action": {{"camera": [0, 45]}}, "memory_update": "Step 1: spawned in a forest biome next to a stone path. Nothing found yet."}}

Example 2 - Fast exploration, nothing new to remember:
{{"thought": "Open ground ahead and nothing new in view. I will keep sprinting forward.", "action": {{"forward": 1, "sprint": 1}}}}

Example 3 - A new finding, so the memory is rewritten in full:
{{"thought": "I found the jukebox inside the stone hut. Moving toward it.", "action": {{"forward": 1}}, "memory_update": "Spawned near a stone hut. Explored east side - found crafting table and chest. Found jukebox inside stone hut at north side. Currently approaching jukebox."}}

Example 4 - Recording a failed attempt:
{{"thought": "The path north is blocked by lava. I will try east instead.", "action": {{"right": 1, "sprint": 1}}, "memory_update": "Spawned in desert. North path blocked by lava pool - cannot pass. East direction looks open. West has sand dunes. Target object not yet found."}}

**Remember**: Always use sprint when moving forward in open areas to explore efficiently! Send "memory_update" on the first step and whenever the memory changes or is due, and then send the FULL memory; a memory that does not mention what you have found or completed is stale. Keep the whole reply on one line.
"""

_ESC_RULE = """
**Important**: Only set ESC=1 when the "Environment-verified task status" line above says the task HAS been verified complete. Your own visual read of a frame is not proof the action worked (e.g. a door may look open, an item may look mined, an attack may look lethal, when it actually was not) — trust the environment-verified status, not your impression of the last frame. If it says the task is not yet complete, keep working even if you believe you just succeeded.
"""

BASE_PROMPT = (_DEFAULT_HEADER + _DEFAULT_THOUGHT_PROCESS_FULL + _DEFAULT_ACTION_REFERENCE
               + _DEFAULT_RESPONSE_FULL + _ESC_RULE)

BASE_PROMPT_COMPACT = (_DEFAULT_HEADER + _DEFAULT_THOUGHT_PROCESS_COMPACT + _DEFAULT_ACTION_REFERENCE
                       + _DEFAULT_RESPONSE_COMPACT + _ESC_RULE)


# ---------------------------------------------------------------------------
# MineRL task description examples (used in eval_benchmark.py)
# ---------------------------------------------------------------------------

@dataclass
class MineRLTaskDescExample:
    FIND_CAVE_GOAL = "Your current high-level goal is: **Find a cave.** Explore and find a cave. When inside a cave. You are not allowed to dig down from the surface to find a cave."
    CREATE_PEN_GOAL = "Your current high-level goal is: **Build an animal pen.** Build it next to a house in a village. Use fence posts and at least one gate. It must contain at least two of the same animal (chickens, cows, pigs, or sheep). Do not mix animal types. Do not harm villagers or village structures."
    MAKE_WATERFALL_GOAL = "Your current high-level goal is: **Make a beautiful waterfall.** Use your water bucket in this extreme hills biome to make a beautiful waterfall. Then take an aesthetic 'picture' by positioning the camera for a nice view."
    BUILD_HOUSE_GOAL = "Your current high-level goal is: **Build a house in the style of the village.** Do not damage the village. Build in an appropriate location (e.g. next to the path). Then give a brief tour (spin around slowly so all walls and roof are visible)."
    OBTAIN_DIAMOND_SHOVEL_GOAL = "Your current high-level goal is: **Obtain a diamond shovel.** You need to gather resources (wood, stone, iron, diamonds), craft tools (crafting table, furnace, pickaxes), and eventually craft a diamond shovel."


MINERL_TASK_MAP = {
    "MineRLBasaltFindCave-v0": MineRLTaskDescExample.FIND_CAVE_GOAL,
    "MineRLBasaltCreateVillageAnimalPen-v0": MineRLTaskDescExample.CREATE_PEN_GOAL,
    "MineRLBasaltMakeWaterfall-v0": MineRLTaskDescExample.MAKE_WATERFALL_GOAL,
    "MineRLBasaltBuildVillageHouse-v0": MineRLTaskDescExample.BUILD_HOUSE_GOAL,
    "MineRLObtainDiamondShovel-v0": MineRLTaskDescExample.OBTAIN_DIAMOND_SHOVEL_GOAL,
}

MINERL_DEFAULT_TASK_EXAMPLE = "MineRLBasaltFindCave-v0"
