#!/usr/bin/env python3
"""Entry point: ``python3 pac-man.py config.json``. Errors exit cleanly."""

from __future__ import annotations

import sys

from src.config import Config, ConfigError, load_config


def _usage() -> None:
    """Print correct usage."""
    print("usage: python3 pac-man.py <config.json>")


def _load(argv: list[str]) -> Config | None:
    """Validate CLI args and load the config, or return ``None`` on error."""
    if len(argv) != 2:
        print("error: exactly one argument (a .json config file) is required")
        _usage()
        return None
    try:
        return load_config(argv[1])
    except ConfigError as exc:
        print(f"error: {exc}")
        return None


def main(argv: list[str]) -> int:
    """Program entry point. Returns a process exit code."""
    config = _load(argv)
    if config is None:
        return 1

    # Import the UI lazily so config errors never require a display/pygame.
    from src.ui.app import run
    try:
        return run(config)
    except KeyboardInterrupt:
        print("\ninterrupted; exiting cleanly.")
        return 0
    except Exception as exc:  # noqa: BLE001 - last-resort guard, no traceback
        print(f"error: unexpected failure: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
