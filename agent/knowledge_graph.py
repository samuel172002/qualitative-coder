from __future__ import annotations
import hashlib
import logging
import re
from collections import deque

import networkx as nx

from shared.models import FirstCycleResult, SecondCycleResult

logger = logging.getLogger(__name__)

TOP_CODES = 50

NODE_SIZES = {
    "core": 5.0,
    "theme": 3.5,
    "category": 2.5,
    "pattern": 2.0,
    "code": 1.0,
    "source": 1.0,
}

TYPE_PRIORITY = {"core": 0, "theme": 1, "category": 2, "pattern": 3, "code": 4, "source": 5}


def _safe_name(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", label)[:30]


def _node_id(prefix: str, label: str) -> str:
    h = hashlib.md5(f"{prefix}:{label}".encode()).hexdigest()[:6]
    return f"{prefix}_{_safe_name(label)}_{h}"


class KnowledgeGraphBuilder:
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._first_cycle: FirstCycleResult | None = None
        self._second_cycle: SecondCycleResult | None = None

    def build(self, first_cycle: FirstCycleResult, second_cycle: SecondCycleResult) -> nx.DiGraph:
        self._first_cycle = first_cycle
        self._second_cycle = second_cycle
        G = nx.DiGraph()

        # Top codes by frequency
        top_codes = sorted(
            first_cycle.code_frequencies.items(), key=lambda x: x[1], reverse=True
        )[:TOP_CODES]
        max_freq = top_codes[0][1] if top_codes else 1

        code_node_ids: dict[str, str] = {}
        for label, freq in top_codes:
            nid = _node_id("code", label)
            code_node_ids[label] = nid
            size = 0.5 + 1.5 * (freq / max_freq)
            G.add_node(nid, label=label, node_type="code", size=size, frequency=freq)

        # Source file nodes
        source_node_ids: dict[str, str] = {}
        for src in first_cycle.source_files:
            nid = _node_id("source", src)
            source_node_ids[src] = nid
            G.add_node(nid, label=src, node_type="source", size=NODE_SIZES["source"])

        # Category nodes
        cat_node_ids: dict[str, str] = {}
        for cat in second_cycle.categories:
            nid = _node_id("cat", cat.name)
            cat_node_ids[cat.name] = nid
            G.add_node(nid, label=cat.name, node_type="category",
                       size=NODE_SIZES["category"], description=cat.description,
                       frequency=cat.frequency, properties=cat.properties,
                       dimensions=cat.dimensions)
            # edges: category → member codes
            for code_label in cat.codes:
                code_nid = code_node_ids.get(code_label)
                if code_nid:
                    G.add_edge(nid, code_nid, relationship="contains_code", weight=1.0)

        # Pattern nodes
        pattern_node_ids: dict[str, str] = {}
        for pattern_name, member_codes in second_cycle.pattern_codes.items():
            nid = _node_id("pattern", pattern_name)
            pattern_node_ids[pattern_name] = nid
            G.add_node(nid, label=pattern_name, node_type="pattern", size=NODE_SIZES["pattern"])
            for code_label in member_codes:
                code_nid = code_node_ids.get(code_label)
                if code_nid:
                    G.add_edge(nid, code_nid, relationship="groups_code", weight=0.8)

        # Axial relationships between categories
        for rel in second_cycle.axial_relationships:
            src_nid = cat_node_ids.get(rel.source_category)
            tgt_nid = cat_node_ids.get(rel.target_category)
            if src_nid and tgt_nid:
                G.add_edge(src_nid, tgt_nid,
                           relationship=rel.relationship_type,
                           weight=1.5,
                           description=rel.description)

        # Theme nodes
        theme_node_ids: dict[str, str] = {}
        for theme in second_cycle.themes:
            nid = _node_id("theme", theme.statement[:40])
            theme_node_ids[theme.statement] = nid
            G.add_node(nid, label=theme.statement[:60], node_type="theme",
                       size=NODE_SIZES["theme"], level=theme.level,
                       full_statement=theme.statement)
            for cat_name in theme.categories:
                cat_nid = cat_node_ids.get(cat_name)
                if cat_nid:
                    G.add_edge(nid, cat_nid, relationship="integrates_category", weight=2.0)

        # Core category node
        if second_cycle.core_category:
            core = second_cycle.core_category
            core_nid = _node_id("core", core.name)
            G.add_node(core_nid, label=core.name, node_type="core",
                       size=NODE_SIZES["core"], description=core.description,
                       theoretical_statement=core.theoretical_statement)
            # core → categories
            for cat_name in core.related_categories:
                cat_nid = cat_node_ids.get(cat_name)
                if cat_nid:
                    G.add_edge(core_nid, cat_nid, relationship="integrates_category", weight=2.5)
            # core → themes
            for theme in core.themes:
                theme_nid = theme_node_ids.get(theme.statement)
                if theme_nid:
                    G.add_edge(core_nid, theme_nid, relationship="integrates_theme", weight=2.5)

        # Source → code edges
        for src_name, src_nid in source_node_ids.items():
            for cs in (self._first_cycle.coded_segments if self._first_cycle else []):
                if cs.segment.source_file == src_name:
                    for code in cs.codes:
                        code_nid = code_node_ids.get(code.label)
                        if code_nid and not G.has_edge(src_nid, code_nid):
                            G.add_edge(src_nid, code_nid, relationship="source_of", weight=0.3)

        self.graph = G
        logger.info("Knowledge graph built: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
        return G

    def to_json(self) -> dict:
        G = self.graph
        nodes = []
        for nid, data in G.nodes(data=True):
            node = {"id": nid}
            node.update(data)
            nodes.append(node)
        edges = []
        for src, tgt, data in G.edges(data=True):
            edge = {"source": src, "target": tgt}
            edge.update(data)
            edges.append(edge)
        type_counts: dict[str, int] = {}
        for _, data in G.nodes(data=True):
            t = data.get("node_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "node_types": type_counts,
            },
        }

    def get_high_level_subgraph(self, max_nodes: int = 20) -> nx.DiGraph:
        G = self.graph
        candidates = [
            (data.get("node_type", "code"), -data.get("size", 1.0), nid)
            for nid, data in G.nodes(data=True)
            if data.get("node_type") in ("core", "theme", "category", "pattern")
        ]
        candidates.sort(key=lambda x: (TYPE_PRIORITY.get(x[0], 99), x[1]))
        selected = [nid for _, _, nid in candidates[:max_nodes]]
        return G.subgraph(selected).copy()

    def get_node_detail_subgraph(self, node_id: str, depth: int = 2) -> nx.DiGraph:
        G = self.graph
        if node_id not in G:
            return nx.DiGraph()
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current, d = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if d < depth:
                for neighbor in list(G.successors(current)) + list(G.predecessors(current)):
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))
        return G.subgraph(visited).copy()
