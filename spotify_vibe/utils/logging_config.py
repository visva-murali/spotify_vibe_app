import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO") -> None:
    """Configure console and file logging."""

    root = logging.getLogger()
    if root.handlers:
        # Avoid duplicate handlers when re-running in same process
        return

    root.setLevel(log_level.upper())

    console_handler = logging.StreamHandler(sys.stdout)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    root.addHandler(console_handler)

    file_handler = logging.FileHandler("spotify_vibe.log")
    json_format = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    file_handler.setFormatter(json_format)
    root.addHandler(file_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("spotipy").setLevel(logging.INFO)
