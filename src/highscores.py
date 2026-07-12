"""Top-10 highscores in a JSON file; a bad/missing file gives empty table."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10


@dataclass(frozen=True)
class Score:
    """A single highscore entry."""

    name: str
    points: int


def sanitize_name(name: str) -> str:
    """Keep alnum/spaces, cap at 10 chars; empty -> ``AAA``."""
    cleaned = "".join(
        ch for ch in name if ch.isalnum() or ch == " ")
    cleaned = cleaned.strip()[:MAX_NAME_LENGTH]
    return cleaned if cleaned else "AAA"


class HighScoreStore:
    """Loads, updates and persists the top-10 highscores."""

    def __init__(self, path: str) -> None:
        """Create a store backed by the file at ``path`` and load it."""
        self._path = path
        self._scores: list[Score] = []
        self.load()

    @property
    def scores(self) -> list[Score]:
        """Return the current top scores, highest first."""
        return list(self._scores)

    def load(self) -> None:
        """Load scores from disk, tolerating any file/format error."""
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            self._scores = []
            return
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[highscores] warning: could not read "
                  f"'{self._path}' ({exc}); starting empty")
            self._scores = []
            return
        self._scores = self._parse(data)

    def _parse(self, data: Any) -> list[Score]:
        """Turn decoded JSON into a sorted, trimmed list of valid scores."""
        if not isinstance(data, list):
            print("[highscores] warning: file is not a list; ignoring")
            return []
        parsed: list[Score] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            points = item.get("points")
            if not isinstance(name, str):
                continue
            if not isinstance(points, int) or isinstance(points, bool):
                continue
            if points < 0:
                continue
            parsed.append(Score(sanitize_name(name), points))
        parsed.sort(key=lambda s: s.points, reverse=True)
        return parsed[:MAX_ENTRIES]

    def qualifies(self, points: int) -> bool:
        """Return whether ``points`` would make the top-10 table."""
        if points < 0:
            return False
        if len(self._scores) < MAX_ENTRIES:
            return True
        return points > self._scores[-1].points

    def add(self, name: str, points: int) -> None:
        """Insert a new score (sanitising inputs) and keep the top 10."""
        safe_points = max(0, int(points))
        entry = Score(sanitize_name(name), safe_points)
        self._scores.append(entry)
        self._scores.sort(key=lambda s: s.points, reverse=True)
        self._scores = self._scores[:MAX_ENTRIES]

    def save(self) -> None:
        """Persist scores to disk, tolerating write errors."""
        payload = [{"name": s.name, "points": s.points}
                   for s in self._scores]
        try:
            with open(self._path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except OSError as exc:
            print(f"[highscores] warning: could not save "
                  f"'{self._path}' ({exc})")
