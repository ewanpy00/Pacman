#!/usr/bin/env python3
"""Entry point: ``python3 pac-man.py config.json``. Errors exit cleanly."""

from __future__ import annotations

import sys

from src.config import Config, ConfigError, load_config


def _usage() -> None:
    """Print correct usage."""
    print("usage: python3 pac-man.py <config.json>")


def _load(argv: list[str]) -> Config | None:
    """Validate the command line and load the configuration.

    Args:
        argv: The full argument vector, including the program name.

    Returns:
        The loaded configuration, or None after printing the reason it
        could not be loaded.
    """
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
    """Load the configuration and run the game.

    Args:
        argv: The full argument vector, including the program name.

    Returns:
        A process exit code: ``0`` on success, ``1`` on any failure.
    """
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
