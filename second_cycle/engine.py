from __future__ import annotations
import logging
from typing import Callable

from shared.llm import LLMClient
from shared.models import FirstCycleResult, SecondCycleResult
from second_cycle.coders import AxialCoder, FocusedCoder, PatternCoder, TheoreticalCoder

logger = logging.getLogger(__name__)


class SecondCycleEngine:
    def __init__(self, llm: LLMClient) -> None:
        self.pattern_coder = PatternCoder(llm)
        self.focused_coder = FocusedCoder(llm)
        self.axial_coder = AxialCoder(llm)
        self.theoretical_coder = TheoreticalCoder(llm)

    def run(
        self,
        first_cycle: FirstCycleResult,
        progress_callback: Callable[[str, str, float], None] | None = None,
    ) -> SecondCycleResult:
        result = SecondCycleResult()

        def _cb(stage: str, detail: str, local_pct: float) -> None:
            if progress_callback:
                # second cycle occupies 60%–95% of overall progress
                overall = 0.60 + local_pct * 0.35
                progress_callback(stage, detail, overall)

        logger.info("Second cycle: running pattern coding")
        _cb("second_cycle", "Pattern coding…", 0.0)
        result.pattern_codes = self.pattern_coder.analyze(first_cycle)
        _cb("second_cycle", f"Pattern coding complete — {len(result.pattern_codes)} patterns", 0.25)

        logger.info("Second cycle: running focused coding")
        _cb("second_cycle", "Focused coding…", 0.25)
        result.categories = self.focused_coder.analyze(first_cycle)
        _cb("second_cycle", f"Focused coding complete — {len(result.categories)} categories", 0.50)

        logger.info("Second cycle: running axial coding")
        _cb("second_cycle", "Axial coding…", 0.50)
        result.categories, result.axial_relationships = self.axial_coder.analyze(
            first_cycle, categories=result.categories
        )
        _cb("second_cycle", f"Axial coding complete — {len(result.axial_relationships)} relationships", 0.75)

        logger.info("Second cycle: running theoretical coding")
        _cb("second_cycle", "Theoretical coding…", 0.75)
        result.core_category, result.themes = self.theoretical_coder.analyze(
            first_cycle, categories=result.categories, relationships=result.axial_relationships
        )
        _cb("second_cycle", f"Theoretical coding complete — core: {result.core_category.name}", 1.0)

        logger.info(
            "Second cycle complete: %d categories, %d relationships, %d themes, core: %s",
            len(result.categories),
            len(result.axial_relationships),
            len(result.themes),
            result.core_category.name if result.core_category else "none",
        )
        return result
