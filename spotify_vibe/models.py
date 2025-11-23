from typing import List

from pydantic import BaseModel, Field, field_validator


class SpotifyAudioParams(BaseModel):
    """LLM output schema enforced via Instructor."""

    target_valence: float = Field(..., ge=0.0, le=1.0, description="Positivity of the track")
    target_energy: float = Field(..., ge=0.0, le=1.0, description="Intensity of the track")
    target_danceability: float = Field(..., ge=0.0, le=1.0, description="Danceability of the track")
    min_tempo: int = Field(..., ge=40, le=220, description="Minimum BPM")
    max_tempo: int = Field(..., ge=40, le=220, description="Maximum BPM")
    seed_genres: List[str] = Field(..., min_length=1, max_length=2, description="Seed genres")
    reasoning: str = Field(..., min_length=8, max_length=240, description="Why these parameters")

    @field_validator("seed_genres")
    @classmethod
    def ensure_valid_genres(cls, genres: List[str]) -> List[str]:
        """Ensure genres are lowercase and unique."""
        normalized = list(dict.fromkeys([g.strip().lower() for g in genres if g.strip()]))
        if not normalized:
            raise ValueError("seed_genres must contain at least one genre")
        if len(normalized) > 2:
            raise ValueError("seed_genres must be 1-2 items")
        return normalized

    @field_validator("max_tempo")
    @classmethod
    def tempo_range(cls, max_tempo: int, info) -> int:
        """Ensure max_tempo is not below min_tempo."""
        min_tempo = info.data.get("min_tempo")
        if min_tempo is not None and max_tempo < min_tempo:
            raise ValueError("max_tempo cannot be less than min_tempo")
        return max_tempo


class SpotifyTrack(BaseModel):
    """Normalized Spotify track representation."""

    id: str
    name: str
    artists: List[str]
    uri: str
    preview_url: str | None = None
    duration_ms: int


class PlaylistResult(BaseModel):
    """Metadata for a created playlist."""

    playlist_id: str
    playlist_url: str
    playlist_name: str
    track_count: int
    tracks: List[SpotifyTrack]


class VibeRequest(BaseModel):
    """Validated user request from CLI."""

    vibe_prompt: str = Field(..., min_length=5, max_length=500)
    limit: int = Field(default=20, ge=5, le=50)
    energy_override: float | None = Field(default=None, ge=0.0, le=1.0)
    valence_override: float | None = Field(default=None, ge=0.0, le=1.0)
    dry_run: bool = False
