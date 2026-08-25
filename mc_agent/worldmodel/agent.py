"""The agent: two kinds of turn over one filesystem.

Ported from MCU-AgentBeats' `mcu_worldmodel/agent.py` minus its GUI/cursor/vision layer
(this benchmark's scenes are navigation/collection/placement; the pixel machinery served
crafting tasks this benchmark does not pose).

The loop, in one paragraph. The harness steps the environment and hands every step to
`observe`, which writes the ground truth into the memory filesystem -- position, events,
a frame -- and never asks the model anything. When the action queue runs dry,
`next_action` fires an **act turn**: Codex is given the current frame, the milestone
checklist, the compiled world model and a view of the belief graph, and writes
`actions.json`, which refills the queue. Every `induction_every` steps the queue is held
and an **induction turn** runs instead: no actions, just a pass over the accumulated
filesystem that rewrites the five world-model documents, settles beliefs acting never
got back to, and re-evaluates whether the current goal is still the right one -- the one
question no act turn ever asks.

What replaces MCU's cursor-in-harness here is pose-in-harness: the closed-loop markers
(`_goto`, `_lookabs`, `_facept`) steer against the measured [STATE] every tick, so a
heading is arithmetic rather than a belief the graph has to carry.
"""
from __future__ import annotations

import io
import math
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from PIL import Image

from mc_agent.worldmodel import prompts
from mc_agent.worldmodel.actions import describe_entry, parse_actions
from mc_agent.worldmodel.discipline import Discipline
from mc_agent.worldmodel.hypotheses import CycleError, HypothesisGraph
from mc_agent.worldmodel.memory import MultimodalMemory
from mc_agent.worldmodel.milestones import (
    MilestoneLedger, gui_open, held_line, hotbar_line, inventory_counts, location,
    vitals,
)
from mc_agent.worldmodel.procedures import act as mk_act, bearing, noop

RETRY_NUDGE = ('Your previous response did not produce a valid ./actions.json. Write one '
               'with the shape {"actions": [{"action": {...}, "repeat": N}]} or '
               '{"actions": [{"procedure": "name", "args": {...}}]}.')


class WorldModelCore:
    """The dual-turn loop. Driven by the adapter in mc_agent/worldmodel_agent.py, which
    owns the harness-facing get_action interface."""

    def __init__(
        self,
        *,
        workspace: str | Path,
        task_text: str,
        ledger: MilestoneLedger,
        codex_turn,
        entry_cap: int = 20,
        repeat_cap: int = 50,
        step_cap: int = 80,
        induction_every: int = 60,
        per_doc_chars: int = 1200,
        analyzer_retries: int = 3,
        max_steps: int = 300,
    ) -> None:
        self.task_text = task_text
        self.ledger = ledger
        self.entry_cap, self.repeat_cap, self.step_cap = entry_cap, repeat_cap, step_cap
        self.induction_every = induction_every
        self.per_doc_chars = per_doc_chars
        self.analyzer_retries = analyzer_retries
        # The episode's hard step budget, surfaced in every turn header: an agent that
        # cannot see the deadline plans a two-visit endgame it has no steps left for.
        self.max_steps = max_steps

        self.memory = MultimodalMemory(workspace)
        self.memory.seed_world_model(task_text)
        self.graph = HypothesisGraph()
        if self.memory.graph_path.exists():
            try:
                self.graph = HypothesisGraph.load(self.memory.graph_path)
                logger.info(f"[wm] resumed {len(self.graph.nodes)} hypotheses")
            except Exception as e:
                logger.warning(f"[wm] could not load hypothesis graph: {e}")
        self.discipline = Discipline(self.graph, ledger)
        self.codex = codex_turn

        # (action, plan-entry index). The index is what lets a log section be written
        # when an entry *finishes*, with the position it actually reached -- logging at
        # planning time made every [STATE] line read moved=0.00 in MCU's first runs.
        self.queue: deque[tuple[dict[str, Any], int]] = deque()
        self.plan: list[str] = []
        self.step = 0
        self.action_num = 0
        self._prev_pos: dict | None = None
        self._cur_pos: dict | None = None
        self._last_frame: str | None = None
        self._pending_events: list[str] = []
        self._plan_entries: list[dict[str, Any]] = []
        self._entry_index: int | None = None
        self._entry_start_pos: dict | None = None
        self._cur_inv: dict[str, int] = {}
        self._entry_start_inv: dict[str, int] = {}
        self._last_health: float | None = None
        self._gui_open = False
        self._log_breaks = 0.0
        self._other_breaks = 0.0
        self._last_break_item = ""
        self._breaks_seen = 0.0
        self._last_induction = 0
        # Act turns since ground truth last moved (a milestone, an inventory change, or
        # >3 blocks of displacement -- displacement counts here where it did not in MCU,
        # because on a navigation benchmark walking IS progress). The early-induction
        # trigger below fires on a stall.
        self._stall_turns = 0
        self._progress_marker: tuple | None = None
        # Circuit breaker for a dead model channel. Smoke run 1 measured the failure
        # mode: the hosted credential vanished mid-run and the loop fired 1,162 codex
        # invocations in the ~160 dead steps that followed (2 turns x 3 retries per
        # step, each failing in ~0.2s). Three consecutive failed act turns now buy a
        # 20-step cooldown in which no model turn (act or induction) is attempted; one
        # probe per cooldown re-tests the channel.
        self._consec_act_failures = 0
        self._act_cooldown_until = 0
        self.turns = {"act": 0, "induction": 0, "act_failed": 0, "induction_silent": 0}
        self.stats: dict[str, Any] = {
            "goto_arrived": 0, "chop_early_stops": 0, "esc_blocked": 0,
            "attack_holds_cut": 0, "facept_centred": 0,
        }
        self.started = False

    # -- lifecycle ---------------------------------------------------------

    def start(self, info: dict, frame: np.ndarray | None) -> None:
        # AGENTS.md is written once. Rewriting it mid-episode would change the agent's
        # standing instructions underneath it, and Codex only reads it at thread start.
        self.codex.write_system_prompt(self._act_prompt())
        self.ledger.reset(info)
        pos = location(info)
        rel = self._save_frame(frame, 0)
        self.memory.write_initial(self.task_text, pos, rel)
        self.memory.append_visited(0, pos)
        self._prev_pos = pos
        self._cur_pos = pos
        self._cur_inv = inventory_counts(info)
        self._entry_start_inv = dict(self._cur_inv)
        self.started = True

    def _act_prompt(self) -> str:
        return prompts.act_prompt(
            task_text=self.task_text,
            progress_block=self.ledger.progress_line() + "\n"
                           + self.ledger.progress_block(),
            graph_summary=self.graph.to_prompt_summary(
                max_items=12, flags=self.discipline.flags(self.step)),
            plan_summary="\n".join(f"{i+1}. {s}" for i, s in enumerate(self.plan)),
            discipline_summary=self.discipline.summary(),
            entry_cap=self.entry_cap, step_cap=self.step_cap,
        )

    # -- observation -------------------------------------------------------

    def _save_frame(self, frame: np.ndarray | None, step: int) -> str | None:
        """Write the current view to disk at whatever resolution the env returned.

        MCU read the full 640x360 render out of info['pov']; this env's HTTP wire has a
        single screenshot channel sized by create_env's obs_size, so the run config, not
        this method, decides how much a saved frame can show (eval_benchmark asks for
        640x360 on the worldmodel arm)."""
        if frame is None:
            return None
        try:
            arr = np.asarray(frame)
            if arr.dtype != np.uint8:
                arr = arr.astype(np.uint8)
            buf = io.BytesIO()
            Image.fromarray(arr).save(buf, format="PNG")
            rel = self.memory.save_frame(step, buf.getvalue())
            self._last_frame = rel
            return rel
        except Exception as e:
            logger.warning(f"[wm] could not save frame at step {step}: {e}")
            return None

    def observe(self, info: dict, step: int, frame: np.ndarray | None) -> None:
        """Record one environment step. Ground truth only -- no model involved."""
        self.step = step
        self._save_frame(frame, step)
        fired = self.ledger.update(info, step)
        if fired:
            self.memory.append_events(step, fired)
            self._pending_events += [f"MILESTONE {f['identity']} verified" for f in fired]
            if self.queue:
                # Ground truth that a milestone just fired changes what the right next
                # action is. Without this the rest of a plan runs to the end first --
                # up to step_cap ticks of an intention the world has already moved past.
                logger.info(f"[wm] milestone verified at step {step}: dropping "
                            f"{len(self.queue)} queued action(s) and re-planning")
                self.queue.clear()
        stats = self.ledger.stat_events(info)
        if stats:
            self.memory.append_events(step, stats)
            self._pending_events += [f"{s['event']} {s['item']} +{s['delta']:g}"
                                     for s in stats]
            # Running counts of blocks BROKEN, which is what the chop macro and the
            # attack-hold refund key on. Wood breaking proves the aim; anything else
            # breaking names what the crosshair is actually on.
            for s in stats:
                if s["event"] != "mine_block":
                    continue
                if "log" in s["item"] or "wood" in s["item"]:
                    self._log_breaks += s["delta"]
                else:
                    self._other_breaks += s["delta"]
                    self._last_break_item = s["item"]

        pos = location(info)
        self._gui_open = gui_open(info)
        hp_raw = info.get("health")
        try:
            hp = float(hp_raw) if hp_raw is not None else None
        except (TypeError, ValueError):
            hp = None
        prev = self._cur_pos
        if prev and pos:
            jump = (abs(pos["x"] - prev["x"]) + abs(pos["y"] - prev["y"])
                    + abs(pos["z"] - prev["z"]))
            if jump > 15 and (hp is None or hp >= 19.0):
                # A death is a position teleport with health restored. It voids the
                # running plan: whatever macro was executing, the world has changed out
                # from under it.
                self.stats["deaths"] = self.stats.get("deaths", 0) + 1
                self.memory.add_note(
                    f"YOU DIED (or were teleported) at ({prev['x']:.0f}, {prev['y']:.0f}, "
                    f"{prev['z']:.0f}) and are now at ({pos['x']:.0f}, {pos['y']:.0f}, "
                    f"{pos['z']:.0f}). Anything you carried dropped at the old position. "
                    f"Re-plan from where you actually are.")
                self.queue.clear()
        if (hp is not None and self._last_health is not None
                and hp - self._last_health <= -3.0):
            self.stats["damage_interrupts"] = self.stats.get("damage_interrupts", 0) + 1
            where = (f"({pos['x']:.0f}, {pos['y']:.0f}, {pos['z']:.0f})" if pos else "?")
            self.memory.add_note(
                f"took {self._last_health - hp:.0f} damage -- health {hp:.0f}/20 at "
                f"{where}. The plan was interrupted; find the danger before continuing.")
            self.queue.clear()
        self._last_health = hp
        self.memory.append_visited(step, pos)
        self._prev_pos = prev
        self._cur_pos = pos
        self._cur_inv = inventory_counts(info)

        # The entry just executed is finished when the next queued action belongs to a
        # different entry (or the queue is empty).
        if self._entry_index is not None:
            nxt = self.queue[0][1] if self.queue else None
            if nxt != self._entry_index:
                self._log_entry_done(self._entry_index)
                self._entry_index = None

    # -- the act turn ------------------------------------------------------

    def next_action(self, info: dict) -> dict[str, Any]:
        """One env action. Fires a model turn only when the queue is dry."""
        if self._due_for_induction():
            self.run_induction(info)
        # A raw attack-hold is cut the moment its block breaks; markers already key on
        # the stat stream, plain steps popped blind would run their full duration past
        # the break with nothing to say so.
        total_breaks = self._log_breaks + self._other_breaks
        if total_breaks > self._breaks_seen:
            self._cut_attack_hold()
        self._breaks_seen = total_breaks
        for _ in range(2):
            while self.queue:
                head, idx = self.queue[0]
                if idx != self._entry_index:
                    self._entry_index = idx
                    self._entry_start_pos = self._cur_pos
                    self._entry_start_inv = dict(self._cur_inv)
                _MARKERS = {"_goto": self._goto_tick, "_lookabs": self._lookabs_tick,
                            "_facept": self._facept_tick, "_chop": self._chop_tick,
                            "_dig": self._dig_tick, "_seq": self._seq_tick}
                kind = next((k for k in _MARKERS if k in head), None)
                if kind is not None:
                    action = _MARKERS[kind](head[kind])
                    if action is None:
                        # A marker finishes *between* observes, so the entry-done log
                        # observe writes on a head change would never see it.
                        self.queue.popleft()
                        nxt = self.queue[0][1] if self.queue else None
                        if nxt != idx:
                            self._log_entry_done(idx)
                            self._entry_index = None
                        continue
                else:
                    action, _ = self.queue.popleft()
                action = self._gate_esc(action)
                return action
            if self.step < self._act_cooldown_until:
                break               # channel cooling down: no model turn this step
            self._act_turn(info)
        # Two turns in a row produced nothing usable (or the channel is cooling
        # down). A no-op costs one tick and the next turn sees the [NOTE].
        self._entry_index = None
        return noop()

    def _gate_esc(self, action: dict[str, Any]) -> dict[str, Any]:
        """Refuse a premature ESC and make it cost what a false claim costs.

        eval_benchmark already ignores an ESC while milestones are unverified, so the
        press could never end the episode early -- but silently eating it teaches the
        agent nothing and (measured on the 4-hop campaigns) the false-completion belief
        then rides the episode as ESC spam. Here the press is treated as the completion
        claim it is: every unverified milestone is run through the claim gate, the goals
        the model believed done are locked at 0.5, and a [NOTE] says so."""
        if not action.get("ESC"):
            return action
        if self.ledger.all_done():
            return action           # a true claim; the harness will accept it
        unverified = [i for i in self.ledger.order if not self.ledger.is_verified(i)]
        self.stats["esc_blocked"] += 1
        note = self.discipline.check_claim({"completed": unverified}, self.step)
        self.memory.add_note(
            f"ESC refused: {len(unverified)} milestone(s) are not verified "
            f"({', '.join(unverified[:6])}). The episode continues."
            + (f" {note}" if note else ""))
        out = dict(action)
        out["ESC"] = 0
        return out

    # -- closed-loop markers ----------------------------------------------

    def _goto_tick(self, gt: dict[str, Any]) -> dict[str, Any] | None:
        """One tick of walking toward a world (x, z), heading recomputed from truth.

        Turn-then-move: a large heading error is corrected standing still, and only
        small corrections ride along with the walk. Three ticks without horizontal
        progress while trying to walk reads as a wall or a drop, and stopping with a
        [NOTE] there beats walking into it for the rest of the entry."""
        pos = self._cur_pos
        if not pos:
            if gt["remaining"] <= 0:
                return None
            gt["remaining"] -= 1
            return mk_act()
        dx, dz = gt["x"] - pos["x"], gt["z"] - pos["z"]
        dist = math.hypot(dx, dz)
        if dist <= gt["within"]:
            self.stats["goto_arrived"] += 1
            return None
        if gt["remaining"] <= 0:
            self.memory.add_note(
                f"go_to ({gt['x']:.1f}, {gt['z']:.1f}) ran out of ticks at "
                f"({pos['x']:.1f}, {pos['z']:.1f}), {dist:.1f} blocks short.")
            return None
        last = gt.get("last")
        moved = (math.hypot(pos["x"] - last[0], pos["z"] - last[1])
                 if last is not None else None)
        gt["last"] = (pos["x"], pos["z"])
        dyaw = ((bearing(pos, gt["x"], gt["z"]) - pos["yaw"] + 180.0) % 360.0) - 180.0
        gt["remaining"] -= 1
        if abs(dyaw) > 20.0:
            gt["stuck"] = 0
            return mk_act(camera=[0.0, max(-30.0, min(30.0, dyaw))])
        if moved is not None and moved < 0.03:
            gt["stuck"] += 1
            if gt["stuck"] >= 3:
                self.memory.add_note(
                    f"go_to ({gt['x']:.1f}, {gt['z']:.1f}) is blocked at "
                    f"({pos['x']:.1f}, {pos['z']:.1f}), {dist:.1f} blocks short -- a "
                    f"wall, pit or tree is in the way. Clear it or route around.")
                return None
        else:
            gt["stuck"] = 0
        return mk_act(forward=1, jump=1, sprint=1,
                      camera=[0.0, max(-8.0, min(8.0, dyaw))])

    def _lookabs_tick(self, la: dict[str, Any]) -> dict[str, Any] | None:
        """One tick of steering the camera to an ABSOLUTE (pitch, yaw), from truth."""
        pos = self._cur_pos
        if la["remaining"] <= 0:
            if pos is not None:
                self.memory.add_note(
                    f"look_abs ran out of ticks at pitch {pos['pitch']:.0f} yaw "
                    f"{pos['yaw']:.0f} (target {la.get('pitch')}, {la.get('yaw')}).")
            return None
        la["remaining"] -= 1
        if pos is None:
            return mk_act()
        dp = (float(la["pitch"]) - pos["pitch"]) if la.get("pitch") is not None else 0.0
        dy = ((float(la["yaw"]) - pos["yaw"] + 180.0) % 360.0 - 180.0
              ) if la.get("yaw") is not None else 0.0
        if abs(dp) <= 2.0 and abs(dy) <= 2.0:
            return None
        return mk_act(camera=[max(-30.0, min(30.0, dp)), max(-30.0, min(30.0, dy))])

    def _facept_tick(self, fp: dict[str, Any]) -> dict[str, Any] | None:
        """One tick of steering the crosshair onto a world (x, y, z), from truth.

        The run-time form of MCU's plan-time look_at: the target pitch/yaw are re-derived
        from the CURRENT position every tick, so the aim is right no matter where the
        preceding entries left the player. Aims from the eye (feet + 1.62)."""
        pos = self._cur_pos
        if fp["remaining"] <= 0:
            if pos is not None:
                self.memory.add_note(
                    f"face_point ({fp['x']:.1f}, {fp['y']:.1f}, {fp['z']:.1f}) ran out "
                    f"of ticks at pitch {pos['pitch']:.0f} yaw {pos['yaw']:.0f}.")
            return None
        fp["remaining"] -= 1
        if pos is None:
            return mk_act()
        dx = fp["x"] - pos["x"]
        dy = fp["y"] - (pos["y"] + 1.62)
        dz = fp["z"] - pos["z"]
        horiz = math.hypot(dx, dz)
        yaw_target = bearing(pos, fp["x"], fp["z"]) if horiz > 1e-6 else pos["yaw"]
        pitch_target = (math.degrees(-math.atan2(dy, horiz)) if horiz > 1e-6
                        else (90.0 if dy < 0 else -90.0))
        dyaw = ((yaw_target - pos["yaw"] + 180.0) % 360.0) - 180.0
        dpitch = max(-90.0, min(90.0, pitch_target)) - pos["pitch"]
        if abs(dpitch) <= 2.0 and abs(dyaw) <= 2.0:
            self.stats["facept_centred"] += 1
            return None
        return mk_act(camera=[max(-30.0, min(30.0, dpitch)),
                              max(-30.0, min(30.0, dyaw))])

    def _chop_tick(self, ch: dict[str, Any]) -> dict[str, Any] | None:
        """One tick of attack, ending early the moment wood actually breaks.

        Keyed on the `mine_block` statistic, not the inventory: the block breaking is
        the instant the aim is proven. The inventory count is kept as a second trigger
        for a drop from an earlier miss rolling in mid-chop."""
        if ch.get("base") is None:
            ch["base"] = {k: v for k, v in self._cur_inv.items()
                          if "log" in k or "wood" in k}
            ch["base_breaks"] = self._log_breaks
            ch["base_other"] = self._other_breaks
            ch["used"] = 0
        broken = self._log_breaks - ch["base_breaks"]
        if ch["until"]:
            gained = sum(v - ch["base"].get(k, 0)
                         for k, v in self._cur_inv.items()
                         if ("log" in k or "wood" in k) and v > ch["base"].get(k, 0))
            if max(broken, gained) >= ch["until"]:
                self.stats["chop_early_stops"] += 1
                return None
        # Miss-fast: two non-wood breaks with no wood yet means the crosshair is on
        # leaves/dirt; 75 ticks with nothing breaking at all means out of range or aimed
        # at sky. Ending there turns a 180-tick miss into a <=75-tick answer.
        if broken == 0:
            wrong = self._other_breaks - ch["base_other"]
            if wrong >= 2:
                self.stats["chop_wrong_target"] = (
                    self.stats.get("chop_wrong_target", 0) + 1)
                self.memory.add_note(
                    f"chop stopped early: breaking {self._last_break_item}, not wood. "
                    f"Re-aim at a trunk face.")
                return None
            if ch["used"] >= 75:
                self.stats["chop_nothing_broke"] = (
                    self.stats.get("chop_nothing_broke", 0) + 1)
                self.memory.add_note(
                    "chop stopped early: 75 ticks and nothing broke -- the block is out "
                    "of reach or the crosshair is on sky. Get within ~3 blocks of the "
                    "trunk and centre a bark face before chopping again.")
                return None
        if ch["remaining"] <= 0:
            return None
        ch["remaining"] -= 1
        ch["used"] += 1
        return mk_act(attack=1)

    def _dig_tick(self, dg: dict[str, Any]) -> dict[str, Any] | None:
        """One tick of digging, ending when the target depth is reached."""
        y = (self._cur_pos or {}).get("y")
        if dg["until_y"] is not None and y is not None and y <= dg["until_y"]:
            self.stats["dig_reached_depth"] = (
                self.stats.get("dig_reached_depth", 0) + 1)
            return None
        if dg["remaining"] <= 0:
            return None
        dg["remaining"] -= 1
        return mk_act(attack=1)

    def _seq_tick(self, sq: dict[str, Any]) -> dict[str, Any] | None:
        """Play out a fixed sequence. `watch` is the hook MCU's ore sentinel hung off;
        no frame-watcher is registered in this port, so it is carried, not consulted."""
        if sq["i"] >= len(sq["steps"]):
            return None
        action = sq["steps"][sq["i"]]
        sq["i"] += 1
        return action

    def _cut_attack_hold(self) -> None:
        """Refund the rest of a raw attack-hold entry once a block has broken.

        Only pure holds are cut -- attack with nothing else pressed -- only while that
        entry is the one running, and only when at least 10 such ticks remain, so short
        bursts and attack-while-walking steps are untouched."""
        if not self.queue:
            return
        head, idx = self.queue[0]
        if idx != self._entry_index:
            return          # the break belongs to the entry that just finished

        def _is_hold(a: dict) -> bool:
            if any(k.startswith("_") for k in a):
                return False
            if not a.get("attack"):
                return False
            cam = a.get("camera", [0, 0])
            try:
                if any(abs(float(c)) > 0.01 for c in cam):
                    return False
            except (TypeError, ValueError):
                return False
            other = ("forward", "back", "left", "right", "jump", "sneak", "sprint",
                     "use", "drop", "inventory", "pickItem", "swapHands", "ESC")
            if any(a.get(k) for k in other):
                return False
            return not any(a.get(f"hotbar.{n}") for n in range(1, 10))

        if not _is_hold(head):
            return
        run = 0
        for a, i in self.queue:
            if i != idx or not _is_hold(a):
                break
            run += 1
        if run < 10:
            return
        for _ in range(run):
            self.queue.popleft()
        self.stats["attack_holds_cut"] += 1
        self.memory.add_note(
            f"attack-hold entry cut short at step {self.step}: a block broke "
            f"({self._last_break_item or 'wood'}), {run} leftover attack ticks "
            f"refunded. To mine several blocks in a row use mine_forward/stair_down.")

    # -- turns -------------------------------------------------------------

    def _act_turn(self, info: dict) -> None:
        self.turns["act"] += 1
        pos = self._cur_pos or {}
        marker = (len(self.ledger.achieved), tuple(sorted(self._cur_inv.items())),
                  (round(pos.get("x", 0) / 3.0), round(pos.get("z", 0) / 3.0)))
        if marker != self._progress_marker:
            self._progress_marker = marker
            self._stall_turns = 0
        else:
            self._stall_turns += 1

        prompt = self._turn_prompt(info)
        images = [self.memory.root / self._last_frame] if self._last_frame else []
        before = self.memory.snapshot_harness_files()
        result = {"ok": False}
        for attempt in range(self.analyzer_retries):
            result = self.codex.run(prompt if attempt == 0 else RETRY_NUDGE, images)
            if result.get("ok"):
                break
            logger.warning(f"[wm] act turn attempt {attempt+1} produced no actions.json")
        for t in self.memory.assert_harness_files_intact(before):
            self.memory.add_note(f"harness-owned file was modified and is not yours to "
                                 f"write: {t}")

        briefing, plan_text = self.codex.split_briefing(result.get("message", ""))
        self.memory.set_plan(plan_text, briefing)
        self.plan = [ln.strip("-* ").strip()
                     for ln in plan_text.splitlines() if ln.strip()][:5]

        outs = self.codex.read_outputs()
        for err in outs["errors"]:
            self.memory.add_note(err)
        self._apply_ops(outs.get("hypotheses_ops"))
        note = self.discipline.check_claim(outs.get("claim"), self.step)
        if note:
            self.memory.add_note(note)

        if not result.get("ok"):
            self.turns["act_failed"] += 1
            self._consec_act_failures += 1
            if self._consec_act_failures >= 3:
                self._act_cooldown_until = self.step + 20
                self.stats["model_cooldowns"] = self.stats.get("model_cooldowns", 0) + 1
                logger.warning(
                    f"[wm] {self._consec_act_failures} consecutive act turns produced "
                    f"nothing; pausing model turns until step {self._act_cooldown_until}")
            self.memory.add_note("no valid actions.json this turn; one no-op was executed")
            return
        self._consec_act_failures = 0
        plan = parse_actions(result["actions_json"], entry_cap=self.entry_cap,
                             repeat_cap=self.repeat_cap, step_cap=self.step_cap,
                             info=info)
        for n in plan.notes:
            self.memory.add_note(n)
        # Rebuild the (action, entry index) pairing that parse_actions flattened away.
        self._plan_entries = list(plan.entries)
        pairs: list[tuple[dict[str, Any], int]] = []
        cursor = 0
        for i, entry in enumerate(plan.entries):
            n = (entry.get("items", entry["steps"]) if "procedure" in entry
                 else entry["repeat"])
            for _ in range(n):
                if cursor < len(plan.steps):
                    pairs.append((plan.steps[cursor], i))
                    cursor += 1
        self.queue.extend(pairs)
        self._entry_index = None

    def _turn_prompt(self, info: dict) -> str:
        """The per-turn user message. The standing instructions live in AGENTS.md; this
        carries only what changed -- which is what makes a resumed thread cheap."""
        inv = inventory_counts(info)
        inv_line = ", ".join(f"{k}x{v}" for k, v in sorted(inv.items())[:24]) or "empty"
        pos = location(info)
        pos_line = (f"pos=({pos['x']:.1f}, {pos['y']:.1f}, {pos['z']:.1f}) "
                    f"pitch={pos['pitch']:.0f} yaw={pos['yaw']:.0f}") if pos else "unknown"
        wm = self.memory.world_model_summary(self.per_doc_chars)
        notices = self.discipline.summary()
        return (
            f"Step {self.step}/{self.max_steps} -- "
            f"{max(0, self.max_steps - self.step)} steps remain. "
            f"{self.ledger.progress_line()}\n\n"
            f"Milestones:\n{self.ledger.progress_block()}\n\n"
            f"[STATE] {pos_line}\n"
            f"Vitals: {vitals(info)}\n"
            f"Inventory: {inv_line}\n"
            f"Hotbar: {hotbar_line(info)}\n"
            f"Held: {held_line(info)}\n"
            f"GUI open: {gui_open(info)}\n\n"
            f"Your compiled world model:\n{wm}\n\n"
            f"Your hypothesis graph (a view):\n"
            f"{self.graph.to_prompt_summary(12, self.discipline.flags(self.step)) or '(empty)'}\n\n"
            f"{('Harness notices:' + chr(10) + notices + chr(10) + chr(10)) if notices else ''}"
            f"The current view is attached. `logs.txt` holds everything before it.\n"
            f"Write ./actions.json (and optionally ./hypotheses_ops.json, ./claim.json)."
        )

    def _log_entry_done(self, index: int) -> None:
        """Write one log section for a plan entry that has just finished executing."""
        if not (0 <= index < len(self._plan_entries)):
            return
        self.action_num += 1
        self.memory.write_action(
            action_num=self.action_num, step=self.step,
            entry_desc=describe_entry(self._plan_entries[index]),
            pos=self._cur_pos, prev_pos=self._entry_start_pos,
            frame=self._last_frame,
            plan_step=f"{index + 1}/{len(self._plan_entries)}",
            verified=f"{len(self.ledger.achieved)}/{len(self.ledger.cfg)} verified",
            events=self._pending_events,
            inventory_delta=self._inventory_delta(),
            # The [GUI] feedback line, present on this sandbox (isGuiOpen verified by
            # probe): a grep over the log can tell whether a toggle actually opened a
            # screen, without which every GUI attempt is re-tested by hand.
            gui_open=self._gui_open,
        )
        self._pending_events = []

    def _inventory_delta(self) -> str:
        """What the finished entry changed in the inventory, as a signed list. Empty when
        nothing moved -- and an empty [INV] after a collect attempt is itself the finding."""
        bits = []
        for item in sorted(set(self._entry_start_inv) | set(self._cur_inv)):
            d = self._cur_inv.get(item, 0) - self._entry_start_inv.get(item, 0)
            if d:
                bits.append(f"{item} {d:+d}")
        return ", ".join(bits)

    # -- belief ops --------------------------------------------------------

    def _apply_ops(self, parsed: dict[str, Any] | None) -> None:
        """Fold one turn's hypothesis ops into the graph, then let the warden run.

        Every failure here is contained: a belief-bookkeeping mistake costing the
        episode its next plan would be a far worse failure than the mistake itself."""
        if not isinstance(parsed, dict):
            self.discipline.enforce([], self.step)
            self._persist()
            return
        touched: list[str] = []
        for op in parsed.get("hypotheses") or []:
            if not isinstance(op, dict) or not op.get("id"):
                continue
            hid = str(op["id"])
            ev = op.get("evidence")
            try:
                self.graph.add_or_update(
                    id=hid, statement=op.get("statement"),
                    confidence=op.get("confidence"), status=op.get("status"),
                    kind=op.get("kind"),
                    evidence=[ev] if isinstance(ev, str) and ev.strip()
                             else (ev if isinstance(ev, list) else None),
                    step=self.step,
                )
                touched.append(hid)
            except Exception as e:
                logger.warning(f"[wm] bad hypothesis op {hid!r}: {e}")
                continue
            for parent in op.get("depends_on") or []:
                try:
                    self.graph.add_dependency(hid, str(parent), step=self.step)
                except CycleError as e:
                    self.memory.add_note(f"dependency rejected: {e}")
                except Exception as e:
                    logger.warning(f"[wm] bad dependency {hid}->{parent}: {e}")

        note = self.discipline.track_testing(parsed.get("testing"), self.step)
        if note:
            self.memory.add_note(note)
            self.plan = []          # the budget clears the plan, as the prompt promises
        self.discipline.enforce(touched, self.step)
        self._persist()

    def _persist(self) -> None:
        self.graph.save(self.memory.graph_path)
        self.graph.write_markdown(self.memory.root / "hypotheses")

    # -- the induction turn ------------------------------------------------

    def _due_for_induction(self) -> bool:
        if self.induction_every <= 0:
            return False
        if self.step < self._act_cooldown_until:
            # A dead channel fails induction passes exactly as fast as act turns --
            # run 1 burned six silent inductions in its dead tail. Postponed, not
            # skipped: the cadence check below re-fires once the cooldown lifts.
            return False
        if self.step - self._last_induction >= self.induction_every:
            return True
        # Early trigger on a stall: three act turns with no milestone, no inventory
        # change and no displacement is this benchmark's spinning-in-place signature
        # (MCU used twelve turns against a 20x step budget). The step floor keeps a
        # stalled agent from compiling on every turn thereafter.
        return (self._stall_turns >= 3
                and self.step - self._last_induction >= max(20, self.induction_every // 2))

    def run_induction(self, info: dict) -> None:
        """Rewrite the compiled world model from the accumulated filesystem.

        Produces no actions on purpose. The queue is left alone; whatever was mid-plan
        resumes afterwards, because interrupting a walk to think is fine but forgetting
        where you were walking is not."""
        self.turns["induction"] += 1
        self._last_induction = self.step
        self._stall_turns = 0
        logger.info(f"[wm] induction turn {self.turns['induction']} at step {self.step}")

        prompt = prompts.induction_prompt(
            task_text=self.task_text,
            progress_block=(
                f"Step {self.step}/{self.max_steps} -- "
                f"{max(0, self.max_steps - self.step)} steps remain.\n"
                + self.ledger.progress_line() + "\n" + self.ledger.progress_block()),
            per_doc_chars=self.per_doc_chars,
        )
        before = self.memory.snapshot_harness_files()
        # The five documents this pass exists to rewrite, sampled before and after: an
        # induction turn writes no actions.json by design, so the backend's usual
        # success signal says nothing here, and a pass that produced nothing at all
        # looks exactly like one that worked.
        docs = sorted((self.memory.root / "world_model").glob("*.md"))
        stamps = {p: p.stat().st_mtime_ns for p in docs}
        images = [self.memory.root / self._last_frame] if self._last_frame else []
        result = self.codex.run(prompt, images, expect_actions=False)
        touched = sum(1 for p, t in stamps.items()
                      if not p.exists() or p.stat().st_mtime_ns != t)
        touched += sum(1 for p in (self.memory.root / "world_model").glob("*.md")
                       if p not in stamps)
        if not touched:
            self.turns["induction_silent"] += 1
            logger.warning(
                f"[wm] induction turn {self.turns['induction']} at step {self.step} "
                f"rewrote none of the {len(docs)} world model documents")
            self.memory.add_note(
                f"induction turn {self.turns['induction']} at step {self.step} left "
                f"world_model/ unchanged")
        for t in self.memory.assert_harness_files_intact(before):
            self.memory.add_note(f"harness-owned file was modified during induction: {t}")

        outs = self.codex.read_outputs()
        self._apply_ops(outs.get("hypotheses_ops"))
        summary = (result.get("message") or "").strip()
        if summary:
            self.memory.set_plan(self.memory._plan or "", f"[INDUCTION] {summary[:1200]}")
        # An induction turn must not leave actions behind: the file is the act turn's
        # channel, and a stale one here would execute unreviewed on the next dequeue.
        (self.memory.root / "actions.json").unlink(missing_ok=True)

    # -- reporting ---------------------------------------------------------

    def report(self) -> dict[str, Any]:
        return {
            "task": self.task_text,
            "steps": self.step,
            "turns": dict(self.turns),
            "milestones": self.ledger.summary(),
            "hypotheses": {
                "n": len(self.graph.nodes),
                "by_kind": self.graph.counts_by_kind(),
                "noop_updates": self.graph.noop_updates,
            },
            "discipline": dict(self.discipline.counters),
            "stats": {k: v for k, v in self.stats.items() if v},
        }
