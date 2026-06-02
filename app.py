"""Streamlit web interface for the qualitative coding agent."""
from __future__ import annotations
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from first_cycle.coders import CODER_REGISTRY

st.set_page_config(
    page_title="Qualitative Coding Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session state defaults ───────────────────────────────────────────────────

if "text_sources" not in st.session_state:
    st.session_state.text_sources = [{"label": "Source 1", "text": ""}]
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "summary" not in st.session_state:
    st.session_state.summary = {}
if "output_dir" not in st.session_state:
    st.session_state.output_dir = ""

# ─── Sidebar configuration ────────────────────────────────────────────────────

api_key = os.environ.get("ANTHROPIC_API_KEY", "")

with st.sidebar:
    st.title("⚙️ Configuration")

    model = st.selectbox(
        "Model",
        options=[
            "claude-sonnet-4-20250514",
            "claude-opus-4-5",
            "claude-haiku-4-5-20251001",
        ],
        index=0,
    )

    all_methods = list(CODER_REGISTRY.keys())
    selected_methods = st.multiselect(
        "First-Cycle Coding Methods",
        options=all_methods,
        default=["descriptive", "in_vivo", "process", "values"],
        help="Select which Saldaña coding methods to apply.",
    )

    research_questions_raw = st.text_area(
        "Research Questions (one per line)",
        placeholder="e.g.\nHow do teachers adapt to mandated change?\nWhat support structures exist?",
        height=100,
        help="Used by Structural Coding. Leave blank if not using that method.",
    )
    research_questions = [q.strip() for q in research_questions_raw.splitlines() if q.strip()]

    max_segments = st.number_input(
        "Max Segments (0 = unlimited)",
        min_value=0,
        value=0,
        step=1,
        help="Limit segments for faster testing. Set 0 for full analysis.",
    )

    max_segment_chars = st.slider(
        "Max Chars per Segment",
        min_value=500,
        max_value=5000,
        value=2500,
        step=100,
    )

    output_base = st.text_input(
        "Output Directory",
        value="./output",
        help="Base directory for results. A timestamped subfolder will be created.",
    )

    st.markdown("---")
    st.caption("Built on Saldaña's *Coding Manual for Qualitative Researchers*")

# ─── Main area ────────────────────────────────────────────────────────────────

st.title("🔬 Qualitative Coding Agent")
st.markdown(
    "Upload interview transcripts or paste text to apply Saldaña's qualitative coding framework "
    "using AI, construct a knowledge graph, and export layered visualizations."
)

input_tab, paste_tab = st.tabs(["📁 Upload Files", "📝 Paste Text"])

uploaded_paths: list[str] = []
pasted_paths: list[str] = []

with input_tab:
    uploaded_files = st.file_uploader(
        "Upload your transcripts or documents",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx", "md"],
        help="Supports .txt, .pdf, .docx, and .md files.",
    )

with paste_tab:
    st.markdown("Add one or more text sources. Each will be treated as a separate file.")

    for i, source in enumerate(st.session_state.text_sources):
        col_label, col_remove = st.columns([4, 1])
        with col_label:
            st.session_state.text_sources[i]["label"] = st.text_input(
                f"Label for source {i+1}",
                value=source["label"],
                key=f"label_{i}",
            )
        with col_remove:
            st.write("")
            if len(st.session_state.text_sources) > 1 and st.button("✕", key=f"remove_{i}"):
                st.session_state.text_sources.pop(i)
                st.rerun()
        st.session_state.text_sources[i]["text"] = st.text_area(
            f"Text content for {source['label']}",
            value=source["text"],
            height=200,
            key=f"text_{i}",
            label_visibility="collapsed",
        )
        st.divider()

    if st.button("➕ Add another text source"):
        n = len(st.session_state.text_sources) + 1
        st.session_state.text_sources.append({"label": f"Source {n}", "text": ""})
        st.rerun()

# ─── Run button ───────────────────────────────────────────────────────────────

st.markdown("---")
run_col, spacer = st.columns([2, 6])
with run_col:
    run_clicked = st.button("▶ Run Analysis", type="primary", use_container_width=True)

if run_clicked:
    if not api_key:
        st.error("Anthropic API key not found. Add it to the `.env` file as `ANTHROPIC_API_KEY=sk-ant-...` and restart the app.")
        st.stop()
    if not selected_methods:
        st.error("Please select at least one coding method.")
        st.stop()

    tmp_dir = tempfile.mkdtemp(prefix="qc_inputs_")
    all_input_paths: list[str] = []

    # Save uploaded files
    if uploaded_files:
        for uf in uploaded_files:
            dest = Path(tmp_dir) / uf.name
            dest.write_bytes(uf.read())
            all_input_paths.append(str(dest))

    # Save pasted texts
    for source in st.session_state.text_sources:
        text = source["text"].strip()
        if text:
            safe_label = "".join(c if c.isalnum() or c in " _-" else "_" for c in source["label"])[:40]
            dest = Path(tmp_dir) / f"{safe_label}.txt"
            dest.write_text(text, encoding="utf-8")
            all_input_paths.append(str(dest))

    if not all_input_paths:
        st.error("No input provided. Upload files or paste text before running.")
        st.stop()

    # Timestamped output dir
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir = str(Path(output_base) / ts)

    # Progress display
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def update_progress(stage: str, detail: str, pct: float) -> None:
        progress_bar.progress(min(pct, 1.0))
        status_text.markdown(f"**{stage.replace('_', ' ').title()}** — {detail}")

    with st.status("Running analysis…", expanded=True) as status_widget:
        try:
            from agent.pipeline import QualitativeCodingAgent

            agent = QualitativeCodingAgent(
                api_key=api_key,
                model=model,
                first_cycle_methods=selected_methods,
                research_questions=research_questions if research_questions else None,
                max_segments=int(max_segments),
            )
            summary = agent.run(
                input_files=all_input_paths,
                output_dir=run_output_dir,
                max_segment_chars=int(max_segment_chars),
                progress_callback=update_progress,
            )
            st.session_state.summary = summary
            st.session_state.output_dir = run_output_dir
            st.session_state.analysis_done = True
            status_widget.update(label="Analysis complete ✅", state="complete")
        except Exception as exc:
            status_widget.update(label=f"Error: {exc}", state="error")
            st.exception(exc)
            st.stop()

    progress_bar.progress(1.0)
    status_text.markdown("**Done** — analysis complete.")
    st.success(f"Results saved to `{run_output_dir}`")

# ─── Results ──────────────────────────────────────────────────────────────────

if st.session_state.analysis_done and st.session_state.summary:
    summary = st.session_state.summary
    out_dir = Path(st.session_state.output_dir)

    st.markdown("---")
    tab_overview, tab_codes, tab_graph, tab_theory, tab_export = st.tabs([
        "📊 Overview",
        "🏷️ First Cycle Codes",
        "🕸️ Knowledge Graph",
        "💡 Themes & Theory",
        "⬇️ Export",
    ])

    # ── Overview ──────────────────────────────────────────────────────────────
    with tab_overview:
        st.subheader("Analysis Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Segments Coded", summary.get("total_segments", 0))
        col2.metric("Unique Codes", summary.get("unique_codes", 0))
        col3.metric("Categories", summary.get("categories", 0))
        col4, col5, col6 = st.columns(3)
        col4.metric("Themes", summary.get("themes", 0))
        col5.metric("Graph Nodes", summary.get("graph_nodes", 0))
        col6.metric("Graph Edges", summary.get("graph_edges", 0))

        st.markdown(f"**Core Category:** {summary.get('core_category') or '—'}")
        st.markdown(f"**Run Time:** {summary.get('run_time_seconds', 0):.1f}s")
        st.markdown(f"**Input Files:** {', '.join(summary.get('input_files', []))}")

    # ── First Cycle Codes ─────────────────────────────────────────────────────
    with tab_codes:
        fc_path = out_dir / "first_cycle_codes.json"
        if fc_path.exists():
            with open(fc_path, encoding="utf-8") as f:
                fc_data = json.load(f)

            st.subheader("Code Frequencies")
            freq = fc_data.get("code_frequencies", {})
            if freq:
                import pandas as pd
                df = pd.DataFrame(list(freq.items()), columns=["Code", "Frequency"])
                df = df.sort_values("Frequency", ascending=False).reset_index(drop=True)
                st.dataframe(df, use_container_width=True, height=300)

            st.subheader("Coded Segments")
            for seg in fc_data.get("coded_segments", []):
                with st.expander(f"**{seg['segment_id']}** — {len(seg['codes'])} codes"):
                    st.markdown(f"*{seg.get('text_preview', '')[:300]}…*")
                    for code in seg.get("codes", []):
                        st.markdown(
                            f"- **`{code['label']}`** `[{code['type']}]` — {code.get('description', '')}"
                        )

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    with tab_graph:
        layer1_path = out_dir / "graphs" / "layer1_high_level_graph.png"
        if layer1_path.exists():
            st.subheader("Layer 1 — High-Level Knowledge Graph")
            st.image(str(layer1_path), use_container_width=True)

            detail_dir = out_dir / "graphs" / "layer2_details"
            detail_images = sorted(detail_dir.glob("detail_*.png")) if detail_dir.exists() else []
            if detail_images:
                st.subheader("Layer 2 — Node Detail Views")
                selected_detail = st.selectbox(
                    "Select a node to view its detail graph:",
                    options=[p.stem.replace("detail_", "") for p in detail_images],
                )
                if selected_detail:
                    img_path = detail_dir / f"detail_{selected_detail}.png"
                    if img_path.exists():
                        st.image(str(img_path), use_container_width=True)
        else:
            st.info("Graph images not yet generated.")

    # ── Themes & Theory ───────────────────────────────────────────────────────
    with tab_theory:
        sc_path = out_dir / "second_cycle_results.json"
        if sc_path.exists():
            with open(sc_path, encoding="utf-8") as f:
                sc_data = json.load(f)

            # Core category
            core = sc_data.get("core_category")
            if core:
                st.subheader("🎯 Core Category")
                st.markdown(
                    f"""
                    <div style="background:#ffeaea;padding:16px;border-radius:8px;border-left:4px solid #E74C3C;">
                    <h3 style="margin:0;color:#c0392b;">{core['name']}</h3>
                    <p>{core.get('description', '')}</p>
                    <hr style="border-color:#f5b7b1;"/>
                    <em><strong>Theoretical Statement:</strong> {core.get('theoretical_statement', '')}</em>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("")

            # Themes
            themes = sc_data.get("themes", [])
            if themes:
                st.subheader("Themes")
                for t in themes:
                    level_badge = "🌐 Latent" if t.get("level") == "latent" else "👁️ Manifest"
                    with st.expander(f"{level_badge} — {t['statement'][:100]}"):
                        st.markdown(f"**Statement:** {t['statement']}")
                        if t.get("categories"):
                            st.markdown(f"**Categories:** {', '.join(t['categories'])}")
                        for ev in t.get("evidence", []):
                            st.markdown(f"> {ev}")

            # Axial relationships
            rels = sc_data.get("axial_relationships", [])
            if rels:
                st.subheader("Axial Relationships")
                import pandas as pd
                rel_rows = [
                    {
                        "Source": r["source"],
                        "Relationship": r["type"],
                        "Target": r["target"],
                        "Description": r.get("description", ""),
                    }
                    for r in rels
                ]
                st.dataframe(pd.DataFrame(rel_rows), use_container_width=True)

    # ── Export ────────────────────────────────────────────────────────────────
    with tab_export:
        st.subheader("Download Full Report")
        pdf_path = out_dir / "analysis_report.pdf"
        if pdf_path.exists():
            st.markdown(
                "The PDF report contains every section of the analysis: summary metrics, "
                "all first-cycle codes and coded segments, pattern codes, focused categories, "
                "axial relationships, themes, the core category and theoretical statement, "
                "the Layer 1 knowledge graph, and every Layer 2 node detail graph."
            )
            st.download_button(
                label="⬇️ Download Analysis Report (PDF)",
                data=pdf_path.read_bytes(),
                file_name="analysis_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        else:
            st.info("PDF report not yet generated. Run an analysis first.")
