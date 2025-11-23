import logging
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from vibe_coder.config import get_settings
from vibe_coder.models import VibeRequest
from vibe_coder.services.llm_service import LLMInterpretationError, LLMService
from vibe_coder.services.spotify_service import (
    NoRecommendationsError,
    RateLimitError,
    SpotifyAuthError,
    SpotifyService,
)
from vibe_coder.utils.logging_config import setup_logging

app = typer.Typer(add_completion=False, help="AI-powered Spotify playlist generator.")
console = Console()


def _display_tracks(tracks, limit: int) -> None:
    table = Table(title=f"🎧 {min(limit, len(tracks))} Tracks Found")
    table.add_column("Track", style="cyan", no_wrap=True)
    table.add_column("Artist(s)", style="green")
    table.add_column("Duration")

    for track in tracks[:limit]:
        minutes = track.duration_ms // 60000
        seconds = (track.duration_ms // 1000) % 60
        duration = f"{minutes}:{seconds:02d}"
        table.add_row(track.name, ", ".join(track.artists), duration)

    console.print(table)


@app.command("create")
def create_playlist(
    vibe: str = typer.Option(..., "--vibe", "-v", help="Describe your current vibe/mood."),
    limit: int = typer.Option(20, "--limit", "-l", min=5, max=50, help="Number of tracks."),
    energy: Optional[float] = typer.Option(
        None, "--energy", help="Override energy (0-1).", min=0.0, max=1.0
    ),
    valence: Optional[float] = typer.Option(
        None, "--valence", help="Override valence (0-1).", min=0.0, max=1.0
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview tracks without creating playlist."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """Generate a Spotify playlist from a vibe description."""

    setup_logging("DEBUG" if verbose else "INFO")

    try:
        request = VibeRequest(
            vibe_prompt=vibe, limit=limit, energy_override=energy, valence_override=valence, dry_run=dry_run
        )
    except Exception as exc:  # pragma: no cover - validation is simple
        console.print(f"[bold red]Invalid input:[/] {exc}")
        raise typer.Exit(code=1)

    settings = get_settings()
    spotify = SpotifyService(settings, logging.getLogger("vibe_coder.spotify"))
    llm = LLMService(settings, logging.getLogger("vibe_coder.llm"))

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
    ) as progress:
        progress.add_task(description="Fetching available genres...", total=None)
        genres = spotify.get_available_genres()

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
    ) as progress:
        progress.add_task(description="Analyzing your vibe...", total=None)
        params = llm.interpret_vibe(request.vibe_prompt, genres)

    # Apply overrides if provided
    if request.energy_override is not None:
        params.target_energy = request.energy_override
    if request.valence_override is not None:
        params.target_valence = request.valence_override

    console.print(
        Panel.fit(
            f"[bold]Audio Profile[/]\n"
            f"Energy: {params.target_energy:.2f} | Valence: {params.target_valence:.2f} | "
            f"Danceability: {params.target_danceability:.2f}\n"
            f"Tempo: {params.min_tempo}-{params.max_tempo} BPM\n"
            f"Genres: {', '.join(params.seed_genres)}\n\n"
            f"[italic]{params.reasoning}[/]",
            border_style="magenta",
        )
    )

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
    ) as progress:
        progress.add_task(description="Finding tracks...", total=None)
        tracks = spotify.recommend_tracks(params, limit=request.limit)

    _display_tracks(tracks, request.limit)

    if dry_run:
        console.print("[yellow]Dry run enabled; not creating playlist.[/]")
        return

    if typer.confirm("Create this playlist on Spotify?", default=True):
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
        ) as progress:
            progress.add_task(description="Creating playlist...", total=None)
            result = spotify.create_playlist(f"Vibe: {request.vibe_prompt[:40]}", tracks[: request.limit])

        console.print(
            Panel.fit(
                f"[bold green]Playlist created![/]\n"
                f"Name: {result.playlist_name}\n"
                f"Tracks: {result.track_count}\n"
                f"URL: [link={result.playlist_url}]{result.playlist_url}[/]",
                border_style="green",
            )
        )
    else:
        console.print("[yellow]Playlist creation canceled.[/]")


@app.command("auth")
def auth_info() -> None:
    """Guide user to refresh Spotify authentication."""
    console.print(
        "Authentication uses the browser-based OAuth flow managed by spotipy.\n"
        "If you need to reset tokens, delete the `.spotify_cache` file and rerun a command."
    )


def main() -> None:
    try:
        app()
    except SpotifyAuthError as exc:
        console.print(f"[bold red]Spotify authentication failed:[/] {exc}")
        raise typer.Exit(code=1)
    except RateLimitError as exc:
        console.print(f"[bold red]Rate limited by Spotify:[/] {exc}")
        raise typer.Exit(code=1)
    except NoRecommendationsError as exc:
        console.print(f"[bold yellow]No recommendations:[/] {exc}")
        raise typer.Exit(code=1)
    except LLMInterpretationError as exc:
        console.print(f"[bold red]LLM interpretation failed:[/] {exc}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    main()
