from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Callable

from shared.llm import LLMClient
from shared.models import FirstCycleResult, SecondCycleResult
from first_cycle.engine import FirstCycleEngine
from second_cycle.engine import SecondCycleEngine
from agent.file_loader import load_and_segment
from agent.knowledge_graph import KnowledgeGraphBuilder
from agent.visualizer import export_graphs

logger = logging.getLogger(__name__)


class QualitativeCodingAgent:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        first_cycle_methods: list[str] | None = None,
        research_questions: list[str] | None = None,
        max_segments: int = 0,
    ) -> None:
        self.llm = LLMClient(api_key=api_key, model=model)
        self.first_cycle_methods = first_cycle_methods
        self.research_questions = research_questions or []
        self.max_segments = max_segments

    def run(
        self,
        input_files: list[str],
        output_dir: str = "./output",
        max_segment_chars: int = 2500,
        progress_callback: Callable[[str, str, float], None] | None = None,
    ) -> dict:
        start_time = time.time()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        def _cb(stage: str, detail: str, pct: float) -> None:
            logger.info("[%s] %.0f%% — %s", stage, pct * 100, detail)
            if progress_callback:
                progress_callback(stage, detail, pct)

        # 1. Load and segment
        _cb("loading", "Loading and segmenting files…", 0.02)
        segments = load_and_segment(input_files, max_segment_chars=max_segment_chars)
        source_files = list({s.source_file for s in segments})

        if self.max_segments and len(segments) > self.max_segments:
            logger.info("Limiting to %d segments (from %d)", self.max_segments, len(segments))
            segments = segments[: self.max_segments]

        _cb("loading", f"Loaded {len(segments)} segments from {len(source_files)} file(s)", 0.05)

        # 2. First cycle
        _cb("first_cycle", "Starting first cycle coding…", 0.05)
        fc_engine = FirstCycleEngine(
            self.llm,
            methods=self.first_cycle_methods,
            research_questions=self.research_questions,
        )
        first_cycle: FirstCycleResult = fc_engine.run(segments, progress_callback=_cb)
        first_cycle.source_files = source_files

        _save_json(output_path / "first_cycle_codes.json", _serialize_first_cycle(first_cycle))
        _cb("first_cycle", "First cycle saved", 0.62)

        # 3. Second cycle
        _cb("second_cycle", "Starting second cycle coding…", 0.62)
        sc_engine = SecondCycleEngine(self.llm)
        second_cycle: SecondCycleResult = sc_engine.run(first_cycle, progress_callback=_cb)

        _save_json(output_path / "second_cycle_results.json", _serialize_second_cycle(second_cycle))
        _cb("second_cycle", "Second cycle saved", 0.95)

        # 4. Knowledge graph
        _cb("graph", "Building knowledge graph…", 0.95)
        graph_builder = KnowledgeGraphBuilder()
        graph_builder.build(first_cycle, second_cycle)
        graph_json = graph_builder.to_json()
        _save_json(output_path / "knowledge_graph.json", graph_json)

        # 5. Export graph images
        _cb("graph", "Exporting graph visualizations…", 0.97)
        exported_images = export_graphs(graph_builder, output_path)

        # 6. Summary
        elapsed = time.time() - start_time
        summary = {
            "run_time_seconds": round(elapsed, 1),
            "input_files": source_files,
            "total_segments": len(segments),
            "unique_codes": len(first_cycle.all_codes),
            "categories": len(second_cycle.categories),
            "themes": len(second_cycle.themes),
            "core_category": second_cycle.core_category.name if second_cycle.core_category else None,
            "graph_nodes": graph_json["metadata"]["total_nodes"],
            "graph_edges": graph_json["metadata"]["total_edges"],
            "exported_images": list(exported_images.keys()),
            "output_dir": str(output_path.resolve()),
        }

        # 7. PDF report
        _cb("pdf", "Generating PDF report…", 0.98)
        try:
            from agent.pdf_exporter import PDFExporter
            pdf_path = PDFExporter().export(first_cycle, second_cycle, summary, output_path)
            summary["pdf_report"] = pdf_path
        except Exception as exc:
            logger.warning("PDF generation failed (non-fatal): %s", exc)
            summary["pdf_report"] = None

        _save_json(output_path / "analysis_summary.json", summary)
        _cb("done", "Analysis complete", 1.0)

        logger.info(
            "Pipeline complete in %.1fs — %d segments, %d codes, %d categories, %d themes",
            elapsed, len(segments), len(first_cycle.all_codes),
            len(second_cycle.categories), len(second_cycle.themes),
        )
        return summary


def _save_json(path: Path, data: dict | list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug("Saved %s", path)


def _serialize_first_cycle(fc: FirstCycleResult) -> dict:
    segments_out = []
    for cs in fc.coded_segments:
        seg = cs.segment
        segments_out.append({
            "segment_id": seg.segment_id,
            "source_file": seg.source_file,
            "text_preview": seg.text[:200],
            "codes": [
                {
                    "label": c.display_label,
                    "type": c.code_type.value,
                    "description": c.description,
                    "excerpt": c.excerpt,
                    "confidence": c.confidence,
                }
                for c in cs.codes
            ],
        })
    return {
        "source_files": fc.source_files,
        "code_frequencies": dict(sorted(fc.code_frequencies.items(), key=lambda x: -x[1])),
        "coded_segments": segments_out,
    }


def _serialize_second_cycle(sc: SecondCycleResult) -> dict:
    return {
        "pattern_codes": sc.pattern_codes,
        "categories": [
            {
                "name": c.name,
                "description": c.description,
                "member_codes": c.codes,
                "frequency": c.frequency,
                "properties": c.properties,
                "dimensions": c.dimensions,
            }
            for c in sc.categories
        ],
        "axial_relationships": [
            {
                "source": r.source_category,
                "target": r.target_category,
                "type": r.relationship_type,
                "description": r.description,
                "conditions": r.conditions,
                "consequences": r.consequences,
            }
            for r in sc.axial_relationships
        ],
        "themes": [
            {
                "statement": t.statement,
                "categories": t.categories,
                "evidence": t.evidence,
                "level": t.level,
            }
            for t in sc.themes
        ],
        "core_category": (
            {
                "name": sc.core_category.name,
                "description": sc.core_category.description,
                "theoretical_statement": sc.core_category.theoretical_statement,
                "related_categories": sc.core_category.related_categories,
            }
            if sc.core_category else None
        ),
    }
