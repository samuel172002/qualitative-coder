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


def build_interactive_html(
    G: nx.DiGraph,
    output_path: str | Path,
    title: str,
) -> None:
    if G.number_of_nodes() == 0:
        logger.warning("Empty graph — skipping HTML export for '%s'", title)
        return

    from pyvis.network import Network  # lazy import; pyvis is optional

    net = Network(
        height="750px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        directed=True,
        notebook=False,
    )

    for nid, data in G.nodes(data=True):
        node_type = data.get("node_type", "code")
        label_text = str(data.get("label", nid))
        color = COLOR_MAP.get(node_type, "#BDC3C7")
        pyvis_size = data.get("size", 1.0) * 10

        parts = [f"<b>{label_text}</b>", f"Type: {node_type}"]
        if "frequency" in data:
            parts.append(f"Frequency: {data['frequency']}")
        if "description" in data:
            parts.append(f"Description: {str(data['description'])[:200]}")
        if "full_statement" in data:
            parts.append(f"Statement: {str(data['full_statement'])[:200]}")
        if "theoretical_statement" in data:
            parts.append(f"Theory: {str(data['theoretical_statement'])[:200]}")
        if "level" in data:
            parts.append(f"Level: {data['level']}")

        net.add_node(
            nid,
            label=label_text,
            title="<br>".join(parts),
            color=color,
            size=pyvis_size,
            font={"size": 12, "color": "#ffffff"},
        )

    for src, tgt, data in G.edges(data=True):
        rel = data.get("relationship", "")
        style_info = EDGE_STYLES.get(rel, {"color": "#BDC3C7", "style": "solid", "width": 1.0})
        edge_label = "" if rel in SKIP_EDGE_LABELS else rel.replace("_", " ")
        net.add_edge(
            src, tgt,
            title=rel,
            label=edge_label,
            color=style_info["color"],
            width=max(style_info["width"], 1.0),
            arrows="to",
            font={"size": 9, "color": "#cccccc", "strokeWidth": 0},
        )

    net.set_options("""{
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 1.0
        },
        "minVelocity": 0.5,
        "maxVelocity": 30,
        "timestep": 0.2,
        "stabilization": {
          "enabled": true,
          "iterations": 300,
          "fit": true
        },
        "solver": "barnesHut"
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true,
        "keyboard": true
      },
      "edges": {
        "smooth": {"type": "curvedCW", "roundness": 0.2},
        "font": {"align": "middle"}
      },
      "nodes": {
        "shape": "dot",
        "scaling": {"min": 8, "max": 50},
        "borderWidth": 2,
        "borderWidthSelected": 4
      }
    }""")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output_path))

    # Freeze nodes once the initial layout stabilizes so the graph is static by default.
    # Users can still drag individual nodes manually.
    html = output_path.read_text(encoding="utf-8")
    freeze_js = (
        "<script>"
        "document.addEventListener('DOMContentLoaded',function(){"
        "var _t=setInterval(function(){"
        "if(typeof network!=='undefined'){"
        "clearInterval(_t);"
        "network.once('stabilized',function(){"
        "network.setOptions({physics:{enabled:false}});"
        "});"
        "}"
        "},100);"
        "});"
        "</script>"
    )
    output_path.write_text(html.replace("</body>", freeze_js + "</body>"), encoding="utf-8")
    logger.info("Saved interactive graph HTML: %s", output_path)


def _wrap_label(label: str, width: int = 16) -> str:
    return "\n".join(textwrap.wrap(label, width))


def draw_graph(
    G: nx.DiGraph,
    title: str,
    output_path: str | Path,
    figsize: tuple[int, int] = (16, 12),
    font_size: int = 10,
) -> None:
    if G.number_of_nodes() == 0:
        logger.warning("Empty graph — skipping draw for '%s'", title)
        return

    fig, ax = plt.subplots(figsize=figsize, facecolor="white")
    ax.set_facecolor("white")

    # Layout — spring with increased node spacing (~3× NetworkX default)
    import math as _math
    n = max(G.number_of_nodes(), 1)
    k_spacing = 3.0 / _math.sqrt(n)
    try:
        pos = nx.spring_layout(G, seed=42, k=k_spacing, iterations=100)
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
            width=style_info["width"] * 1.5,
            ax=ax,
            arrows=True,
            arrowsize=20,
            connectionstyle="arc3,rad=0.2",
            alpha=0.90,
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
    draw_graph(high_level, "Knowledge Graph — High-Level View", layer1_path, figsize=(24, 18))
    exported["layer1"] = str(layer1_path)
    layer1_html = graphs_dir / "layer1_high_level_graph.html"
    build_interactive_html(high_level, layer1_html, "Knowledge Graph — High-Level View")
    exported["layer1_html"] = str(layer1_html)

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
            figsize=(20, 15),
            font_size=9,
        )
        exported[f"layer2_{safe}"] = str(detail_path)
        detail_html = detail_dir / f"detail_{safe}.html"
        build_interactive_html(subgraph, detail_html, f"Detail: {label[:60]}")
        exported[f"layer2_{safe}_html"] = str(detail_html)

    logger.info("Exported %d graph images to %s", len(exported), graphs_dir)
    return exported
