"""Dependency-free text renderer: one Level frame to stdout (smoke tests)."""

from __future__ import annotations

from src.level import Level
from src.maze_loader import Direction, Maze

_PLAYER = "C"
_GHOST = "M"
_SUPER = "O"
_PACGUM = "."
_EMPTY = " "


def _cell_char(maze: Maze, level: Level, x: int, y: int) -> str:
    """Return the glyph for a single maze cell."""
    if (x, y) == level.player.position:
        return _PLAYER
    for ghost in level.ghosts:
        if ghost.position == (x, y):
            return _GHOST
    if (x, y) in level.super_pacgums:
        return _SUPER
    if (x, y) in level.pacgums:
        return _PACGUM
    if not maze.is_corridor(x, y):
        return "#"
    return _EMPTY


def render_level(level: Level) -> str:
    """Render one level frame as multi-line ASCII (debug view only)."""
    maze = level.maze
    rows: list[str] = []
    for y in range(maze.height):
        chars: list[str] = []
        for x in range(maze.width):
            chars.append(_cell_char(maze, level, x, y))
            # Draw the east wall as a separator when present.
            east = maze.is_wall_between(x, y, Direction.RIGHT)
            chars.append("|" if east else " ")
        rows.append("".join(chars))
    return "\n".join(rows)
