"""Adapter around the assigned ``mazegenerator`` package.

The generator is used as-is. Everything the rest of the game knows about
its interface (grid shape, wall bit layout, coordinate order) lives here,
behind the :class:`Maze` model.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """A cardinal direction, its cell delta and its wall bit.

    The generator encodes walls in the low four bits of every cell:
    north=1, east=2, south=4, west=8.
    """

    UP = (0, -1, 1)
    RIGHT = (1, 0, 2)
    DOWN = (0, 1, 4)
    LEFT = (-1, 0, 8)

    def __init__(self, dx: int, dy: int, wall_bit: int) -> None:
        """Store the per-direction deltas and wall mask."""
        self.dx = dx
        self.dy = dy
        self.wall_bit = wall_bit

    def opposite(self) -> "Direction":
        """Return the direction facing the other way."""
        return _OPPOSITES[self]


_OPPOSITES: dict[Direction, Direction] = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}

_ISOLATED = 15


class MazeError(Exception):
    """Raised when the maze generator is missing or returns bad data."""


@dataclass
class Maze:
    """A grid of wall bitmasks plus the queries the game needs.

    Attributes:
        grid: ``grid[y][x]`` is the wall bitmask of that cell.
        width: Number of columns.
        height: Number of rows.
    """

    grid: list[list[int]]
    width: int
    height: int

    def in_bounds(self, x: int, y: int) -> bool:
        """Return whether ``(x, y)`` lies inside the grid."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall_between(self, x: int, y: int, direction: Direction) -> bool:
        """Return whether a wall blocks ``direction`` out of ``(x, y)``."""
        return bool(self.grid[y][x] & direction.wall_bit)

    def can_move(self, x: int, y: int, direction: Direction) -> bool:
        """Return whether a step from ``(x, y)`` in ``direction`` is legal."""
        nx, ny = x + direction.dx, y + direction.dy
        if not self.in_bounds(nx, ny):
            return False
        return not self.is_wall_between(x, y, direction)

    def neighbors(self, x: int, y: int) -> list[tuple[int, int, Direction]]:
        """Return the reachable neighbours of ``(x, y)``.

        Args:
            x: Column of the cell.
            y: Row of the cell.

        Returns:
            One ``(nx, ny, direction)`` triple per open side.
        """
        result: list[tuple[int, int, Direction]] = []
        for direction in Direction:
            if self.can_move(x, y, direction):
                result.append(
                    (x + direction.dx, y + direction.dy, direction))
        return result

    def is_corridor(self, x: int, y: int) -> bool:
        """Return whether ``(x, y)`` is walkable rather than walled off."""
        return self.in_bounds(x, y) and self.grid[y][x] != _ISOLATED

    def corners(self) -> list[tuple[int, int]]:
        """Return the four corner cells, clockwise from the top left."""
        return [
            (0, 0),
            (self.width - 1, 0),
            (0, self.height - 1),
            (self.width - 1, self.height - 1),
        ]

    def center_corridor(self) -> tuple[int, int]:
        """Return an open cell near the middle of the maze.

        The generator draws a solid "42" logo in the centre, so the
        geometric middle is often walled in. A breadth-first search
        outwards finds the closest cell that is open and has at least one
        exit; the geometric centre is returned if none exists.
        """
        cx, cy = self.width // 2, self.height // 2
        seen: set[tuple[int, int]] = {(cx, cy)}
        queue: deque[tuple[int, int]] = deque([(cx, cy)])
        while queue:
            x, y = queue.popleft()
            if self.is_corridor(x, y) and self.grid[y][x] != _ISOLATED:
                if any(self.can_move(x, y, d) for d in Direction):
                    return (x, y)
            for direction in Direction:
                nx, ny = x + direction.dx, y + direction.dy
                if self.in_bounds(nx, ny) and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return (cx, cy)

    def corridor_cells(self) -> list[tuple[int, int]]:
        """Return every walkable cell of the maze."""
        cells: list[tuple[int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != _ISOLATED:
                    cells.append((x, y))
        return cells


def _validate_grid(grid: object, width: int, height: int) -> list[list[int]]:
    """Check the generator's output and normalise it to wall bitmasks.

    Args:
        grid: Whatever the generator returned.
        width: Expected number of columns.
        height: Expected number of rows.

    Returns:
        A ``height`` x ``width`` grid of ints masked to four bits.

    Raises:
        MazeError: If the shape or the cell types are not as expected.
    """
    if not isinstance(grid, list) or len(grid) != height:
        raise MazeError("generator returned an unexpected grid shape")
    checked: list[list[int]] = []
    for row in grid:
        if not isinstance(row, list) or len(row) != width:
            raise MazeError("generator returned a row of the wrong length")
        checked_row: list[int] = []
        for cell in row:
            if not isinstance(cell, int):
                raise MazeError("generator returned a non-integer cell")
            checked_row.append(cell & 0xF)
        checked.append(checked_row)
    return checked


def load_maze(width: int, height: int, seed: int = 0) -> Maze:
    """Generate a maze with the assigned ``mazegenerator`` package.

    ``perfect=False`` is required so the maze contains loops, which is
    what makes it playable as a Pac-Man level.

    Args:
        width: Number of columns.
        height: Number of rows.
        seed: Generator seed; ``0`` asks the package for a random maze.

    Returns:
        The generated maze.

    Raises:
        MazeError: If the package is missing, fails, or returns bad data.
    """
    try:
        from mazegenerator import MazeGenerator
    except ImportError as exc:
        raise MazeError(
            "the 'mazegenerator' package is not installed "
            "(run `make install`)") from exc

    try:
        generator = MazeGenerator(
            size=(width, height), perfect=False, seed=seed)
        raw_grid = generator.maze
    except Exception as exc:
        raise MazeError(f"maze generation failed: {exc}") from exc

    grid = _validate_grid(raw_grid, width, height)
    return Maze(grid=grid, width=width, height=height)
