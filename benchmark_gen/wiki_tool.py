"""
agents/wiki_tool.py

Local Minecraft Wiki Tools for CommonSenseAgent
================================================
Provides three AutoGen-compatible wiki tool functions that read from
pre-fetched JSON files under benchmark_gen/wiki_data/
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
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BENCHMARK_GEN_DIR = Path(__file__).resolve().parent.parent  # benchmark_gen/
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
