# Qualitative Coding Agent

An AI-powered research tool that applies **Johnny Saldaña's qualitative coding framework** to interview transcripts and documents. It runs a full two-cycle coding pipeline via the Anthropic API, constructs a knowledge graph from the results, and presents everything through a Streamlit web interface.

---

## What This Does

Qualitative coding is how researchers turn raw interview data into theory. The process is manual, time-consuming, and requires deep knowledge of coding methods. This tool automates it:

1. **Loads** your text files (interviews, field notes, transcripts)
2. **Segments** the text into manageable chunks
3. **Applies First Cycle coding** — nine of Saldaña's methods, each targeting a different dimension of the data (topics, participant language, actions, emotions, values, conflicts, judgments)
4. **Applies Second Cycle coding** — synthesises first-cycle codes into categories, axial relationships, themes, and a core theoretical category
5. **Builds a knowledge graph** — nodes for codes, categories, themes, and the core; edges for relationships
6. **Exports layered visualisations** — a high-level overview graph and per-node detail graphs
7. **Displays results** in a browser UI with downloadable JSON outputs

All coding is done by an LLM (Claude) guided by Saldaña's exact definitions — not by keyword matching or NLP heuristics.

---

## Theoretical Foundation

This tool is built on **Johnny Saldaña's *The Coding Manual for Qualitative Researchers*** (SAGE Publications, 2009), the standard reference on qualitative coding. Saldaña advocates *pragmatic eclecticism* — choosing the right coding method for the right data and research question.

### The Codes-to-Theory Hierarchy

```
Raw Data
   │
   ▼  First Cycle Coding
Codes  (labels applied to segments: SECURITY, "SURVIVAL", ADAPTING, V: PROFESSIONAL AUTONOMY)
   │
   ▼  Pattern + Focused Coding
Categories  (grouped codes: STRUGGLING WITH MANDATED CHANGE, BUILDING PEER SUPPORT)
   │
   ▼  Axial Coding
Relationships  (Conditions → Actions → Consequences between categories)
   │
   ▼  Theoretical Coding
Themes + Core Category + Theoretical Statement
```

A **code** is a word or short phrase capturing the meaning of a segment. A **category** is a group of related codes. A **theme** is a full sentence expressing a key insight. The **core category** is the one central concept that integrates everything into a coherent theory.

---

## First Cycle Coding Methods

Each method in this tool follows Saldaña's exact definition. Nine methods are available:

| Method | What it captures | Code format | Example |
|---|---|---|---|
| **Descriptive** | The *topic* of a passage — what it is about, not what it means | NOUN PHRASE | `TEACHER WORKLOAD` |
| **In Vivo** | The participant's *exact words* — prioritise metaphors and memorable phrases | `"EXACT WORDS"` | `"THAT'S NOT PROFESSIONAL DEVELOPMENT"` |
| **Process** | *Actions and movement* — always gerunds (−ing words) | GERUND PHRASE | `NEGOTIATING ROLES`, `SURVIVING CHANGE` |
| **Initial** | Open, unrestricted first-pass — the entry point for grounded theory | Any form | `OVERWHELMED BY BUREAUCRACY` |
| **Structural** | Tied to *research questions* — acts as an indexing device | `RQ1: TOPIC` | `RQ1: SUPPORT STRUCTURES FOR TEACHERS` |
| **Emotion** | Emotions — explicit (stated) or inferred; always precise | EMOTION WORD | `DESPONDENCY [inferred, intense]` |
| **Values** | Values (`V:`), attitudes (`A:`), and beliefs (`B:`) | Prefixed label | `V: PROFESSIONAL AUTONOMY`, `B: TEACHERS KNOW BEST` |
| **Versus** | Conflicts, tensions, and power dynamics | `X VS. Y` | `TEACHERS VS. ADMINISTRATION` |
| **Evaluation** | Judgments of merit or worth with polarity | `+/-/0 TOPIC: ASSESSMENT` | `- IMPLEMENTATION: POORLY PLANNED` |

**Default methods** (cost-effective starting point): `descriptive`, `in_vivo`, `process`, `values`

---

## Second Cycle Coding Methods

Second Cycle methods operate on the output of First Cycle coding — they never see the raw text.

| Method | What it does | Output |
|---|---|---|
| **Pattern Coding** | Groups first-cycle codes into 5–15 explanatory meta-patterns | `dict[pattern_name → [codes]]` |
| **Focused Coding** | Finds the most salient categories; prefers gerund names | `list[Category]` |
| **Axial Coding** | Enriches categories with properties/dimensions; maps Conditions → Actions → Consequences | `list[Category]`, `list[AxialRelationship]` |
| **Theoretical Coding** | Identifies one core category; produces a theoretical statement and 2–5 themes | `CoreCategory`, `list[Theme]` |

These run sequentially — each stage's output feeds the next.

---

## Project Architecture

```
qualitative_coder/
├── app.py                        # Streamlit web UI
├── main.py                       # CLI entry point
├── requirements.txt
├── .env                          # API key (not committed to git)
│
├── shared/
│   ├── models.py                 # All dataclasses and enums
│   └── llm.py                    # Anthropic API client with retry + JSON parsing
│
├── first_cycle/
│   ├── coders.py                 # 9 concrete coder classes + BaseCoder ABC
│   └── engine.py                 # Runs selected coders across all segments
│
├── second_cycle/
│   ├── coders.py                 # PatternCoder, FocusedCoder, AxialCoder, TheoreticalCoder
│   └── engine.py                 # Sequential pipeline: Pattern → Focused → Axial → Theoretical
│
├── agent/
│   ├── file_loader.py            # Loads .txt, .pdf, .docx, .md and segments text
│   ├── knowledge_graph.py        # NetworkX DiGraph builder
│   ├── visualizer.py             # Matplotlib PNG export (headless)
│   └── pipeline.py               # QualitativeCodingAgent — orchestrates everything
│
├── sample_data/
│   └── interview_sarah.txt       # Example: teacher on mandated curriculum change
│
└── docs/
    └── saldana_reference.md      # Full Saldaña framework reference
```

### Key Design Decisions

- **LLM-based coding** — each coder sends the segment to Claude with a method-specific system prompt derived from Saldaña's exact definitions. No keyword matching.
- **Separation of concerns** — each first-cycle coder has one job: call LLM → parse JSON → return `list[Code]`. No shared state between coders.
- **Second cycle operates on summaries** — `_format_code_summary()` builds a structured text block of top codes for the LLM. Second-cycle methods never see raw text, which mirrors how a human researcher would work.
- **Node ID hashing** — graph node IDs use `MD5(label)[:6]` suffix to prevent collisions between similarly-named nodes of different types.
- **Progress callbacks** — the pipeline accepts a `progress_callback(stage, detail, pct)` function, allowing both the CLI and the Streamlit UI to display progress without coupling.

---

## Installation

```bash
pip install -r requirements.txt
```

**Set your Anthropic API key** in the `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get a key at [console.anthropic.com](https://console.anthropic.com). The `.env` file is excluded from git — your key is never committed.

---

## Usage

### Streamlit Web UI

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501`. The sidebar lets you configure:
- **Model** — which Claude model to use
- **First-Cycle Methods** — which of the 9 coding methods to apply
- **Research Questions** — used by Structural Coding only; leave blank otherwise
- **Max Segments** — limit segments to control cost (0 = unlimited; use 3–5 for testing)
- **Max Chars per Segment** — chunk size (~2500 chars ≈ 400 words)
- **Output Directory** — where results are saved locally

Upload files via the **Upload Files** tab or paste text directly in the **Paste Text** tab. Both can be used together.

After the run completes, results are shown across five tabs (Overview, First Cycle Codes, Knowledge Graph, Themes & Theory, Export). The **Export** tab has a single button to download the full PDF report.

### Command Line

```bash
python main.py sample_data/interview_sarah.txt --max-segments 3 --output ./test_output -v
```

Full options:

```
positional arguments:
  files                         One or more input files (.txt, .pdf, .docx, .md)

options:
  -o, --output DIR              Output directory (default: ./output)
  -m, --methods METHOD [...]    First-cycle methods to apply (default: descriptive in_vivo process values)
  -rq, --research-questions Q   Research questions for structural coding (one per argument)
  --max-segments N              Maximum segments to process (0 = unlimited)
  --max-segment-chars N         Max characters per segment (default: 2500)
  --model MODEL                 Claude model to use
  --api-key KEY                 Anthropic API key (overrides .env and environment variable)
  -v, --verbose                 Verbose logging
```

---

## Output Structure

Every run creates a timestamped subfolder:

```
output/
└── 20240601_143022/
    ├── analysis_report.pdf           # ← Single downloadable PDF report (all sections + all graphs)
    ├── first_cycle_codes.json        # All coded segments: codes, excerpts, types, frequencies
    ├── second_cycle_results.json     # Categories, axial relationships, themes, core category
    ├── knowledge_graph.json          # Full graph as node/edge lists with metadata
    ├── analysis_summary.json         # Run statistics: segments, codes, timing, input files
    └── graphs/
        ├── layer1_high_level_graph.png      # Overview: core → themes → categories → patterns
        └── layer2_details/
            ├── detail_CORE_CATEGORY.png     # 2-hop neighbourhood for each Layer 1 node
            ├── detail_THEME_1.png
            └── ...
```

### PDF Report Contents

The `analysis_report.pdf` consolidates the entire analysis into a single shareable document:

| Section | Contents |
|---|---|
| Cover page | Title, date, run summary (files, codes, categories, themes) |
| Analysis Summary | Full metrics table |
| First Cycle Codes | Complete code frequency table (all codes, type, count) |
| Coded Segments | Every segment with its text preview and assigned codes |
| Pattern Codes | All meta-patterns with their member codes |
| Focused Categories | Each category with description, member codes, properties, dimensions |
| Axial Relationships | Relationship table + conditions/consequences per relationship |
| Themes & Theory | Core category (highlighted), theoretical statement, all themes with evidence |
| Knowledge Graph Layer 1 | Full high-level graph image |
| Knowledge Graph Layer 2 | One detail graph page per key node (core, themes, categories, patterns) |

---

## Supported File Types

| Extension | Parser |
|---|---|
| `.txt` | Plain text read |
| `.md` | Markdown read |
| `.pdf` | pdfplumber |
| `.docx` | python-docx |

---

## Cost and Speed

Each segment × each selected coding method = one LLM API call. With default methods (4) and a typical interview transcript (~20 segments):

- **Testing** (`--max-segments 3`): ~12 API calls, < 1 minute, < $0.05
- **Full run** (20 segments, 4 methods): ~80+ API calls, 5–15 minutes depending on model
- **claude-haiku-4-5** is fastest and cheapest; **claude-sonnet-4** gives the most nuanced codes

---

## Further Reading

- Saldaña, J. (2009). *The Coding Manual for Qualitative Researchers*. SAGE Publications.
- Charmaz, K. (2006). *Constructing Grounded Theory*. SAGE Publications.
- Strauss, A., & Corbin, J. (1998). *Basics of Qualitative Research*. SAGE Publications.
- Glaser, B. G. (1978). *Theoretical Sensitivity*. Sociology Press.

See [`docs/saldana_reference.md`](docs/saldana_reference.md) for a detailed breakdown of every coding method implemented in this tool.
