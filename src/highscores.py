"""Persistent top-ten highscore table, stored as a JSON file.

Every read is defensive: a missing, unreadable, malformed or partly
corrupt file yields an empty (or partial) table rather than an error, so
a bad file can never stop the game from starting.
"""

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
    """Reduce ``name`` to the characters the subject allows.

    Args:
        name: Raw name as typed by the player.

    Returns:
        Up to ten alphanumeric-or-space characters, or ``"AAA"`` when
        nothing usable is left.
    """
    cleaned = "".join(
        ch for ch in name if ch.isalnum() or ch == " ")
    cleaned = cleaned.strip()[:MAX_NAME_LENGTH]
    return cleaned if cleaned else "AAA"


class HighScoreStore:
    """The top-ten table, loaded on creation and saved on demand."""

    def __init__(self, path: str) -> None:
        """Load the table from ``path``, starting empty if unreadable.

        Args:
            path: JSON file backing the table.
        """
        self._path = path
        self._scores: list[Score] = []
        self.load()

    @property
    def scores(self) -> list[Score]:
        """A copy of the table, best score first."""
        return list(self._scores)

    def load(self) -> None:
        """Re-read the table from disk, warning but not raising on error."""
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
        """Turn decoded JSON into a sorted, validated table.

        Entries that are not well-formed objects with a string name and a
        non-negative integer score are skipped individually.

        Args:
            data: Whatever the JSON file decoded to.

        Returns:
            At most ``MAX_ENTRIES`` scores, best first.
        """
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
        """Return whether ``points`` would make it into the table."""
        if points < 0:
            return False
        if len(self._scores) < MAX_ENTRIES:
            return True
        return points > self._scores[-1].points

    def add(self, name: str, points: int) -> None:
        """Insert a score, keeping the table sorted and capped at ten.

        Args:
            name: Player name; sanitised before being stored.
            points: Score to record; negative values become zero.
        """
        safe_points = max(0, int(points))
        entry = Score(sanitize_name(name), safe_points)
        self._scores.append(entry)
        self._scores.sort(key=lambda s: s.points, reverse=True)
        self._scores = self._scores[:MAX_ENTRIES]

    def save(self) -> None:
        """Write the table back to disk, warning but not raising on error."""
        payload = [{"name": s.name, "points": s.points}
                   for s in self._scores]
        try:
            with open(self._path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except OSError as exc:
            print(f"[highscores] warning: could not save "
                  f"'{self._path}' ({exc})")
