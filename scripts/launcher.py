"""Entry point used by the PyInstaller build.

Unlike ``pac-man.py`` this takes no arguments: it finds the bundled
``config.json`` next to the executable and redirects the highscore file
into the user's home directory, because the bundle itself is read-only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_dir() -> str:
    """Return the directory holding the bundled data files."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _writable_dir() -> Path:
    """Return (creating it if needed) a writable directory for save data."""
    target = Path.home() / ".pacman"
    target.mkdir(parents=True, exist_ok=True)
    return target


def main() -> int:
    """Run the packaged game.

    Returns:
        A process exit code: ``0`` on success, ``1`` on any failure.
    """
    sys.path.insert(0, os.path.dirname(_bundle_dir()))
    sys.path.insert(0, _bundle_dir())

    from src.config import ConfigError, load_config
    from src.ui.app import run

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
