"""Ghost entities and their movement AI."""

from __future__ import annotations

import random
from collections import deque
from enum import Enum, auto

from src.entities.entity import Entity
from src.maze_loader import Direction, Maze


class GhostMode(Enum):
    """The behavioural state of a ghost."""

    CHASE = auto()        # hunt the player
    FRIGHTENED = auto()   # edible; flee the player
    EATEN = auto()        # returning to its corner, temporarily inactive


class Ghost(Entity):
    """Autonomous ghost: BFS toward the player, or away when frightened."""

    def __init__(self, x: int, y: int, color: str = "red"):
        """Create a ghost at corner cell ``(x, y)`` with a display colour."""
        super().__init__(x, y, Direction.UP)
        self.color = color
        self.mode: GhostMode = GhostMode.CHASE
        self.respawn_timer: float = 0.0

    def set_frightened(self, frightened: bool) -> None:
        """Enter or leave frightened mode (ignored while eaten)."""
        if self.mode is GhostMode.EATEN:
            return
        self.mode = GhostMode.FRIGHTENED if frightened else GhostMode.CHASE

    def get_eaten(self, respawn_delay: float) -> None:
        """Mark the ghost as eaten and start its respawn countdown."""
        self.mode = GhostMode.EATEN
        self.respawn_timer = respawn_delay
        self.reset_to_spawn()

    def update(self, maze: Maze, target: tuple[int, int], dt: float) -> None:
        """Advance one step toward/away from ``target`` for this tick."""
        if self.mode is GhostMode.EATEN:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.mode = GhostMode.CHASE
            return
        step = self._next_step(maze, target)
        if step is not None:
            self.try_move(maze, step)

    def _next_step(
        self, maze: Maze, target: tuple[int, int]
    ) -> Direction | None:
        """First step toward ``target`` (BFS), or away when frightened."""
        if self.mode is GhostMode.FRIGHTENED:
            return self._flee_step(maze, target)
        return self._chase_step(maze, target)

    def _chase_step(
        self, maze: Maze, target: tuple[int, int]
    ) -> Direction | None:
        start = (self.x, self.y)
        seen: set[tuple[int, int]] = {start}
        # Queue holds (cell, first_direction_taken_from_start).
        queue: deque[tuple[tuple[int, int], Direction | None]] = deque(
            [(start, None)])
        while queue:
            (cx, cy), first = queue.popleft()
            if (cx, cy) == target:
                return first
            for nx, ny, direction in maze.neighbors(cx, cy):
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                queue.append(((nx, ny), first or direction))
        return None

    def _flee_step(
        self, maze: Maze, target: tuple[int, int]
    ) -> Direction | None:
        options = maze.neighbors(self.x, self.y)
        if not options:
            return None

        def distance(cell: tuple[int, int]) -> int:
            return abs(cell[0] - target[0]) + abs(cell[1] - target[1])

        random.shuffle(options)
        best = max(options, key=lambda opt: distance((opt[0], opt[1])))
        return best[2]
