from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CodeType(Enum):
    ATTRIBUTE = "attribute"
    MAGNITUDE = "magnitude"
    STRUCTURAL = "structural"
    DESCRIPTIVE = "descriptive"
    IN_VIVO = "in_vivo"
    PROCESS = "process"
    INITIAL = "initial"
    EMOTION = "emotion"
    VALUES = "values"
    VERSUS = "versus"
    EVALUATION = "evaluation"
    PATTERN = "pattern"
    FOCUSED = "focused"
    AXIAL = "axial"
    THEORETICAL = "theoretical"


class ValuesSubtype(Enum):
    VALUE = "V"
    ATTITUDE = "A"
    BELIEF = "B"


class EvaluationPolarity(Enum):
    POSITIVE = "+"
    NEGATIVE = "-"
    NEUTRAL = "0"


@dataclass
class TextSegment:
    text: str
    segment_id: str
    source_file: str
    paragraph_index: int
    char_start: int
    char_end: int


@dataclass
class Code:
    label: str
    code_type: CodeType
    description: str
    excerpt: str
    confidence: float = 1.0
    values_subtype: Optional[ValuesSubtype] = None
    eval_polarity: Optional[EvaluationPolarity] = None
    magnitude: Optional[str] = None

    @property
    def display_label(self) -> str:
        if self.values_subtype is not None:
            return f"{self.values_subtype.value}: {self.label}"
        if self.eval_polarity is not None:
            return f"{self.eval_polarity.value} {self.label}"
        return self.label


@dataclass
class CodedSegment:
    segment: TextSegment
    codes: list[Code] = field(default_factory=list)

    def codes_by_type(self, code_type: CodeType) -> list[Code]:
        return [c for c in self.codes if c.code_type == code_type]


@dataclass
class FirstCycleResult:
    coded_segments: list[CodedSegment] = field(default_factory=list)
    all_codes: dict[str, list[Code]] = field(default_factory=dict)
    code_frequencies: dict[str, int] = field(default_factory=dict)
    source_files: list[str] = field(default_factory=list)

    def add_coded_segment(self, cs: CodedSegment) -> None:
        self.coded_segments.append(cs)
        for code in cs.codes:
            label = code.label
            if label not in self.all_codes:
                self.all_codes[label] = []
            self.all_codes[label].append(code)
            self.code_frequencies[label] = self.code_frequencies.get(label, 0) + 1


@dataclass
class Category:
    name: str
    description: str
    codes: list[str] = field(default_factory=list)
    code_objects: list[Code] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    dimensions: dict = field(default_factory=dict)
    frequency: int = 0


@dataclass
class AxialRelationship:
    source_category: str
    target_category: str
    relationship_type: str
    description: str
    conditions: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)


@dataclass
class Theme:
    statement: str
    categories: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    level: str = "manifest"


@dataclass
class CoreCategory:
    name: str
    description: str
    related_categories: list[str] = field(default_factory=list)
    themes: list[Theme] = field(default_factory=list)
    theoretical_statement: str = ""


@dataclass
class SecondCycleResult:
    categories: list[Category] = field(default_factory=list)
    axial_relationships: list[AxialRelationship] = field(default_factory=list)
    themes: list[Theme] = field(default_factory=list)
    core_category: Optional[CoreCategory] = None
    pattern_codes: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class GraphNode:
    id: str
    label: str
    node_type: str
    properties: dict = field(default_factory=dict)
    size: float = 1.0


@dataclass
class GraphEdge:
    source: str
    target: str
    relationship: str
    weight: float = 1.0
    properties: dict = field(default_factory=dict)
