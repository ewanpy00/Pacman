"""Tests for the persistent highscore table."""

import os

from src.highscores import HighScoreStore, sanitize_name


def test_sanitize_name_strips_symbols() -> None:
    """Names keep only letters, digits and spaces, capped at ten."""
    assert sanitize_name("Bob!!@#") == "Bob"
    assert sanitize_name("") == "AAA"
    assert sanitize_name("a" * 30) == "a" * 10


def test_top_ten_only(tmp_path: object) -> None:
    """Only the ten best scores are kept, best first."""
    path = os.path.join(str(tmp_path), "hs.json")
    store = HighScoreStore(path)
    for i in range(15):
        store.add(f"P{i}", i * 10)
    assert len(store.scores) == 10
    assert store.scores[0].points == 140


def test_persistence_roundtrip(tmp_path: object) -> None:
    """A saved table reloads identically."""
    path = os.path.join(str(tmp_path), "hs.json")
    store = HighScoreStore(path)
    store.add("Ivan", 500)
    store.save()
    reloaded = HighScoreStore(path)
    assert reloaded.scores[0].name == "Ivan"
    assert reloaded.scores[0].points == 500


def test_missing_file_is_empty(tmp_path: object) -> None:
    """A missing file yields an empty table rather than an error."""
    path = os.path.join(str(tmp_path), "nope.json")
    store = HighScoreStore(path)
    assert store.scores == []
    assert store.qualifies(1) is True


def test_corrupt_file_is_ignored(tmp_path: object) -> None:
    """Unparsable content is reported but never raises."""
    path = os.path.join(str(tmp_path), "hs.json")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{not json at all")
    assert HighScoreStore(path).scores == []


def test_bad_entries_are_skipped(tmp_path: object) -> None:
    """Malformed rows are dropped one by one, keeping the good ones."""
    path = os.path.join(str(tmp_path), "hs.json")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('[{"name": "Ok", "points": 10},'
                     ' {"name": 5, "points": 10},'
                     ' {"name": "Neg", "points": -3},'
                     ' "junk"]')
    scores = HighScoreStore(path).scores
    assert [s.name for s in scores] == ["Ok"]
