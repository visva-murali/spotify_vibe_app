from __future__ import annotations

import logging
import random
import time
from typing import List

import instructor
from groq import Groq
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from vibe_coder.config import Settings
from vibe_coder.models import SpotifyAudioParams


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
            return instructor.from_groq(Groq(api_key=self._config.groq_api_key))

        if self._config.llm_provider == "ollama":
            client = OpenAI(
                base_url=f"{self._config.ollama_base_url}/v1",
                api_key="ollama",  # dummy key for Ollama
            )
            return instructor.from_openai(client, mode=instructor.Mode.JSON)

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
- Respond with valid JSON only, matching the schema.
"""

        model_name = "llama-3.1-8b-instant" if self._config.llm_provider == "groq" else self._config.ollama_model

        try:
            start = time.time()
            response = self._client.chat.completions.create(
                model=model_name,
                response_model=SpotifyAudioParams,
                validation_context={"valid_genres": valid_genres},
                max_retries=self._config.max_retries,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": vibe_prompt},
                ],
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
