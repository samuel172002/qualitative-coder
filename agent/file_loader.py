from __future__ import annotations
import logging
import re
from pathlib import Path

from shared.models import TextSegment

logger = logging.getLogger(__name__)

MIN_SEGMENT_CHARS = 60
MIN_PARA_CHARS = 40


def load_file(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber is required for PDF support: pip install pdfplumber")
        text_parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
        return "\n\n".join(text_parts)
    if suffix == ".docx":
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx is required for DOCX support: pip install python-docx")
        doc = docx.Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError(f"Unsupported file type: {suffix}")


def load_files(paths: list[str | Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for p in paths:
        try:
            content = load_file(p)
            result[str(Path(p).name)] = content
            logger.info("Loaded %s (%d chars)", p, len(content))
        except Exception as exc:
            logger.error("Failed to load %s: %s", p, exc)
    return result


def segment_text(
    text: str,
    source_file: str,
    max_segment_chars: int = 2500,
) -> list[TextSegment]:
    raw_paragraphs = re.split(r"\n\n+", text)
    paragraphs: list[str] = []
    char_offsets: list[int] = []
    running = 0

    for para in raw_paragraphs:
        stripped = para.strip()
        offset = text.find(stripped, running) if stripped else running
        if offset < 0:
            offset = running
        if stripped:
            paragraphs.append(stripped)
            char_offsets.append(offset)
        running = offset + len(stripped) + 2

    # Merge short paragraphs into previous
    merged: list[str] = []
    merged_offsets: list[int] = []
    for i, (para, off) in enumerate(zip(paragraphs, char_offsets)):
        if merged and len(para) < MIN_PARA_CHARS:
            merged[-1] = merged[-1] + "\n\n" + para
        else:
            merged.append(para)
            merged_offsets.append(off)

    # Build segments by chunking merged paragraphs up to max_segment_chars
    segments: list[TextSegment] = []
    current_paras: list[str] = []
    current_start = 0
    current_len = 0
    para_idx = 0
    seg_index = 0

    def flush():
        nonlocal seg_index, current_paras, current_start, current_len
        text_block = "\n\n".join(current_paras)
        if len(text_block) >= MIN_SEGMENT_CHARS:
            segments.append(TextSegment(
                text=text_block,
                segment_id=f"{source_file}::seg_{seg_index:04d}",
                source_file=source_file,
                paragraph_index=para_idx,
                char_start=current_start,
                char_end=current_start + len(text_block),
            ))
            seg_index += 1
        current_paras = []
        current_len = 0

    for para, off in zip(merged, merged_offsets):
        if current_len + len(para) + 2 > max_segment_chars and current_paras:
            flush()
            current_start = off
        if not current_paras:
            current_start = off
        current_paras.append(para)
        current_len += len(para) + 2
        para_idx += 1

    if current_paras:
        flush()

    logger.info("Segmented '%s' into %d segments", source_file, len(segments))
    return segments


def load_and_segment(
    paths: list[str | Path],
    max_segment_chars: int = 2500,
) -> list[TextSegment]:
    all_segments: list[TextSegment] = []
    files = load_files(paths)
    for filename, content in files.items():
        segs = segment_text(content, filename, max_segment_chars)
        all_segments.extend(segs)
    return all_segments
