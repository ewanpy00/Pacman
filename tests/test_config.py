"""Tests for the config loader and its defensive validation."""

from src.config import parse_config, strip_comments


def test_strip_comments_removes_hash_lines() -> None:
    raw = '# comment\n{\n  # another\n  "lives": 3\n}\n'
    assert "comment" not in strip_comments(raw)
    assert '"lives": 3' in strip_comments(raw)


def test_missing_values_use_defaults() -> None:
    cfg = parse_config({})
    assert cfg.lives == 3
    assert cfg.points_per_pacgum == 10
    assert len(cfg.levels) >= 10  # padded to the minimum


def test_out_of_range_values_are_clamped() -> None:
    cfg = parse_config({"lives": 9999, "fps": -5})
    assert cfg.lives == 99
    assert cfg.fps == 15


def test_invalid_types_fall_back() -> None:
    cfg = parse_config({"lives": "three", "seed": None})
    assert cfg.lives == 3
    assert cfg.seed == 42


def test_unknown_keys_ignored() -> None:
    cfg = parse_config({"totally_unknown": 123, "lives": 5})
    assert cfg.lives == 5
