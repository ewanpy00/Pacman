"""Tests for the maze generator adapter."""

from src.maze_loader import Direction, load_maze


def test_reproducible_with_seed() -> None:
    """The same non-zero seed always yields the same maze."""
    a = load_maze(21, 21, seed=42)
    b = load_maze(21, 21, seed=42)
    assert a.grid == b.grid


def test_dimensions_match_request() -> None:
    """The adapter returns exactly the requested grid shape."""
    maze = load_maze(23, 21, seed=42)
    assert maze.width == 23
    assert maze.height == 21
    assert len(maze.grid) == 21
    assert all(len(row) == 23 for row in maze.grid)


def test_center_corridor_is_walkable() -> None:
    """The player spawn is always an open cell with at least one exit."""
    maze = load_maze(21, 21, seed=42)
    cx, cy = maze.center_corridor()
    assert maze.in_bounds(cx, cy)
    assert any(maze.can_move(cx, cy, d) for d in Direction)


def test_can_move_respects_walls() -> None:
    """Movement off the grid is refused, as is movement through a wall."""
    maze = load_maze(21, 21, seed=42)
    assert not maze.can_move(0, 0, Direction.UP)
    assert not maze.can_move(0, 0, Direction.LEFT)


def test_neighbors_are_symmetric() -> None:
    """If A lists B as a neighbour, B lists A back."""
    maze = load_maze(21, 21, seed=42)
    for x, y, direction in maze.neighbors(5, 5):
        back = [d for _, _, d in maze.neighbors(x, y)]
        assert direction.opposite() in back
