"""Entry point for the *packaged* build (PyInstaller / Itch.io / Steam).

The CLI entry ``pac-man.py`` requires a config path argument, which a
double-clicked game has no way to pass. This launcher instead loads the
``config.json`` bundled inside the executable and redirects the highscore
file to a per-user writable location (the app bundle itself is read-only).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_dir() -> str:
    """Directory holding bundled data (PyInstaller sets ``_MEIPASS``)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _writable_dir() -> Path:
    """A per-user directory we may write highscores into."""
    target = Path.home() / ".pacman"
    target.mkdir(parents=True, exist_ok=True)
    return target


def main() -> int:
    """Load the bundled config and launch the game."""
    # Make ``import src...`` work whether frozen or run from the repo root.
    sys.path.insert(0, os.path.dirname(_bundle_dir()))
    sys.path.insert(0, _bundle_dir())

    from src.config import ConfigError, load_config
    from src.ui.app import run

    # Bundled next to the executable when frozen; at the repo root in dev.
    candidates = [
        os.path.join(_bundle_dir(), "config.json"),
        os.path.join(os.path.dirname(_bundle_dir()), "config.json"),
    ]
    config_path = next((p for p in candidates if os.path.exists(p)),
                       candidates[0])
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"error: {exc}")
        return 1

    config.highscore_filename = str(_writable_dir() / "highscores.json")
    try:
        return run(config)
    except Exception as exc:  # noqa: BLE001 - last-resort guard, no traceback
        print(f"error: unexpected failure: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
