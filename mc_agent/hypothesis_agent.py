"""HypothesisAgent – an LLM agent that maintains an explicit DAG of
hypotheses about the world (mc_agent.hypothesis.HypothesisGraph) alongside
a short-horizon plan, in addition to the thought/action/memory_update loop
DefaultAgent already does.

Design intent (see repo discussion): the graph is *advisory*, not
controlling — each step it is rendered into the prompt (active hypotheses,
confidences, dependencies, current plan) and the LLM is asked to (a) act,
same as DefaultAgent, and (b) report which hypotheses it proposed, tested,
or updated as a result, plus a short refreshed plan. The agent code never
overrides the LLM's chosen action; it only maintains/persists the graph.

HypothesisAgent is duck-type compatible with DefaultAgent
(`load_system_prompt`, `get_action`, `get_default_action`) so it can be
swapped in wherever a DefaultAgent is constructed without touching the
surrounding step loop (see eval_benchmark.py's `--agent-mode` flag).
"""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from mc_agent.action_space import BaseActionSpace, extract_json_from_response
from mc_agent.context import (
    APPEND_ONLY_WINDOW_PHRASE, PROMPT_LAYOUTS, RESPONSE_STYLES, STATE_BLOCK_HEADER,
    DefaultContextBuilder, MEMORY_SECTION_TEMPLATE, MILESTONE_SECTION_TEMPLATE,
    CAMERA_SECTION_TEMPLATE, MOVEMENT_SECTION_TEMPLATE,
)
from mc_agent.hypothesis import CycleError, HypothesisGraph
from mc_agent.llm_provider import BaseLLMProvider
from mc_agent.utils import convert_buffer_to_base64_images


def hypothesis_reply_schema(style: str = "full") -> dict:
    """The JSON Schema for the hypothesis agent's reply; see default_reply_schema for why.

    `hypotheses` and `plan` are required under `full` (the prompt asks for them every step,
    possibly empty) and optional under `compact` (sent only when they change). A hypothesis op
    needs only its `id`: an update carries the id plus whatever changed.
    """
    required = ["thought", "action"] + (["memory_update", "hypotheses", "plan"] if style == "full" else [])
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "thought": {"type": "string"},
            "action": {"type": "object", "additionalProperties": True},
            "memory_update": {"type": "string"},
            "hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "statement": {"type": "string"},
                        "confidence": {"type": "number"},
                        "status": {"type": "string", "enum": ["active", "confirmed", "refuted", "stale"]},
                        "kind": {"type": "string", "enum": ["goal", "location", "mechanism", "state", "other"]},
                        "depends_on": {"type": "array", "items": {"type": "string"}},
                        "evidence": {"type": "string"},
                    },
                    "required": ["id"],
                },
            },
            "plan": {"type": "array", "items": {"type": "string"}},
            "testing": {"type": ["string", "null"]},
        },
        "required": required,
    }


class HypothesisContextBuilder(DefaultContextBuilder):
    """Same per-frame captions as DefaultContextBuilder; a different system
    prompt that adds hypothesis-DAG + planning instructions and sections."""

    @classmethod
    def _hypothesis_sections(cls, hypothesis_summary: str = "", plan_summary: str = "",
                             discipline_summary: str = "") -> dict[str, str]:
        return {
            "hypothesis_section": (
                HYPOTHESIS_SECTION_TEMPLATE.format(hypothesis_summary=hypothesis_summary.strip())
                if hypothesis_summary and hypothesis_summary.strip()
                else HYPOTHESIS_EMPTY_TEMPLATE
            ),
            "plan_section": (
                PLAN_SECTION_TEMPLATE.format(plan_summary=plan_summary.strip())
                if plan_summary and plan_summary.strip()
                else ""
            ),
            "discipline_section": (
                DISCIPLINE_SECTION_TEMPLATE.format(discipline_summary=discipline_summary.strip())
                if discipline_summary and discipline_summary.strip()
                else ""
            ),
        }

    @classmethod
    def system_prompt(
        cls,
        task_desc: str,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
        hypothesis_summary: str = "",
        plan_summary: str = "",
        layout: str = "legacy",
        style: str = "full",
        memory_step: int | None = None,
        current_step: int | None = None,
        discipline_summary: str = "",
    ):
        TASK_SUFFIX = "end the episode by setting the 'ESC' action to 1."
        goal_desc = f"{task_desc}, {TASK_SUFFIX}"

        builder = cls()
        if layout == "legacy":
            sections = cls._state_sections(long_term_memory, milestone_hint, camera_hint, movement_hint,
                                           style, memory_step, current_step)
            sections.update(cls._hypothesis_sections(hypothesis_summary, plan_summary, discipline_summary))
        else:
            # Same idea as DefaultContextBuilder: the state -- memory, hints, hypothesis graph,
            # plan -- moves to state_block() after the frames, and this block never changes.
            sections = dict(memory_section="", milestone_section="", camera_section="",
                            movement_section="", hypothesis_section="", plan_section="",
                            discipline_section="")
        template = HYPOTHESIS_BASE_PROMPT if style == "full" else HYPOTHESIS_BASE_PROMPT_COMPACT
        text = template.format(goal_desc=goal_desc, test_budget=TEST_BUDGET_STEPS, **sections)
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
        hypothesis_summary: str = "",
        plan_summary: str = "",
        style: str = "full",
        memory_step: int | None = None,
        current_step: int | None = None,
        discipline_summary: str = "",
    ) -> str:
        sections = cls._state_sections(long_term_memory, milestone_hint, camera_hint, movement_hint,
                                       style, memory_step, current_step)
        sections.update(cls._hypothesis_sections(hypothesis_summary, plan_summary, discipline_summary))
        # The hypothesis section is never empty (HYPOTHESIS_EMPTY_TEMPLATE), so this block always
        # exists for the hypothesis agent -- the graph is state the model must read every step.
        return STATE_BLOCK_HEADER + "".join(sections.values())


HYPOTHESIS_SECTION_TEMPLATE = """
**Your Hypothesis Graph (beliefs about the world, with self-rated confidence 0-1):**
{hypothesis_summary}
"""

HYPOTHESIS_EMPTY_TEMPLATE = """
**Your Hypothesis Graph:** empty so far — this is a good time to propose your first hypothesis.
"""

PLAN_SECTION_TEMPLATE = """
**Your Current Plan (steps toward testing your top hypothesis):**
{plan_summary}
"""

DISCIPLINE_SECTION_TEMPLATE = """
**Harness notices (facts about your own graph, enforced -- not advice):**
{discipline_summary}
"""

# Steps a hypothesis may stay "under test" with no change in its confidence before the
# harness marks it stale and clears the plan. Calibrated on the 4-hop trajectories: 46
# attack ticks on "breaking the trunks will clear a path" (0311, confidence 0.65
# throughout) and 202 ESC presses on "I mined the quartz" (0603) -- a test that has not
# moved a belief in 25 steps is not a test any more.
TEST_BUDGET_STEPS = 25

# The hypothesis agent's prompt, in pieces so that the two response styles share every piece
# they have in common (HYPOTHESIS_BASE_PROMPT, the `full` style, is the concatenation the campaign
# has always used -- byte for byte, see scripts/prompt_layout_check.py --golden).
_HYP_HEADER = """
You are an expert Minecraft player embodied as an AI agent. Your mission is to survive and thrive.
{goal_desc}
{memory_section}
{milestone_section}
{camera_section}
{movement_section}
{hypothesis_section}
{plan_section}
{discipline_section}
You will be given a recent history of your thoughts and a sequence of the last 20 frames from your point of view. Based on this full context, you must decide on your next thought, action, memory update, hypothesis updates, and plan.
"""

# The discipline the harness enforces on the graph (HypothesisAgent._enforce_discipline),
# stated once so the model can act on it rather than be surprised by it. Shared by both
# response styles. Why each rule exists is in experiments/HYPOTHESIS_V2_DESIGN.md.
_HYP_DISCIPLINE = """
**Kinds, and what the harness enforces:**
- Give every hypothesis a `kind`: "goal" (a sub-goal the task names: found / reached / mined X -- the
  step-2 scaffolding is all "goal"), "location" (where something is, relative to you or to spawn),
  "mechanism" (how the world responds to an action: "attacking this trunk clears the path"), "state"
  (what you carry or have done: "the pickaxe is in slot 3"), or "other".
- **Goals are confirmed by the environment, not by you.** A "goal" hypothesis stays "active" until the
  Environment-verified task status says the task HAS been verified; until then use confidence (up
  to 0.9) to say how sure you are. A "confirmed" you send for a goal before that is reverted. An
  item is "mined" only if it is in your hotbar/inventory; a landmark is "found" only when you stand
  next to it and look at it; a door is "open" only if you can walk through it.
- **If your ESC is refused, every goal you believed complete is capped at 0.5 and locked** (shown
  as "locked" in the graph): at least one of them is NOT done, whatever your memory says. Re-verify
  each locked goal physically, starting with the least directly observed, instead of pressing ESC
  again -- ESC while the status says NOT verified is dropped before it reaches the game.
- Name the hypothesis your action tests in `"testing"` (an id, or null for plain travel). A
  hypothesis under test for {test_budget} steps without a change in its confidence is marked "stale"
  and your plan is cleared -- pick a different hypothesis, or a different way to test this one,
  before that happens.
"""

_HYP_THOUGHT_PROCESS_FULL = """
**Your Thought Process:**
1.  Review your long-term memory and hypothesis graph (if any). What do you already believe, and how confident are you?
2.  If the task description names multiple sub-goals in sequence (look for words like "first"/"then"/
    "after"/"using X to Y"/"finally") and you have not already opened a hypothesis for each of them,
    do that now: propose one hypothesis per named sub-goal, in the order they're mentioned, each
    `depends_on` the one(s) named just before it (see Example 5). Use a low starting confidence
    (0.2-0.3) since you haven't verified any of them yet — this is a map of the task's structure to
    fill in with real evidence as you go, not a claim you've confirmed anything.
3.  Analyze the sequence of images AND the Environment-reported position line above. Do you see movement? Have you turned? What is new in your view? Cross-check your visual impression against the real position numbers - if that line says you haven't moved, or that your net displacement over the last several steps is small, trust that over what individual frames seem to suggest (near-identical terrain can still look "new" frame to frame). Does the evidence - visual and positional together - confirm, refute, or leave untouched any active hypothesis?
4.  Formulate a new, concise thought describing your immediate reasoning.
5.  Decide the single next action to take.
6.  Update your long-term memory: rewrite it as a concise, updated summary. Keep it under 200 words.
7.  Update your hypotheses: propose new hypotheses about the world when you notice something uncertain worth investigating (e.g. "there is likely a village nearby"), and update existing ones (by id) when you gather evidence — raise confidence toward 1.0 when confirmed, lower toward 0.0 when refuted, and mark status "confirmed"/"refuted" once you're sure.

    `depends_on` covers TWO kinds of relationship, both worth recording — only list dependency ids
    that already exist or that you are defining in this same response:
    - **Refinement**: a more specific claim about the same object (e.g. "the chest has a diamond"
      depends_on "there is a chest here").
    - **Task-order prerequisite**: a later sub-goal that requires an earlier one first (e.g. "the
      potted cactus is in the first room" depends_on "the trapdoor is the building's entrance",
      because you can't reach the first room without going through the entrance). This is the more
      common case for multi-step task descriptions — see step 2 above and Example 5.

    **One id = one claim about one specific object/location — never bundle two different sub-goals
    into a single hypothesis's statement** (e.g. don't write one hypothesis claiming a building has
    both "a ladder" and "a trapped chest"; give the ladder its own id, and make the chest hypothesis
    `depends_on` it). Bundling erases the exact structure you're supposed to be capturing. Once you've
    physically moved on from a specific candidate (e.g. you've fully searched one particular building
    and it didn't have what you need), mark THAT id "refuted" or "stale" and give the NEXT candidate
    you investigate a NEW id - even if the new candidate matches the same general statement as the
    old one. Do not keep reusing the same id to describe a whole sequence of different physical
    objects; that erases the distinction between them and makes confidence/evidence meaningless (see
    Example 4 below).

    **A hypothesis must say something you don't already know from the task description.** A
    goal-restating placeholder is fine ONLY as the very first-step scaffolding described in step 2
    above (you haven't seen anything yet, so you have nothing more specific to say). Past that first
    step, once you've actually spent time searching, restating the goal verbatim (e.g. "There is a
    polished granite pillar nearby in this forest biome." when the task IS to find a polished granite
    pillar) is not a hypothesis - it's the assignment, and tracking confidence on a fact you were
    already told teaches you nothing. A real hypothesis adds a specific,
    checkable claim beyond the goal text: a direction you're committing to based on the
    Environment-reported position numbers, not a step count (e.g. "not present within the ~60 blocks
    I've covered heading east from spawn - likely further out, or in another direction entirely"); a
    landmark you've actually spotted ("a stone path visible to the northeast may lead to it"); or a
    world-knowledge-based mechanism ("granite pillars are a placed decorative structure, not natural
    forest generation, so it's more likely near a clearing, ruin, or biome edge than deep in dense
    trees"). If you cannot state anything more specific than the task text itself, you don't have
    enough evidence yet to hypothesize - spend the next few steps actually covering new ground (check
    Environment-reported position to confirm you are) rather than resubmitting the restated goal with
    an incremented counter as "evidence."

    **Evidence must cite the ground-truth position, not your own step-count narrative.** "300
    consecutive scans, environment unchanged" is not evidence if Environment-reported position shows
    you're still near your spawn point - that means your last N actions didn't do what you intended,
    not that the object is absent. Before refuting a hypothesis on the grounds of an "exhaustive
    search," confirm your spawn-distance has actually grown enough to justify that claim.

    **If your last few evidence entries for one id are near-duplicates that only changed a step
    count or a number, stop and pivot** (see Example 4): mark that id "stale" (or "refuted" only if
    you're genuinely confident it's false) and open a NEW id naming a specific unexplored direction,
    landmark, or mechanism - don't just keep re-affirming the same restated claim.
8.  Update your plan: a short ordered list (2-5 short steps) of what you intend to do next to test or act on your highest-priority hypothesis.
"""

# `compact`: steps 4, 6, 7 (last sentences) and 8 differ -- concise thought; memory / hypotheses /
# plan only when they change. Everything else, including the hypothesis-writing guidance, is the same.
_HYP_THOUGHT_PROCESS_COMPACT = """
**Your Thought Process:**
1.  Review your long-term memory and hypothesis graph (if any). What do you already believe, and how confident are you?
2.  If the task description names multiple sub-goals in sequence (look for words like "first"/"then"/
    "after"/"using X to Y"/"finally") and you have not already opened a hypothesis for each of them,
    do that now: propose one hypothesis per named sub-goal, in the order they're mentioned, each
    `depends_on` the one(s) named just before it (see Example 5). Use a low starting confidence
    (0.2-0.3) since you haven't verified any of them yet — this is a map of the task's structure to
    fill in with real evidence as you go, not a claim you've confirmed anything.
3.  Analyze the sequence of images AND the Environment-reported position line above. Do you see movement? Have you turned? What is new in your view? Cross-check your visual impression against the real position numbers - if that line says you haven't moved, or that your net displacement over the last several steps is small, trust that over what individual frames seem to suggest (near-identical terrain can still look "new" frame to frame). Does the evidence - visual and positional together - confirm, refute, or leave untouched any active hypothesis?
4.  Formulate a new, concise thought: 1-3 sentences on what you conclude and what you will do next. Do not restate the memory, the hint lines, the hypothesis graph or the frame captions - they are already in front of you.
5.  Decide the single next action to take.
6.  Your long-term memory is what survives beyond the frames you can see, so keep it complete: write it on your first step, and rewrite it in FULL (a concise summary under 200 words) whenever it no longer records everything important - a landmark or object found, a sub-goal completed, a direction or attempt that failed, a change of plan - and whenever the memory line above says it is due. On the other steps do not send it.
7.  Update your hypotheses: propose new hypotheses about the world when you notice something uncertain worth investigating (e.g. "there is likely a village nearby"), and update existing ones (by id) when you gather evidence — raise confidence toward 1.0 when confirmed, lower toward 0.0 when refuted, and mark status "confirmed"/"refuted" once you're sure. Send a hypothesis op only when something actually changes: a new hypothesis, or an existing id whose confidence moves by at least 0.1 or whose status changes. On an update send the id, the fields that changed and a short evidence phrase (at most 15 words) - never a re-statement of an unchanged hypothesis. If nothing changed, do not send hypotheses at all.

    `depends_on` covers TWO kinds of relationship, both worth recording — only list dependency ids
    that already exist or that you are defining in this same response:
    - **Refinement**: a more specific claim about the same object (e.g. "the chest has a diamond"
      depends_on "there is a chest here").
    - **Task-order prerequisite**: a later sub-goal that requires an earlier one first (e.g. "the
      potted cactus is in the first room" depends_on "the trapdoor is the building's entrance",
      because you can't reach the first room without going through the entrance). This is the more
      common case for multi-step task descriptions — see step 2 above and Example 5.

    **One id = one claim about one specific object/location — never bundle two different sub-goals
    into a single hypothesis's statement** (e.g. don't write one hypothesis claiming a building has
    both "a ladder" and "a trapped chest"; give the ladder its own id, and make the chest hypothesis
    `depends_on` it). Bundling erases the exact structure you're supposed to be capturing. Once you've
    physically moved on from a specific candidate (e.g. you've fully searched one particular building
    and it didn't have what you need), mark THAT id "refuted" or "stale" and give the NEXT candidate
    you investigate a NEW id - even if the new candidate matches the same general statement as the
    old one. Do not keep reusing the same id to describe a whole sequence of different physical
    objects; that erases the distinction between them and makes confidence/evidence meaningless (see
    Example 4 below).

    **A hypothesis must say something you don't already know from the task description.** A
    goal-restating placeholder is fine ONLY as the very first-step scaffolding described in step 2
    above (you haven't seen anything yet, so you have nothing more specific to say). Past that first
    step, once you've actually spent time searching, restating the goal verbatim (e.g. "There is a
    polished granite pillar nearby in this forest biome." when the task IS to find a polished granite
    pillar) is not a hypothesis - it's the assignment, and tracking confidence on a fact you were
    already told teaches you nothing. A real hypothesis adds a specific,
    checkable claim beyond the goal text: a direction you're committing to based on the
    Environment-reported position numbers, not a step count (e.g. "not present within the ~60 blocks
    I've covered heading east from spawn - likely further out, or in another direction entirely"); a
    landmark you've actually spotted ("a stone path visible to the northeast may lead to it"); or a
    world-knowledge-based mechanism ("granite pillars are a placed decorative structure, not natural
    forest generation, so it's more likely near a clearing, ruin, or biome edge than deep in dense
    trees"). If you cannot state anything more specific than the task text itself, you don't have
    enough evidence yet to hypothesize - spend the next few steps actually covering new ground (check
    Environment-reported position to confirm you are) rather than resubmitting the restated goal with
    an incremented counter as "evidence."

    **Evidence must cite the ground-truth position, not your own step-count narrative.** "300
    consecutive scans, environment unchanged" is not evidence if Environment-reported position shows
    you're still near your spawn point - that means your last N actions didn't do what you intended,
    not that the object is absent. Before refuting a hypothesis on the grounds of an "exhaustive
    search," confirm your spawn-distance has actually grown enough to justify that claim.

    **If your last few evidence entries for one id are near-duplicates that only changed a step
    count or a number, stop and pivot** (see Example 4): mark that id "stale" (or "refuted" only if
    you're genuinely confident it's false) and open a NEW id naming a specific unexplored direction,
    landmark, or mechanism - don't just keep re-affirming the same restated claim.
8.  Update your plan only when it changes: a short ordered list (2-5 short steps) of what you intend to do next to test or act on your highest-priority hypothesis. If the plan still stands, do not send it.
"""

_HYP_ACTION_REFERENCE = """
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

**Movement Tips for Efficient Exploration:**
- **USE SPRINT!** Combine "forward": 1 with "sprint": 1 for FAST movement when exploring open areas
- **Turn, then move - don't do both every step.** A camera yaw change and "forward" fire in the same
  in-game tick, so pairing a large yaw turn (e.g. 90 degrees) with "forward" on every single step turns
  your path into a tight loop instead of a straight line - each step points you in a new direction before
  you've gone anywhere in the last one. If you want to change direction, spend one step turning
  (camera yaw only, forward=0), then spend several subsequent steps moving straight (forward=1,
  camera=[0,0]) before turning again. Check the player-position deltas across recent frames in your
  history to confirm you're actually covering new ground, not oscillating in place.
- Use "jump": 1 with forward movement to navigate obstacles
- Use camera to look around before deciding where to move
"""

_HYP_RESPONSE_FULL = """
**RESPONSE FORMAT:**
Your response **MUST** be valid JSON with these keys: "thought", "action", "memory_update", "hypotheses", "plan", "testing".
- "thought": your current reasoning and plan (string)
- "action": the action JSON object
- "memory_update": updated long-term memory (string, max 200 words, write the FULL memory not just the delta)
- "hypotheses": a list of hypothesis objects you are proposing or updating this step (can be empty list if none). Each object:
  {{"id": "h1", "kind": "location", "statement": "...", "confidence": 0.6, "status": "active", "depends_on": [], "evidence": "what you just observed"}}
  - "id" is required (reuse an existing id to update it; a new id creates a new hypothesis).
  - All other fields are optional on an update — omit a field to leave it unchanged.
  - "kind" is one of "goal", "location", "mechanism", "state", "other".
  - "status" is one of "active", "confirmed", "refuted", "stale" ("confirmed" is not accepted for a goal until the environment verifies the task).
- "plan": a list of 2-5 short strings describing your next intended steps (can be empty list).
- "testing": the id of the hypothesis this action tests, or null.

**Examples:**

Example 1 - Proposing a hypothesis while exploring:
```json
{{
  "thought": "I see smoke in the distance, possibly a village. I'll head toward it.",
  "action": {{"forward": 1, "sprint": 1, "camera": [0, 15]}},
  "memory_update": "Step 1: Spawned in plains biome. Spotted smoke to the northeast, heading there.",
  "hypotheses": [
    {{"id": "h1", "kind": "location", "statement": "There is a village to the northeast (smoke visible).", "confidence": 0.4, "status": "active", "evidence": "saw smoke rising above the treeline"}}
  ],
  "plan": ["Continue northeast toward the smoke", "Confirm village on arrival", "Look for animal pens or houses"],
  "testing": "h1"
}}
```

Example 2 - Confirming a hypothesis with new evidence:
```json
{{
  "thought": "I can now see houses and a path. This confirms the village.",
  "action": {{"forward": 1}},
  "memory_update": "Confirmed village to the northeast. Approaching main path now.",
  "hypotheses": [
    {{"id": "h1", "confidence": 0.95, "status": "confirmed", "evidence": "houses and a path now visible"}}
  ],
  "plan": ["Enter the village", "Look for animal pen location", "Check for existing fences/gates"]
}}
```

Example 3 - Refuting a hypothesis and pivoting:
```json
{{
  "thought": "The path north is blocked by lava, not a village entrance as I guessed. I should try east.",
  "action": {{"right": 1, "sprint": 1}},
  "memory_update": "North path blocked by lava, not a village. Trying east instead.",
  "hypotheses": [
    {{"id": "h2", "confidence": 0.05, "status": "refuted", "evidence": "path north is a lava pool, no village"}}
  ],
  "plan": ["Head east", "Scan for smoke or paths", "Reassess if nothing found in ~10 steps"]
}}
```

Example 4 - Ruling out one candidate and opening a new id for the next (don't reuse the old id):
```json
{{
  "thought": "I've now fully searched the stone-brick hut (walls, interior, roof) and it has no polished diorite stairs. It's a dead end. I see a different, larger building further east - that's a new, distinct candidate.",
  "action": {{"forward": 1, "sprint": 1}},
  "memory_update": "Searched the first stone-brick hut fully - no stairs, ruled out. Spotted a second, larger building to the east; heading there now as a new candidate.",
  "hypotheses": [
    {{"id": "h1", "status": "refuted", "confidence": 0.05, "evidence": "fully searched interior, walls, and roof of this specific hut; no polished diorite anywhere"}},
    {{"id": "h2", "statement": "The larger building to the east contains the polished diorite stairs.", "confidence": 0.3, "status": "active", "evidence": "new, larger building spotted east of the first (already-ruled-out) hut"}}
  ],
  "plan": ["Approach the second building", "Enter and search it", "If empty, rule it out (h2 -> refuted) and open a new id for the next candidate"]
}}
```

Example 5 - Decomposing a multi-step task description into a dependency chain on your very first step
(do this immediately whenever the task names multiple sub-goals, before you've seen anything):
```json
{{
  "thought": "The task names three sub-goals in order: find the spruce trapdoor entrance, then the potted cactus in the first room, then the fletching table in the back room. I haven't seen any of them yet, but I'll open one hypothesis per sub-goal now and chain them in the stated order so the dependency structure is explicit from the start.",
  "action": {{"camera": [0, 30]}},
  "memory_update": "Step 1: task requires 3 sequential sub-goals (trapdoor entrance -> cactus in first room -> fletching table in back room). Scanning surroundings for the stone building.",
  "hypotheses": [
    {{"id": "h1", "kind": "goal", "statement": "There is a spruce trapdoor entrance to a stone building somewhere nearby.", "confidence": 0.3, "status": "active", "evidence": "stated as the first sub-goal in the task description"}},
    {{"id": "h2", "kind": "goal", "statement": "There is a potted cactus in the first room, reachable once I'm through the trapdoor.", "confidence": 0.2, "status": "active", "depends_on": ["h1"], "evidence": "stated as the second sub-goal; requires entering through h1 first"}},
    {{"id": "h3", "kind": "goal", "statement": "There is a fletching table in a back room, reachable once I've found the cactus room.", "confidence": 0.2, "status": "active", "depends_on": ["h2"], "evidence": "stated as the third sub-goal; requires passing through the cactus room first"}}
  ],
  "plan": ["Locate the stone building with the spruce trapdoor", "Enter through the trapdoor", "Find the potted cactus in the first room", "Proceed to back room and find fletching table"],
  "testing": null
}}
```

Example 6 - Deepening a stale goal-restatement placeholder into a specific hypothesis after real search
(this is the required pivot once a first-step placeholder like h1 above has survived many steps of
searching with no new evidence - use the Environment-reported position numbers, not a step count, to
decide how much ground you've actually covered):
```json
{{
  "thought": "h1 ('there is a polished granite pillar nearby in this forest biome') has had zero new evidence for the last 40 steps, and Environment-reported position shows I'm still only ~35 blocks from spawn despite all that time - I've been circling, not covering ground. Restating 'still no pillar' again would just be the same placeholder with a bigger number. Two things I actually know now: granite pillars are a placed decorative structure, not natural forest generation, so it's more likely near a clearing/ruin/biome edge than deep in unbroken trees; and I have not yet gone further than ~35 blocks in any single direction. I'll retire h1 as stale and commit to a specific, checkable claim instead.",
  "action": {{"camera": [0, 90]}},
  "memory_update": "Spent ~40 steps near spawn without finding the granite pillar (spawn-distance only ~35 blocks despite the step count - was circling). Retired the goal-restatement hypothesis. New theory: pillars are placed structures, likelier near a clearing or biome edge than deep forest. Committing to a sustained push south (unexplored direction) for at least 100 blocks of real spawn-distance before reassessing.",
  "hypotheses": [
    {{"id": "h1", "status": "stale", "confidence": 0.15, "evidence": "40 steps searched but spawn-distance stayed ~35 blocks (per Environment-reported position) - this was circling, not a real negative result; retiring the vague placeholder rather than falsely refuting it"}},
    {{"id": "h2", "statement": "The pillar is a placed decorative structure, more likely near a clearing or this biome's edge than deep in unbroken forest - committing to a sustained push south, unexplored so far.", "confidence": 0.35, "status": "active", "evidence": "world-knowledge: pillars don't generate naturally in dense forest; south is the one compass direction not yet covered per position history"}}
  ],
  "plan": ["Turn to face south (one step, camera only)", "Sprint south in a straight line for several steps, checking Environment-reported spawn-distance grows", "Watch for a clearing, biome transition, or structure", "Reassess only once spawn-distance actually exceeds ~100 blocks in this direction"]
}}
```

**Remember**: Always update memory_update with the FULL current memory (not just new info). Only propose/update hypotheses that are meaningfully new or changed this step — don't repeat unchanged ones. Give each physically distinct candidate object/location its own id (Example 4) rather than folding it into an old id that was about something else. If the task names multiple sub-goals, open the whole chain up front with `depends_on` (Example 5) rather than only describing sub-goals reactively as you happen to see them. A goal-restating placeholder is only acceptable on the step it's first created — once it's survived real search time with no new evidence, retire it and open a more specific id naming a direction, landmark, or mechanism instead (Example 6), using Environment-reported position (not step count) to judge how much ground you've actually covered.
"""

_HYP_RESPONSE_COMPACT = """
**RESPONSE FORMAT:**
Your response **MUST** be exactly one JSON object on a single line - no line breaks, no indentation, no text before or after it. Keys:
- "thought": your concise reasoning and plan (string, 1-3 sentences) - always
- "action": the action JSON object (only the keys you set; omitted keys are 0) - always
- "memory_update": the FULL long-term memory (string, max 200 words) - on your first step and whenever the memory changes or the memory line says it is due; then send the whole memory, never just the delta. No key means "memory unchanged".
- "hypotheses": the hypothesis objects you are proposing or updating THIS step - only when there is one. Each object:
  {{"id": "h1", "kind": "location", "statement": "...", "confidence": 0.6, "status": "active", "depends_on": [], "evidence": "what you just observed"}}
  - "id" is required (reuse an existing id to update it; a new id creates a new hypothesis).
  - On an update send only "id" plus the fields that changed (omitted fields stay as they are) and a short "evidence" phrase.
  - "kind" is one of "goal", "location", "mechanism", "state", "other".
  - "status" is one of "active", "confirmed", "refuted", "stale" ("confirmed" is not accepted for a goal until the environment verifies the task).
- "plan": a list of 2-5 short strings describing your next intended steps - only when the plan changes. No key means "same plan".
- "testing": the id of the hypothesis this action tests - only when it changes; null for plain travel.

**Examples:**

Example 0 - A quiet step: nothing to record, the plan still stands (USE THIS OFTEN!):
{{"thought": "Still crossing the plain toward the smoke; nothing new in view. Keep sprinting.", "action": {{"forward": 1, "sprint": 1}}}}

Example 1 - Proposing a hypothesis while exploring:
{{"thought": "Smoke in the distance, possibly a village. Heading toward it.", "action": {{"forward": 1, "sprint": 1, "camera": [0, 15]}}, "memory_update": "Step 1: Spawned in plains biome. Spotted smoke to the northeast, heading there.", "hypotheses": [{{"id": "h1", "kind": "location", "statement": "There is a village to the northeast (smoke visible).", "confidence": 0.4, "status": "active", "evidence": "smoke above the treeline"}}], "plan": ["Continue northeast toward the smoke", "Confirm village on arrival", "Look for animal pens or houses"], "testing": "h1"}}

Example 2 - Confirming a hypothesis with new evidence:
{{"thought": "Houses and a path are now visible - the village is confirmed. Entering it.", "action": {{"forward": 1}}, "memory_update": "Confirmed village to the northeast. Approaching main path now.", "hypotheses": [{{"id": "h1", "confidence": 0.95, "status": "confirmed", "evidence": "houses and a path visible"}}], "plan": ["Enter the village", "Look for animal pen location", "Check for existing fences/gates"]}}

Example 3 - Refuting a hypothesis and pivoting:
{{"thought": "The path north ends in lava, not a village. Trying east.", "action": {{"right": 1, "sprint": 1}}, "memory_update": "North path blocked by lava, not a village. Trying east instead.", "hypotheses": [{{"id": "h2", "confidence": 0.05, "status": "refuted", "evidence": "north path is a lava pool"}}], "plan": ["Head east", "Scan for smoke or paths", "Reassess if nothing found in ~10 steps"]}}

Example 4 - Ruling out one candidate and opening a new id for the next (don't reuse the old id):
{{"thought": "The stone-brick hut is fully searched and has no polished diorite stairs; the larger building to the east is a new candidate.", "action": {{"forward": 1, "sprint": 1}}, "memory_update": "Searched the first stone-brick hut fully - no stairs, ruled out. Spotted a second, larger building to the east; heading there now as a new candidate.", "hypotheses": [{{"id": "h1", "status": "refuted", "confidence": 0.05, "evidence": "interior, walls and roof searched; no polished diorite"}}, {{"id": "h2", "statement": "The larger building to the east contains the polished diorite stairs.", "confidence": 0.3, "status": "active", "evidence": "larger building spotted east of the ruled-out hut"}}], "plan": ["Approach the second building", "Enter and search it", "If empty, rule it out (h2 -> refuted) and open a new id for the next candidate"]}}

Example 5 - Decomposing a multi-step task description into a dependency chain on your very first step (do this immediately whenever the task names multiple sub-goals, before you've seen anything):
{{"thought": "The task names three sub-goals in order (trapdoor entrance, potted cactus in the first room, fletching table in the back room); I will open one hypothesis per sub-goal, chained in that order, and start scanning.", "action": {{"camera": [0, 30]}}, "memory_update": "Step 1: task requires 3 sequential sub-goals (trapdoor entrance -> cactus in first room -> fletching table in back room). Scanning surroundings for the stone building.", "hypotheses": [{{"id": "h1", "kind": "goal", "statement": "There is a spruce trapdoor entrance to a stone building somewhere nearby.", "confidence": 0.3, "status": "active", "evidence": "first sub-goal in the task description"}}, {{"id": "h2", "kind": "goal", "statement": "There is a potted cactus in the first room, reachable once I'm through the trapdoor.", "confidence": 0.2, "status": "active", "depends_on": ["h1"], "evidence": "second sub-goal; requires h1 first"}}, {{"id": "h3", "kind": "goal", "statement": "There is a fletching table in a back room, reachable once I've found the cactus room.", "confidence": 0.2, "status": "active", "depends_on": ["h2"], "evidence": "third sub-goal; requires h2 first"}}], "plan": ["Locate the stone building with the spruce trapdoor", "Enter through the trapdoor", "Find the potted cactus in the first room", "Proceed to back room and find fletching table"]}}

Example 6 - Deepening a stale goal-restatement placeholder into a specific hypothesis after real search (the required pivot once a first-step placeholder like h1 above has survived many steps of searching with no new evidence - use the Environment-reported position numbers, not a step count, to decide how much ground you've actually covered):
{{"thought": "h1 has had no new evidence for 40 steps and I am still only ~35 blocks from spawn, so I have been circling, not searching. Granite pillars are placed structures, likelier near a clearing or biome edge; I will retire h1 and commit to a sustained push south.", "action": {{"camera": [0, 90]}}, "memory_update": "Spent ~40 steps near spawn without finding the granite pillar (spawn-distance only ~35 blocks despite the step count - was circling). Retired the goal-restatement hypothesis. New theory: pillars are placed structures, likelier near a clearing or biome edge than deep forest. Committing to a sustained push south (unexplored direction) for at least 100 blocks of real spawn-distance before reassessing.", "hypotheses": [{{"id": "h1", "status": "stale", "confidence": 0.15, "evidence": "40 steps but spawn-distance stayed ~35 blocks: circling, not a negative result"}}, {{"id": "h2", "statement": "The pillar is a placed decorative structure, more likely near a clearing or this biome's edge than deep in unbroken forest - committing to a sustained push south, unexplored so far.", "confidence": 0.35, "status": "active", "evidence": "pillars do not generate in dense forest; south not yet covered per position history"}}], "plan": ["Turn to face south (one step, camera only)", "Sprint south in a straight line for several steps, checking Environment-reported spawn-distance grows", "Watch for a clearing, biome transition, or structure", "Reassess only once spawn-distance actually exceeds ~100 blocks in this direction"]}}

**Remember**: Send "memory_update", "hypotheses" and "plan" only on the steps where they change (no key = unchanged), and keep the whole reply on one line. When you do send memory_update, send the FULL current memory (not just new info); write it on the first step, and a memory that does not mention what you have found or completed is stale. Only propose/update hypotheses that are meaningfully new or changed this step — don't repeat unchanged ones. Give each physically distinct candidate object/location its own id (Example 4) rather than folding it into an old id that was about something else. If the task names multiple sub-goals, open the whole chain up front with `depends_on` (Example 5) rather than only describing sub-goals reactively as you happen to see them. A goal-restating placeholder is only acceptable on the step it's first created — once it's survived real search time with no new evidence, retire it and open a more specific id naming a direction, landmark, or mechanism instead (Example 6), using Environment-reported position (not step count) to judge how much ground you've actually covered.
"""

_HYP_ESC_RULE = """
**Important**: Only set ESC=1 when the "Environment-verified task status" line above says the task HAS been verified complete. Your own visual read of a frame is not proof the action worked — trust the environment-verified status, not your impression of the last frame. If it says the task is not yet complete, keep working even if you believe you just succeeded.
"""

HYPOTHESIS_BASE_PROMPT = (_HYP_HEADER + _HYP_THOUGHT_PROCESS_FULL + _HYP_DISCIPLINE
                          + _HYP_ACTION_REFERENCE + _HYP_RESPONSE_FULL + _HYP_ESC_RULE)

HYPOTHESIS_BASE_PROMPT_COMPACT = (_HYP_HEADER + _HYP_THOUGHT_PROCESS_COMPACT + _HYP_DISCIPLINE
                                  + _HYP_ACTION_REFERENCE + _HYP_RESPONSE_COMPACT + _HYP_ESC_RULE)


def _env_verified(milestone_hint: str) -> bool | None:
    """The environment's verification bit as the harness renders it: True once the task
    is verified, False while it is not, None under the no-hint protocol (no line)."""
    text = (milestone_hint or "").strip()
    if not text:
        return None
    return "HAS verified" in text


class HypothesisAgent:
    """LLM agent with an explicit hypothesis DAG + short-horizon plan.

    Mirrors DefaultAgent's public surface (`load_system_prompt`,
    `get_action`, `get_default_action`) so it's a drop-in replacement for
    it. Unlike DefaultAgent, this class does own per-episode mutable state
    (the hypothesis graph + current plan) since that state is what makes
    it a "hypothesis agent" rather than a bag of pure functions — one
    instance should be constructed per episode, same lifetime as a
    DefaultAgent instance is used for today.
    """

    def __init__(
        self,
        action_space: BaseActionSpace,
        provider: BaseLLMProvider,
        context_builder_class: type[HypothesisContextBuilder] = HypothesisContextBuilder,
        model: str = None,
        max_hypotheses_in_prompt: int = 8,
        prompt_layout: str = "legacy",
        response_style: str = "full",
    ) -> None:
        self.action_space = action_space
        self.provider = provider
        self.context_builder_class = context_builder_class
        self.model = model
        self.max_hypotheses_in_prompt = max_hypotheses_in_prompt
        if prompt_layout not in PROMPT_LAYOUTS:
            raise ValueError(f"prompt_layout must be one of {PROMPT_LAYOUTS}, got {prompt_layout!r}")
        self.prompt_layout = prompt_layout
        if response_style not in RESPONSE_STYLES:
            raise ValueError(f"response_style must be one of {RESPONSE_STYLES}, got {response_style!r}")
        self.response_style = response_style
        # For the compact style's memory line (see DefaultAgent._note_memory).
        self._memory_seen: str | None = None
        self._memory_step: int | None = None

        self.graph = HypothesisGraph()
        self.current_plan: list[str] = []
        # Discipline state (experiments/HYPOTHESIS_V2_DESIGN.md): which goal ids are locked
        # after a refused ESC, what is under test since when, and the counters that say how
        # often each rule fired -- written by save_state next to the graph.
        self._locked: set[str] = set()
        self._testing: tuple[str, int, float] | None = None   # (id, since_step, confidence then)
        self._env_verified: bool | None = None                # None under the no-hint protocol
        self._first_response_step: int | None = None
        self.discipline = {
            "goal_confirm_reverted": 0, "locked_raise_capped": 0, "esc_dropped": 0,
            "esc_lock_events": 0, "stale_by_budget": 0,
        }

        logger.info(
            f"HypothesisAgent  action_space={self.action_space.__class__.__name__}  "
            f"provider={self.provider.__class__.__name__}  model={self.model}  "
            f"prompt_layout={self.prompt_layout}  response_style={self.response_style}"
        )

    def load_system_prompt(self, task_desc: str) -> None:
        self.task_desc = task_desc

    def _note_memory(self, long_term_memory: str, current_step: int | None) -> None:
        mem = (long_term_memory or "").strip()
        if mem != self._memory_seen:
            self._memory_seen = mem
            self._memory_step = (current_step - 1) if current_step else None

    def get_action(
        self,
        frame_buffer: list[np.ndarray],
        thought_history: dict,
        action_history: dict,
        current_step: int | None = None,
        return_messages: bool = False,
        return_messages_with_pic: bool = False,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
    ) -> tuple[Any, ...]:
        """Same contract as DefaultAgent.get_action — see mc_agent/agent.py.

        Additionally maintains self.graph / self.current_plan from the
        LLM's "hypotheses"/"plan" response keys before returning.
        """
        logger.info("Processing observation history...")

        base64_images = convert_buffer_to_base64_images(frame_buffer)
        if not base64_images:
            logger.error("No valid frames could be processed.")
            thought, action = self.get_default_action()
            return thought, action, long_term_memory

        self._env_verified = _env_verified(milestone_hint)
        if self._env_verified:
            # The environment has verified the task: nothing is locked any more.
            self._locked.clear()
        flags = {hid: "locked" for hid in self._locked}
        if self._testing and self._testing[0] in self.graph.nodes and current_step is not None:
            flags[self._testing[0]] = (
                f"under test for {current_step - self._testing[1]} steps (budget {TEST_BUDGET_STEPS})"
            )
        hypothesis_summary = self.graph.to_prompt_summary(
            max_items=self.max_hypotheses_in_prompt, flags=flags)
        plan_summary = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(self.current_plan))
        discipline_summary = self._discipline_summary()
        layout = self.prompt_layout
        self._note_memory(long_term_memory, current_step)

        content = [{"type": "text", "text": self.context_builder_class.system_prompt(
            self.task_desc,
            long_term_memory=long_term_memory,
            milestone_hint=milestone_hint,
            camera_hint=camera_hint,
            movement_hint=movement_hint,
            hypothesis_summary=hypothesis_summary,
            plan_summary=plan_summary,
            layout=layout,
            style=self.response_style,
            memory_step=self._memory_step,
            current_step=current_step,
            discipline_summary=discipline_summary,
        ).build()}]
        save_content = copy.deepcopy(content)

        for i, base64_img in enumerate(base64_images):
            frame_step = current_step - (len(base64_images) - 1 - i) if current_step is not None else None
            hist_index = frame_step - 2 if frame_step is not None else None
            if frame_step is not None and frame_step > 1 and hist_index is not None \
                    and hist_index < len(action_history) and hist_index < len(thought_history):
                hist_thought = thought_history[hist_index]
                hist_action = action_history[hist_index]
                frame_text = self.context_builder_class.next_step(
                    images_idx=i,
                    total_images_length=len(base64_images),
                    frame_step=frame_step,
                    hist_action=hist_action,
                    hist_thought=hist_thought,
                    layout=layout,
                ).build()
            else:
                frame_text = self.context_builder_class.next_step(
                    images_idx=i,
                    total_images_length=len(base64_images),
                    frame_step=frame_step,
                    layout=layout,
                ).build()

            content.append({"type": "text", "text": frame_text})
            save_content.append({"type": "text", "text": frame_text})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_img}"}
            })
            save_content.append({
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,..."}
            })

        if layout != "legacy":
            state_text = self.context_builder_class.state_block(
                long_term_memory=long_term_memory,
                milestone_hint=milestone_hint,
                camera_hint=camera_hint,
                movement_hint=movement_hint,
                hypothesis_summary=hypothesis_summary,
                plan_summary=plan_summary,
                style=self.response_style,
                memory_step=self._memory_step,
                current_step=current_step,
                discipline_summary=discipline_summary,
            )
            if state_text:
                content.append({"type": "text", "text": state_text})
                save_content.append({"type": "text", "text": state_text})

        messages = [{"role": "user", "content": content}]
        save_messages = [{"role": "user", "content": save_content}]

        max_json_retries = 3
        for attempt in range(max_json_retries):
            try:
                response_content = self.provider.chat(messages)
                logger.info(f"[HypothesisAgent] Raw LLM response (attempt {attempt + 1}):\n{response_content}")

                action_state = self.action_space.load_action(response_content)
                thought = action_state.think
                memory_update = action_state.memory_update
                action = self.action_space.dump_action_to_dict(action_state)

                self._apply_hypothesis_ops(response_content, current_step or 0)
                action = self._gate_esc(action, current_step or 0)
                break

            except Exception as e:
                if isinstance(e, json.JSONDecodeError):
                    logger.error(f"JSON parsing failed on attempt {attempt + 1}/{max_json_retries}: {e}")
                else:
                    logger.exception(f"Error during LLM call or JSON parsing (attempt {attempt + 1}/{max_json_retries}):")
                logger.error(
                    f"[HypothesisAgent] Response content that failed to parse:\n"
                    f"{response_content if 'response_content' in locals() else '<no response received>'}"
                )

                # A call that ran to the provider's ceiling is a stall, not a transient
                # error, and the retries here are priced for transient errors (a parse
                # failure, a dropped connection). Only CodexProvider raises this: with
                # thinking off the model loops `view_image` on the attached frames until
                # the ceiling (measured 2026-08-18), and a retry loops again -- three
                # ceilings per step is 45 min at the 900 s default. One ceiling, then the
                # no-op the ceiling was priced for.
                if isinstance(e, subprocess.TimeoutExpired):
                    logger.error("Provider call hit its ceiling; not retrying. Using default action.")
                    thought, action = self.get_default_action()
                    memory_update = long_term_memory
                    response_content = "{}"
                    break

                if attempt < max_json_retries - 1:
                    logger.info("Retrying due to error...")
                    continue
                else:
                    logger.error("All retries exhausted. Using default action.")
                    thought, action = self.get_default_action()
                    memory_update = long_term_memory
                    response_content = "{}"

        if return_messages:
            msg_to_return = messages if return_messages_with_pic else save_messages
            return thought, action, memory_update, msg_to_return, response_content
        return thought, action, memory_update

    def _apply_hypothesis_ops(self, response_content: str, step: int) -> None:
        """Best-effort update of the hypothesis graph + plan from the raw
        LLM response text. Failures here never affect the already-decided
        action — a malformed "hypotheses"/"plan" block just means the
        graph doesn't change this step, it does not fail the whole action."""
        try:
            parsed = extract_json_from_response(response_content)
        except Exception as e:
            logger.warning(f"[HypothesisAgent] Could not parse hypotheses/plan block: {e}")
            return

        if self._first_response_step is None:
            self._first_response_step = step

        touched: list[str] = []
        for op in parsed.get("hypotheses", []) or []:
            if not isinstance(op, dict) or not op.get("id"):
                continue
            hid = str(op["id"])
            evidence = op.get("evidence")
            kind = op.get("kind")
            # The prompt's step 2 says the first response opens one hypothesis per named
            # sub-goal; a model that forgets `kind` there still means "goal".
            if kind is None and hid not in self.graph.nodes and step == self._first_response_step:
                kind = "goal"
            try:
                self.graph.add_or_update(
                    id=hid,
                    statement=op.get("statement"),
                    confidence=op.get("confidence"),
                    status=op.get("status"),
                    evidence=[str(evidence)] if evidence else None,
                    step=step,
                    kind=kind,
                )
                touched.append(hid)
                for parent_id in op.get("depends_on", []) or []:
                    self.graph.add_dependency(hid, str(parent_id), step=step)
            except CycleError as e:
                logger.warning(f"[HypothesisAgent] Skipped dependency edge: {e}")
            except Exception as e:
                logger.warning(f"[HypothesisAgent] Skipped malformed hypothesis op {op!r}: {e}")

        self._enforce_discipline(touched, step)

        plan = parsed.get("plan")
        if isinstance(plan, list) and plan:
            self.current_plan = [str(p) for p in plan]

        self._track_testing(parsed.get("testing"), step)

    # -- discipline: the rules the harness holds the graph to ------------------

    def _enforce_discipline(self, touched: list[str], step: int) -> None:
        """Goals are confirmed by the environment; locked goals cannot be raised.

        The rules answer two things the 4-hop trajectories showed (BEHAVIOR §3.3, §3.6):
        goal nodes marked "confirmed" from a visual read (0603: "mined the quartz" after
        one attack tick), and re-confirmation at 1.0 on the very step after the harness
        had demoted them (q35-hyp-0603, steps 99-300, ESC on every one). Each
        intervention is written into the node's evidence so the model sees why the graph
        does not say what it just said.
        """
        for hid in touched:
            node = self.graph.nodes.get(hid)
            if node is None:
                continue
            if node.kind == "goal" and node.status == "confirmed" and self._env_verified is False:
                node.status = "active"
                node.confidence = min(node.confidence, 0.9)
                node.evidence.append(
                    f"[harness, step {step}] reverted to active: only the environment "
                    "confirms goals, and its status says NOT verified"
                )
                self.discipline["goal_confirm_reverted"] += 1
            if hid in self._locked and self._env_verified is not True:
                if node.status == "confirmed" or node.confidence > 0.5:
                    node.status = "active" if node.status == "confirmed" else node.status
                    node.confidence = min(node.confidence, 0.5)
                    node.evidence.append(
                        f"[harness, step {step}] capped at 0.5: locked since ESC was refused; "
                        "re-verify physically before raising this again"
                    )
                    self.discipline["locked_raise_capped"] += 1
            if len(node.evidence) > 8:
                node.evidence = node.evidence[-8:]

    def _track_testing(self, testing: Any, step: int) -> None:
        """Mark a hypothesis stale once it has been 'under test' for TEST_BUDGET_STEPS
        with no change in confidence, and clear the plan that was testing it."""
        tid = str(testing) if isinstance(testing, str) and testing.strip() else None
        if tid and tid not in self.graph.nodes:
            tid = None
        if tid is None:
            # A model that stops naming the test keeps the last one on the clock: silence
            # is not a pivot.
            tid = self._testing[0] if self._testing else None
            if tid is None:
                return
        node = self.graph.nodes.get(tid)
        if node is None or node.status != "active" or node.kind == "goal":
            # Goals are the task's map, not a test that can run out of budget: searching
            # for hop 2 for 40 steps is the job, not perseveration.
            self._testing = None
            return
        if self._testing is None or self._testing[0] != tid or abs(self._testing[2] - node.confidence) >= 0.05:
            self._testing = (tid, step, node.confidence)
            return
        if step - self._testing[1] >= TEST_BUDGET_STEPS:
            node.status = "stale"
            node.evidence.append(
                f"[harness, step {step}] stale: under test for {step - self._testing[1]} steps "
                f"with no change in confidence; test something else, or test this differently"
            )
            node.updated_step = step
            self.current_plan = []
            self.discipline["stale_by_budget"] += 1
            self._testing = None

    def _lock_goals(self, step: int, why: str) -> None:
        """Cap and lock every goal the model believes done. Called when the model tries
        to end the episode while the environment says the task is not verified."""
        self.discipline["esc_lock_events"] += 1
        for node in self.graph.nodes.values():
            # What the model "believed complete": a goal it rated likely, or any
            # confirmed claim about what it has done or carries. Location/mechanism
            # beliefs are not completion claims and are left alone.
            believed_done = (
                (node.kind == "goal" and (node.status == "confirmed" or node.confidence >= 0.5))
                or (node.kind in ("state", "other") and node.status == "confirmed")
            )
            if not believed_done or node.status in ("refuted", "stale"):
                continue
            if node.status == "confirmed":
                node.status = "active"
            node.confidence = min(node.confidence, 0.5)
            node.updated_step = step
            if node.id not in self._locked:
                self._locked.add(node.id)
                node.evidence.append(
                    f"[harness, step {step}] {why}: at least one goal is NOT done; this one is "
                    "capped at 0.5 and locked until the environment verifies the task"
                )
                if len(node.evidence) > 8:
                    node.evidence = node.evidence[-8:]

    def _gate_esc(self, action: dict, step: int) -> dict:
        """Drop ESC while the environment says NOT verified (the harness would refuse it
        anyway), and treat the attempt as the belief error it is: lock the goals.

        Under the no-hint protocol (`_env_verified is None`) ESC passes through: there
        the agent is allowed to end its own episode.
        """
        if not action.get("ESC") or self._env_verified is not False:
            return action
        self.discipline["esc_dropped"] += 1
        self._lock_goals(step, "ESC dropped (environment status: NOT verified)")
        logger.warning(
            f"[HypothesisAgent] step {step}: ESC dropped -- the environment has not verified "
            f"the task; goals locked: {sorted(self._locked)}"
        )
        action = dict(action)
        action["ESC"] = 0
        return action

    def _discipline_summary(self) -> str:
        lines = []
        if self.discipline["esc_dropped"]:
            n = self.discipline["esc_dropped"]
            lines.append(
                f"- You tried to end the episode {n} time(s) while the environment said NOT "
                f"verified; each ESC was dropped. At least one goal is not done."
            )
        if self._locked and self._env_verified is not True:
            lines.append(
                f"- Locked goals (capped at 0.5 until the environment verifies the task): "
                f"{', '.join(sorted(self._locked))}. Re-verify each physically -- an item is "
                f"mined only if it is in your hotbar/inventory."
            )
        if self.discipline["goal_confirm_reverted"]:
            lines.append(
                f"- {self.discipline['goal_confirm_reverted']} 'confirmed' on goals were reverted: "
                f"the environment has not verified the task."
            )
        if self.discipline["stale_by_budget"]:
            lines.append(
                f"- {self.discipline['stale_by_budget']} hypothesis(es) went stale for staying under "
                f"test {TEST_BUDGET_STEPS} steps without a confidence change; the plan was cleared."
            )
        return "\n".join(lines)

    def on_esc_rejected(self, step: int | None = None) -> None:
        """Called by the harness when it ignores a premature ESC because the
        environment has not verified task completion (see eval_benchmark.py).

        Demotes any hypothesis the graph currently considers "confirmed"
        back to "active" with reduced confidence, and records the rejection
        as evidence. Without this, a falsely "confirmed" hypothesis keeps
        getting echoed back into the prompt as settled fact every step
        (see HypothesisGraph.to_prompt_summary), which anchors the LLM into
        repeating the same wrong ESC instead of gathering new evidence."""
        # Normally unreachable now that _gate_esc drops ESC before the harness sees it;
        # kept for a harness that refuses ESC on its own grounds.
        self._lock_goals(step or 0, "ESC was rejected by the environment")

    def get_default_action(self, is_call_failed: bool = True) -> tuple[str, dict]:
        if is_call_failed:
            logger.warning("LLM call failed or returned invalid data. Returning a default 'do nothing' action.")
        default_text = "I am experiencing technical difficulties and will stay still."
        default_action_dict = self.action_space.dump_action_to_dict(self.action_space.load_default_action())
        return default_text, default_action_dict

    def save_state(self, output_dir: str | Path) -> None:
        """Persist the hypothesis graph + current plan for post-hoc analysis.

        Safe to call at the end of an episode; no-op-equivalent counterpart
        does not exist on DefaultAgent, so callers should feature-detect
        with `hasattr(agent, "save_state")` (see eval_benchmark.py).
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.graph.save(out / "hypothesis_graph.json")
        with open(out / "hypothesis_plan.json", "w", encoding="utf-8") as f:
            json.dump({"plan": self.current_plan}, f, ensure_ascii=False, indent=2)
        with open(out / "hypothesis_discipline.json", "w", encoding="utf-8") as f:
            json.dump(
                {**self.discipline, "locked": sorted(self._locked),
                 "testing": list(self._testing) if self._testing else None,
                 "test_budget_steps": TEST_BUDGET_STEPS},
                f, ensure_ascii=False, indent=2,
            )
