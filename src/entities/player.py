"""The player-controlled Pac-Man."""

from __future__ import annotations

from src.entities.entity import Entity
from src.maze_loader import Direction, Maze


class Player(Entity):
    """Pac-Man: buffers a desired turn, applied once it's legal."""

    def __init__(self, x: int, y: int):
        """Create the player at spawn cell ``(x, y)``."""
        super().__init__(x, y, Direction.LEFT)
        self.desired_direction: Direction = Direction.LEFT
        self.alive = True

    def request_direction(self, direction: Direction) -> None:
        """Buffer a turn to be applied as soon as it is legal."""
        self.desired_direction = direction

    def update(self, maze: Maze) -> None:
        """Advance one step, honouring the buffered turn if possible."""
        if self.try_move(maze, self.desired_direction):
            return
        # Buffered turn blocked: keep gliding in the current direction.
        self.try_move(maze, self.direction)
