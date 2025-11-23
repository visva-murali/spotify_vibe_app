.PHONY: help install dev run test lint format clean

help:
	@echo "Spotify Vibe - Makefile Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    - Install package in editable mode"
	@echo "  make dev        - Install with dev dependencies"
	@echo ""
	@echo "Run:"
	@echo "  make run        - Launch interactive mode"
	@echo "  make vibe PROMPT='your vibe' - Create playlist directly"
	@echo ""
	@echo "Development:"
	@echo "  make test       - Run pytest with coverage"
	@echo "  make lint       - Run ruff linter"
	@echo "  make format     - Format code with black"
	@echo "  make clean      - Remove cache files"

install:
	@echo "Installing Spotify Vibe..."
	pip install -e .
	@echo "✓ Done! Run 'spotify-vibe' to start"

dev:
	@echo "Installing Spotify Vibe with dev dependencies..."
	pip install -e ".[dev]"
	@echo "✓ Done! Dev tools installed"

run:
	@echo "Launching Spotify Vibe interactive mode..."
	@spotify-vibe || python -m spotify_vibe.interactive

vibe:
	@if [ -z "$(PROMPT)" ]; then \
		echo "Usage: make vibe PROMPT='your vibe here'"; \
		exit 1; \
	fi
	@python -m spotify_vibe.cli create --vibe "$(PROMPT)"

test:
	@echo "Running tests..."
	pytest

lint:
	@echo "Running linter..."
	ruff check .

format:
	@echo "Formatting code..."
	black .
	ruff check --fix .

clean:
	@echo "Cleaning cache files..."
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf *.egg-info
	rm -rf build dist
	rm -f .coverage
	@echo "✓ Cache cleaned"
