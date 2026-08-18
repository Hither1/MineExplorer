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
    def _state_sections(
        cls,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
    ) -> dict[str, str]:
        """The per-step sections, rendered from the same templates whichever layout uses them."""
        return {
            "memory_section": (
                MEMORY_SECTION_TEMPLATE.format(long_term_memory=long_term_memory.strip())
                if long_term_memory and long_term_memory.strip() else ""),
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
    ) -> Self:
        TASK_SUFFIX = "end the episode by setting the 'ESC' action to 1."
        goal_desc = f"{task_desc}, {TASK_SUFFIX}"

        builder = cls()
        if layout == "legacy":
            sections = cls._state_sections(long_term_memory, milestone_hint, camera_hint, movement_hint)
        else:
            # The state goes into state_block() after the frames; what is left here is the same
            # text every step, which is the point.
            sections = dict(memory_section="", milestone_section="", camera_section="", movement_section="")
        text = BASE_PROMPT.format(goal_desc=goal_desc, **sections)
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
    ) -> str:
        """The per-step state as one text part, for the non-legacy layouts (empty if nothing to say)."""
        sections = cls._state_sections(long_term_memory, milestone_hint, camera_hint, movement_hint)
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

MILESTONE_SECTION_TEMPLATE = """
**Environment-verified task status:** {milestone_hint}
"""

CAMERA_SECTION_TEMPLATE = """
**Environment-reported camera state:** {camera_hint}
"""

MOVEMENT_SECTION_TEMPLATE = """
**Environment-reported position (ground truth - trust this over your own step-count narrative):** {movement_hint}
"""

BASE_PROMPT = """
You are an expert Minecraft player embodied as an AI agent. Your mission is to survive and thrive.
{goal_desc}
{memory_section}
{milestone_section}
{camera_section}
{movement_section}
You will be given a recent history of your thoughts and a sequence of the last 20 frames from your point of view. Based on this full context, you must decide on your next thought, action, and memory update.

**Your Thought Process:**
1.  Review your long-term memory (if any). What important facts have you accumulated?
2.  Analyze the past thoughts. What was your most recent plan? Are you still following it?
3.  Analyze the sequence of images. Do you see movement? Have you turned? What is new in your view?
4.  Formulate a new, concise thought. Your thought should describe your immediate plan or observation.
5.  Based on your thought, decide the single next action to take.
6.  Update your long-term memory: rewrite it as a concise, updated summary that incorporates new key findings. Keep it under 200 words. Focus on: locations visited, objects found, failed attempts, current progress toward the goal.

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

**Important**: Only set ESC=1 when the "Environment-verified task status" line above says the task HAS been verified complete. Your own visual read of a frame is not proof the action worked (e.g. a door may look open, an item may look mined, an attack may look lethal, when it actually was not) — trust the environment-verified status, not your impression of the last frame. If it says the task is not yet complete, keep working even if you believe you just succeeded.
"""


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
