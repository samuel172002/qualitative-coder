# Qualitative Coding Agent

An AI agent that applies Johnny Saldaña's qualitative coding methods to text data, constructs a knowledge graph, and exports layered visualizations. Built on the Anthropic API.

## Features

- **First Cycle Coding** — 9 methods: Descriptive, In Vivo, Process, Initial, Structural, Emotion, Values, Versus, Evaluation
- **Second Cycle Coding** — Pattern, Focused, Axial, and Theoretical coding following Saldaña's codes-to-theory hierarchy
- **Knowledge Graph** — NetworkX DiGraph with typed nodes (core, theme, category, pattern, code) and typed edges
- **Layered Visualizations** — High-level graph + per-node detail graphs exported as PNG
- **Streamlit UI** — Upload files or paste text, configure methods, view results in browser
- **CLI** — Run from terminal with full control over all parameters

## Installation

```bash
pip install -r requirements.txt
```

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

### Streamlit Web UI

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Upload files or paste text in the UI, configure options in the sidebar, and click **Run Analysis**.

### Command Line

```bash
python main.py sample_data/interview_sarah.txt --max-segments 3 --output ./test_output -v
```

Full options:
```
usage: qualitative_coder [-h] [--output OUTPUT]
                         [--methods {descriptive,in_vivo,process,...} ...]
                         [--research-questions Q [Q ...]]
                         [--max-segments N] [--max-segment-chars N]
                         [--model MODEL] [--api-key API_KEY] [--verbose]
                         files [files ...]
```

## Output Structure

```
output/
├── first_cycle_codes.json        # All coded segments with codes
├── second_cycle_results.json     # Categories, relationships, themes, core category
├── knowledge_graph.json          # Full graph as JSON
├── analysis_summary.json         # Run statistics
└── graphs/
    ├── layer1_high_level_graph.png
    └── layer2_details/
        ├── detail_CORE_CATEGORY.png
        ├── detail_THEME_1.png
        └── ...
```

## Supported File Types

- `.txt` — Plain text
- `.md` — Markdown
- `.pdf` — PDF (via pdfplumber)
- `.docx` — Word documents (via python-docx)

## Theoretical Foundation

Follows Saldaña's codes-to-theory model:
```
Raw Data → Codes → Categories → Themes → Theory
           ^^^^^^               ^^^^^^^^^^  ^^^^^^
           First Cycle          Second Cycle  Theoretical
```
