from __future__ import annotations

import base64
import io
import json
import math
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _inventory_count(state: Dict[str, Any], item: str) -> int:
    """Get the count of an item in the inventory from state."""
    inventory = state.get("inventory", {})
    if isinstance(inventory, dict):
        return int(inventory.get(item, 0))
    return 0


def _to_vec3(v: Any) -> Tuple[float, float, float]:
    """Convert a value to (x, y, z) tuple."""
    if isinstance(v, dict):
        return (float(v.get("x", 0)), float(v.get("y", 0)), float(v.get("z", 0)))
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return (float(v[0]), float(v[1]), float(v[2]))
    return (0.0, 0.0, 0.0)


def _add_vec3(a: Tuple[float, ...], b: Tuple[float, ...]) -> Tuple[float, float, float]:
    """Add two 3D vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """Calculate Euclidean distance between two 3D points."""
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2 + (a[2] - b[2])**2)


def evaluate_milestone_rule(
    rule: Dict[str, Any],
    state: Dict[str, Any],
    coordinate_origin: Any = None,
) -> bool:
    """Evaluate one milestone rule against a merged simulator state dict."""
    rule_type = rule["type"]
    params = rule["params"]
    coordinate_frame = str(params.get("coordinate_frame", ""))

    origin = _to_vec3(coordinate_origin) if coordinate_origin else (0.0, 0.0, 0.0)

    if rule_type == "inventory_has":
        return _inventory_count(state, params["item"]) >= int(params["min_count"])

    if rule_type == "position_inside_box":
        player_pos = state.get("player_pos", {})
        pos = _to_vec3(player_pos)
        if coordinate_frame == "spawn_relative":
            pos = _add_vec3(pos, (-origin[0], -origin[1], -origin[2]))
        min_vec = _to_vec3(params["min"])
        max_vec = _to_vec3(params["max"])
        return (
            min_vec[0] <= pos[0] <= max_vec[0]
            and min_vec[1] <= pos[1] <= max_vec[1]
            and min_vec[2] <= pos[2] <= max_vec[2]
        )

    if rule_type == "position_near_with_facing":
        player_pos = state.get("player_pos", {})
        pos = _to_vec3(player_pos)
        target = _to_vec3(params["target"])
        if coordinate_frame == "spawn_relative":
            target = _add_vec3(target, origin)
        max_dist = float(params.get("max_distance", 5.0))
        # Distance check
        if _distance(pos, target) > max_dist:
            return False
        # Facing check: verify the player is looking toward the target
        facing_tolerance = float(params.get("facing_tolerance", 360.0))
        if facing_tolerance < 360.0:
            # player_pos dict may contain yaw (horizontal, degrees) and pitch (vertical, degrees)
            # Minecraft yaw: 0=south, -90/270=east, 90/-270=west, 180/-180=north
            player_pos_dict = state.get("player_pos", {})
            yaw_deg = float(player_pos_dict.get("yaw", 0.0))
            # Direction vector from player to target (horizontal plane only)
            dx = target[0] - pos[0]
            dz = target[2] - pos[2]
            if abs(dx) < 1e-6 and abs(dz) < 1e-6:
                # Player is standing exactly on the target — accept any facing
                return True
            # Expected yaw: atan2(-dx, dz) gives Minecraft-convention yaw in radians
            expected_yaw_deg = math.degrees(math.atan2(-dx, dz))
            # Normalise both angles to [-180, 180]
            diff = (yaw_deg - expected_yaw_deg + 180.0) % 360.0 - 180.0
            if abs(diff) > facing_tolerance / 2.0:
                return False
        return True

    if rule_type == "count_in_box_at_least":
        kind = params["kind"]  # "block" or "mob"
        obj_name = params["object"]
        min_count = int(params["min_count"])
        min_vec = _to_vec3(params["min"])
        max_vec = _to_vec3(params["max"])

        if coordinate_frame == "spawn_relative":
            min_vec = _add_vec3(min_vec, origin)
            max_vec = _add_vec3(max_vec, origin)

        if kind == "block":
            voxels = state.get("voxels", [])
            count = 0
            for voxel in voxels:
                v_pos = _to_vec3(voxel.get("pos", [0, 0, 0]))
                v_name = voxel.get("name", "")
                if v_name == obj_name or v_name.endswith(f":{obj_name}"):
                    if (min_vec[0] <= v_pos[0] <= max_vec[0]
                        and min_vec[1] <= v_pos[1] <= max_vec[1]
                        and min_vec[2] <= v_pos[2] <= max_vec[2]):
                        count += 1
            return count >= min_count

        if kind == "mob":
            mobs = state.get("mobs", [])
            count = 0
            for mob in mobs:
                m_pos = _to_vec3(mob.get("pos", [0, 0, 0]))
                m_name = mob.get("name", "")
                if m_name == obj_name:
                    if (min_vec[0] <= m_pos[0] <= max_vec[0]
                        and min_vec[1] <= m_pos[1] <= max_vec[1]
                        and min_vec[2] <= m_pos[2] <= max_vec[2]):
                        count += 1
            return count >= min_count

    if rule_type == "count_in_box_at_most":
        kind = params["kind"]  # "block" or "mob"
        obj_name = params["object"]
        max_count = int(params["max_count"])
        min_vec = _to_vec3(params["min"])
        max_vec = _to_vec3(params["max"])

        if coordinate_frame == "spawn_relative":
            min_vec = _add_vec3(min_vec, origin)
            max_vec = _add_vec3(max_vec, origin)

        if kind == "block":
            voxels = state.get("voxels", [])
            count = 0
            for voxel in voxels:
                v_pos = _to_vec3(voxel.get("pos", [0, 0, 0]))
                v_name = voxel.get("name", "")
                if v_name == obj_name or v_name.endswith(f":{obj_name}"):
                    if (min_vec[0] <= v_pos[0] <= max_vec[0]
                        and min_vec[1] <= v_pos[1] <= max_vec[1]
                        and min_vec[2] <= v_pos[2] <= max_vec[2]):
                        count += 1
            return count <= max_count

        if kind == "mob":
            mobs = state.get("mobs", [])
            count = 0
            for mob in mobs:
                m_pos = _to_vec3(mob.get("pos", [0, 0, 0]))
                m_name = mob.get("name", "")
                if m_name == obj_name:
                    if (min_vec[0] <= m_pos[0] <= max_vec[0]
                        and min_vec[1] <= m_pos[1] <= max_vec[1]
                        and min_vec[2] <= m_pos[2] <= max_vec[2]):
                        count += 1
            return count <= max_count

    return False


def attach_judge_queries_to_action(
    action: Dict[str, Any],
    milestone_spec: Dict[str, Any],
    coordinate_origin: Any = None,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Inject voxel and mob query boxes into the action dict.

    The server only populates info["voxels"] and info["mobs"] when the
    corresponding query box is present in the step action.

    Query boxes are expressed in PLAYER-RELATIVE coordinates (as required
    by the Minecraft simulator), so the current player position from *state*
    is needed for the conversion.
    """
    state = state or {}
    result = dict(action)

    origin = _to_vec3(coordinate_origin) if coordinate_origin else (0.0, 0.0, 0.0)
    player_pos = _to_vec3(state.get("player_pos", {}))

    voxel_boxes: List[Dict[str, Any]] = []
    mob_boxes: List[Dict[str, Any]] = []

    milestones = milestone_spec.get("milestones", [])
    for milestone in milestones:
        for rule in milestone.get("rules", []):
            rule_type = rule.get("type", "")
            params = rule.get("params", {})
            coordinate_frame = str(params.get("coordinate_frame", ""))

            if rule_type in ("count_in_box_at_least", "count_in_box_at_most", "position_inside_box"):
                min_vec = _to_vec3(params.get("min", [0, 0, 0]))
                max_vec = _to_vec3(params.get("max", [0, 0, 0]))

                if coordinate_frame == "spawn_relative":
                    min_vec = _add_vec3(min_vec, origin)
                    max_vec = _add_vec3(max_vec, origin)

                box = {
                    "min": [min_vec[0] - player_pos[0], min_vec[1] - player_pos[1], min_vec[2] - player_pos[2]],
                    "max": [max_vec[0] - player_pos[0], max_vec[1] - player_pos[1], max_vec[2] - player_pos[2]],
                }

                if rule_type in ("count_in_box_at_least", "count_in_box_at_most"):
                    kind = params.get("kind", "")
                    if kind == "block":
                        voxel_boxes.append(box)
                    elif kind == "mob":
                        mob_boxes.append(box)
                elif rule_type == "position_inside_box":
                    voxel_boxes.append(box)

    if voxel_boxes:
        result["voxel_query"] = {"boxes": voxel_boxes}
    if mob_boxes:
        result["mob_query"] = {"boxes": mob_boxes}

    return result


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from LLM output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_json_object(text: str) -> Optional[dict]:
    """
    Robustly extract the first top-level JSON object from LLM output.

    Handles:
    - Pure JSON response (starts with {)
    - JSON wrapped in ```json ... ``` fences
    - JSON preceded/followed by explanation text
    - Trailing commas via lenient cleanup
    """
    text = strip_thinking(text)

    fence_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    candidates = []
    if fence_match:
        candidates.append(fence_match.group(1).strip())
    candidates.append(text.strip())

    for raw in candidates:
        result = _extract_brace_object(raw)
        if result is not None:
            return result

    return None


def _extract_brace_object(text: str) -> Optional[dict]:
    """Find the first complete {...} object in text and parse it as JSON."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    end = -1
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        return None

    raw = text[start: end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _to_scalar(value: Any) -> Any:
    return value.item() if hasattr(value, "item") else value


def _is_number(value: Any) -> bool:
    value = _to_scalar(value)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(_is_number(v) for v in value)


def _is_int_like(value: Any) -> bool:
    value = _to_scalar(value)
    return _is_number(value) and float(value).is_integer()


def _is_positive_int_like(value: Any) -> bool:
    return _is_int_like(value) and int(float(_to_scalar(value))) >= 1


def _is_non_negative_int_like(value: Any) -> bool:
    return _is_int_like(value) and int(float(_to_scalar(value))) >= 0


def _is_integer_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(_is_int_like(v) for v in value)


def _validate_box_params(params: Dict[str, Any]) -> bool:
    if params.get("coordinate_frame") != "spawn_relative":
        return False
    if not _is_integer_vec3(params.get("min")) or not _is_integer_vec3(params.get("max")):
        return False
    return all(params["min"][i] <= params["max"][i] for i in range(3))


def validate_scene_design(data: Optional[dict]) -> bool:
    """Check that the scene design JSON has all required fields."""
    if not isinstance(data, dict):
        return False
    required = ["scene_name", "task_text", "atomic_tasks_ordered", "commands"]
    return all(k in data for k in required)


def validate_reasoning_graph(data: Optional[dict]) -> bool:
    """Check that the reasoning graph JSON has nodes and edges."""
    if not isinstance(data, dict):
        return False
    return "nodes" in data and "edges" in data


def validate_milestones(data: Optional[dict], ordered_tasks: List[str]) -> bool:
    """Check that milestone JSON follows the required online-judge schema.

    Every milestone must have at least one rule — empty ``"rules": []`` is not valid.

    Supported rule types:
      - inventory_has
      - position_near_with_facing  (preferred for find/locate tasks)
      - position_inside_box
      - count_in_box_at_least      (kind="block"|"mob")
      - count_in_box_at_most       (kind="block"|"mob")
    """
    if not isinstance(data, dict) or set(data.keys()) != {"milestones"}:
        return False
    milestones = data.get("milestones")
    if not isinstance(milestones, list) or len(milestones) != len(ordered_tasks):
        return False

    valid_rule_types = {
        "inventory_has",
        "position_near_with_facing",
        "position_inside_box",
        "count_in_box_at_least",
        "count_in_box_at_most",
    }
    seen_milestone_ids: set = set()

    for idx, milestone in enumerate(milestones):
        if not isinstance(milestone, dict) or set(milestone.keys()) != {
            "task", "milestone_id", "description", "rules"
        }:
            return False
        if milestone.get("task") != ordered_tasks[idx]:
            return False
        milestone_id = milestone.get("milestone_id")
        if not isinstance(milestone_id, str) or not milestone_id:
            return False
        if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", milestone_id) is None:
            return False
        if milestone_id in seen_milestone_ids:
            return False
        seen_milestone_ids.add(milestone_id)
        if not isinstance(milestone.get("description"), str) or not milestone["description"]:
            return False
        rules = milestone.get("rules")
        # rules must be a non-empty list — empty [] is no longer valid.
        if not isinstance(rules, list) or len(rules) == 0:
            return False
        for rule in rules:
            if not isinstance(rule, dict) or set(rule.keys()) != {"type", "params"}:
                return False
            rule_type = rule.get("type")
            params = rule.get("params")
            if rule_type not in valid_rule_types or not isinstance(params, dict):
                return False
            if rule_type == "inventory_has":
                if set(params.keys()) != {"item", "min_count"}:
                    return False
                if not isinstance(params.get("item"), str) or not _is_positive_int_like(
                    params.get("min_count")
                ):
                    return False
            elif rule_type == "position_near_with_facing":
                # Required: target ([x,y,z]), coordinate_frame
                # Optional: max_distance, facing_tolerance
                required = {"target", "coordinate_frame"}
                allowed = {"target", "coordinate_frame", "max_distance", "facing_tolerance"}
                if not required.issubset(params.keys()) or not set(params.keys()).issubset(allowed):
                    return False
                target = params.get("target")
                if not isinstance(target, list) or len(target) != 3:
                    return False
                if not all(isinstance(v, (int, float)) for v in target):
                    return False
                if params.get("coordinate_frame") not in ("spawn_relative", "world"):
                    return False
            elif rule_type == "position_inside_box":
                if set(params.keys()) != {"min", "max", "coordinate_frame"}:
                    return False
                if not _validate_box_params(params):
                    return False
            elif rule_type == "count_in_box_at_least":
                required = {"kind", "object", "min", "max", "min_count", "coordinate_frame"}
                if not required.issubset(params.keys()):
                    return False
                if params.get("kind") not in ("block", "mob"):
                    return False
                if not isinstance(params.get("object"), str) or not params["object"]:
                    return False
                if not _is_positive_int_like(params.get("min_count")):
                    return False
                if not _validate_box_params(params):
                    return False
            elif rule_type == "count_in_box_at_most":
                required = {"kind", "object", "min", "max", "max_count", "coordinate_frame"}
                if not required.issubset(params.keys()):
                    return False
                if params.get("kind") not in ("block", "mob"):
                    return False
                if not isinstance(params.get("object"), str) or not params["object"]:
                    return False
                if not _is_non_negative_int_like(params.get("max_count")):
                    return False
                if not _validate_box_params(params):
                    return False

    return True


def parse_task_selection(text: str) -> Tuple[Optional[List[str]], str]:
    """
    Parse LLM response from task selection round.

    Returns:
        (selected_tasks, selection_reasoning) or (None, error_msg) if parsing fails.
    """
    data = extract_json_object(text)
    if not isinstance(data, dict):
        return None, "Failed to extract JSON object"

    selected_tasks = data.get("selected_tasks")
    reasoning = data.get("selection_reasoning", "")

    if not isinstance(selected_tasks, list) or len(selected_tasks) == 0:
        return None, "selected_tasks is not a non-empty list"

    if not all(isinstance(t, str) for t in selected_tasks):
        return None, "Not all items in selected_tasks are strings"

    return selected_tasks, reasoning


def save_fallback_response(
    fallback_dir: str,
    sample_idx: int,
    round_name: str,
    raw_response: str,
    attempt: int,
    validation_error: Optional[str] = None,
) -> None:
    """Save a failed JSON parsing response to fallback folder for debugging."""
    Path(fallback_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_file = (
        Path(fallback_dir)
        / f"{sample_idx:04d}_{round_name}_attempt{attempt}_{timestamp}.json"
    )

    fallback_data = {
        "sample_idx": sample_idx,
        "round": round_name,
        "attempt": attempt,
        "timestamp": timestamp,
        "validation_error": validation_error,
        "raw_response": raw_response,
    }

    with open(fallback_file, "w", encoding="utf-8") as f:
        json.dump(fallback_data, f, indent=2, ensure_ascii=False)

    print(f"  [FALLBACK] Saved to {fallback_file}")


def make_scene_id(idx: int) -> str:
    """Create a zero-padded directory-safe ID for the benchmark entry."""
    return f"{idx:04d}"


def save_benchmark_sample(
    result: Dict[str, Any],
    sample_idx: int,
    benchmark_dir: str,
    mode: str = "single",
    tool_log_staging_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Save a benchmark sample.

    Output structure under benchmark/<scene_id>/:
      metadata.json           - core fields (same schema for single and multi-agent)
      reasoning_graph.json    - dependency DAG
      reasoning_graph.png     - auto-rendered graph visualization
      [multi-agent only]
      debate_log.json         - truncated debate messages
      agent_conversation_log.json - full conversation with tool-call image refs
      tool_call_log.json      - all sandbox tool invocations

    Args:
        result:               Result dict from single_agent or multi_agent workflow.
        sample_idx:           0-based index used in the generated scene_id.
        benchmark_dir:        Root output directory.
        mode:                 "single" or "multi" — controls which extra files are saved.
        tool_log_staging_dir: Temp dir (multi-agent only) to move tool screenshots from.

    Returns the output directory path, or None if the sample is invalid.
    """
    if result is None:
        return None

    scene_design = result.get("scene_design")
    is_partial = result.get("partial", False)

    # For non-partial results, scene_design is required
    if not is_partial and scene_design is None:
        return None

    scene_id = make_scene_id(sample_idx)

    # Structure: benchmark/<scene_id>/<mode>-agent/
    mode_dir_name = f"{mode}-agent"
    out_dir = Path(benchmark_dir) / scene_id / mode_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata: Dict[str, Any] = {
        "id": scene_id,
        "sample_idx": sample_idx,
        "mode": mode,
        "selected_tasks": result.get("selected_tasks", []),
        "selection_reasoning": result.get("selection_reasoning", ""),
        "reasoning_graph": result.get("reasoning_graph"),
        "milestones": result.get("milestones"),
    }

    if scene_design is not None:
        metadata.update({
            "scene_name": scene_design.get("scene_name", ""),
            "scene_description": scene_design.get("scene_description", ""),
            "task_text": scene_design.get("task_text", ""),
            "atomic_tasks_ordered": scene_design.get(
                "atomic_tasks_ordered", result.get("selected_tasks", [])
            ),
            "commands": scene_design.get("commands", []),
            "design_notes": scene_design.get("design_notes", ""),
        })

    if is_partial:
        metadata["partial"] = True
        metadata["failure_reason"] = result.get("failure_reason", "Unknown failure")
        print(f"  [WARN] Saving partial multi-agent result: {metadata['failure_reason']}")

    if mode == "multi" and result.get("debate_log"):
        metadata["debate_log"] = result["debate_log"]

    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    if result.get("reasoning_graph"):
        with open(out_dir / "reasoning_graph.json", "w", encoding="utf-8") as f:
            json.dump(result["reasoning_graph"], f, indent=2, ensure_ascii=False)
        ok = render_reasoning_graph(str(out_dir), result["reasoning_graph"])
        if ok:
            print(f"  [VIZ] Dependency graph: {out_dir / 'reasoning_graph.png'}")
        else:
            print("  [WARN] Could not render reasoning_graph.png (matplotlib/networkx missing?)")

    if result.get("milestones"):
        with open(out_dir / "milestones.json", "w", encoding="utf-8") as f:
            json.dump(result["milestones"], f, indent=2, ensure_ascii=False)

    if mode == "multi":
        if result.get("debate_log"):
            with open(out_dir / "debate_log.json", "w", encoding="utf-8") as f:
                json.dump(result["debate_log"], f, indent=2, ensure_ascii=False)

        if result.get("full_conversation_log"):
            with open(out_dir / "agent_conversation_log.json", "w", encoding="utf-8") as f:
                json.dump(result["full_conversation_log"], f, indent=2, ensure_ascii=False)

        tool_call_log = result.get("tool_call_log", [])
        if tool_call_log:
            with open(out_dir / "tool_call_log.json", "w", encoding="utf-8") as f:
                json.dump(tool_call_log, f, indent=2, ensure_ascii=False)

        if tool_log_staging_dir:
            _move_staging_dir(tool_log_staging_dir, str(out_dir))

    print(f"  [SAVED] {out_dir}")
    return str(out_dir)


def _move_staging_dir(staging_dir: str, out_dir: str) -> None:
    """Move scene_map/, tool_use/ from staging_dir into out_dir."""
    staging = Path(staging_dir)
    dest = Path(out_dir)

    for sub in ("scene_map", "tool_use"):
        src = staging / sub
        if not src.is_dir():
            continue
        dst = dest / sub
        if dst.exists():
            shutil.rmtree(str(dst), ignore_errors=True)
        try:
            shutil.move(str(src), str(dst))
            print(f"  [STAGING] Moved {sub}/ → {dst}")
        except Exception as e:
            print(f"  [WARN] Could not move {sub}/: {e}")


def render_reasoning_graph(out_dir: str, reasoning_graph: Dict[str, Any]) -> bool:
    """
    Draw a clean left-to-right task dependency DAG using matplotlib + networkx.

    Improvements over the previous version:
    - Supports arbitrary DAG structures (not just linear chains).
    - Node positions computed via Sugiyama-style layered layout (longest-path).
    - Every edge is labelled with its "reason" annotation.
    - Multi-edge curves use arc rad to avoid overlap.

    Returns True on success, False on failure.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import matplotlib.patheffects as pe
    except ImportError:
        print("  [WARN] matplotlib not available, skipping graph rendering.")
        return False

    import textwrap
    import math as _math

    raw_nodes = reasoning_graph.get("nodes", [])
    edges: List[Dict[str, Any]] = reasoning_graph.get("edges", [])
    if not raw_nodes:
        return False

    def _node_id(n: Any) -> str:
        if isinstance(n, str):
            return n
        if isinstance(n, dict):
            return str(n.get("id") or n.get("task") or n.get("name") or list(n.values())[0])
        return str(n)

    nodes: List[str] = [_node_id(n) for n in raw_nodes]

    try:
        import networkx as nx
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        for e in edges:
            src, dst = e.get("from"), e.get("to")
            if src in G and dst in G:
                G.add_edge(src, dst)
    except ImportError:
        # Fallback: no networkx, treat as a chain
        G = None  # type: ignore

    NODE_W = 2.4
    NODE_H = 0.70
    H_GAP  = 2.4   # horizontal gap between layers
    V_GAP  = 1.2   # vertical gap between nodes in the same layer

    if G is not None and len(G.nodes) > 0:
        try:
            layer_of: Dict[str, int] = {}
            for node in nx.topological_sort(G):
                preds = list(G.predecessors(node))
                layer_of[node] = max((layer_of[p] for p in preds), default=-1) + 1
        except Exception:
            layer_of = {n: i for i, n in enumerate(nodes)}
    else:
        layer_of = {n: i for i, n in enumerate(nodes)}

    layers: Dict[int, List[str]] = {}
    for node, layer in layer_of.items():
        layers.setdefault(layer, []).append(node)

    n_layers = max(layers.keys(), default=0) + 1
    for layer in layers.values():
        layer.sort()

    node_pos: Dict[str, tuple] = {}
    for layer_idx, layer_nodes in sorted(layers.items()):
        n_in_layer = len(layer_nodes)
        for rank, node in enumerate(layer_nodes):
            cx = layer_idx * (NODE_W + H_GAP) + NODE_W / 2
            cy = -(rank - (n_in_layer - 1) / 2.0) * (NODE_H + V_GAP)
            node_pos[node] = (cx, cy)

    all_x = [p[0] for p in node_pos.values()]
    all_y = [p[1] for p in node_pos.values()]
    min_x = min(all_x) - NODE_W * 0.6
    max_x = max(all_x) + NODE_W * 0.6
    min_y = min(all_y) - NODE_H * 1.2
    max_y = max(all_y) + NODE_H * 1.8   # headroom for title

    fig_w = max(5.0, (max_x - min_x) + 0.8)
    fig_h = max(3.0, (max_y - min_y) + 0.8)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="#F8FAFD")
    ax.set_facecolor("#F8FAFD")
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_aspect("equal")
    ax.axis("off")

    NODE_COLORS = [
        "#2563EB", "#16A34A", "#D97706", "#9333EA", "#DC2626", "#0891B2",
        "#B45309", "#0D9488",
    ]
    badge_symbols = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]

    node_color_map: Dict[str, str] = {}
    for idx, node in enumerate(nodes):
        color = NODE_COLORS[idx % len(NODE_COLORS)]
        node_color_map[node] = color
        cx, cy = node_pos[node]

        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - NODE_W / 2 + 0.07, cy - NODE_H / 2 - 0.08),
            NODE_W, NODE_H,
            boxstyle="round,pad=0.12",
            facecolor="#B0BAC8", edgecolor="none", alpha=0.45, zorder=2,
        ))
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - NODE_W / 2, cy - NODE_H / 2),
            NODE_W, NODE_H,
            boxstyle="round,pad=0.12",
            facecolor=color, edgecolor="white", linewidth=2.2, zorder=3,
        ))
        badge = badge_symbols[idx] if idx < len(badge_symbols) else str(idx + 1)
        ax.text(
            cx - NODE_W / 2 + 0.24, cy + NODE_H / 2 - 0.16,
            badge, ha="center", va="center",
            fontsize=9, color="white", fontweight="bold", alpha=0.95, zorder=4,
        )
        label = "\n".join(textwrap.wrap(node, width=22))
        ax.text(
            cx, cy, label,
            ha="center", va="center",
            fontsize=9.5, fontweight="bold",
            color="white", linespacing=1.3, zorder=4,
        )

    edge_count: Dict[tuple, int] = {}

    for e in edges:
        src, dst = e.get("from"), e.get("to")
        reason = e.get("reason", "")
        if src not in node_pos or dst not in node_pos:
            continue

        sx, sy = node_pos[src]
        dx, dy = node_pos[dst]

        pair = (src, dst)
        rad_idx = edge_count.get(pair, 0)
        edge_count[pair] = rad_idx + 1
        rad = 0.0 + rad_idx * 0.25

        if abs(dx - sx) >= abs(dy - sy):
            x0 = sx + NODE_W / 2 if dx > sx else sx - NODE_W / 2
            y0 = sy
            x1 = dx - NODE_W / 2 if dx > sx else dx + NODE_W / 2
            y1 = dy
        else:
            x0 = sx
            y0 = sy - NODE_H / 2 if dy < sy else sy + NODE_H / 2
            x1 = dx
            y1 = dy + NODE_H / 2 if dy < sy else dy - NODE_H / 2

        ax.annotate(
            "",
            xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-|>",
                color="#4A5E8A",
                lw=2.0,
                mutation_scale=20,
                connectionstyle=f"arc3,rad={rad:.2f}",
            ),
            zorder=3,
        )

        if reason:
            mx = (x0 + x1) / 2 - rad * (y1 - y0) * 0.5
            my = (y0 + y1) / 2 + rad * (x1 - x0) * 0.5
            wrapped = "\n".join(textwrap.wrap(reason, width=24))
            ax.text(
                mx, my, wrapped,
                ha="center", va="center",
                fontsize=7.5, color="#1E3A5F",
                linespacing=1.25,
                bbox=dict(
                    boxstyle="round,pad=0.35",
                    facecolor="#DDEEFF",
                    edgecolor="#8AADD4",
                    linewidth=0.9,
                    alpha=0.92,
                ),
                zorder=5,
            )

    ax.set_title(
        "Task Dependency Graph", fontsize=11, fontweight="bold",
        pad=6, color="#0F1D3A", loc="center",
    )
    fig.tight_layout(pad=0.4)
    out_path = Path(out_dir) / "reasoning_graph.png"
    fig.savefig(str(out_path), dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"  [VIZ] Reasoning graph saved: {out_path}")
    return True


def render_minecraft_scene_via_server(
    out_dir: str,
    scene_design: Dict[str, Any],
    server_url: str,
    env_id: str = "MineRLBasaltFindCave-v0",
    wait_steps_after_cmd: int = 3,
    settle_steps: int = 6,
) -> Optional[str]:
    """
    Execute scene commands via luminescent-server HTTP API and capture screenshots.

    Connects to the remote luminescent-server (mc_server.py FastAPI service)
    via its REST endpoints:
      POST /create_env  — create the Minecraft environment
      POST /reset_env   — reset and get initial observation
      POST /step        — execute one action step (supports "chat" for /commands)

    Each Minecraft command is sent as a chat action: {"chat": "/fill ..."}.
    After all commands are executed, screenshots are captured from the server response.

    Args:
        out_dir:               Output directory for screenshots.
        scene_design:          Dict with "commands", "task_text", "scene_name".
        server_url:            Full URL to luminescent-server, e.g. "http://10.x.x.x:8000".
        env_id:                MineRL env ID to use (default: MineRLBasaltFindCave-v0).
        wait_steps_after_cmd:  No-op steps to wait after each command for world to update.
        settle_steps:          No-op steps to let the environment settle after all commands.

    Returns:
        Path to scene_preview.png, or None on failure.
    """
    import base64
    import io as _io
    import time

    try:
        import requests
        from PIL import Image as _Image
        import numpy as _np
    except ImportError as e:
        print(f"  [SERVER_RENDER] Missing dependency: {e}. Install requests and Pillow.")
        return None

    commands: List[str] = scene_design.get("commands", [])
    task_text: str = scene_design.get("task_text", "")
    scene_name: str = scene_design.get("scene_name", "scene")

    if not commands:
        print("  [SERVER_RENDER] No commands to execute.")
        return None

    base_url = server_url.rstrip("/")
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    def _post(endpoint: str, payload: dict = None, timeout: int = 300) -> Optional[dict]:
        try:
            resp = requests.post(
                f"{base_url}/{endpoint.lstrip('/')}",
                json=payload or {},
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  [SERVER_RENDER] POST /{endpoint} failed: {e}")
            return None

    def _b64_to_pil(b64_str: str) -> Optional[Any]:
        try:
            img_bytes = base64.b64decode(b64_str)
            img = _Image.open(_io.BytesIO(img_bytes))
            return img
        except Exception as e:
            print(f"  [SERVER_RENDER] Failed to decode screenshot: {e}")
            return None

    def _save_pil(img: Any, path: Path) -> bool:
        try:
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(str(path))
            return True
        except Exception as e:
            print(f"  [SERVER_RENDER] Failed to save image to {path}: {e}")
            return False

    print(f"  [SERVER_RENDER] Connecting to {base_url}, creating env '{env_id}'...")
    create_resp = _post("create_env", {"env": env_id}, timeout=600)
    if create_resp is None or create_resp.get("status") != 0:
        msg = create_resp.get("msg", "unknown error") if create_resp else "no response"
        print(f"  [SERVER_RENDER] create_env failed: {msg}")
        return None
    print(f"  [SERVER_RENDER] Env created.")

    print("  [SERVER_RENDER] Resetting environment...")
    reset_resp = _post("reset_env", {}, timeout=180)
    if reset_resp is None or reset_resp.get("status") != 0:
        msg = reset_resp.get("msg", "unknown error") if reset_resp else "no response"
        print(f"  [SERVER_RENDER] reset_env failed: {msg}")
        return None

    noop_action = {
        "ESC": 0, "attack": 0, "back": 0, "camera": [0, 0],
        "drop": 0, "forward": 0, "hotbar.1": 0, "hotbar.2": 0,
        "hotbar.3": 0, "hotbar.4": 0, "hotbar.5": 0, "hotbar.6": 0,
        "hotbar.7": 0, "hotbar.8": 0, "hotbar.9": 0,
        "inventory": 0, "jump": 0, "left": 0, "pickItem": 0,
        "right": 0, "sneak": 0, "sprint": 0, "swapHands": 0, "use": 0,
    }

    print(f"  [SERVER_RENDER] Executing {len(commands)} scene commands via chat...")
    last_step_resp = None
    for idx, cmd in enumerate(commands):
        chat_action = dict(noop_action)
        chat_action["chat"] = cmd
        step_resp = _post("step", {"action": chat_action}, timeout=60)
        if step_resp is None or step_resp.get("status") != 0:
            err = step_resp.get("msg", "unknown") if step_resp else "no response"
            print(f"  [SERVER_RENDER] Command [{idx+1}/{len(commands)}] '{cmd[:60]}' failed: {err}")
        else:
            last_step_resp = step_resp
            print(f"  [SERVER_RENDER] Command [{idx+1}/{len(commands)}] OK")

        for _ in range(wait_steps_after_cmd):
            step_resp = _post("step", {"action": noop_action}, timeout=30)
            if step_resp and step_resp.get("status") == 0:
                last_step_resp = step_resp

    print(f"  [SERVER_RENDER] Settling ({settle_steps} no-op steps)...")
    for _ in range(settle_steps):
        step_resp = _post("step", {"action": noop_action}, timeout=30)
        if step_resp and step_resp.get("status") == 0:
            last_step_resp = step_resp

    snapshot_path = None
    if last_step_resp and last_step_resp.get("screenshot"):
        img = _b64_to_pil(last_step_resp["screenshot"])
        if img:
            snapshot_file = out_path / "scene_preview.png"
            if _save_pil(img, snapshot_file):
                snapshot_path = str(snapshot_file)
                print(f"  [SERVER_RENDER] Saved scene_preview.png ({img.size})")
    else:
        print("  [SERVER_RENDER] No screenshot from last step, trying reset for snapshot...")
        reset_resp2 = _post("reset_env", {}, timeout=120)
        if reset_resp2 and reset_resp2.get("screenshot"):
            img = _b64_to_pil(reset_resp2["screenshot"])
            if img:
                snapshot_file = out_path / "scene_preview.png"
                if _save_pil(img, snapshot_file):
                    snapshot_path = str(snapshot_file)
                    print(f"  [SERVER_RENDER] Saved scene_preview.png from reset ({img.size})")

    if snapshot_path is None:
        print("  [SERVER_RENDER] Could not capture screenshot.")
        return None

    try:
        min_x, max_x, min_y, max_y, min_z, max_z = _estimate_scene_bbox(commands)
        cx = (min_x + max_x) / 2.0
        cz = (min_z + max_z) / 2.0
        span = max(max_x - min_x, max_z - min_z)
        cam_height_offset = max(15.0, min(60.0, span * 0.8))
        cam_y = max_y + cam_height_offset

        spectator_action = dict(noop_action)
        spectator_action["chat"] = "/gamemode spectator @s"
        _post("step", {"action": spectator_action}, timeout=30)

        tp_action = dict(noop_action)
        tp_action["chat"] = f"/tp @s ~{cx:.1f} ~{cam_y:.1f} ~{cz:.1f}"
        _post("step", {"action": tp_action}, timeout=30)

        for _ in range(4):
            step_resp = _post("step", {"action": noop_action}, timeout=30)

        pitch_action = dict(noop_action)
        for _ in range(6):
            pitch_action["camera"] = [15.0, 0.0]
            step_resp = _post("step", {"action": pitch_action}, timeout=30)

        final_resp = _post("step", {"action": noop_action}, timeout=30)
        if final_resp and final_resp.get("screenshot"):
            img = _b64_to_pil(final_resp["screenshot"])
            if img:
                overview_file = out_path / "scene_overview.png"
                if _save_pil(img, overview_file):
                    print(
                        f"  [SERVER_RENDER] Saved scene_overview.png "
                        f"(cam ~{cx:.0f},{cam_y:.0f},{cz:.0f}, span={span:.0f})"
                    )

        survival_action = dict(noop_action)
        survival_action["chat"] = "/gamemode survival @s"
        _post("step", {"action": survival_action}, timeout=30)

    except Exception as ov_err:
        print(f"  [SERVER_RENDER] Aerial overview skipped: {ov_err}")

    return snapshot_path


def _estimate_scene_bbox(
    commands: List[str],
) -> Tuple[float, float, float, float, float, float]:
    """
    Parse relative-coordinate (~X) commands to estimate the bounding box
    of the built scene.
    """
    xs: List[float] = [0.0]
    ys: List[float] = [0.0]
    zs: List[float] = [0.0]

    coord_re = re.compile(r"~(-?\d*\.?\d*)")

    for cmd in commands:
        cmd_lower = cmd.strip().lower()
        if not any(kw in cmd_lower for kw in ("/fill ", "/setblock ", "/tp ", "/summon ")):
            continue

        raw_coords = coord_re.findall(cmd)
        if not raw_coords:
            continue

        values = []
        for raw in raw_coords:
            try:
                values.append(float(raw) if raw else 0.0)
            except ValueError:
                pass

        for i, v in enumerate(values):
            axis = i % 3
            if axis == 0:
                xs.append(v)
            elif axis == 1:
                ys.append(v)
            else:
                zs.append(v)

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    if (max_x - min_x) < 10:
        min_x -= 5
        max_x += 5
    if (max_z - min_z) < 10:
        min_z -= 5
        max_z += 5

    return min_x, max_x, min_y, max_y, min_z, max_z
