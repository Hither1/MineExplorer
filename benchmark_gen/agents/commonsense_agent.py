"""
agents/commonsense_agent.py

CommonSenseAgent — System Prompt & Local Wiki Tools
====================================================
In the AutoGen-based workflow, CommonSenseAgent is a ConversableAgent with
three registered wiki tool functions.

Wiki data is read from the pre-fetched JSON files under benchmark_gen/wiki_data/
(populated by benchmark_gen/fetch_wiki.py).

Three-step wiki lookup via AutoGen function calling:
  Step 1 – wiki_list_categories()
      → returns available databases + entry counts
  Step 2 – wiki_list_keys(category)
      → returns all object names in that category
  Step 3 – wiki_lookup(category, names)
      → returns official wiki intro descriptions for the requested objects
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_AGENTS_DIR        = Path(__file__).resolve().parent   # benchmark_gen/agents/
_BENCHMARK_GEN_DIR = _AGENTS_DIR.parent                # benchmark_gen/
_WIKI_DATA_DIR     = _BENCHMARK_GEN_DIR / "wiki_data"

# Maps logical category name → JSON file stem
_CATEGORY_FILES: Dict[str, str] = {
    "blocks":       "blocks",
    "items":        "items",
    "mobs":         "mobs",
    "biomes":       "biomes",
    "effects":      "effects",
    "enchantments": "enchantments",
    "structures":   "structures",
}

# ---------------------------------------------------------------------------
# In-memory cache so each file is loaded only once
# ---------------------------------------------------------------------------

_CACHE: Dict[str, Optional[Dict[str, str]]] = {}


def _load(category: str) -> Optional[Dict[str, str]]:
    """Load and cache the JSON file for *category*. Returns None if missing."""
    if category not in _CACHE:
        path = _WIKI_DATA_DIR / f"{_CATEGORY_FILES[category]}.json"
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                _CACHE[category] = json.load(f)
        else:
            _CACHE[category] = None
    return _CACHE[category]


# ---------------------------------------------------------------------------
# Wiki tool functions (registered via make_wiki_tools())
# ---------------------------------------------------------------------------

def wiki_list_categories() -> str:
    """
    List all available Minecraft wiki databases and the number of entries each
    contains.  Call this first to decide which category to browse.
    """
    lines = ["Available Minecraft wiki databases:"]
    for cat in _CATEGORY_FILES:
        data = _load(cat)
        count = len(data) if data else 0
        status = f"{count} entries" if data else "unavailable (run fetch_wiki.py)"
        lines.append(f"  • {cat}: {status}")
    return "\n".join(lines)


def wiki_list_keys(category: str) -> str:
    """
    Return the full list of object names available in *category*.

    Args:
        category: one of blocks, items, mobs, biomes, effects,
                  enchantments, structures.

    Returns a newline-separated list of names you can pass to wiki_lookup().
    """
    if category not in _CATEGORY_FILES:
        valid = ", ".join(_CATEGORY_FILES)
        return f"[Wiki] Unknown category '{category}'. Valid choices: {valid}"
    data = _load(category)
    if data is None:
        return (
            f"[Wiki] Data file for '{category}' not found. "
            "Run `python benchmark_gen/fetch_wiki.py` to populate wiki_data/."
        )
    keys = sorted(data.keys())
    return f"Objects in '{category}' ({len(keys)} total):\n" + "\n".join(keys)


def wiki_lookup(category: str, names: List[str]) -> str:
    """
    Return the official Minecraft Wiki intro description for each requested
    object name.

    Args:
        category: one of blocks, items, mobs, biomes, effects,
                  enchantments, structures.
        names:    list of exact object names (as returned by wiki_list_keys).

    Returns a formatted string with one entry per name.
    """
    if category not in _CATEGORY_FILES:
        valid = ", ".join(_CATEGORY_FILES)
        return f"[Wiki] Unknown category '{category}'. Valid choices: {valid}"
    data = _load(category)
    if data is None:
        return (
            f"[Wiki] Data file for '{category}' not found. "
            "Run `python benchmark_gen/fetch_wiki.py` to populate wiki_data/."
        )
    parts: List[str] = []
    for name in names:
        desc = data.get(name)
        if desc:
            parts.append(f"### {name}\n{desc}")
        else:
            # Try case-insensitive fallback
            lower_map = {k.lower(): k for k in data}
            real_key = lower_map.get(name.lower())
            if real_key:
                parts.append(f"### {real_key}\n{data[real_key]}")
            else:
                parts.append(f"### {name}\n[not found in '{category}' database]")
    return "\n\n".join(parts) if parts else "[Wiki] No names provided."


def make_wiki_tools() -> List[Dict]:
    """
    Return a list of AutoGen-compatible tool dicts for the three wiki functions.

    Each dict has the flat format expected by BenchmarkOrchestrator._register_tools():
      {"name": str, "description": str, "function": callable}
    """
    return [
        {
            "name": "wiki_list_categories",
            "description": (
                "List all available Minecraft wiki databases "
                "(blocks, items, mobs, biomes, effects, enchantments, structures) "
                "and the number of entries each contains. "
                "Call this first to see what data is available."
            ),
            "function": wiki_list_categories,
        },
        {
            "name": "wiki_list_keys",
            "description": (
                "Return all object names in a wiki category. "
                "Use the names returned here as input to wiki_lookup(). "
                "Call this to browse what objects exist before doing a lookup."
            ),
            "function": wiki_list_keys,
        },
        {
            "name": "wiki_lookup",
            "description": (
                "Fetch the official Minecraft Wiki intro description for a "
                "list of specific objects. Returns plain-text summaries that "
                "describe what each object is and how it behaves."
            ),
            "function": wiki_lookup,
        },
    ]


# ---------------------------------------------------------------------------
# Agent name & system prompt
# ---------------------------------------------------------------------------

AGENT_NAME = "CommonSenseAgent"

SYSTEM_PROMPT = """
You are the **CommonSense Judge Agent** in a multi-agent Minecraft benchmark generation team.

## Your Responsibilities
1. Inspect the full benchmark state (tasks, scene, milestones) for Minecraft-specific knowledge issues.
2. Identify anything that requires deep Minecraft domain knowledge to complete.
3. Use the wiki tools to verify game mechanics when uncertain.
4. Send targeted critiques to TaskSelectorAgent and/or SceneDesignerAgent.
5. Re-inspect after revisions to confirm issues are resolved.

## What to Check
- Do any tasks require knowing Minecraft crafting recipes that aren't obvious?
- Do any tasks require knowing mob spawn conditions, biome specifics, or game mechanics?
- Does the scene design use blocks/items in ways that conflict with Minecraft physics?
- Are there Minecraft-specific gotchas (e.g. wood must be exact orientation for crafting)?
- Can a general-purpose AI agent (without Minecraft expertise) complete all tasks?

## Severity Levels
- critical: Makes benchmark impossible without domain knowledge
- high: Significantly disadvantages non-expert players
- medium: Minor domain knowledge advantage
- low: Cosmetic or negligible issue

## Response Format
```json
{
  "issues": [
    {
      "issue": "Description of the problem",
      "severity": "critical|high|medium|low",
      "target_agent": "TaskSelectorAgent|SceneDesignerAgent|both"
    }
  ],
  "approved": true,
  "critique_for_task_selector": "Specific actionable critique (empty if none)",
  "critique_for_scene_designer": "Specific actionable critique (empty if none)",
  "summary": "Overall assessment"
}
```

Set `approved=true` when there are no critical or high severity issues.
Set `approved=false` when at least one critical or high severity issue exists.

## Wiki Lookup (Three-Step via Tool Calls)
You have access to a local Minecraft wiki database with pre-fetched descriptions.

**Step 1** — Call `wiki_list_categories()` to see available databases
(blocks, items, mobs, biomes, effects, enchantments, structures).

**Step 2** — Call `wiki_list_keys(category)` with one of those category names
to receive the full list of object names available in that database.

**Step 3** — Call `wiki_lookup(category, names)` with a list of the specific
object names you want to verify. You will receive the official wiki intro
description for each one.

Use the descriptions to determine whether a task or scene element requires
non-obvious Minecraft domain knowledge that should be flagged.
""".strip()

DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS  = 2048


# ---------------------------------------------------------------------------
# Legacy shims — kept for backward-compatible imports in orchestrator.py
# ---------------------------------------------------------------------------

def query_minecraft_wiki(query: str, max_chars: int = 2000) -> str:
    """
    Legacy online wiki search (kept for backward compatibility).
    Prefer the offline wiki_lookup() tool via make_wiki_tools() instead.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = (
            "https://minecraft.wiki/api.php"
            "?action=query&list=search"
            f"&srsearch={encoded_query}"
            "&srlimit=3&format=json"
        )
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "MCBench/2.0 (minecraft-benchmark-research)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return f"[Wiki] No results for: {query}"

        title = search_results[0]["title"]
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        extract_url = (
            "https://minecraft.wiki/api.php"
            f"?action=query&titles={encoded_title}"
            "&prop=extracts&exintro=true&format=json&explaintext=true"
        )
        req2 = urllib.request.Request(
            extract_url,
            headers={"User-Agent": "MCBench/2.0 (minecraft-benchmark-research)"},
        )
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            extract_data = json.loads(resp2.read().decode("utf-8"))

        pages = extract_data.get("query", {}).get("pages", {})
        for page in pages.values():
            extract = page.get("extract", "")
            if extract:
                return f"[Wiki: {title}]\n{extract[:max_chars]}"

        return f"[Wiki] Retrieved '{title}' but no extract available."

    except Exception as e:
        return f"[Wiki] Query failed ({e}). Proceeding without wiki information."


def handle_wiki_action(action: str, params: dict) -> str:
    """
    Legacy shim dispatching wiki tool calls by action name string.
    Kept so any older code that calls handle_wiki_action() still works.
    """
    if action == "wiki_list_categories":
        return wiki_list_categories()
    if action == "wiki_list_keys":
        return wiki_list_keys(params.get("category", ""))
    if action == "wiki_lookup":
        return wiki_lookup(
            params.get("category", ""),
            params.get("names", []),
        )
    return f"[Wiki] Unknown action '{action}'."
