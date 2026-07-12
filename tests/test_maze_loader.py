"""Tests for the maze adapter against the real assigned generator."""

from src.maze_loader import Direction, load_maze


def test_reproducible_with_seed() -> None:
    a = load_maze(21, 21, seed=42)
    b = load_maze(21, 21, seed=42)
    assert a.grid == b.grid


def test_dimensions_match_request() -> None:
    maze = load_maze(23, 21, seed=42)
    assert maze.width == 23
    assert maze.height == 21
    assert len(maze.grid) == 21
    assert all(len(row) == 23 for row in maze.grid)


def test_center_corridor_is_walkable() -> None:
    maze = load_maze(21, 21, seed=42)
    cx, cy = maze.center_corridor()
    assert maze.in_bounds(cx, cy)
    assert any(maze.can_move(cx, cy, d) for d in Direction)


def test_can_move_respects_walls() -> None:
    maze = load_maze(21, 21, seed=42)
    # Outer corner (0,0) must not be able to leave the grid.
    assert not maze.can_move(0, 0, Direction.UP)
    assert not maze.can_move(0, 0, Direction.LEFT)
