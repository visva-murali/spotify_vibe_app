"""Interactive conversational CLI for Spotify Vibe."""

import logging
import sys
from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from spotify_vibe.config import get_settings
from spotify_vibe.models import PlaylistResult, SpotifyAudioParams, SpotifyTrack
from spotify_vibe.services.llm_service import LLMInterpretationError, LLMService
from spotify_vibe.services.spotify_service import (
    NoRecommendationsError,
    RateLimitError,
    SpotifyAuthError,
    SpotifyService,
)
from spotify_vibe.utils.logging_config import setup_logging

console = Console()

# Spotify green theme for prompt
prompt_style = Style.from_dict({
    'prompt': '#1DB954 bold',  # Spotify green
})


class VibeSession:
    """Manages conversational session state."""

    def __init__(self):
        self.last_vibe: Optional[str] = None
        self.last_params: Optional[SpotifyAudioParams] = None
        self.last_tracks: List[SpotifyTrack] = []
        self.last_limit: int = 20


def print_banner():
    """Display welcome banner with Spotify theme."""
    banner_text = (
        "[bold green]🎵  Spotify Vibe Generator  🎵[/]\n"
        "[dim]AI-Powered • Always Free • Open Source[/]"
    )
    banner = Panel(
        banner_text,
        style="green",
        padding=(1, 2),
        expand=False
    )
    console.print("\n")
    console.print(banner, justify="center")
    console.print()


def print_menu():
    """Display action menu."""
    console.print("\n[dim]What would you like to do?[/]")
    menu_text = (
        "[cyan]1[/] 👀 Preview tracks   "
        "[cyan]2[/] ✅ Create playlist   "
        "[cyan]3[/] 🎛️  Adjust settings\n"
        "[cyan]4[/] 🔄 New vibe         "
        "[cyan]5[/] ❓ Help             "
        "[cyan]6[/] 👋 Exit"
    )
    console.print(menu_text)
    console.print()


def display_tracks(tracks: List[SpotifyTrack], limit: Optional[int] = None):
    """Display tracks in a beautiful table."""
    display_limit = limit if limit else len(tracks)
    table = Table(title=f"🎧 {min(display_limit, len(tracks))} Tracks")
    table.add_column("#", style="dim", width=4)
    table.add_column("Track", style="cyan", no_wrap=False)
    table.add_column("Artist(s)", style="green")
    table.add_column("Duration", style="magenta")

    for idx, track in enumerate(tracks[:display_limit], 1):
        minutes = track.duration_ms // 60000
        seconds = (track.duration_ms // 1000) % 60
        duration = f"{minutes}:{seconds:02d}"
        table.add_row(
            str(idx),
            track.name[:50] + "..." if len(track.name) > 50 else track.name,
            ", ".join(track.artists)[:40],
            duration
        )

    console.print(table)


def parse_command(user_input: str, session: VibeSession) -> tuple[str, Optional[str]]:
    """Parse user input to determine intent."""
    user_input = user_input.strip().lower()

    # Menu numbers
    if user_input in ['1', 'preview', 'show', 'tracks']:
        return 'preview', None
    if user_input in ['2', 'create', 'make']:
        return 'create', None
    if user_input in ['3', 'adjust', 'settings', 'change']:
        return 'adjust', None
    if user_input in ['4', 'new', 'another', 'different']:
        return 'new_vibe', None
    if user_input in ['5', 'help', '?']:
        return 'help', None
    if user_input in ['6', 'exit', 'quit', 'bye', 'q']:
        return 'exit', None

    # Natural language vibe descriptions
    if any(word in user_input for word in ['want', 'create', 'make', 'need', 'give me']):
        # Extract the vibe part
        for prefix in ['i want', 'create', 'make me', 'make a', 'give me', 'need']:
            if prefix in user_input:
                vibe = user_input.split(prefix, 1)[1].strip()
                if vibe:
                    return 'vibe', vibe

    # Direct vibe input (no command words)
    if len(user_input) > 10 and not user_input.isdigit():
        return 'vibe', user_input

    return 'unknown', None


def show_help():
    """Display help information."""
    help_text = Panel(
        "[bold cyan]How to use Spotify Vibe:[/]\n\n"
        "[green]Natural language:[/]\n"
        "  • 'chill evening coding vibes'\n"
        "  • 'I want upbeat workout music'\n"
        "  • 'create a relaxing jazz playlist'\n\n"
        "[green]Quick commands:[/]\n"
        "  • [cyan]1[/] or 'preview' - Show track list\n"
        "  • [cyan]2[/] or 'create' - Create Spotify playlist\n"
        "  • [cyan]3[/] or 'adjust' - Change settings (limit, energy, etc.)\n"
        "  • [cyan]4[/] or 'new' - Start fresh with a new vibe\n"
        "  • [cyan]5[/] or 'help' - Show this help\n"
        "  • [cyan]6[/] or 'exit' - Quit\n\n"
        "[dim]Just describe your vibe in your own words![/]",
        title="💡 Help",
        border_style="green"
    )
    console.print(help_text)


def adjust_settings(session: VibeSession) -> dict:
    """Interactive settings adjustment."""
    console.print("\n[cyan]Current settings:[/]")
    console.print(f"  Tracks limit: {session.last_limit}")
    if session.last_params:
        console.print(f"  Energy: {session.last_params.target_energy:.2f}")
        console.print(f"  Valence: {session.last_params.target_valence:.2f}")

    console.print("\n[dim]What would you like to adjust?[/]")
    console.print("[cyan]1[/] Number of tracks  [cyan]2[/] Energy level  [cyan]3[/] Valence (mood)  [cyan]4[/] Cancel")

    choice = console.input("\n[green]>[/] ").strip()

    changes = {}
    if choice == '1':
        try:
            limit = int(console.input("[green]How many tracks?[/] (5-50): ").strip())
            if 5 <= limit <= 50:
                changes['limit'] = limit
                session.last_limit = limit
                console.print(f"[green]✓[/] Limit set to {limit}")
        except ValueError:
            console.print("[red]Invalid number[/]")
    elif choice == '2':
        try:
            energy = float(console.input("[green]Energy level[/] (0.0-1.0, current={:.2f}): ".format(
                session.last_params.target_energy if session.last_params else 0.5)).strip())
            if 0.0 <= energy <= 1.0:
                changes['energy'] = energy
                console.print(f"[green]✓[/] Energy set to {energy:.2f}")
        except ValueError:
            console.print("[red]Invalid number[/]")
    elif choice == '3':
        try:
            valence = float(console.input("[green]Valence (happiness)[/] (0.0-1.0, current={:.2f}): ".format(
                session.last_params.target_valence if session.last_params else 0.5)).strip())
            if 0.0 <= valence <= 1.0:
                changes['valence'] = valence
                console.print(f"[green]✓[/] Valence set to {valence:.2f}")
        except ValueError:
            console.print("[red]Invalid number[/]")

    return changes


def run_interactive():
    """Main interactive loop."""
    setup_logging("INFO")
    print_banner()

    try:
        settings = get_settings()
        spotify = SpotifyService(settings, logging.getLogger("spotify_vibe.spotify"))
        llm = LLMService(settings, logging.getLogger("spotify_vibe.llm"))
    except Exception as exc:
        console.print(f"[bold red]Setup failed:[/] {exc}")
        console.print("[yellow]Make sure your .env file is configured correctly.[/]")
        sys.exit(1)

    session = VibeSession()
    prompt_session = PromptSession(style=prompt_style)

    console.print("[bold green]💬 What's your vibe?[/] [dim](or type 'help')[/]")
    console.print()

    while True:
        try:
            # Get user input
            user_input = prompt_session.prompt('> ', style=prompt_style).strip()

            if not user_input:
                continue

            # Parse command
            command, vibe_text = parse_command(user_input, session)

            if command == 'exit':
                console.print("\n[green]✨ Thanks for vibing! See you next time.[/]")
                break

            elif command == 'help':
                show_help()
                continue

            elif command == 'preview':
                if not session.last_tracks:
                    console.print("[yellow]No tracks yet! Describe a vibe first.[/]")
                else:
                    display_tracks(session.last_tracks, session.last_limit)
                print_menu()
                continue

            elif command == 'create':
                if not session.last_tracks:
                    console.print("[yellow]No tracks yet! Describe a vibe first.[/]")
                    continue

                # Ask about custom playlist name
                console.print("\n[cyan]📝 Playlist name:[/]")
                console.print("  [dim]1[/] Auto-generate with AI (recommended)")
                console.print("  [dim]2[/] Use vibe description")
                console.print("  [dim]3[/] Enter custom name")

                name_choice = console.input("\n[green]>[/] ").strip()

                playlist_name = f"Vibe: {session.last_vibe[:40]}"  # Default

                if name_choice == '1':
                    # Generate with LLM
                    with Progress(
                        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
                    ) as progress:
                        progress.add_task(description="Generating name...", total=None)
                        generated_name = llm.generate_playlist_name(session.last_vibe)

                    console.print(f"\n[green]✨ Generated:[/] {generated_name}")
                    edit = console.input("[dim]Press Enter to use this, or type a new name:[/] ").strip()
                    playlist_name = edit if edit else generated_name

                elif name_choice == '3':
                    custom = console.input("\n[green]Enter playlist name:[/] ").strip()
                    if custom:
                        playlist_name = custom

                # Create playlist
                with Progress(
                    SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
                ) as progress:
                    progress.add_task(description="Creating playlist...", total=None)
                    result = spotify.create_playlist(
                        playlist_name,
                        session.last_tracks[:session.last_limit]
                    )

                console.print(
                    Panel.fit(
                        f"[bold green]✓ Playlist created![/]\n"
                        f"Name: {result.playlist_name}\n"
                        f"Tracks: {result.track_count}\n"
                        f"URL: [link={result.playlist_url}]{result.playlist_url}[/]",
                        border_style="green",
                    )
                )
                print_menu()
                continue

            elif command == 'adjust':
                changes = adjust_settings(session)
                if changes and session.last_vibe:
                    console.print("[cyan]Regenerating with new settings...[/]")
                    command = 'vibe'
                    vibe_text = session.last_vibe
                else:
                    print_menu()
                    continue

            elif command == 'new_vibe':
                session.last_vibe = None
                session.last_params = None
                session.last_tracks = []
                console.print("[green]🔄 Ready for a new vibe! What are you feeling?[/]\n")
                continue

            elif command == 'unknown':
                console.print("[yellow]I didn't quite catch that. Try describing your vibe or type 'help'.[/]")
                continue

            # Process vibe
            if command == 'vibe' and vibe_text:
                session.last_vibe = vibe_text
                console.print(f"\n[cyan]🤖 Analyzing:[/] {vibe_text}\n")

                # Ask for track limit
                limit_input = console.input(f"[dim]How many tracks?[/] [green](5-50, default {session.last_limit}):[/] ").strip()
                if limit_input:
                    try:
                        new_limit = int(limit_input)
                        if 5 <= new_limit <= 50:
                            session.last_limit = new_limit
                            console.print(f"[green]✓[/] Will find {new_limit} tracks\n")
                        else:
                            console.print(f"[yellow]Using default {session.last_limit} tracks (value must be 5-50)[/]\n")
                    except ValueError:
                        console.print(f"[yellow]Using default {session.last_limit} tracks[/]\n")
                else:
                    console.print(f"[dim]Using {session.last_limit} tracks[/]\n")

                # Fetch genres
                with Progress(
                    SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
                ) as progress:
                    progress.add_task(description="Loading...", total=None)
                    genres = spotify.get_available_genres()

                # Get LLM interpretation
                with Progress(
                    SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
                ) as progress:
                    progress.add_task(description="Analyzing vibe...", total=None)
                    params = llm.interpret_vibe(vibe_text, genres)

                session.last_params = params

                # Show audio profile
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

                # Find tracks
                with Progress(
                    SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True
                ) as progress:
                    progress.add_task(description="Finding tracks...", total=None)
                    tracks = spotify.recommend_tracks(params, limit=session.last_limit)

                session.last_tracks = tracks
                console.print(f"\n[bold green]✓ Found {len(tracks)} tracks![/]")

                print_menu()

        except KeyboardInterrupt:
            console.print("\n\n[green]✨ Interrupted. Bye![/]")
            break
        except (SpotifyAuthError, RateLimitError, NoRecommendationsError, LLMInterpretationError) as exc:
            console.print(f"\n[bold red]Error:[/] {exc}")
            console.print("[yellow]Try again or type 'help' for assistance.[/]\n")
        except Exception as exc:
            console.print(f"\n[bold red]Unexpected error:[/] {exc}")
            console.print("[dim]Check logs/spotify_vibe.log for details.[/]\n")


def main():
    """Entry point for interactive CLI."""
    try:
        run_interactive()
    except Exception as exc:
        console.print(f"[bold red]Fatal error:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
