"""Load/validate the JSON-with-#-comments config; bad values -> defaults."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# Default values used when a key is missing or invalid.
_DEFAULTS: dict[str, Any] = {
    "highscore_filename": "highscores.json",
    "cell_size": 24,
    "fps": 60,
    "lives": 3,
    "player_speed": 5,
    "points_per_pacgum": 10,
    "points_per_super_pacgum": 50,
    "points_per_ghost": 200,
    "ghost_speed": 4,
    "frightened_duration": 8,
    "ghost_respawn_delay": 6,
    "seed": 42,
    "level_max_time": 90,
}

# Inclusive (min, max) bounds for integer keys. Values are clamped into range.
_BOUNDS: dict[str, tuple[int, int]] = {
    "cell_size": (8, 64),
    "fps": (15, 240),
    "lives": (1, 99),
    "player_speed": (1, 20),
    "points_per_pacgum": (0, 100000),
    "points_per_super_pacgum": (0, 100000),
    "points_per_ghost": (0, 100000),
    "ghost_speed": (1, 20),
    "frightened_duration": (1, 60),
    "ghost_respawn_delay": (0, 60),
    "seed": (1, 2**31 - 1),
    "level_max_time": (5, 3600),
}

# A maze must be at least this large or the generator refuses to embed its
# '42' pattern and warns on stderr.
_MIN_LEVEL_SIZE = 15
_MAX_LEVEL_SIZE = 60
_MIN_LEVELS = 10


class ConfigError(Exception):
    """Raised when the config file cannot be read or parsed at all."""


@dataclass
class LevelConfig:
    """Parameters describing a single maze/level."""

    width: int
    height: int
    pacgum: int


@dataclass
class Config:
    """Validated config: every field present and within range."""

    highscore_filename: str = _DEFAULTS["highscore_filename"]
    cell_size: int = _DEFAULTS["cell_size"]
    fps: int = _DEFAULTS["fps"]
    lives: int = _DEFAULTS["lives"]
    player_speed: int = _DEFAULTS["player_speed"]
    points_per_pacgum: int = _DEFAULTS["points_per_pacgum"]
    points_per_super_pacgum: int = _DEFAULTS["points_per_super_pacgum"]
    points_per_ghost: int = _DEFAULTS["points_per_ghost"]
    ghost_speed: int = _DEFAULTS["ghost_speed"]
    frightened_duration: int = _DEFAULTS["frightened_duration"]
    ghost_respawn_delay: int = _DEFAULTS["ghost_respawn_delay"]
    seed: int = _DEFAULTS["seed"]
    level_max_time: int = _DEFAULTS["level_max_time"]
    levels: list[LevelConfig] = field(default_factory=list)


def _warn(message: str) -> None:
    """Log a non-fatal configuration problem to the user."""
    print(f"[config] warning: {message}")


def strip_comments(raw: str) -> str:
    """Strip leading-``#`` comment lines (``#`` inside strings survives)."""
    lines: list[str] = []
    for line in raw.splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _coerce_int(data: dict[str, Any], key: str) -> int:
    """Return a bounded int for ``key``, falling back to its default."""
    default = int(_DEFAULTS[key])
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        _warn(f"'{key}' must be an integer; using default {default}")
        value = default
    low, high = _BOUNDS[key]
    if value < low or value > high:
        clamped = max(low, min(high, value))
        _warn(f"'{key}'={value} out of range [{low}, {high}]; "
              f"clamped to {clamped}")
        value = clamped
    return value


def _coerce_filename(data: dict[str, Any]) -> str:
    """Return a safe highscore filename."""
    default = str(_DEFAULTS["highscore_filename"])
    value = data.get("highscore_filename", default)
    if not isinstance(value, str) or not value.strip():
        _warn(f"'highscore_filename' invalid; using default '{default}'")
        return default
    return value


def _coerce_levels(data: dict[str, Any]) -> list[LevelConfig]:
    """Return a validated, padded list of at least ``_MIN_LEVELS`` levels."""
    raw = data.get("levels")
    levels: list[LevelConfig] = []
    if not isinstance(raw, list) or not raw:
        _warn("'levels' missing or empty; generating default levels")
        raw = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            _warn(f"level #{index} is not an object; skipped")
            continue
        levels.append(_coerce_level(entry, index))
    # Pad up to the minimum number of levels required by the subject.
    while len(levels) < _MIN_LEVELS:
        size = min(_MAX_LEVEL_SIZE, 21 + 2 * len(levels))
        levels.append(LevelConfig(width=size, height=size, pacgum=42))
    return levels


def _coerce_level(entry: dict[str, Any], index: int) -> LevelConfig:
    """Validate a single level entry."""
    def bounded(key: str, fallback: int) -> int:
        value = entry.get(key, fallback)
        if not isinstance(value, int) or isinstance(value, bool):
            _warn(f"level #{index} '{key}' invalid; using {fallback}")
            return fallback
        clamped = max(_MIN_LEVEL_SIZE, min(_MAX_LEVEL_SIZE, value))
        if clamped != value and key in ("width", "height"):
            _warn(f"level #{index} '{key}'={value} out of range; "
                  f"clamped to {clamped}")
            return clamped
        return value if key == "pacgum" else clamped

    width = bounded("width", 21)
    height = bounded("height", 21)
    pacgum = max(1, bounded("pacgum", 42))
    return LevelConfig(width=width, height=height, pacgum=pacgum)


def parse_config(data: dict[str, Any]) -> Config:
    """Build a validated :class:`Config` from a raw JSON-decoded dict."""
    if not isinstance(data, dict):
        _warn("top-level config is not an object; using all defaults")
        data = {}
    return Config(
        highscore_filename=_coerce_filename(data),
        cell_size=_coerce_int(data, "cell_size"),
        fps=_coerce_int(data, "fps"),
        lives=_coerce_int(data, "lives"),
        player_speed=_coerce_int(data, "player_speed"),
        points_per_pacgum=_coerce_int(data, "points_per_pacgum"),
        points_per_super_pacgum=_coerce_int(data, "points_per_super_pacgum"),
        points_per_ghost=_coerce_int(data, "points_per_ghost"),
        ghost_speed=_coerce_int(data, "ghost_speed"),
        frightened_duration=_coerce_int(data, "frightened_duration"),
        ghost_respawn_delay=_coerce_int(data, "ghost_respawn_delay"),
        seed=_coerce_int(data, "seed"),
        level_max_time=_coerce_int(data, "level_max_time"),
        levels=_coerce_levels(data),
    )


def load_config(path: str) -> Config:
    """Load + decomment + validate a config file (raises ConfigError)."""
    if not path.endswith(".json"):
        raise ConfigError(f"'{path}' is not a .json file")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        raise ConfigError(f"config file '{path}' not found")
    except OSError as exc:
        raise ConfigError(f"cannot read config file '{path}': {exc}")

    try:
        data = json.loads(strip_comments(raw))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in '{path}': {exc}")

    return parse_config(data)
