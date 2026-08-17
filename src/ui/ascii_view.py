"""Plain-text rendering of a level, used by the headless demo and tests."""

from __future__ import annotations

from src.level import Level
from src.maze_loader import Direction, Maze

_PLAYER = "C"
_GHOST = "M"
_SUPER = "O"
_PACGUM = "."
_EMPTY = " "


def _cell_char(maze: Maze, level: Level, x: int, y: int) -> str:
    """Return the character standing for whatever occupies ``(x, y)``.

    Args:
        maze: The level's maze.
        level: The level to inspect.
        x: Column of the cell.
        y: Row of the cell.

    Returns:
        A single character: actors take priority over pellets, which take
        priority over the floor.
    """
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
    """Render ``level`` as multi-line ASCII art.

    Each cell takes two characters: its contents, then ``|`` when a wall
    closes off its eastern side.

    Args:
        level: The level to draw.

    Returns:
        The drawing, with rows separated by newlines.
    """
    maze = level.maze
    rows: list[str] = []
    for y in range(maze.height):
        chars: list[str] = []
        for x in range(maze.width):
            chars.append(_cell_char(maze, level, x, y))
            east = maze.is_wall_between(x, y, Direction.RIGHT)
            chars.append("|" if east else " ")
        rows.append("".join(chars))
    return "\n".join(rows)
