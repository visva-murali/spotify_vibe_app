import re


def sanitize_playlist_name(name: str) -> str:
    """Remove special characters and trim length for Spotify compatibility."""
    cleaned = re.sub(r"[^\w\s-]", "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = "Spotify Vibe Playlist"
    return cleaned[:100]
