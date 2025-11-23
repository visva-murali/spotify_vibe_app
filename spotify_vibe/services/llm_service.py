from __future__ import annotations

import logging
import random
import time
from typing import List

from groq import Groq
import ollama
from tenacity import retry, stop_after_attempt, wait_exponential

from spotify_vibe.config import Settings
from spotify_vibe.models import SpotifyAudioParams


class LLMInterpretationError(Exception):
    """Raised when the LLM fails to produce valid parameters."""


class LLMService:
    """LLM wrapper that enforces structured JSON output."""

    PROMPT_VERSION = "v1.0"

    def __init__(self, config: Settings, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._client = self._initialize_client()

    def _initialize_client(self):
        if self._config.llm_provider == "groq":
            if not self._config.groq_api_key:
                raise ValueError("GROQ_API_KEY required for Groq provider")
            return Groq(api_key=self._config.groq_api_key)

        if self._config.llm_provider == "ollama":
            # ollama client used directly (no Instructor)
            return ollama.Client(host=self._config.ollama_base_url)

        raise ValueError(f"Unsupported LLM provider: {self._config.llm_provider}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def interpret_vibe(self, vibe_prompt: str, valid_genres: List[str]) -> SpotifyAudioParams:
        """Convert vibe text to audio parameters via structured LLM output."""

        genre_sample = random.sample(valid_genres, min(50, len(valid_genres)))
        genre_str = ", ".join(sorted(genre_sample))

        system_prompt = f"""
You are an expert DJ and music psychologist.
Map the user's vibe to Spotify recommendation parameters.

Rules:
- Choose 1-2 seed_genres ONLY from this list: {genre_str}
- Valence: 0=sad/melancholic, 1=happy/euphoric
- Energy: 0=calm/ambient, 1=intense/aggressive
- Danceability: 0=listening music, 1=club bangers
- Tempo guidance: slow=60-90 BPM, medium=90-120, fast=120-180
- Output JSON with exactly these top-level keys (no nesting):
  {{
    "target_valence": float between 0 and 1,
    "target_energy": float between 0 and 1,
    "target_danceability": float between 0 and 1,
    "min_tempo": integer between 40 and 220,
    "max_tempo": integer between 40 and 220,
    "seed_genres": ["genre1","genre2"],
    "reasoning": "short sentence"
  }}
- Do not add extra keys. Do not nest fields. Return valid JSON only.
"""

        try:
            start = time.time()

            if self._config.llm_provider == "groq":
                model_name = "llama-3.1-8b-instant"
                groq_resp = self._client.chat.completions.create(
                    model=model_name,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": vibe_prompt},
                    ],
                    temperature=0.2,
                )
                content = groq_resp.choices[0].message.content
                response = SpotifyAudioParams.model_validate_json(
                    content, context={"valid_genres": valid_genres}
                )
            else:
                model_name = self._config.ollama_model
                result = self._client.chat(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": vibe_prompt},
                    ],
                    options={"temperature": 0.2},
                )
                content = result["message"]["content"]
                response = SpotifyAudioParams.model_validate_json(
                    content, context={"valid_genres": valid_genres}
                )

            latency_ms = int((time.time() - start) * 1000)
            self._logger.info(
                "LLM interpretation complete",
                extra={
                    "latency_ms": latency_ms,
                    "model": model_name,
                    "prompt_version": self.PROMPT_VERSION,
                },
            )
            return response
        except Exception as exc:  # pragma: no cover - handled at caller
            self._logger.error("LLM interpretation failed: %s", exc)
            raise LLMInterpretationError("Failed to interpret vibe, please try rephrasing.") from exc
