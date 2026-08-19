"""Hypothesis data model + DAG for the HypothesisAgent.

A `Hypothesis` is a small, LLM-authored belief about the world
("there is likely a village to the north", "this chest requires a key"),
carrying a self-reported confidence in [0, 1]. `HypothesisGraph` stores
these as nodes in a DAG, where an edge `child -> parent` means "child
refines/depends on parent" (e.g. "the key is in the chest" depends on
"there is a locked chest nearby"). The graph is pure bookkeeping — it does
not choose actions itself; HypothesisAgent renders it into the prompt each
step and lets the LLM decide what to do next.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

HypothesisStatus = Literal["active", "confirmed", "refuted", "stale"]

# Cap on stored evidence strings per node. Without this, a hypothesis id that
# the LLM keeps reusing across an entire episode (observed: one id absorbing
# evidence about several unrelated physical structures in a row) grows
# unbounded and the oldest, most-superseded entries are the least useful ones
# to keep around.
MAX_EVIDENCE_PER_NODE = 8


# What a hypothesis is about. `goal` is a sub-goal the task names (found / reached /
# mined X) and is the one kind the harness holds to a rule: only the environment
# confirms goals (see HypothesisAgent._enforce_discipline).
HypothesisKind = Literal["goal", "location", "mechanism", "state", "other"]
KINDS = ("goal", "location", "mechanism", "state", "other")


class Hypothesis(BaseModel):
    id: str
    statement: str
    confidence: float = 0.5
    status: HypothesisStatus = "active"
    kind: HypothesisKind = "other"
    depends_on: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    created_step: int = 0
    updated_step: int = 0


class CycleError(ValueError):
    """Raised when adding a dependency edge would create a cycle in the DAG."""


class HypothesisGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Hypothesis] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_or_update(
        self,
        *,
        id: str,
        statement: Optional[str] = None,
        confidence: Optional[float] = None,
        status: Optional[str] = None,
        evidence: Optional[List[str]] = None,
        step: int = 0,
        kind: Optional[str] = None,
    ) -> Hypothesis:
        """Create a hypothesis node if `id` is new, otherwise update the
        fields that were actually supplied (None/omitted fields are left
        untouched on an existing node)."""
        node = self.nodes.get(id)
        if node is None:
            node = Hypothesis(
                id=id,
                statement=statement or "(unspecified)",
                confidence=confidence if confidence is not None else 0.5,
                status=status or "active",
                kind=kind if kind in KINDS else "other",
                evidence=(list(evidence) if evidence else [])[-MAX_EVIDENCE_PER_NODE:],
                created_step=step,
                updated_step=step,
            )
            self.nodes[id] = node
            return node

        if kind in KINDS:
            node.kind = kind
        if statement:
            node.statement = statement
        if confidence is not None:
            node.confidence = max(0.0, min(1.0, float(confidence)))
        if status:
            node.status = status
        if evidence:
            node.evidence.extend(evidence)
            if len(node.evidence) > MAX_EVIDENCE_PER_NODE:
                node.evidence = node.evidence[-MAX_EVIDENCE_PER_NODE:]
        node.updated_step = step
        return node

    def _reachable(self, start: str) -> set:
        """All ids reachable from `start` by following depends_on edges
        (i.e. start's ancestors)."""
        seen: set = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            node = self.nodes.get(cur)
            if node:
                stack.extend(node.depends_on)
        return seen

    def add_dependency(self, child_id: str, parent_id: str, step: int = 0) -> None:
        """Record that `child_id` depends on / refines `parent_id`.

        Raises CycleError instead of corrupting the DAG if `parent_id`
        already (transitively) depends on `child_id`.
        """
        if child_id == parent_id:
            raise CycleError(f"hypothesis '{child_id}' cannot depend on itself")
        if parent_id not in self.nodes:
            # Auto-create a placeholder so a forward reference to a
            # not-yet-described parent doesn't crash the episode.
            self.add_or_update(id=parent_id, step=step)
        if child_id in self._reachable(parent_id):
            raise CycleError(
                f"adding edge {child_id} -> {parent_id} would create a cycle"
            )
        child = self.nodes.get(child_id)
        if child is None:
            child = self.add_or_update(id=child_id, step=step)
        if parent_id not in child.depends_on:
            child.depends_on.append(parent_id)
        child.updated_step = step

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def frontier(self, k: int = 5) -> List[Hypothesis]:
        """Active hypotheses whose dependencies are all resolved (confirmed
        or refuted, or have none), ranked most-uncertain-first (confidence
        closest to 0.5), tie-broken by staleness (oldest update first)."""
        candidates = []
        for node in self.nodes.values():
            if node.status != "active":
                continue
            deps = [self.nodes.get(d) for d in node.depends_on]
            if any(d is not None and d.status == "active" for d in deps):
                continue
            candidates.append(node)
        candidates.sort(key=lambda n: (abs(n.confidence - 0.5), n.updated_step))
        return candidates[:k]

    def to_prompt_summary(self, max_items: int = 8, flags: Optional[Dict[str, str]] = None) -> str:
        """`flags` maps id -> a short tag the harness wants shown next to the node
        (e.g. "locked", "under test for 12 steps"). Goals are listed first: they are
        the map of the task the rest of the graph hangs off, and the discipline rules
        act on them."""
        if not self.nodes:
            return ""
        goals = sorted((n for n in self.nodes.values() if n.kind == "goal"),
                       key=lambda n: n.created_step)
        ranked = goals[:max_items]
        shown_ids = {n.id for n in ranked}
        for n in self.frontier(k=max_items):
            if n.id not in shown_ids and len(ranked) < max_items:
                ranked.append(n)
                shown_ids.add(n.id)
        remaining = [n for n in self.nodes.values() if n.id not in shown_ids]
        remaining.sort(key=lambda n: n.updated_step, reverse=True)
        ranked = ranked + remaining[: max(0, max_items - len(ranked))]

        lines = []
        for n in ranked:
            deps = f" (depends on: {', '.join(n.depends_on)})" if n.depends_on else ""
            flag = f", {flags[n.id]}" if flags and n.id in flags else ""
            lines.append(
                f"- [{n.id}] ({n.kind}, {n.status}, confidence={n.confidence:.2f}{flag}) "
                f"{n.statement}{deps}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"nodes": [n.model_dump() for n in self.nodes.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "HypothesisGraph":
        graph = cls()
        for raw in data.get("nodes", []):
            node = Hypothesis(**raw)
            graph.nodes[node.id] = node
        return graph

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "HypothesisGraph":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
