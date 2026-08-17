"""Shared base class for everything that walks the maze."""

from __future__ import annotations

from src.maze_loader import Direction, Maze


class Entity:
    """An actor sitting on exactly one maze cell.

    Movement is discrete: an entity is always on a cell, never between
    two. The previous cell is kept so the renderer can interpolate a
    smooth position between two logic steps.
    """

    def __init__(self, x: int, y: int, direction: Direction = Direction.LEFT):
        """Place the entity on ``(x, y)`` facing ``direction``.

        Args:
            x: Starting column, also remembered as the spawn column.
            y: Starting row, also remembered as the spawn row.
            direction: Initial facing.
        """
        self.x = x
        self.y = y
        self.direction = direction
        self.spawn_x = x
        self.spawn_y = y
        self.prev_x = x
        self.prev_y = y

    def mark_prev(self) -> None:
        """Record the current cell as the interpolation start point."""
        self.prev_x = self.x
        self.prev_y = self.y

    def reset_to_spawn(self) -> None:
        """Teleport back to the spawn cell, cancelling interpolation."""
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.prev_x = self.spawn_x
        self.prev_y = self.spawn_y

    def try_move(self, maze: Maze, direction: Direction) -> bool:
        """Step one cell in ``direction`` if no wall blocks the way.

        Args:
            maze: The maze to test against.
            direction: The direction to step in.

        Returns:
            True if the entity moved, False if a wall stopped it.
        """
        if not maze.can_move(self.x, self.y, direction):
            return False
        self.x += direction.dx
        self.y += direction.dy
        self.direction = direction
        return True

    @property
    def position(self) -> tuple[int, int]:
        """The current cell as an ``(x, y)`` tuple."""
        return (self.x, self.y)
