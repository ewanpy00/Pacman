"""The player-controlled Pac-Man."""

from __future__ import annotations

from src.entities.entity import Entity
from src.maze_loader import Direction, Maze

_TURN_TTL_STEPS = 3
_MAX_PENDING = 2


class Player(Entity):
    """Pac-Man, steered by a short queue of buffered turn requests.

    A key press never moves anything: it appends the direction to a small
    queue that is consulted on the next step. Two properties matter for
    how the controls feel.

    *Nothing is lost.* Between two steps there are many frames, so a
    player rounding a corner often presses two directions before the
    first one is applied. A single slot would drop the earlier press; the
    queue applies them on consecutive steps instead.

    *Nothing goes stale.* A request that never becomes legal is forgotten
    after a few steps, so a turn pressed into a wall cannot fire much
    later at an unrelated junction.
    """

    def __init__(self, x: int, y: int):
        """Spawn the player on ``(x, y)`` facing left with no turns queued."""
        super().__init__(x, y, Direction.LEFT)
        self._pending: list[tuple[Direction, int]] = []
        self.alive = True

    @property
    def pending_turns(self) -> list[Direction]:
        """The queued directions, oldest first."""
        return [direction for direction, _ttl in self._pending]

    def request_direction(self, direction: Direction) -> None:
        """Queue ``direction`` as a turn to take at the next opportunity.

        Repeating the direction already at the back of the queue is
        ignored, so holding or mashing one key cannot flood it.

        Args:
            direction: The direction the player asked for.
        """
        if self._pending and self._pending[-1][0] is direction:
            return
        self._pending.append((direction, _TURN_TTL_STEPS))
        if len(self._pending) > _MAX_PENDING:
            self._pending.pop(0)

    def update(self, maze: Maze) -> None:
        """Advance one cell, honouring the oldest turn that is legal now.

        Queued turns are tried oldest first. The first legal one is taken
        and every request before it is dropped, so a stale turn into a
        wall cannot hold up a newer one the player actually wants. If
        none is legal the player carries on in its current direction,
        which is what stops a turn into a wall from stalling it; only a
        dead end does that.

        Args:
            maze: The maze to walk in.
        """
        for index, (direction, _ttl) in enumerate(self._pending):
            if self.try_move(maze, direction):
                del self._pending[:index + 1]
                self._age()
                return
        self.try_move(maze, self.direction)
        self._age()

    def reset_to_spawn(self) -> None:
        """Teleport back to spawn and forget any queued turns."""
        super().reset_to_spawn()
        self._pending.clear()

    def _age(self) -> None:
        """Drop queued turns that have waited too many steps."""
        self._pending = [(direction, ttl - 1)
                         for direction, ttl in self._pending if ttl > 1]
