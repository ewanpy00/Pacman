"""A single playable level: maze, pellets, actors and timer."""

from __future__ import annotations

import random

from src.config import Config, LevelConfig
from src.entities import Ghost, Player
from src.maze_loader import Maze, load_maze

_GHOST_COLORS = ("red", "pink", "cyan", "orange")


class Level:
    """One level's state: maze, pellets, actors, timer (model only)."""

    def __init__(self, config: Config, spec: LevelConfig, seed: int):
        """Build a level from ``spec`` using ``seed`` for its maze."""
        self.config = config
        self.spec = spec
        self.maze: Maze = load_maze(spec.width, spec.height, seed)

        spawn = self.maze.center_corridor()
        self.player = Player(*spawn)

        self.ghosts: list[Ghost] = [
            Ghost(cx, cy, color)
            for (cx, cy), color in zip(self.maze.corners(), _GHOST_COLORS)
        ]

        self.pacgums: set[tuple[int, int]] = set()
        self.super_pacgums: set[tuple[int, int]] = set()
        self._place_pellets(seed)

        self.time_left: float = float(config.level_max_time)

    def _place_pellets(self, seed: int) -> None:
        """Scatter pacgums in corridors and super-pacgums in the corners."""
        rng = random.Random(seed)
        corners = set(self.maze.corners())
        occupied = {self.player.position} | corners
        candidates = [
            cell for cell in self.maze.corridor_cells()
            if cell not in occupied
        ]
        rng.shuffle(candidates)
        count = min(self.spec.pacgum, len(candidates))
        self.pacgums = set(candidates[:count])
        # Super-pacgums sit in the four corners.
        self.super_pacgums = {
            corner for corner in corners
            if self.maze.is_corridor(*corner)
        }

    @property
    def cleared(self) -> bool:
        """Return whether every pellet has been eaten."""
        return not self.pacgums and not self.super_pacgums

    def remaining_pellets(self) -> int:
        """Return the number of pellets still on the board."""
        return len(self.pacgums) + len(self.super_pacgums)
