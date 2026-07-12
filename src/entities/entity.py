"""Base class shared by the player and the ghosts."""

from __future__ import annotations

from src.maze_loader import Direction, Maze


class Entity:
    """An actor on the grid; position is in whole cells (no sub-pixel here)."""

    def __init__(self, x: int, y: int, direction: Direction = Direction.LEFT):
        """Create an entity at cell ``(x, y)`` facing ``direction``."""
        self.x = x
        self.y = y
        self.direction = direction
        self.spawn_x = x
        self.spawn_y = y

    def reset_to_spawn(self) -> None:
        """Move the entity back to its spawn cell."""
        self.x = self.spawn_x
        self.y = self.spawn_y

    def try_move(self, maze: Maze, direction: Direction) -> bool:
        """Step one cell if legal; return whether it moved."""
        if not maze.can_move(self.x, self.y, direction):
            return False
        self.x += direction.dx
        self.y += direction.dy
        self.direction = direction
        return True

    @property
    def position(self) -> tuple[int, int]:
        """Return the entity's ``(x, y)`` cell."""
        return (self.x, self.y)
