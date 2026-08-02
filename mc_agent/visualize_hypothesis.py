"""Simple visualization for a saved HypothesisGraph (hypothesis_graph.json).

Usage:
    python -m mc_agent.visualize_hypothesis path/to/hypothesis_graph.json
    python -m mc_agent.visualize_hypothesis path/to/hypothesis_graph.json -o out.png
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from mc_agent.hypothesis import HypothesisGraph

STATUS_COLORS = {
    "active": "#f6c945",
    "confirmed": "#4caf7d",
    "refuted": "#e05c5c",
    "stale": "#b0b0b0",
}


def build_networkx_graph(graph: HypothesisGraph) -> nx.DiGraph:
    g = nx.DiGraph()
    for node in graph.nodes.values():
        g.add_node(node.id, **node.model_dump())
        for parent_id in node.depends_on:
            # child depends_on parent -> draw edge parent -> child
            g.add_edge(parent_id, node.id)
    return g


def plot_hypothesis_graph(graph: HypothesisGraph, output_path: str | Path) -> None:
    g = build_networkx_graph(graph)
    if g.number_of_nodes() == 0:
        raise ValueError("hypothesis graph is empty, nothing to plot")

    try:
        pos = nx.nx_agraph.graphviz_layout(g, prog="dot")
    except ImportError:
        pos = nx.spring_layout(g, seed=0)

    colors = [STATUS_COLORS.get(g.nodes[n].get("status", "active"), "#cccccc") for n in g.nodes]
    labels = {
        n: f"{n}\n{g.nodes[n].get('confidence', 0):.2f}\n"
        + "\n".join(textwrap.wrap(g.nodes[n].get("statement", ""), width=24)[:3])
        for n in g.nodes
    }

    fig, ax = plt.subplots(figsize=(max(6, 3 * g.number_of_nodes() ** 0.5), 6))
    nx.draw_networkx_nodes(g, pos, node_color=colors, node_size=2500, edgecolors="black", ax=ax)
    nx.draw_networkx_edges(g, pos, arrows=True, arrowstyle="-|>", arrowsize=15, ax=ax)
    nx.draw_networkx_labels(g, pos, labels=labels, font_size=7, ax=ax)

    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=10, label=status)
        for status, color in STATUS_COLORS.items()
    ]
    ax.legend(handles=handles, loc="upper right", title="status")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize a hypothesis_graph.json as a DAG image.")
    parser.add_argument("graph_path", type=str, help="Path to hypothesis_graph.json")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output image path (default: alongside input, .png)")
    args = parser.parse_args()

    graph_path = Path(args.graph_path)
    output_path = Path(args.output) if args.output else graph_path.with_suffix(".png")

    graph = HypothesisGraph.load(graph_path)
    plot_hypothesis_graph(graph, output_path)
    print(f"Saved visualization to {output_path}")


if __name__ == "__main__":
    main()
