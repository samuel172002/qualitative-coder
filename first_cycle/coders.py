from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from shared.models import Code, CodeType, EvaluationPolarity, TextSegment, ValuesSubtype

if TYPE_CHECKING:
    from shared.llm import LLMClient

logger = logging.getLogger(__name__)


class BaseCoder(ABC):
    code_type: CodeType
    method_name: str

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @abstractmethod
    def system_prompt(self) -> str: ...

    def code_segment(self, segment: TextSegment) -> list[Code]:
        user_prompt = (
            f"Text segment to code (segment ID: {segment.segment_id}):\n\n"
            f"{segment.text}"
        )
        try:
            response = self.llm.query_json(self.system_prompt(), user_prompt, max_tokens=1024)
            return self._parse_codes(response, segment.text)
        except Exception as exc:
            logger.warning("Coder %s failed on segment %s: %s", self.method_name, segment.segment_id, exc)
            return []

    @abstractmethod
    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]: ...


# ---------------------------------------------------------------------------
# Elemental coders
# ---------------------------------------------------------------------------

class DescriptiveCoder(BaseCoder):
    code_type = CodeType.DESCRIPTIVE
    method_name = "descriptive"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Descriptive Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "DESCRIPTIVE CODING assigns labels that are nouns or short noun phrases summarizing the TOPIC "
            "of a passage — what it is ABOUT, not what it means.\n"
            "Rules:\n"
            "- Codes must be nouns or noun phrases (e.g., SECURITY, TEACHER WORKLOAD, STUDENT CONFUSION)\n"
            "- Write codes in UPPER CASE\n"
            "- Each code captures the topical essence of a portion of the text\n"
            "- A single passage may have 1–4 descriptive codes\n"
            "- Do NOT interpret meaning — just label the topic\n"
            "- Example: field notes about a teacher struggling with technology → TECHNOLOGY CHALLENGES\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"TOPIC\", \"excerpt\": \"short quote from text\", "
            "\"description\": \"one sentence explaining the topic\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label:
                continue
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


class InVivoCoder(BaseCoder):
    code_type = CodeType.IN_VIVO
    method_name = "in_vivo"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying In Vivo Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "IN VIVO CODING uses the EXACT words or short phrases from the participant's own language as codes. "
            "These codes ALWAYS appear in quotation marks to distinguish them from researcher-generated codes.\n"
            "Rules:\n"
            "- Extract only the participant's own words — never paraphrase\n"
            "- Prioritize: impactful nouns, strong action verbs, metaphors, ironic phrases, repeated words\n"
            "- Codes should be 2–8 words, capturing something memorable or analytically significant\n"
            "- Write in UPPER CASE with quotation marks: \"A LOT TO LEARN\"\n"
            "- Saldaña: 'In Vivo Codes can provide a crucial check on whether you have grasped what is significant'\n"
            "- A passage may yield 1–5 in vivo codes\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"\\\"EXACT WORDS\\\"\", \"excerpt\": \"the full sentence it comes from\", "
            "\"description\": \"why this phrase is analytically significant\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            # Ensure quotation marks
            if not label.startswith('"'):
                label = f'"{label.upper()}"'
            else:
                label = label.upper()
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


class ProcessCoder(BaseCoder):
    code_type = CodeType.PROCESS
    method_name = "process"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Process Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "PROCESS CODING uses GERUNDS — words ending in -ing — exclusively as codes to capture action and movement.\n"
            "Rules:\n"
            "- Every code MUST be a gerund or gerund phrase (e.g., ADAPTING, NEGOTIATING ROLES, SURVIVING CHANGE)\n"
            "- Capture both observable activity (READING, WATCHING) and conceptual processes (STRUGGLING, RESISTING)\n"
            "- Saldaña: processes can be 'strategic, routine, random, novel, automatic, and/or thoughtful'\n"
            "- Write in UPPER CASE\n"
            "- Example: teacher lines students up for lunch → LINING UP FOR LUNCH\n"
            "- A passage may yield 1–4 process codes\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"GERUND PHRASE\", \"excerpt\": \"short quote from text\", "
            "\"description\": \"what action or process is occurring\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label:
                continue
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


class InitialCoder(BaseCoder):
    code_type = CodeType.INITIAL
    method_name = "initial"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Initial Coding (Open Coding) as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "INITIAL CODING is an open-ended first pass — the starting point for grounded theory. "
            "Codes can be anything: descriptive, in vivo, process-based, or conceptual.\n"
            "Rules:\n"
            "- Code closely, almost line-by-line\n"
            "- Use your first-impression response to the data\n"
            "- No restrictions on code form — be open and exploratory\n"
            "- Write codes in UPPER CASE\n"
            "- Aim for 3–8 codes per passage to capture all nuances\n"
            "- Ask yourself: 'What is happening here? What is the person doing or experiencing?'\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"CODE\", \"excerpt\": \"short quote from text\", "
            "\"description\": \"first-impression interpretation\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label:
                continue
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


class StructuralCoder(BaseCoder):
    code_type = CodeType.STRUCTURAL
    method_name = "structural"

    def __init__(self, llm: LLMClient, research_questions: list[str] | None = None) -> None:
        super().__init__(llm)
        self.research_questions = research_questions or []

    def system_prompt(self) -> str:
        rq_section = ""
        if self.research_questions:
            rq_list = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(self.research_questions))
            rq_section = f"\n\nResearch Questions to code for:\n{rq_list}\n"
        return (
            "You are a qualitative researcher applying Structural Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "STRUCTURAL CODING ties codes directly to specific research questions. "
            "It acts as 'a labeling and indexing device, allowing researchers to quickly access data "
            "likely to be relevant to a particular analysis.'"
            + rq_section
            + "\nRules:\n"
            "- Each code should reference which research question the passage addresses\n"
            "- Format: RQ[N]: TOPIC (e.g., RQ1: PROFESSIONAL SUPPORT STRUCTURES)\n"
            "- If no research questions are provided, create structural labels that categorize the passage type\n"
            "- Write codes in UPPER CASE\n"
            "- A passage may address 1–3 research questions\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"RQ1: TOPIC\", \"excerpt\": \"short quote\", "
            "\"description\": \"how this passage addresses the research question\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label:
                continue
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


# ---------------------------------------------------------------------------
# Affective coders
# ---------------------------------------------------------------------------

class EmotionCoder(BaseCoder):
    code_type = CodeType.EMOTION
    method_name = "emotion"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Emotion Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "EMOTION CODING labels the emotions recalled, experienced, or inferred in the text.\n"
            "Rules:\n"
            "- Use precise, specific emotion words — not just 'happy' but ELATION, CONTENTMENT, RELIEF\n"
            "- Not just 'sad' but GRIEF, DISAPPOINTMENT, DESPONDENCY\n"
            "- Mark whether emotion is EXPLICIT (stated outright) or INFERRED (implied by context)\n"
            "- Mark intensity: mild, moderate, or intense\n"
            "- If ANGER appears, look for the underlying trigger emotion (SHAME, EMBARRASSMENT, FEAR)\n"
            "- Write emotion labels in UPPER CASE\n"
            "- A passage may yield 1–4 emotion codes\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"EMOTION_NAME\", \"excerpt\": \"quote that reveals emotion\", "
            "\"description\": \"context of the emotion\", \"explicit\": true/false, "
            "\"intensity\": \"mild|moderate|intense\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label:
                continue
            explicit = item.get("explicit", True)
            intensity = item.get("intensity", "moderate")
            desc = item.get("description", "")
            full_desc = f"[{'explicit' if explicit else 'inferred'}, {intensity}] {desc}"
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=full_desc,
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


class ValuesCoder(BaseCoder):
    code_type = CodeType.VALUES
    method_name = "values"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Values Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "VALUES CODING identifies three types of constructs:\n"
            "- VALUE (V:) — what someone considers important; 'the greater the personal meaning, the greater the value'\n"
            "  Example: V: PROFESSIONAL GROWTH\n"
            "- ATTITUDE (A:) — how one thinks and feels about something; evaluative and affective\n"
            "  Example: A: COLLEGE IS SCARY\n"
            "- BELIEF (B:) — part of a system including values, attitudes, experiences, opinions, and prejudices\n"
            "  Example: B: PERSEVERANCE NETS SUCCESS\n"
            "Rules:\n"
            "- Always prefix with V:, A:, or B:\n"
            "- Write code labels in UPPER CASE after the prefix\n"
            "- Distinguish carefully: a value is something cherished; an attitude is a stance; a belief is a conviction\n"
            "- A passage may yield 1–4 values codes\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"LABEL WITHOUT PREFIX\", \"subtype\": \"V|A|B\", "
            "\"excerpt\": \"quote from text\", \"description\": \"explanation of this value/attitude/belief\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        subtype_map = {"V": ValuesSubtype.VALUE, "A": ValuesSubtype.ATTITUDE, "B": ValuesSubtype.BELIEF}
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            # Strip any prefix the LLM accidentally included
            for prefix in ("V: ", "A: ", "B: "):
                if label.startswith(prefix):
                    label = label[len(prefix):]
            if not label:
                continue
            raw_subtype = str(item.get("subtype", "V")).upper().strip()
            subtype = subtype_map.get(raw_subtype, ValuesSubtype.VALUE)
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
                values_subtype=subtype,
            ))
        return codes


class VersusCoder(BaseCoder):
    code_type = CodeType.VERSUS
    method_name = "versus"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Versus Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "VERSUS CODING identifies conflicts, tensions, dilemmas, and power dynamics in the data.\n"
            "Rules:\n"
            "- Format MUST be: X VS. Y (e.g., TEACHERS VS. ADMINISTRATORS, DESIRE VS. DUTY)\n"
            "- Both sides must be clearly named\n"
            "- Conflicts can be between: people, groups, organizations, concepts, processes, ideologies\n"
            "- Look for: tensions, contradictions, power imbalances, competing interests, inner dilemmas\n"
            "- Conflicts may be explicit (stated) or implicit (implied)\n"
            "- Write in UPPER CASE\n"
            "- A passage may yield 0–3 versus codes (not every passage has conflict)\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"X VS. Y\", \"excerpt\": \"quote showing the tension\", "
            "\"description\": \"nature of the conflict or tension\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label or "VS." not in label:
                continue
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
            ))
        return codes


class EvaluationCoder(BaseCoder):
    code_type = CodeType.EVALUATION
    method_name = "evaluation"

    def system_prompt(self) -> str:
        return (
            "You are a qualitative researcher applying Evaluation Coding as defined by Johnny Saldaña "
            "in 'The Coding Manual for Qualitative Researchers'.\n\n"
            "EVALUATION CODING assigns judgments of quality — merit, worth, and significance.\n"
            "Rules:\n"
            "- Each code has a polarity: + (positive), - (negative), or 0 (neutral/mixed)\n"
            "- Format: TOPIC: ASSESSMENT (e.g., TRAINING PROGRAM: INADEQUATE)\n"
            "- Look for: what's working, what isn't, recommendations, critiques, praise, disappointment\n"
            "- The polarity is separate from the label — return it as a 'polarity' field\n"
            "- Write labels in UPPER CASE\n"
            "- A passage may yield 1–4 evaluation codes\n\n"
            "Return JSON: {\"codes\": [{\"label\": \"TOPIC: ASSESSMENT\", \"polarity\": \"+|-|0\", "
            "\"excerpt\": \"quote expressing the judgment\", \"description\": \"what is being evaluated and how\"}]}"
        )

    def _parse_codes(self, llm_response: dict | list, source_text: str) -> list[Code]:
        codes = []
        items = llm_response.get("codes", []) if isinstance(llm_response, dict) else llm_response
        polarity_map = {"+": EvaluationPolarity.POSITIVE, "-": EvaluationPolarity.NEGATIVE, "0": EvaluationPolarity.NEUTRAL}
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).upper().strip()
            if not label:
                continue
            raw_polarity = str(item.get("polarity", "0")).strip()
            polarity = polarity_map.get(raw_polarity, EvaluationPolarity.NEUTRAL)
            codes.append(Code(
                label=label,
                code_type=self.code_type,
                description=item.get("description", ""),
                excerpt=item.get("excerpt", source_text[:80]),
                confidence=float(item.get("confidence", 1.0)),
                eval_polarity=polarity,
            ))
        return codes


# Registry for use by the engine
CODER_REGISTRY: dict[str, type[BaseCoder]] = {
    "descriptive": DescriptiveCoder,
    "in_vivo": InVivoCoder,
    "process": ProcessCoder,
    "initial": InitialCoder,
    "structural": StructuralCoder,
    "emotion": EmotionCoder,
    "values": ValuesCoder,
    "versus": VersusCoder,
    "evaluation": EvaluationCoder,
}
