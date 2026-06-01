from __future__ import annotations
import logging
from typing import Callable

from shared.llm import LLMClient
from shared.models import CodedSegment, FirstCycleResult, TextSegment
from first_cycle.coders import CODER_REGISTRY, BaseCoder, StructuralCoder

logger = logging.getLogger(__name__)

DEFAULT_METHODS = ["descriptive", "in_vivo", "process", "values"]


class FirstCycleEngine:
    def __init__(
        self,
        llm: LLMClient,
        methods: list[str] | None = None,
        research_questions: list[str] | None = None,
    ) -> None:
        self.llm = llm
        self.research_questions = research_questions or []
        selected = methods if methods is not None else DEFAULT_METHODS
        self.coders: list[BaseCoder] = []
        for name in selected:
            cls = CODER_REGISTRY.get(name)
            if cls is None:
                logger.warning("Unknown coding method: %s — skipping", name)
                continue
            if cls is StructuralCoder:
                self.coders.append(StructuralCoder(llm, research_questions=self.research_questions))
            else:
                self.coders.append(cls(llm))
        logger.info("FirstCycleEngine initialized with methods: %s", [c.method_name for c in self.coders])

    def run(
        self,
        segments: list[TextSegment],
        progress_callback: Callable[[str, str, float], None] | None = None,
    ) -> FirstCycleResult:
        result = FirstCycleResult()
        total = len(segments) * len(self.coders)
        done = 0

        for seg in segments:
            cs = CodedSegment(segment=seg)
            for coder in self.coders:
                logger.debug("Coding %s with %s", seg.segment_id, coder.method_name)
                codes = coder.code_segment(seg)
                cs.codes.extend(codes)
                done += 1
                if progress_callback:
                    pct = done / total if total > 0 else 1.0
                    progress_callback(
                        "first_cycle",
                        f"[{coder.method_name}] {seg.segment_id} → {len(codes)} codes",
                        pct * 0.6,  # first cycle is 60% of overall progress
                    )
            result.add_coded_segment(cs)

        logger.info(
            "First cycle complete: %d segments, %d unique codes",
            len(result.coded_segments),
            len(result.all_codes),
        )
        return result
