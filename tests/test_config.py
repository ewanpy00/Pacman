"""Tests for configuration parsing, clamping and comment stripping."""

from src.config import parse_config, strip_comments


def test_strip_comments_removes_hash_lines() -> None:
    """A leading ``#`` turns the whole line into a comment."""
    raw = '# comment\n{\n  # another\n  "lives": 3\n}\n'
    assert "comment" not in strip_comments(raw)
    assert '"lives": 3' in strip_comments(raw)


def test_strip_comments_removes_c_style_lines() -> None:
    """``//`` line comments and ``/* */`` blocks are also removed."""
    raw = ('// header\n'
           '/* a block\n'
           '   spanning lines */\n'
           '{\n'
           '  /* inline */\n'
           '  "lives": 3\n'
           '}\n')
    cleaned = strip_comments(raw)
    assert "header" not in cleaned
    assert "block" not in cleaned
    assert "inline" not in cleaned
    assert '"lives": 3' in cleaned


def test_strip_comments_keeps_markers_inside_strings() -> None:
    """A ``#`` or ``//`` inside a value is part of the value."""
    raw = '{\n  "highscore_filename": "a//b#c.json"\n}\n'
    assert "a//b#c.json" in strip_comments(raw)


def test_missing_values_use_defaults() -> None:
    """An empty config still yields a playable game."""
    cfg = parse_config({})
    assert cfg.lives == 3
    assert cfg.points_per_pacgum == 10
    assert len(cfg.levels) >= 10


def test_out_of_range_values_are_clamped() -> None:
    """Values outside their bounds are pulled back inside."""
    cfg = parse_config({"lives": 9999, "fps": -5})
    assert cfg.lives == 99
    assert cfg.fps == 15


def test_invalid_types_fall_back() -> None:
    """Values of the wrong type are replaced by the default."""
    cfg = parse_config({"lives": "three", "seed": None})
    assert cfg.lives == 3
    assert cfg.seed == 42


def test_unknown_keys_ignored() -> None:
    """Unknown keys neither raise nor disturb the known ones."""
    cfg = parse_config({"totally_unknown": 123, "lives": 5})
    assert cfg.lives == 5


def test_ghost_speed_is_validated() -> None:
    """``ghost_speed`` has a default and is clamped like every rate."""
    assert parse_config({}).ghost_speed == 4
    assert parse_config({"ghost_speed": 999}).ghost_speed == 20
    assert parse_config({"ghost_speed": "fast"}).ghost_speed == 4
