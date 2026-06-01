from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from shared.models import (
    AxialRelationship,
    Category,
    CoreCategory,
    FirstCycleResult,
    Theme,
)

if TYPE_CHECKING:
    from shared.llm import LLMClient

logger = logging.getLogger(__name__)


class BaseSecondCycleCoder(ABC):
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _format_code_summary(self, first_cycle: FirstCycleResult, top_n: int = 60) -> str:
        sorted_codes = sorted(
            first_cycle.code_frequencies.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        lines = ["TOP FIRST-CYCLE CODES (label | frequency | type | sample excerpt):"]
        for label, freq in sorted_codes:
            code_list = first_cycle.all_codes.get(label, [])
            if not code_list:
                continue
            code_obj = code_list[0]
            excerpt = code_obj.excerpt[:60].replace("\n", " ") if code_obj.excerpt else ""
            lines.append(f"  {label} | freq={freq} | {code_obj.code_type.value} | \"{excerpt}\"")
        return "\n".join(lines)

    @abstractmethod
    def analyze(self, first_cycle: FirstCycleResult, **kwargs): ...


class PatternCoder(BaseSecondCycleCoder):
    def analyze(self, first_cycle: FirstCycleResult, **kwargs) -> dict[str, list[str]]:
        code_summary = self._format_code_summary(first_cycle)
        system_prompt = (
            "You are a qualitative researcher applying Pattern Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "PATTERN CODING groups first-cycle codes into meta-patterns — explanatory or inferential categories "
            "that synthesize large blocks of data. Pattern codes identify themes, causes, relationships, "
            "or theoretical constructs.\n"
            "Saldaña: 'Many pattern codes are captured in the form of metaphors where they can synthesize "
            "large blocks of data in a single trope.'\n\n"
            "Rules:\n"
            "- Create 5–15 meta-patterns from the first-cycle codes\n"
            "- Each pattern should meaningfully group related codes\n"
            "- Pattern names should be conceptually rich and evocative\n"
            "- Every first-cycle code should belong to at least one pattern\n"
            "- Patterns may overlap (a code can belong to multiple patterns)\n\n"
            "Return JSON: {\"patterns\": [{\"name\": \"PATTERN NAME\", \"codes\": [\"CODE1\", \"CODE2\", ...], "
            "\"rationale\": \"why these codes form a pattern\"}]}"
        )
        user_prompt = f"Analyze these first-cycle codes and group them into meta-patterns:\n\n{code_summary}"

        try:
            response = self.llm.query_json(system_prompt, user_prompt, max_tokens=2048)
            pattern_list = response.get("patterns", []) if isinstance(response, dict) else []
            result: dict[str, list[str]] = {}
            for item in pattern_list:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).upper().strip()
                codes = [str(c).upper() for c in item.get("codes", [])]
                if name and codes:
                    result[name] = codes
            logger.info("Pattern coding produced %d meta-patterns", len(result))
            return result
        except Exception as exc:
            logger.error("Pattern coding failed: %s", exc)
            return {}


class FocusedCoder(BaseSecondCycleCoder):
    def analyze(self, first_cycle: FirstCycleResult, **kwargs) -> list[Category]:
        code_summary = self._format_code_summary(first_cycle)
        system_prompt = (
            "You are a qualitative researcher applying Focused Coding as defined by Charmaz (2006) "
            "and Saldaña in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "FOCUSED CODING searches for the most frequent or significant initial codes and uses them "
            "to sift, sort, and synthesize large amounts of data. It develops the most salient categories.\n"
            "Charmaz: Focused coding requires decisions about 'which initial codes make the most analytic sense.'\n\n"
            "Rules:\n"
            "- Develop 5–12 focused categories from the first-cycle codes\n"
            "- Category names should use gerunds when possible (STRUGGLING WITH CHANGE, BUILDING COMMUNITY)\n"
            "- Each category should be substantive and analytically meaningful\n"
            "- Include: name, description, which first-cycle codes belong to it, and how frequent it is\n"
            "- Frequency = total count of member codes across the dataset\n\n"
            "Return JSON: {\"categories\": [{\"name\": \"CATEGORY NAME\", \"description\": \"what this category captures\", "
            "\"member_codes\": [\"CODE1\", \"CODE2\", ...], \"frequency\": 5}]}"
        )
        user_prompt = f"Develop focused categories from these first-cycle codes:\n\n{code_summary}"

        try:
            response = self.llm.query_json(system_prompt, user_prompt, max_tokens=2048)
            cat_list = response.get("categories", []) if isinstance(response, dict) else []
            categories: list[Category] = []
            for item in cat_list:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).upper().strip()
                if not name:
                    continue
                member_codes = [str(c).upper() for c in item.get("member_codes", [])]
                freq = int(item.get("frequency", 0))
                if freq == 0:
                    freq = sum(first_cycle.code_frequencies.get(c, 0) for c in member_codes)
                categories.append(Category(
                    name=name,
                    description=item.get("description", ""),
                    codes=member_codes,
                    frequency=freq,
                ))
            logger.info("Focused coding produced %d categories", len(categories))
            return categories
        except Exception as exc:
            logger.error("Focused coding failed: %s", exc)
            return []


class AxialCoder(BaseSecondCycleCoder):
    def analyze(
        self,
        first_cycle: FirstCycleResult,
        categories: list[Category] | None = None,
        **kwargs,
    ) -> tuple[list[Category], list[AxialRelationship]]:
        categories = categories or []
        code_summary = self._format_code_summary(first_cycle, top_n=40)
        cat_text = "\n".join(
            f"  {c.name}: {c.description} [codes: {', '.join(c.codes[:5])}]"
            for c in categories
        )
        system_prompt = (
            "You are a qualitative researcher applying Axial Coding as defined by Strauss & Corbin (1998) "
            "and Saldaña in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "AXIAL CODING relates categories to subcategories by specifying their properties and dimensions, "
            "and identifying causal relationships using the paradigm:\n"
            "  CONDITIONS → ACTIONS/INTERACTIONS → CONSEQUENCES\n\n"
            "Rules:\n"
            "- Specify properties (characteristics) for each category\n"
            "- Specify dimensions (the range along which properties vary) for each category\n"
            "- Identify relationships between categories. Relationship types:\n"
            "  causes, enables, constrains, is_context_for, leads_to, strategy_for\n"
            "- Each relationship should name conditions under which it holds and its consequences\n\n"
            "Return JSON with two arrays:\n"
            "{\n"
            "  \"enriched_categories\": [{\"name\": \"CAT NAME\", \"properties\": {\"key\": \"value\"}, "
            "\"dimensions\": {\"key\": \"low–high range\"}}],\n"
            "  \"relationships\": [{\"source\": \"CAT A\", \"target\": \"CAT B\", \"type\": \"causes\", "
            "\"description\": \"...\", \"conditions\": [\"...\"], \"consequences\": [\"...\"]}]\n"
            "}"
        )
        user_prompt = (
            f"Focused categories:\n{cat_text}\n\n"
            f"First-cycle code summary:\n{code_summary}\n\n"
            "Apply axial coding: enrich categories with properties/dimensions and identify relationships."
        )

        try:
            response = self.llm.query_json(system_prompt, user_prompt, max_tokens=3000)
            enriched_raw = response.get("enriched_categories", []) if isinstance(response, dict) else []
            rels_raw = response.get("relationships", []) if isinstance(response, dict) else []

            # Enrich existing categories
            enrich_map: dict[str, dict] = {}
            for item in enriched_raw:
                if isinstance(item, dict):
                    n = str(item.get("name", "")).upper().strip()
                    if n:
                        enrich_map[n] = item

            enriched_cats: list[Category] = []
            for cat in categories:
                enrich = enrich_map.get(cat.name, {})
                cat.properties = enrich.get("properties", cat.properties)
                cat.dimensions = enrich.get("dimensions", cat.dimensions)
                enriched_cats.append(cat)

            relationships: list[AxialRelationship] = []
            for item in rels_raw:
                if not isinstance(item, dict):
                    continue
                src = str(item.get("source", "")).upper().strip()
                tgt = str(item.get("target", "")).upper().strip()
                rel_type = str(item.get("type", "leads_to")).lower().strip()
                if src and tgt:
                    relationships.append(AxialRelationship(
                        source_category=src,
                        target_category=tgt,
                        relationship_type=rel_type,
                        description=item.get("description", ""),
                        conditions=list(item.get("conditions", [])),
                        consequences=list(item.get("consequences", [])),
                    ))

            logger.info("Axial coding produced %d enriched categories, %d relationships", len(enriched_cats), len(relationships))
            return enriched_cats, relationships
        except Exception as exc:
            logger.error("Axial coding failed: %s", exc)
            return categories, []


class TheoreticalCoder(BaseSecondCycleCoder):
    def analyze(
        self,
        first_cycle: FirstCycleResult,
        categories: list[Category] | None = None,
        relationships: list[AxialRelationship] | None = None,
        **kwargs,
    ) -> tuple[CoreCategory, list[Theme]]:
        categories = categories or []
        relationships = relationships or []
        code_summary = self._format_code_summary(first_cycle, top_n=30)
        cat_text = "\n".join(f"  {c.name}: {c.description}" for c in categories)
        rel_text = "\n".join(
            f"  {r.source_category} --[{r.relationship_type}]--> {r.target_category}: {r.description}"
            for r in relationships
        )
        system_prompt = (
            "You are a qualitative researcher applying Theoretical Coding as defined by Glaser (1978), "
            "Strauss & Corbin (1998), and Saldaña in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "THEORETICAL CODING identifies ONE central/core category that integrates all other categories "
            "and leads toward a theory grounded in the data.\n\n"
            "The core category must:\n"
            "- Appear frequently and have explanatory power\n"
            "- Relate meaningfully to all other categories\n"
            "- Be abstract enough to have theoretical implications\n"
            "- Lead toward a theoretical statement moving from particular to general\n\n"
            "Glaser's Six C's to consider: Causes, Contexts, Contingencies, Consequences, Covariances, Conditions\n"
            "Saldaña warns: 'mere numeric frequency is not necessarily a reliable indicator of a core category'\n\n"
            "Also identify 2–5 major themes. A theme is a full sentence (not a label) that captures a key insight.\n"
            "Level: 'manifest' = visible in the data; 'latent' = underlying and interpretive.\n\n"
            "Return JSON:\n"
            "{\n"
            "  \"core_category\": {\"name\": \"CORE NAME\", \"description\": \"...\", "
            "\"related_categories\": [\"CAT A\", ...], "
            "\"theoretical_statement\": \"When X happens under Y conditions, Z results because...\"},\n"
            "  \"themes\": [{\"statement\": \"Full sentence theme\", \"categories\": [\"CAT A\", ...], "
            "\"evidence\": [\"quote or paraphrase\"], \"level\": \"manifest|latent\"}]\n"
            "}"
        )
        user_prompt = (
            f"Categories:\n{cat_text}\n\n"
            f"Relationships:\n{rel_text}\n\n"
            f"Top codes:\n{code_summary}\n\n"
            "Identify the core category and major themes."
        )

        try:
            response = self.llm.query_json(system_prompt, user_prompt, max_tokens=3000)
            if not isinstance(response, dict):
                raise ValueError("Expected dict response")

            core_raw = response.get("core_category", {})
            themes_raw = response.get("themes", [])

            core = CoreCategory(
                name=str(core_raw.get("name", "CORE CATEGORY")).upper().strip(),
                description=core_raw.get("description", ""),
                related_categories=[str(c).upper() for c in core_raw.get("related_categories", [])],
                theoretical_statement=core_raw.get("theoretical_statement", ""),
            )

            themes: list[Theme] = []
            for item in themes_raw:
                if not isinstance(item, dict):
                    continue
                statement = item.get("statement", "")
                if not statement:
                    continue
                themes.append(Theme(
                    statement=statement,
                    categories=[str(c).upper() for c in item.get("categories", [])],
                    evidence=list(item.get("evidence", [])),
                    level=item.get("level", "manifest"),
                ))
            core.themes = themes

            logger.info("Theoretical coding: core category '%s', %d themes", core.name, len(themes))
            return core, themes
        except Exception as exc:
            logger.error("Theoretical coding failed: %s", exc)
            fallback_core = CoreCategory(
                name="CORE CATEGORY",
                description="Could not determine core category",
                theoretical_statement="",
            )
            return fallback_core, []
