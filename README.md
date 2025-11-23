# Spotify Vibe 🎵

AI-powered Spotify playlist generator using free/open-source LLMs (Groq or Ollama) plus Spotify search.

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
- **Spotify**: create an app at https://developer.spotify.com/dashboard
  - Add redirect URI: `http://127.0.0.1:8888/callback` (must match exactly)
  - Copy Client ID and Client Secret to `.env`
- **LLM (cloud, free)**: create a key at https://console.groq.com and set `GROQ_API_KEY`, `LLM_PROVIDER=groq`.
- **LLM (local, offline)**: install Ollama, run `ollama run llama3.1`, set `LLM_PROVIDER=ollama` (base URL/model configurable in `.env`).

## Features
- Structured LLM output enforced via Pydantic + Instructor.
- Spotify genre caching to reduce API load, with a static fallback list if the API fails.
- Rich/Typer CLI with spinners, tables, and dry-run mode.
- Logging to console and `logs/spotify_vibe.log` (JSON format).

## Useful commands
- Lint: `ruff check .`
- Format: `black .`
- Tests: `pytest`
- Run CLI: `spotify-vibe --help`

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
