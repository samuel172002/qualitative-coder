"""Generates a comprehensive PDF analysis report from pipeline results."""
from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos

from shared.models import FirstCycleResult, SecondCycleResult

logger = logging.getLogger(__name__)

# ── Unicode -> Latin-1 sanitizer ──────────────────────────────────────────────
# Helvetica (built-in PDF font) is Latin-1 only. LLM output routinely contains
# em dashes, curly quotes, arrows, ellipsis, etc. Map them to safe equivalents.
_UNICODE_MAP: dict[str, str] = {
    '—': '--',   # em dash
    '–': '-',    # en dash
    '‒': '-',    # figure dash
    '‐': '-',    # hyphen
    '‑': '-',    # non-breaking hyphen
    '―': '--',   # horizontal bar
    '‘': "'",    # left single quote
    '’': "'",    # right single quote
    '‚': ',',    # single low-9 quote
    '‛': "'",    # single high reversed-9 quote
    '“': '"',    # left double quote
    '”': '"',    # right double quote
    '„': '"',    # double low-9 quote
    '‟': '"',    # double high reversed-9 quote
    '…': '...',  # horizontal ellipsis
    '•': '-',    # bullet
    '‣': '-',    # triangular bullet
    ' ': ' ',    # non-breaking space
    '­': '-',    # soft hyphen
    '→': '->',   # rightwards arrow
    '←': '<-',   # leftwards arrow
    '↔': '<->',  # left right arrow
    '⇒': '=>',   # rightwards double arrow
    '♥': '*',    # heart suit
    '✓': 'v',    # check mark
    '×': 'x',    # multiplication sign
    '÷': '/',    # division sign
}


def _safe(text: object) -> str:
    """Sanitize any value to Latin-1-safe string for use in PDF cells."""
    s = str(text) if text is not None else ''
    out: list[str] = []
    for ch in s:
        if ch in _UNICODE_MAP:
            out.append(_UNICODE_MAP[ch])
        elif ord(ch) <= 255:
            out.append(ch)
        else:
            out.append('?')
    return ''.join(out)


# Colour palette
_DARK_BLUE   = (26,  60,  100)
_RED         = (231, 76,  60)
_RED_BG      = (255, 235, 235)
_BLUE        = (52,  152, 219)
_GRAY        = (149, 165, 166)
_LIGHT_GRAY  = (240, 240, 240)
_ALT_ROW     = (235, 242, 250)
_WHITE       = (255, 255, 255)
_TEXT        = (40,  40,  40)


class _PDF(FPDF):
    def __init__(self, run_title: str) -> None:
        super().__init__()
        self._run_title = _safe(run_title)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 14, 15)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_fill_color(*_DARK_BLUE)
        self.rect(0, 0, 210, 9, style="F")
        self.set_font("Helvetica", style="B", size=7)
        self.set_text_color(*_WHITE)
        self.set_xy(15, 1.5)
        self.cell(0, 6, self._run_title, new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
        self.set_xy(-35, 1.5)
        self.cell(25, 6, f"Page {self.page_no()}", new_x=XPos.LMARGIN, new_y=YPos.TOP, align="R")
        self.set_text_color(*_TEXT)
        self.ln(4)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-10)
        self.set_font("Helvetica", style="I", size=7)
        self.set_text_color(*_GRAY)
        self.cell(
            0, 5,
            "Qualitative Coding Agent - Saldana's Coding Framework (Anthropic API)",
            align="C",
        )
        self.set_text_color(*_TEXT)


class PDFExporter:
    """Produces a multi-section PDF report from a completed pipeline run."""

    def export(
        self,
        first_cycle: FirstCycleResult,
        second_cycle: SecondCycleResult,
        summary: dict,
        output_dir: str | Path,
    ) -> str:
        output_dir = Path(output_dir)
        pdf_path = output_dir / "analysis_report.pdf"
        title = "Qualitative Coding Analysis Report"
        pdf = _PDF(run_title=title)

        try:
            self._cover(pdf, title, summary)
            self._summary_metrics(pdf, summary)
            self._first_cycle_codes(pdf, first_cycle)
            self._coded_segments(pdf, first_cycle)
            self._pattern_codes(pdf, second_cycle)
            self._categories(pdf, second_cycle)
            self._axial_relationships(pdf, second_cycle)
            self._themes_and_theory(pdf, second_cycle)
            self._graphs(pdf, output_dir)
            pdf.output(str(pdf_path))
            logger.info("PDF report written to %s", pdf_path)
        except Exception:
            logger.exception("PDF export failed")
            raise

        return str(pdf_path)

    # ── Sections ──────────────────────────────────────────────────────────────

    def _cover(self, pdf: _PDF, title: str, summary: dict) -> None:
        pdf.add_page()

        # Dark blue top banner
        pdf.set_fill_color(*_DARK_BLUE)
        pdf.rect(0, 0, 210, 135, style="F")

        # Title
        pdf.set_font("Helvetica", style="B", size=24)
        pdf.set_text_color(*_WHITE)
        pdf.set_xy(15, 40)
        pdf.multi_cell(180, 11, title, align="C")

        # Subtitle
        pdf.set_font("Helvetica", size=11)
        pdf.set_xy(15, 80)
        pdf.cell(
            180, 7,
            "Saldana's Qualitative Coding Framework - AI-Assisted Analysis",
            align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

        # Date
        pdf.set_font("Helvetica", size=9)
        pdf.set_xy(15, 91)
        pdf.cell(
            180, 6,
            f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M')}",
            align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

        # White lower section
        pdf.set_text_color(*_TEXT)
        pdf.set_fill_color(*_WHITE)
        pdf.rect(0, 135, 210, 162, style="F")

        # Run details
        pdf.set_xy(25, 150)
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.set_text_color(*_DARK_BLUE)
        pdf.cell(0, 8, "Run Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*_TEXT)

        details = [
            ("Input Files",       _safe(", ".join(Path(f).name for f in summary.get("input_files", [])))),
            ("Segments Analysed", _safe(summary.get("total_segments", 0))),
            ("Unique Codes",      _safe(summary.get("unique_codes", 0))),
            ("Categories",        _safe(summary.get("categories", 0))),
            ("Themes",            _safe(summary.get("themes", 0))),
            ("Core Category",     _safe(summary.get("core_category") or "-")),
            ("Graph Nodes",       _safe(summary.get("graph_nodes", 0))),
            ("Graph Edges",       _safe(summary.get("graph_edges", 0))),
            ("Run Time",          f"{summary.get('run_time_seconds', 0):.1f}s"),
        ]
        for key, val in details:
            pdf.set_x(30)
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.cell(55, 7, f"{key}:", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(110, 7, val[:120], new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _summary_metrics(self, pdf: _PDF, summary: dict) -> None:
        pdf.add_page()
        self._heading(pdf, "Analysis Summary")
        self._caption(pdf,
            "Key metrics from the completed pipeline run. Each segment was passed through "
            "the selected First Cycle coding methods; Second Cycle methods then operated on "
            "the combined code output.")
        pdf.ln(2)

        rows = [
            ("Metric",                      "Value"),
            ("Input Files",                 _safe(", ".join(Path(f).name for f in summary.get("input_files", [])))),
            ("Segments Analysed",           _safe(summary.get("total_segments", 0))),
            ("Unique First-Cycle Codes",    _safe(summary.get("unique_codes", 0))),
            ("Focused Categories",          _safe(summary.get("categories", 0))),
            ("Themes (Theoretical Coding)", _safe(summary.get("themes", 0))),
            ("Core Category",               _safe(summary.get("core_category") or "-")),
            ("Knowledge Graph Nodes",       _safe(summary.get("graph_nodes", 0))),
            ("Knowledge Graph Edges",       _safe(summary.get("graph_edges", 0))),
            ("Total Run Time",              f"{summary.get('run_time_seconds', 0):.1f} seconds"),
            ("Output Directory",            _safe(summary.get("output_dir", "-"))),
        ]
        hs = FontFace(emphasis="BOLD", fill_color=_DARK_BLUE, color=_WHITE)
        with pdf.table(col_widths=(85, 95), headings_style=hs,
                       cell_fill_color=_ALT_ROW, cell_fill_mode="ROWS", line_height=7) as table:
            for i, (k, v) in enumerate(rows):
                row = table.row()
                row.cell(k)
                row.cell(v[:110] if i > 0 else v)

    def _first_cycle_codes(self, pdf: _PDF, first_cycle: FirstCycleResult) -> None:
        pdf.add_page()
        self._heading(pdf, "First Cycle Codes - Frequency Table")
        self._caption(pdf,
            "All codes generated by the LLM using Saldana's First Cycle methods, "
            "sorted by how frequently each code appeared across all segments.")
        pdf.ln(2)

        sorted_codes = sorted(first_cycle.code_frequencies.items(), key=lambda x: -x[1])
        hs = FontFace(emphasis="BOLD", fill_color=_DARK_BLUE, color=_WHITE)
        with pdf.table(col_widths=(95, 28, 14), headings_style=hs,
                       cell_fill_color=_ALT_ROW, cell_fill_mode="ROWS", line_height=6) as table:
            hrow = table.row()
            hrow.cell("Code")
            hrow.cell("Type")
            hrow.cell("Count")
            for label, count in sorted_codes:
                code_list = first_cycle.all_codes.get(label, [])
                code_type = code_list[0].code_type.value if code_list else ""
                row = table.row()
                row.cell(_safe(label)[:90])
                row.cell(_safe(code_type)[:25])
                row.cell(str(count))

    def _coded_segments(self, pdf: _PDF, first_cycle: FirstCycleResult) -> None:
        pdf.add_page()
        self._heading(pdf, "Coded Segments")
        self._caption(pdf,
            "Each text segment with the codes assigned to it. "
            "A segment is a paragraph-level chunk of the source document.")
        pdf.ln(2)

        hs = FontFace(emphasis="BOLD", fill_color=_BLUE, color=_WHITE)

        for cs in first_cycle.coded_segments:
            if pdf.get_y() > 252:
                pdf.add_page()

            # Segment ID bar
            pdf.set_fill_color(*_LIGHT_GRAY)
            pdf.set_font("Helvetica", style="B", size=9)
            pdf.cell(
                0, 6, f"  {_safe(cs.segment.segment_id)}",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True,
            )

            # Text preview
            preview = _safe(cs.segment.text[:350].replace("\n", " "))
            if len(cs.segment.text) > 350:
                preview += "..."
            pdf.set_font("Helvetica", style="I", size=8)
            pdf.set_text_color(*_GRAY)
            pdf.set_x(pdf.l_margin + 3)
            pdf.multi_cell(0, 4.5, preview, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*_TEXT)
            pdf.ln(1)

            # Codes table
            if cs.codes:
                with pdf.table(col_widths=(55, 25, 100), headings_style=hs,
                               cell_fill_color=_ALT_ROW, cell_fill_mode="ROWS",
                               line_height=5) as table:
                    hrow = table.row()
                    hrow.cell("Label")
                    hrow.cell("Type")
                    hrow.cell("Description")
                    for code in cs.codes:
                        row = table.row()
                        row.cell(_safe(code.display_label)[:52])
                        row.cell(_safe(code.code_type.value)[:22])
                        row.cell(_safe(code.description)[:90])
            pdf.ln(4)

    def _pattern_codes(self, pdf: _PDF, second_cycle: SecondCycleResult) -> None:
        if not second_cycle.pattern_codes:
            return
        pdf.add_page()
        self._heading(pdf, "Second Cycle - Pattern Codes")
        self._caption(pdf,
            "Pattern Coding (Miles & Huberman, 1994) groups first-cycle codes into explanatory "
            "meta-patterns that synthesise large blocks of data into a single conceptual trope. "
            "Saldana: 'Pattern codes are hunches - some pan out, but many do not.'")
        pdf.ln(3)

        for pattern_name, codes in second_cycle.pattern_codes.items():
            if pdf.get_y() > 252:
                pdf.add_page()
            pdf.set_fill_color(*_ALT_ROW)
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.cell(0, 7, f"  {_safe(pattern_name)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            pdf.set_font("Helvetica", size=8)
            pdf.set_text_color(*_GRAY)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(0, 4.5, _safe(",   ".join(codes)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*_TEXT)
            pdf.ln(3)

    def _categories(self, pdf: _PDF, second_cycle: SecondCycleResult) -> None:
        if not second_cycle.categories:
            return
        pdf.add_page()
        self._heading(pdf, "Second Cycle - Focused Categories")
        self._caption(pdf,
            "Focused Coding (Charmaz, 2006) identifies the most salient categories. "
            "Axial Coding (Strauss & Corbin, 1998) enriches each with properties (characteristics) "
            "and dimensions (the range along which properties vary).")
        pdf.ln(3)

        for cat in second_cycle.categories:
            if pdf.get_y() > 245:
                pdf.add_page()

            pdf.set_fill_color(*_DARK_BLUE)
            pdf.set_text_color(*_WHITE)
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.cell(
                0, 7, f"  {_safe(cat.name)}   (frequency: {cat.frequency})",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True,
            )
            pdf.set_text_color(*_TEXT)

            if cat.description:
                pdf.set_font("Helvetica", size=9)
                pdf.set_x(pdf.l_margin + 3)
                pdf.multi_cell(0, 5, _safe(cat.description), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            if cat.codes:
                pdf.set_font("Helvetica", style="I", size=8)
                pdf.set_text_color(*_GRAY)
                pdf.set_x(pdf.l_margin + 3)
                member_text = _safe(",   ".join(cat.codes[:25]))
                if len(cat.codes) > 25:
                    member_text += f"  ... (+{len(cat.codes) - 25} more)"
                pdf.multi_cell(0, 4.5, f"Member codes: {member_text}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(*_TEXT)

            if cat.properties:
                pdf.set_font("Helvetica", style="B", size=8)
                pdf.set_x(pdf.l_margin + 3)
                pdf.cell(0, 5, "Properties:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", size=8)
                for k, v in cat.properties.items():
                    pdf.set_x(pdf.l_margin + 7)
                    pdf.multi_cell(0, 4.5, f"- {_safe(k)}: {_safe(v)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            if cat.dimensions:
                pdf.set_font("Helvetica", style="B", size=8)
                pdf.set_x(pdf.l_margin + 3)
                pdf.cell(0, 5, "Dimensions:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", size=8)
                for k, v in cat.dimensions.items():
                    pdf.set_x(pdf.l_margin + 7)
                    pdf.multi_cell(0, 4.5, f"- {_safe(k)}: {_safe(v)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.ln(5)

    def _axial_relationships(self, pdf: _PDF, second_cycle: SecondCycleResult) -> None:
        if not second_cycle.axial_relationships:
            return
        pdf.add_page()
        self._heading(pdf, "Axial Relationships")
        self._caption(pdf,
            "Axial Coding maps the relationships between categories using the paradigm: "
            "Conditions -> Actions/Interactions -> Consequences. "
            "Relationship types: causes, enables, constrains, is_context_for, leads_to, strategy_for.")
        pdf.ln(2)

        hs = FontFace(emphasis="BOLD", fill_color=_DARK_BLUE, color=_WHITE)
        with pdf.table(col_widths=(45, 25, 45, 65), headings_style=hs,
                       cell_fill_color=_ALT_ROW, cell_fill_mode="ROWS", line_height=6) as table:
            hrow = table.row()
            hrow.cell("Source Category")
            hrow.cell("Relationship")
            hrow.cell("Target Category")
            hrow.cell("Description")
            for rel in second_cycle.axial_relationships:
                row = table.row()
                row.cell(_safe(rel.source_category)[:42])
                row.cell(_safe(rel.relationship_type)[:22])
                row.cell(_safe(rel.target_category)[:42])
                row.cell(_safe(rel.description)[:80])

        pdf.ln(4)

        # Conditions / Consequences detail
        for rel in second_cycle.axial_relationships:
            if not rel.conditions and not rel.consequences:
                continue
            if pdf.get_y() > 252:
                pdf.add_page()
            pdf.set_fill_color(*_LIGHT_GRAY)
            pdf.set_font("Helvetica", style="B", size=9)
            pdf.cell(
                0, 6,
                f"  {_safe(rel.source_category)}  ->  [{_safe(rel.relationship_type)}]  ->  {_safe(rel.target_category)}",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True,
            )
            if rel.conditions:
                pdf.set_font("Helvetica", style="B", size=8)
                pdf.set_x(pdf.l_margin + 4)
                pdf.cell(0, 5, "Conditions:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", size=8)
                for cond in rel.conditions:
                    pdf.set_x(pdf.l_margin + 8)
                    pdf.multi_cell(0, 4.5, f"- {_safe(cond)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if rel.consequences:
                pdf.set_font("Helvetica", style="B", size=8)
                pdf.set_x(pdf.l_margin + 4)
                pdf.cell(0, 5, "Consequences:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", size=8)
                for cons in rel.consequences:
                    pdf.set_x(pdf.l_margin + 8)
                    pdf.multi_cell(0, 4.5, f"- {_safe(cons)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)

    def _themes_and_theory(self, pdf: _PDF, second_cycle: SecondCycleResult) -> None:
        pdf.add_page()
        self._heading(pdf, "Themes & Theoretical Framework")
        self._caption(pdf,
            "Theoretical Coding (Glaser, 1978) identifies one core category that integrates all others "
            "and produces a grounded theoretical statement. "
            "Saldana: 'Mere numeric frequency is not necessarily a reliable indicator of a core category.'")
        pdf.ln(4)

        # Core category
        if second_cycle.core_category:
            core = second_cycle.core_category
            self._sub_heading(pdf, "Core Category")
            pdf.ln(1)

            pdf.set_fill_color(*_RED_BG)
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.set_text_color(*_RED)
            pdf.cell(0, 11, f"  {_safe(core.name)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            pdf.set_text_color(*_TEXT)

            if core.description:
                pdf.set_fill_color(*_RED_BG)
                pdf.set_font("Helvetica", size=9)
                pdf.set_x(pdf.l_margin + 3)
                pdf.multi_cell(0, 5, _safe(core.description),
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

            if core.theoretical_statement:
                pdf.set_fill_color(*_RED_BG)
                pdf.set_font("Helvetica", style="B", size=9)
                pdf.set_x(pdf.l_margin + 3)
                pdf.cell(0, 5, "Theoretical Statement:", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
                pdf.set_font("Helvetica", style="I", size=9)
                pdf.set_x(pdf.l_margin + 3)
                pdf.multi_cell(0, 5, _safe(core.theoretical_statement),
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

            if core.related_categories:
                pdf.set_fill_color(*_RED_BG)
                pdf.set_font("Helvetica", style="I", size=8)
                pdf.set_text_color(*_GRAY)
                pdf.set_x(pdf.l_margin + 3)
                pdf.multi_cell(
                    0, 4.5,
                    "Related categories: " + _safe(", ".join(core.related_categories)),
                    new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True,
                )
                pdf.set_text_color(*_TEXT)

            pdf.ln(6)

        # Themes
        if second_cycle.themes:
            self._sub_heading(pdf, "Themes")
            pdf.ln(2)
            for i, theme in enumerate(second_cycle.themes, 1):
                if pdf.get_y() > 245:
                    pdf.add_page()
                level_label = "Latent" if theme.level == "latent" else "Manifest"
                pdf.set_fill_color(*_ALT_ROW)
                pdf.set_font("Helvetica", style="B", size=9)
                pdf.cell(
                    0, 6, f"  Theme {i}  ({level_label})",
                    new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True,
                )
                pdf.set_font("Helvetica", size=9)
                pdf.set_x(pdf.l_margin + 3)
                pdf.multi_cell(0, 5, _safe(theme.statement), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                if theme.categories:
                    pdf.set_font("Helvetica", style="I", size=8)
                    pdf.set_text_color(*_GRAY)
                    pdf.set_x(pdf.l_margin + 3)
                    pdf.multi_cell(
                        0, 4.5, "Categories: " + _safe(", ".join(theme.categories)),
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                    )
                    pdf.set_text_color(*_TEXT)

                for ev in theme.evidence:
                    if not ev:
                        continue
                    pdf.set_font("Helvetica", style="I", size=8)
                    pdf.set_text_color(*_GRAY)
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.multi_cell(
                        0, 4.5, f'"{_safe(ev[:220])}"',
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                    )
                    pdf.set_text_color(*_TEXT)
                pdf.ln(4)

    def _graphs(self, pdf: _PDF, output_dir: Path) -> None:
        # Layer 1
        layer1 = output_dir / "graphs" / "layer1_high_level_graph.png"
        if layer1.exists():
            pdf.add_page()
            self._heading(pdf, "Knowledge Graph - Layer 1: High-Level Overview")
            self._caption(pdf,
                "Full knowledge graph: core category -> themes -> categories -> patterns -> codes. "
                "Node size reflects importance; edge labels show relationship types.")
            pdf.ln(2)
            pdf.image(str(layer1), x=pdf.l_margin, w=180)

        # Layer 2
        detail_dir = output_dir / "graphs" / "layer2_details"
        if not detail_dir.exists():
            return
        detail_images = sorted(detail_dir.glob("detail_*.png"))
        if not detail_images:
            return

        pdf.add_page()
        self._heading(pdf, "Knowledge Graph - Layer 2: Node Detail Views")
        self._caption(pdf,
            "Each graph shows the 2-hop neighbourhood of a key node - "
            "every node and edge directly connected to and from it.")
        pdf.ln(2)

        for img_path in detail_images:
            node_name = _safe(img_path.stem.replace("detail_", "").replace("_", " "))
            pdf.add_page()
            self._sub_heading(pdf, node_name)
            pdf.ln(2)
            pdf.image(str(img_path), x=pdf.l_margin, w=180)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _heading(self, pdf: _PDF, text: str) -> None:
        pdf.set_fill_color(*_DARK_BLUE)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 9, f"  {text}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_text_color(*_TEXT)
        pdf.ln(2)

    def _sub_heading(self, pdf: _PDF, text: str) -> None:
        pdf.set_fill_color(*_BLUE)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.cell(0, 7, f"  {text}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.set_text_color(*_TEXT)
        pdf.ln(1)

    def _caption(self, pdf: _PDF, text: str) -> None:
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(*_GRAY)
        pdf.multi_cell(0, 4.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*_TEXT)
