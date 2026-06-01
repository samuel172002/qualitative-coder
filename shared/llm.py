from __future__ import annotations
import json
import logging
import os
import re
import time

import anthropic

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return response.content[0].text
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning("LLM query attempt %d failed: %s — retrying in %ds", attempt + 1, exc, wait)
                time.sleep(wait)
        raise RuntimeError(f"LLM query failed after 3 attempts: {last_error}") from last_error

    def query_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> dict | list:
        augmented_system = (
            system_prompt
            + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown fences, no explanation, no preamble."
        )
        raw = self.query(augmented_system, user_prompt, max_tokens=max_tokens, temperature=temperature)
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict | list:
        text = raw.strip()
        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Regex fallback: find first JSON object or array
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse JSON from LLM response: %s", text[:300])
        return {}

    def chunk_text(self, text: str, max_chars: int = 2500, overlap: int = 200) -> list[str]:
        paragraphs = re.split(r"\n\n+", text)
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) + 2 > max_chars and current:
                chunks.append("\n\n".join(current))
                # keep last paragraph as overlap
                overlap_paras = []
                overlap_len = 0
                for p in reversed(current):
                    if overlap_len + len(p) <= overlap:
                        overlap_paras.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break
                current = overlap_paras
                current_len = sum(len(p) for p in current)
            current.append(para)
            current_len += len(para) + 2

        if current:
            chunks.append("\n\n".join(current))
        return chunks
