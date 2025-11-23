# Spotify Vibe 🎵

AI-powered Spotify playlist generator with an interactive conversational CLI. Just describe your vibe, and let AI create the perfect playlist.

Uses free/open-source LLMs (Groq or Ollama) + Spotify Search API.

## Quick start

1) **Install**:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

2) **Configure** (copy `.env.example` to `.env` and fill in your credentials):
```bash
cp .env.example .env
# Edit .env with your Spotify + Groq API keys
```

3) **Run**:
```bash
spotify-vibe
```

That's it! The interactive portal will guide you through the rest.

## Interactive Mode Experience

```
$ spotify-vibe

╔═══════════════════════════════════════════════╗
║                                               ║
║      🎵  Spotify Vibe Generator  🎵          ║
║      AI-Powered • Always Free • Open Source  ║
║                                               ║
╚═══════════════════════════════════════════════╝

💬 What's your vibe?

> chill evening coding vibes

🤖 Analyzing: chill evening coding vibes

╭─────────────── Audio Profile ────────────────╮
│ Energy: 0.40 | Valence: 0.50 | Dance: 0.60   │
│ Tempo: 90-120 BPM                             │
│ Genres: electronic, lo-fi                     │
│                                               │
│ Relaxed and focused atmosphere perfect for    │
│ late-night productivity sessions.             │
╰───────────────────────────────────────────────╯

✓ Found 20 tracks!

What would you like to do?
1 👀 Preview tracks   2 ✅ Create playlist   3 🎛️  Adjust settings
4 🔄 New vibe         5 ❓ Help             6 👋 Exit

> 2

✓ Playlist created!
Name: Vibe: chill evening coding vibes
Tracks: 20
URL: https://open.spotify.com/playlist/...

> another one, upbeat workout energy

🤖 Let's do it! Creating upbeat workout playlist...
```

## Usage

### Interactive Mode (Recommended)
```bash
spotify-vibe
```
Then just chat with the app! Use natural language:
- "I want relaxing jazz for studying"
- "create a workout playlist with high energy"
- "give me sad indie vibes for rainy days"

### Direct Command (Legacy)
```bash
python -m spotify_vibe.cli create --vibe "your vibe here"
```

### Makefile Commands
```bash
make run              # Launch interactive mode
make vibe PROMPT="chill vibes"  # Direct playlist creation
make test             # Run tests
make lint             # Run linter
make format           # Format code
```

## Required Credentials

**Spotify** (Free):
- Create an app at https://developer.spotify.com/dashboard
- Add redirect URI: `http://127.0.0.1:8888/callback`
- Copy Client ID and Secret to `.env`

**LLM** (Choose one):
- **Groq** (Cloud, Free): Get API key at console.groq.com, set `GROQ_API_KEY` in `.env`
- **Ollama** (Local): Install Ollama, run `ollama pull llama3.1`, set `LLM_PROVIDER=ollama`

## Features
- 🎨 **Interactive conversational CLI** - Talk to the app naturally
- 🤖 **AI-powered vibe interpretation** - Converts mood to audio features
- 🎵 **Smart track search** - Uses Spotify Search API for recommendations
- ✨ **Beautiful terminal UI** - Spotify-themed with rich formatting
- 🔒 **Privacy-focused** - 100% free, no data collection
- 📝 **Session memory** - Remembers your settings during conversation

## Development
```bash
make dev       # Install with dev dependencies
make test      # Run pytest
make lint      # Ruff linter
make format    # Black + Ruff formatter
make clean     # Remove cache files
```

## Troubleshooting

### OAuth Issues
- If the browser closes immediately after OAuth: delete `.spotify_cache` and try again
- If redirect fails: ensure `SPOTIFY_REDIRECT_URI` in `.env` exactly matches what's configured in your Spotify Dashboard
- Use `http://127.0.0.1:8888/callback` (not `localhost`) if your Dashboard uses that

### LLM Issues
- Groq free tier: 14,400 requests/day limit - more than enough for this app
- Ollama local: ensure `ollama serve` is running before using `LLM_PROVIDER=ollama`

## Notes
- `.spotify_cache` stores your OAuth token - **keep it** to avoid re-authenticating every run. Delete only if you need to re-auth.
- `logs/spotify_vibe.log` contains debug logs - safe to delete anytime, useful for troubleshooting.
- Keep `.env` private; it is gitignored.
- The app uses Spotify's Search API to find tracks matching your vibe.
