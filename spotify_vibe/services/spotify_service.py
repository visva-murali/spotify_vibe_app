from __future__ import annotations

import logging
import time
from typing import Dict, List

import spotipy
from spotipy import SpotifyException
from spotipy.oauth2 import SpotifyOAuth
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from spotify_vibe.config import Settings
from spotify_vibe.models import PlaylistResult, SpotifyAudioParams, SpotifyTrack
from spotify_vibe.utils.helpers import sanitize_playlist_name


class SpotifyAuthError(Exception):
    """Authentication with Spotify failed."""


class NoRecommendationsError(Exception):
    """No recommendations returned by Spotify."""


class RateLimitError(Exception):
    """Hit Spotify rate limiting."""


class SpotifyService:
    """Spotify client wrapper with caching and validation."""

    # Fallback genres from Spotify seed list (static) used if API fetch fails.
    FALLBACK_GENRES: List[str] = [
        "acoustic",
        "afrobeat",
        "alt-rock",
        "alternative",
        "ambient",
        "anime",
        "bluegrass",
        "blues",
        "bossanova",
        "brazil",
        "breakbeat",
        "british",
        "cantopop",
        "chill",
        "classical",
        "club",
        "country",
        "dance",
        "dancehall",
        "death-metal",
        "deep-house",
        "disco",
        "drum-and-bass",
        "dub",
        "electronic",
        "emo",
        "folk",
        "french",
        "funk",
        "garage",
        "german",
        "gospel",
        "goth",
        "grunge",
        "happy",
        "hard-rock",
        "hardcore",
        "heavy-metal",
        "hip-hop",
        "holidays",
        "house",
        "indian",
        "indie",
        "indie-pop",
        "industrial",
        "j-pop",
        "j-rock",
        "jazz",
        "k-pop",
        "latin",
        "metal",
        "metalcore",
        "movies",
        "opera",
        "party",
        "piano",
        "pop",
        "power-pop",
        "progressive-house",
        "psych-rock",
        "punk",
        "punk-rock",
        "r-n-b",
        "reggae",
        "reggaeton",
        "road-trip",
        "rock",
        "rock-n-roll",
        "rockabilly",
        "romance",
        "sad",
        "salsa",
        "samba",
        "sertanejo",
        "show-tunes",
        "singer-songwriter",
        "ska",
        "sleep",
        "soul",
        "soundtracks",
        "spanish",
        "study",
        "summer",
        "synth-pop",
        "tango",
        "techno",
        "trance",
        "trip-hop",
        "work-out",
        "world-music",
    ]

    def __init__(self, config: Settings, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._client: spotipy.Spotify | None = None
        self._genre_cache: Dict[str, Dict[str, object]] = {}

    @property
    def client(self) -> spotipy.Spotify:
        if self._client is None:
            self._authenticate()
        return self._client

    def _authenticate(self) -> None:
        """Authenticate and store Spotify client instance."""
        try:
            auth_manager = SpotifyOAuth(
                client_id=self._config.spotify_client_id,
                client_secret=self._config.spotify_client_secret,
                redirect_uri=self._config.spotify_redirect_uri,
                scope="playlist-modify-public user-library-read",
                cache_path=".spotify_cache",
            )
            self._client = spotipy.Spotify(
                auth_manager=auth_manager, requests_timeout=self._config.spotify_request_timeout
            )
            self._logger.info("Spotify authentication successful")
        except Exception as exc:  # pragma: no cover - spotipy raises varied errors
            self._logger.error("Spotify authentication failed: %s", exc)
            raise SpotifyAuthError("Failed to authenticate with Spotify") from exc

    def get_available_genres(self) -> List[str]:
        """Return Spotify seed genres; fallback to static list on failure."""
        cache_key = "available_genres"
        cached = self._genre_cache.get(cache_key)
        if cached and time.time() - cached["timestamp"] < self._config.genre_cache_ttl:
            return cached["data"]  # type: ignore[return-value]

        try:
            genres = self._fetch_genres_with_retry()
            self._genre_cache[cache_key] = {"data": genres, "timestamp": time.time()}
            self._logger.info("Fetched %d genres from Spotify", len(genres))
            return genres
        except SpotifyException as exc:
            self._logger.warning(
                "Failed to fetch genres from Spotify (%s). Using static fallback list.",
                exc,
            )
            return self.FALLBACK_GENRES

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException),
        reraise=True,
    )
    def _fetch_genres_with_retry(self) -> List[str]:
        """Internal helper to fetch genres with retry logic."""
        return self.client.recommendation_genre_seeds()["genres"]

    def recommend_tracks(self, params: SpotifyAudioParams, limit: int = 20) -> List[SpotifyTrack]:
        """Get track recommendations using Spotify Search API."""
        self._logger.info(f"Finding tracks via search for genres: {params.seed_genres}")
        tracks = []
        seen_ids = set()

        # Build search queries from genres
        search_queries = [f"genre:{genre}" for genre in params.seed_genres[:3]]

        # Add mood-based keywords based on valence and energy
        if params.target_valence > 0.7:
            search_queries.append("happy OR upbeat OR joyful")
        elif params.target_valence < 0.3:
            search_queries.append("sad OR melancholy OR dark")

        if params.target_energy > 0.7:
            search_queries.append("energetic OR intense")
        elif params.target_energy < 0.3:
            search_queries.append("calm OR chill OR ambient")

        # Search with each query
        for query in search_queries[:2]:  # Limit to avoid too many API calls
            try:
                results = self.client.search(q=query, type="track", limit=min(50, limit * 3))
                for item in results.get("tracks", {}).get("items", []):
                    if item["id"] not in seen_ids and len(tracks) < limit:
                        tracks.append(self._normalize_track(item))
                        seen_ids.add(item["id"])

                    if len(tracks) >= limit:
                        break

            except SpotifyException as exc:
                self._logger.warning(f"Search query '{query}' failed: {exc}")
                continue

        if not tracks:
            raise NoRecommendationsError("No tracks found matching your vibe")

        self._logger.info(f"Found {len(tracks)} tracks")
        return tracks[:limit]

    def create_playlist(self, name: str, tracks: List[SpotifyTrack]) -> PlaylistResult:
        """Create a playlist and add tracks in batches."""
        user = self.client.current_user()
        playlist_name = sanitize_playlist_name(name)
        playlist = self.client.user_playlist_create(
            user["id"],
            playlist_name,
            public=True,
            description=f"Generated by Spotify Vibe | {len(tracks)} tracks",
        )

        track_uris = [track.uri for track in tracks]
        for i in range(0, len(track_uris), 100):
            self.client.playlist_add_items(playlist["id"], track_uris[i : i + 100])

        return PlaylistResult(
            playlist_id=playlist["id"],
            playlist_url=playlist["external_urls"]["spotify"],
            playlist_name=playlist_name,
            track_count=len(tracks),
            tracks=tracks,
        )

    @staticmethod
    def _normalize_track(track: dict) -> SpotifyTrack:
        """Normalize Spotify track to internal model."""
        return SpotifyTrack(
            id=track["id"],
            name=track["name"],
            artists=[artist["name"] for artist in track.get("artists", [])],
            uri=track["uri"],
            preview_url=track.get("preview_url"),
            duration_ms=track.get("duration_ms", 0),
        )
