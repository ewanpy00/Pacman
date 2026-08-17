"""One playable level: its maze, its actors and its pellets."""

from __future__ import annotations

import random

from src.config import Config, LevelConfig
from src.entities import Ghost, Player
from src.maze_loader import Maze, load_maze

_GHOSTS = (
    ("red", "blinky"),
    ("pink", "pinky"),
    ("cyan", "inky"),
    ("orange", "clyde"),
)


class Level:
    """A generated maze populated with the player, ghosts and pellets.

    The player spawns in the middle, the four ghosts on the four corners,
    and the super-pacgums sit on those same corners, as the subject
    requires.
    """

    def __init__(self, config: Config, spec: LevelConfig, seed: int):
        """Generate the maze and place everything on it.

        Args:
            config: Validated game settings.
            spec: Size and pellet budget of this level.
            seed: Maze seed; ``0`` asks for a random maze.

        Raises:
            MazeError: If the maze generator is missing or fails.
        """
        self.config = config
        self.spec = spec
        self.maze: Maze = load_maze(spec.width, spec.height, seed)

        spawn = self.maze.center_corridor()
        self.player = Player(*spawn)

        self.ghosts: list[Ghost] = [
            Ghost(cx, cy, color, personality, scatter_corner=(cx, cy))
            for (cx, cy), (color, personality)
            in zip(self.maze.corners(), _GHOSTS)
        ]

        self.pacgums: set[tuple[int, int]] = set()
        self.super_pacgums: set[tuple[int, int]] = set()
        self._place_pellets(seed)

        self.time_left: float = float(config.level_max_time)

    def _place_pellets(self, seed: int) -> None:
        """Scatter pacgums and put a super-pacgum on every open corner.

        The player's spawn and the corners are excluded from the pacgum
        draw so the level never starts with a free pellet underfoot.

        Args:
            seed: Seed for the placement draw, keeping level one
                reproducible alongside its maze.
        """
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
        self.super_pacgums = {
            corner for corner in corners
            if self.maze.is_corridor(*corner)
        }

    @property
    def cleared(self) -> bool:
        """Whether every pellet on this level has been eaten."""
        return not self.pacgums and not self.super_pacgums

    def remaining_pellets(self) -> int:
        """Return how many pellets of either kind are still uneaten."""
        return len(self.pacgums) + len(self.super_pacgums)
