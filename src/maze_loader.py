"""The only file that knows the assigned ``mazegenerator`` interface.

Wall bits per cell (set bit = wall blocks that way): N=1, E=2, S=4, W=8.
Grid is ``grid[y][x]``; our public API uses ``(x, y)``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """A cardinal direction with its grid delta and blocking wall bit."""

    UP = (0, -1, 1)
    RIGHT = (1, 0, 2)
    DOWN = (0, 1, 4)
    LEFT = (-1, 0, 8)

    def __init__(self, dx: int, dy: int, wall_bit: int) -> None:
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

# A fully walled/isolated cell (the generator uses this for its '42' logo).
_ISOLATED = 15


class MazeError(Exception):
    """Raised when the assigned generator cannot produce a usable maze."""


@dataclass
class Maze:
    """A maze the game uses without knowing wall bits; coords are (x, y)."""

    grid: list[list[int]]
    width: int
    height: int

    def in_bounds(self, x: int, y: int) -> bool:
        """Return whether ``(x, y)`` lies inside the maze."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall_between(self, x: int, y: int, direction: Direction) -> bool:
        """Return whether a wall blocks leaving ``(x, y)`` in ``direction``."""
        return bool(self.grid[y][x] & direction.wall_bit)

    def can_move(self, x: int, y: int, direction: Direction) -> bool:
        """Return whether an entity at ``(x, y)`` may step ``direction``."""
        nx, ny = x + direction.dx, y + direction.dy
        if not self.in_bounds(nx, ny):
            return False
        return not self.is_wall_between(x, y, direction)

    def neighbors(self, x: int, y: int) -> list[tuple[int, int, Direction]]:
        """Return reachable neighbours of ``(x, y)`` as ``(nx, ny, dir)``."""
        result: list[tuple[int, int, Direction]] = []
        for direction in Direction:
            if self.can_move(x, y, direction):
                result.append(
                    (x + direction.dx, y + direction.dy, direction))
        return result

    def is_corridor(self, x: int, y: int) -> bool:
        """Return whether ``(x, y)`` is a walkable (non-isolated) cell."""
        return self.in_bounds(x, y) and self.grid[y][x] != _ISOLATED

    def corners(self) -> list[tuple[int, int]]:
        """Return the four corner cells (ghost spawns / super-pacgums)."""
        return [
            (0, 0),
            (self.width - 1, 0),
            (0, self.height - 1),
            (self.width - 1, self.height - 1),
        ]

    def center_corridor(self) -> tuple[int, int]:
        """Return the walkable cell nearest the centre (player spawn)."""
        # The '42' logo walls off the exact centre, so BFS out to the
        # nearest open corridor.
        cx, cy = self.width // 2, self.height // 2
        seen: set[tuple[int, int]] = {(cx, cy)}
        queue: deque[tuple[int, int]] = deque([(cx, cy)])
        while queue:
            x, y = queue.popleft()
            if self.is_corridor(x, y) and self.grid[y][x] != _ISOLATED:
                # Prefer a cell with at least one open exit.
                if any(self.can_move(x, y, d) for d in Direction):
                    return (x, y)
            for direction in Direction:
                nx, ny = x + direction.dx, y + direction.dy
                if self.in_bounds(nx, ny) and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return (cx, cy)

    def corridor_cells(self) -> list[tuple[int, int]]:
        """Return every walkable cell (used to place pacgums)."""
        cells: list[tuple[int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != _ISOLATED:
                    cells.append((x, y))
        return cells


def _validate_grid(grid: object, width: int, height: int) -> list[list[int]]:
    """Sanity-check the generator's output and normalise to a 2D int list."""
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
    """Generate a maze (seed 0 = random) via the package; raises MazeError."""
    try:
        from mazegenerator import MazeGenerator
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise MazeError(
            "the 'mazegenerator' package is not installed "
            "(run `make install`)") from exc

    try:
        generator = MazeGenerator(
            size=(width, height), perfect=False, seed=seed)
        raw_grid = generator.maze
    except Exception as exc:  # noqa: BLE001 - adapt to any generator failure
        raise MazeError(f"maze generation failed: {exc}") from exc

    grid = _validate_grid(raw_grid, width, height)
    return Maze(grid=grid, width=width, height=height)
