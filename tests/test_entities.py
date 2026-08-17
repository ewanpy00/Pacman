"""Tests for player steering and ghost pathfinding.

These build tiny hand-written mazes instead of calling the generator, so
the expected behaviour is unambiguous. Wall bits are north=1, east=2,
south=4, west=8.
"""

from src.entities import Ghost, GhostMode, Player
from src.entities.player import _TURN_TTL_STEPS
from src.maze_loader import Direction, Maze


def _corridor() -> Maze:
    """Return a horizontal 3x1 corridor with walls all around it."""
    return Maze(grid=[[13, 5, 7]], width=3, height=1)


def _box() -> Maze:
    """Return a 2x2 room open in the middle and closed on the outside."""
    return Maze(grid=[[9, 3], [12, 6]], width=2, height=2)


def test_blocked_turn_keeps_the_current_direction() -> None:
    """Turning into a wall must not stall the player."""
    player = Player(1, 0)
    player.request_direction(Direction.UP)
    player.update(_corridor())
    assert player.position == (0, 0)
    assert player.direction is Direction.LEFT


def test_queued_turn_is_taken_once_it_is_legal() -> None:
    """A queued direction survives until a step can use it."""
    maze = _box()
    player = Player(0, 0)
    player.request_direction(Direction.RIGHT)
    player.update(maze)
    assert player.position == (1, 0)
    player.request_direction(Direction.DOWN)
    player.update(maze)
    assert player.position == (1, 1)
    assert player.direction is Direction.DOWN


def _room() -> Maze:
    """Return a 3x3 room that is open inside and walled on the outside."""
    return Maze(grid=[[9, 1, 3],
                      [8, 0, 2],
                      [12, 4, 6]],
                width=3, height=3)


def test_two_quick_presses_are_both_honoured() -> None:
    """A second press inside one step must not erase the first."""
    maze = _room()
    player = Player(1, 1)
    player.request_direction(Direction.UP)
    player.request_direction(Direction.RIGHT)
    player.update(maze)
    assert player.position == (1, 0)
    player.update(maze)
    assert player.position == (2, 0)
    assert player.direction.name == "RIGHT"


def test_repeated_press_is_collapsed() -> None:
    """Mashing one key does not fill the queue with duplicates."""
    player = Player(1, 1)
    for _ in range(10):
        player.request_direction(Direction.UP)
    assert player.pending_turns == [Direction.UP]


def test_newer_turn_wins_over_a_blocked_one() -> None:
    """A turn into a wall must not hold up the direction actually wanted."""
    maze = _room()
    player = Player(1, 1)
    player.x, player.y = 1, 2
    player.request_direction(Direction.DOWN)
    player.request_direction(Direction.UP)
    player.update(maze)
    assert player.position == (1, 1)
    assert player.pending_turns == []


def test_stale_turn_is_forgotten() -> None:
    """A request that never becomes legal expires instead of lurking."""
    maze = _corridor()
    player = Player(1, 0)
    player.request_direction(Direction.UP)
    for _ in range(_TURN_TTL_STEPS):
        player.update(maze)
    assert player.pending_turns == []


def test_respawn_clears_queued_turns() -> None:
    """Losing a life must not carry an old turn into the next attempt."""
    player = Player(1, 0)
    player.request_direction(Direction.UP)
    player.reset_to_spawn()
    assert player.pending_turns == []


def test_dead_end_stops_the_player() -> None:
    """A cell with no exit leaves the player where it is."""
    player = Player(0, 0)
    player.update(Maze(grid=[[15]], width=1, height=1))
    assert player.position == (0, 0)


def test_reset_to_spawn_cancels_interpolation() -> None:
    """A respawn moves the previous cell too, so nothing slides."""
    player = Player(2, 0)
    player.mark_prev()
    player.update(_corridor())
    assert player.position != (player.prev_x, player.prev_y)
    player.reset_to_spawn()
    assert player.position == (2, 0)
    assert (player.prev_x, player.prev_y) == (2, 0)


def test_chase_step_points_along_the_corridor() -> None:
    """Breadth-first search returns the first step of a shortest path."""
    ghost = Ghost(0, 0)
    assert ghost._chase_step(_corridor(), (2, 0)) is Direction.RIGHT


def test_chase_step_is_none_when_unreachable() -> None:
    """A target with no path yields no step, so the caller can fall back."""
    ghost = Ghost(0, 0)
    maze = Maze(grid=[[9, 3], [12, 6]], width=2, height=2)
    assert ghost._chase_step(maze, (5, 5)) is None


def test_flee_step_moves_away_from_the_player() -> None:
    """A frightened ghost picks the neighbour furthest from the player."""
    ghost = Ghost(1, 0)
    assert ghost._flee_step(_corridor(), (0, 0)) is Direction.RIGHT


def test_resolve_target_clamps_into_the_grid() -> None:
    """An off-grid target is pulled back inside the maze."""
    ghost = Ghost(0, 0)
    assert ghost._resolve_target(_corridor(), (99, 99)) == (2, 0)


def test_resolve_target_finds_the_nearest_corridor() -> None:
    """A target inside a wall is moved to the closest open cell."""
    ghost = Ghost(0, 0)
    maze = Maze(grid=[[13, 5, 15]], width=3, height=1)
    assert ghost._resolve_target(maze, (2, 0)) == (1, 0)


def test_random_step_avoids_turning_back() -> None:
    """Wandering ghosts keep going rather than oscillating in place."""
    ghost = Ghost(1, 0)
    ghost.direction = Direction.RIGHT
    assert ghost._random_step(_corridor()) is Direction.RIGHT


def test_eaten_ghost_ignores_a_super_pacgum() -> None:
    """A ghost serving its respawn delay cannot be made edible again."""
    ghost = Ghost(0, 0)
    ghost.get_eaten(5.0)
    ghost.set_frightened(True)
    assert ghost.mode is GhostMode.EATEN


def test_eaten_ghost_returns_to_chase_after_the_delay() -> None:
    """The respawn timer counts down in seconds and restores the chase."""
    maze = _corridor()
    ghost = Ghost(0, 0)
    ghost.get_eaten(1.0)
    ghost.update(maze, (2, 0), Direction.RIGHT, (0, 0), "classic", 0.5)
    assert ghost.mode is GhostMode.EATEN
    ghost.update(maze, (2, 0), Direction.RIGHT, (0, 0), "classic", 0.5)
    assert ghost.mode.name == "CHASE"
