"""Ghost entities and their movement AI."""

from __future__ import annotations

import random
from collections import deque
from enum import Enum, auto

from src.entities.entity import Entity
from src.maze_loader import Direction, Maze


class GhostMode(Enum):
    """Behavioural state of a ghost.

    Attributes:
        CHASE: Hunting the player; contact costs a life.
        FRIGHTENED: Edible and fleeing; contact scores points.
        EATEN: Waiting on its corner for the respawn delay to elapse.
    """

    CHASE = auto()
    FRIGHTENED = auto()
    EATEN = auto()


def _ahead(pos: tuple[int, int], direction: Direction,
           n: int) -> tuple[int, int]:
    """Return the cell ``n`` steps ahead of ``pos`` along ``direction``.

    The extra leftward shift when facing up reproduces the overflow bug
    of the 1980 arcade machine, which the original Pinky targeting is
    famous for.

    Args:
        pos: The cell to project from.
        direction: The facing to project along.
        n: How many cells to look ahead.

    Returns:
        The projected cell, which may lie outside the maze.
    """
    tx = pos[0] + direction.dx * n
    ty = pos[1] + direction.dy * n
    if direction is Direction.UP:
        tx -= n
    return (tx, ty)


class Ghost(Entity):
    """An autonomous ghost that paths towards a personality-based target.

    Each step is a fresh breadth-first search, so a ghost always takes a
    shortest path to whatever cell its personality currently wants.
    """

    def __init__(self, x: int, y: int, color: str = "red",
                 personality: str = "blinky",
                 scatter_corner: tuple[int, int] = (0, 0)) -> None:
        """Create a ghost on its corner cell.

        Args:
            x: Spawn column, normally a maze corner.
            y: Spawn row, normally a maze corner.
            color: Display colour name.
            personality: One of ``blinky``, ``pinky``, ``inky``, ``clyde``.
            scatter_corner: Cell Clyde retreats to when close to the
                player.
        """
        super().__init__(x, y, Direction.UP)
        self.color = color
        self.personality = personality
        self.scatter_corner = scatter_corner
        self.mode: GhostMode = GhostMode.CHASE
        self.respawn_timer: float = 0.0

    def set_frightened(self, frightened: bool) -> None:
        """Enter or leave frightened mode.

        Ignored while eaten, so a super-pacgum cannot revive a ghost that
        is still serving its respawn delay.

        Args:
            frightened: True to make the ghost edible, False to restore
                the chase.
        """
        if self.mode is GhostMode.EATEN:
            return
        self.mode = GhostMode.FRIGHTENED if frightened else GhostMode.CHASE

    def get_eaten(self, respawn_delay: float) -> None:
        """Send the ghost back to its corner for ``respawn_delay`` seconds."""
        self.mode = GhostMode.EATEN
        self.respawn_timer = respawn_delay
        self.reset_to_spawn()

    def update(self, maze: Maze, player_pos: tuple[int, int],
               player_dir: Direction, blinky_pos: tuple[int, int],
               mode: str, dt: float) -> None:
        """Advance the ghost by one cell.

        Args:
            maze: The maze to walk in.
            player_pos: Current player cell.
            player_dir: Current player facing, used by Pinky and Inky.
            blinky_pos: Current cell of the red ghost, used by Inky.
            mode: Difficulty mode: ``classic``, ``chase`` or ``random``.
            dt: Seconds elapsed since this ghost's previous step, used to
                count down the respawn delay.
        """
        if self.mode is GhostMode.EATEN:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.mode = GhostMode.CHASE
            return
        if self.mode is GhostMode.FRIGHTENED:
            step = self._flee_step(maze, player_pos)
        elif mode == "random":
            step = self._random_step(maze)
        else:
            raw = self._raw_target(player_pos, player_dir, blinky_pos, mode)
            step = self._chase_step(maze, self._resolve_target(maze, raw))
            if step is None:
                step = self._chase_step(maze, player_pos)
        if step is not None:
            self.try_move(maze, step)

    def _raw_target(self, player_pos: tuple[int, int], player_dir: Direction,
                    blinky_pos: tuple[int, int],
                    mode: str) -> tuple[int, int]:
        """Return the cell this ghost's personality aims at.

        Blinky targets the player, Pinky ambushes four cells ahead, Inky
        aims at the player's position mirrored through Blinky, and Clyde
        retreats to his corner once he gets within eight cells. In
        ``chase`` mode every ghost simply targets the player.

        Args:
            player_pos: Current player cell.
            player_dir: Current player facing.
            blinky_pos: Current cell of the red ghost.
            mode: Difficulty mode.

        Returns:
            The target cell, which may be a wall or lie off the grid.
        """
        if mode == "chase" or self.personality == "blinky":
            return player_pos
        if self.personality == "pinky":
            return _ahead(player_pos, player_dir, 4)
        if self.personality == "inky":
            pivot = _ahead(player_pos, player_dir, 2)
            return (2 * pivot[0] - blinky_pos[0],
                    2 * pivot[1] - blinky_pos[1])
        if self.personality == "clyde":
            dx = self.x - player_pos[0]
            dy = self.y - player_pos[1]
            if dx * dx + dy * dy > 64:
                return player_pos
            return self.scatter_corner
        return player_pos

    def _resolve_target(self, maze: Maze,
                        raw: tuple[int, int]) -> tuple[int, int]:
        """Pull a possibly illegal target onto the nearest open cell.

        Args:
            maze: The maze to search.
            raw: The personality's target, possibly a wall or off-grid.

        Returns:
            A cell inside the grid, walkable when one can be reached.
        """
        tx = max(0, min(maze.width - 1, raw[0]))
        ty = max(0, min(maze.height - 1, raw[1]))
        if maze.is_corridor(tx, ty):
            return (tx, ty)
        seen: set[tuple[int, int]] = {(tx, ty)}
        queue: deque[tuple[int, int]] = deque([(tx, ty)])
        while queue:
            cx, cy = queue.popleft()
            if maze.is_corridor(cx, cy):
                return (cx, cy)
            for direction in Direction:
                nx, ny = cx + direction.dx, cy + direction.dy
                if maze.in_bounds(nx, ny) and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return (tx, ty)

    def _chase_step(
        self, maze: Maze, target: tuple[int, int]
    ) -> Direction | None:
        """Return the first step of a shortest path to ``target``.

        The search carries the direction it started with, so reaching the
        target immediately yields the step to take now.

        Args:
            maze: The maze to search.
            target: The cell to path towards.

        Returns:
            The direction to step in, or None when ``target`` is
            unreachable or already occupied.
        """
        start = (self.x, self.y)
        seen: set[tuple[int, int]] = {start}
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
        """Return the neighbour that moves furthest from ``target``.

        Ties are broken randomly so frightened ghosts do not all pick the
        same escape route.

        Args:
            maze: The maze to walk in.
            target: The cell to run away from.

        Returns:
            The direction to step in, or None in a sealed cell.
        """
        options = maze.neighbors(self.x, self.y)
        if not options:
            return None

        def distance(cell: tuple[int, int]) -> int:
            """Return the Manhattan distance from ``cell`` to the target."""
            return abs(cell[0] - target[0]) + abs(cell[1] - target[1])

        random.shuffle(options)
        best = max(options, key=lambda opt: distance((opt[0], opt[1])))
        return best[2]

    def _random_step(self, maze: Maze) -> Direction | None:
        """Return a random step, avoiding a U-turn where possible.

        Args:
            maze: The maze to walk in.

        Returns:
            The direction to step in, or None in a sealed cell.
        """
        options = maze.neighbors(self.x, self.y)
        if not options:
            return None
        back = self.direction.opposite()
        forward = [opt for opt in options if opt[2] is not back]
        return random.choice(forward or options)[2]
