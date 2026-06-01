from __future__ import annotations
import logging
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

logger = logging.getLogger(__name__)

COLOR_MAP = {
    "core": "#E74C3C",
    "theme": "#F39C12",
    "category": "#3498DB",
    "pattern": "#2ECC71",
    "code": "#9B59B6",
    "source": "#95A5A6",
}

EDGE_STYLES: dict[str, dict] = {
    "integrates_theme":    {"color": "#C0392B", "style": "solid",  "width": 2.5},
    "integrates_category": {"color": "#E74C3C", "style": "solid",  "width": 2.0},
    "grounded_in":         {"color": "#E67E22", "style": "solid",  "width": 1.8},
    "contains_pattern":    {"color": "#2980B9", "style": "dashed", "width": 1.5},
    "contains_code":       {"color": "#2980B9", "style": "dashed", "width": 1.0},
    "groups_code":         {"color": "#27AE60", "style": "dotted", "width": 1.0},
    "source_of":           {"color": "#7F8C8D", "style": "dotted", "width": 0.5},
    "causes":              {"color": "#8E44AD", "style": "solid",  "width": 1.8},
    "enables":             {"color": "#16A085", "style": "solid",  "width": 1.5},
    "constrains":          {"color": "#D35400", "style": "dashed", "width": 1.5},
    "is_context_for":      {"color": "#2C3E50", "style": "dashed", "width": 1.2},
    "leads_to":            {"color": "#8E44AD", "style": "solid",  "width": 1.5},
    "strategy_for":        {"color": "#1ABC9C", "style": "dashed", "width": 1.3},
}

SKIP_EDGE_LABELS = {"source_of", "contains_code", "groups_code"}


def _wrap_label(label: str, width: int = 16) -> str:
    return "\n".join(textwrap.wrap(label, width))


def draw_graph(
    G: nx.DiGraph,
    title: str,
    output_path: str | Path,
    figsize: tuple[int, int] = (16, 12),
    font_size: int = 8,
) -> None:
    if G.number_of_nodes() == 0:
        logger.warning("Empty graph — skipping draw for '%s'", title)
        return

    fig, ax = plt.subplots(figsize=figsize, facecolor="white")
    ax.set_facecolor("white")

    # Layout
    try:
        pos = nx.kamada_kawai_layout(G)
    except Exception:
        pos = nx.spring_layout(G, seed=42)

    # Group nodes by type
    type_groups: dict[str, list[str]] = {}
    for nid, data in G.nodes(data=True):
        t = data.get("node_type", "code")
        type_groups.setdefault(t, []).append(nid)

    # Draw nodes by type
    for node_type, node_list in type_groups.items():
        color = COLOR_MAP.get(node_type, "#BDC3C7")
        sizes = [G.nodes[n].get("size", 1.0) * 300 for n in node_list]
        nx.draw_networkx_nodes(G, pos, nodelist=node_list, node_color=color,
                               node_size=sizes, ax=ax, alpha=0.90)

    # Draw node labels
    labels = {nid: _wrap_label(str(data.get("label", nid)), 16)
              for nid, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=font_size,
                            font_weight="bold", ax=ax)

    # Group edges by relationship type
    rel_groups: dict[str, list[tuple[str, str]]] = {}
    for src, tgt, data in G.edges(data=True):
        rel = data.get("relationship", "leads_to")
        rel_groups.setdefault(rel, []).append((src, tgt))

    for rel, edge_list in rel_groups.items():
        style_info = EDGE_STYLES.get(rel, {"color": "#BDC3C7", "style": "solid", "width": 1.0})
        nx.draw_networkx_edges(
            G, pos, edgelist=edge_list,
            edge_color=style_info["color"],
            style=style_info["style"],
            width=style_info["width"],
            ax=ax,
            arrows=True,
            arrowsize=12,
            connectionstyle="arc3,rad=0.1",
            alpha=0.75,
        )

    # Edge labels for important relationships
    edge_labels: dict[tuple[str, str], str] = {}
    for src, tgt, data in G.edges(data=True):
        rel = data.get("relationship", "")
        if rel and rel not in SKIP_EDGE_LABELS:
            edge_labels[(src, tgt)] = rel.replace("_", " ")
    if edge_labels:
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=edge_labels,
            font_size=max(5, font_size - 2),
            ax=ax,
            bbox={"alpha": 0.5, "facecolor": "white", "edgecolor": "none"},
        )

    # Legend
    present_types = {data.get("node_type", "code") for _, data in G.nodes(data=True)}
    patches = [
        mpatches.Patch(color=COLOR_MAP.get(t, "#BDC3C7"), label=t.capitalize())
        for t in sorted(present_types, key=lambda x: ["core","theme","category","pattern","code","source"].index(x) if x in ["core","theme","category","pattern","code","source"] else 99)
    ]
    ax.legend(handles=patches, loc="upper left", fontsize=font_size, framealpha=0.8)

    ax.set_title(title, fontsize=font_size + 4, fontweight="bold", pad=16)
    ax.axis("off")
    plt.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved graph image: %s", output_path)


def export_graphs(
    graph_builder,
    output_dir: str | Path,
    max_high_level_nodes: int = 20,
) -> dict[str, str]:
    """Exports Layer 1 (high-level) and Layer 2 (per-node detail) graph images.

    Returns a dict mapping image keys to file paths.
    """
    output_dir = Path(output_dir)
    graphs_dir = output_dir / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    detail_dir = graphs_dir / "layer2_details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    exported: dict[str, str] = {}
    full_graph = graph_builder.graph

    # Layer 1
    high_level = graph_builder.get_high_level_subgraph(max_nodes=max_high_level_nodes)
    layer1_path = graphs_dir / "layer1_high_level_graph.png"
    draw_graph(high_level, "Knowledge Graph — High-Level View", layer1_path, figsize=(18, 13))
    exported["layer1"] = str(layer1_path)

    # Layer 2 — one detail image per Layer 1 node
    for nid, data in high_level.nodes(data=True):
        node_type = data.get("node_type", "")
        if node_type not in ("core", "theme", "category", "pattern"):
            continue
        subgraph = graph_builder.get_node_detail_subgraph(nid, depth=2)
        if subgraph.number_of_nodes() < 2:
            continue
        label = str(data.get("label", nid))
        safe = "".join(c if c.isalnum() else "_" for c in label)[:40]
        detail_path = detail_dir / f"detail_{safe}.png"
        draw_graph(
            subgraph,
            f"Detail: {label[:60]}",
            detail_path,
            figsize=(16, 12),
            font_size=8,
        )
        exported[f"layer2_{safe}"] = str(detail_path)

    logger.info("Exported %d graph images to %s", len(exported), graphs_dir)
    return exported
