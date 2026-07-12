"""Tests for the highscore store."""

import os

from src.highscores import HighScoreStore, sanitize_name


def test_sanitize_name_strips_symbols() -> None:
    assert sanitize_name("Bob!!@#") == "Bob"
    assert sanitize_name("") == "AAA"
    assert sanitize_name("a" * 30) == "a" * 10


def test_top_ten_only(tmp_path: object) -> None:
    path = os.path.join(str(tmp_path), "hs.json")
    store = HighScoreStore(path)
    for i in range(15):
        store.add(f"P{i}", i * 10)
    assert len(store.scores) == 10
    assert store.scores[0].points == 140


def test_persistence_roundtrip(tmp_path: object) -> None:
    path = os.path.join(str(tmp_path), "hs.json")
    store = HighScoreStore(path)
    store.add("Ivan", 500)
    store.save()
    reloaded = HighScoreStore(path)
    assert reloaded.scores[0].name == "Ivan"
    assert reloaded.scores[0].points == 500


def test_missing_file_is_empty(tmp_path: object) -> None:
    path = os.path.join(str(tmp_path), "nope.json")
    store = HighScoreStore(path)
    assert store.scores == []
    assert store.qualifies(1) is True
