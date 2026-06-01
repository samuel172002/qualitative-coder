"""CLI entry point for the qualitative coding agent."""
from __future__ import annotations
import argparse
import logging
import os
import sys
import time

from agent.pipeline import QualitativeCodingAgent
from first_cycle.coders import CODER_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qualitative_coder",
        description="AI qualitative coding agent based on Saldaña's Coding Manual",
    )
    parser.add_argument("files", nargs="+", help="Input files (txt, pdf, docx, md)")
    parser.add_argument("--output", "-o", default="./output", help="Output directory (default: ./output)")
    parser.add_argument(
        "--methods", "-m",
        nargs="+",
        choices=list(CODER_REGISTRY.keys()),
        default=["descriptive", "in_vivo", "process", "values"],
        help="First-cycle coding methods to apply",
    )
    parser.add_argument(
        "--research-questions", "-rq",
        nargs="+",
        metavar="Q",
        help="Research questions for structural coding",
    )
    parser.add_argument(
        "--max-segments",
        type=int,
        default=0,
        metavar="N",
        help="Limit to first N segments (0 = unlimited; useful for testing)",
    )
    parser.add_argument(
        "--max-segment-chars",
        type=int,
        default=2500,
        metavar="N",
        help="Max characters per text segment (default: 2500)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Anthropic model ID",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)-30s %(message)s",
        datefmt="%H:%M:%S",
    )


def print_summary(summary: dict) -> None:
    print()
    print("=" * 62)
    print("  QUALITATIVE CODING ANALYSIS — RESULTS SUMMARY")
    print("=" * 62)
    rows = [
        ("Run time",       f"{summary.get('run_time_seconds', 0):.1f}s"),
        ("Input files",    str(len(summary.get("input_files", [])))),
        ("Segments coded", str(summary.get("total_segments", 0))),
        ("Unique codes",   str(summary.get("unique_codes", 0))),
        ("Categories",     str(summary.get("categories", 0))),
        ("Themes",         str(summary.get("themes", 0))),
        ("Core category",  str(summary.get("core_category") or "—")),
        ("Graph nodes",    str(summary.get("graph_nodes", 0))),
        ("Graph edges",    str(summary.get("graph_edges", 0))),
        ("Output dir",     str(summary.get("output_dir", ""))),
    ]
    for label, value in rows:
        print(f"  {label:<20} {value}")
    print("=" * 62)
    print()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: No API key provided. Set ANTHROPIC_API_KEY or use --api-key.", file=sys.stderr)
        sys.exit(1)

    agent = QualitativeCodingAgent(
        api_key=api_key,
        model=args.model,
        first_cycle_methods=args.methods,
        research_questions=args.research_questions,
        max_segments=args.max_segments,
    )

    try:
        summary = agent.run(
            input_files=args.files,
            output_dir=args.output,
            max_segment_chars=args.max_segment_chars,
        )
        print_summary(summary)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logging.getLogger(__name__).exception("Pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
