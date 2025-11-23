# Spotify Vibe 🎵

AI-powered Spotify playlist generator using free/open-source LLMs (Groq or Ollama) plus Spotify recommendations.

## Quick start
1) Create a virtualenv and install deps:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
2) Copy env template and fill values:
```bash
cp .env.example .env
```
3) Run the CLI (prompts for vibe):
```bash
python -m spotify_vibe.cli create --vibe "coding at 2am, cyberpunk vibes"
```

## Required credentials
- Spotify: create an app at https://developer.spotify.com/dashboard, add redirect URI `http://localhost:8888/callback`, and set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`.
- LLM (cloud, free): create a key at https://console.groq.com and set `GROQ_API_KEY`, `LLM_PROVIDER=groq`.
- LLM (local, offline): install Ollama, run `ollama run llama3.1`, set `LLM_PROVIDER=ollama` (base URL/model configurable in `.env`).

## Features
- Structured LLM output enforced via Pydantic + Instructor.
- Spotify genre caching to reduce API load.
- Rich/Typer CLI with spinners, tables, and dry-run mode.
- Logging to console and `spotify_vibe.log` (JSON format file).

## Useful commands
- Lint: `ruff check .`
- Format: `black .`
- Tests: `pytest`
- Run CLI: `spotify-vibe --help`

## Notes
- Delete `.spotify_cache` if you need to re-auth Spotify.
- Keep `.env` private; it is gitignored.
