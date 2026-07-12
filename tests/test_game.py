"""Tests for core game rules: collisions, scoring, level progression."""

from src.config import load_config
from src.entities import GhostMode
from src.game import Game, GameState
from src.highscores import HighScoreStore


def _new_game(tmp_path: object) -> Game:
    import os
    cfg = load_config("config.json")
    store = HighScoreStore(os.path.join(str(tmp_path), "hs.json"))
    game = Game(cfg, store)
    game.start_new_game()
    return game


def test_same_cell_chase_costs_a_life(tmp_path: object) -> None:
    game = _new_game(tmp_path)
    assert game.level is not None
    lives = game.lives
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.CHASE
    ghost.x, ghost.y = game.level.player.position
    game._handle_collisions(game.level.player.position, [ghost.position])
    assert game.lives == lives - 1


def test_swap_is_detected_as_a_hit(tmp_path: object) -> None:
    game = _new_game(tmp_path)
    assert game.level is not None
    lives = game.lives
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.CHASE
    # Player and ghost exchanged cells this tick (passed through each other).
    player_prev = (5, 5)
    ghost_prev = (6, 5)
    game.level.player.x, game.level.player.y = ghost_prev
    ghost.x, ghost.y = player_prev
    game._handle_collisions(player_prev, [ghost_prev])
    assert game.lives == lives - 1


def test_eating_frightened_ghost_scores(tmp_path: object) -> None:
    game = _new_game(tmp_path)
    assert game.level is not None
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.FRIGHTENED
    ghost.x, ghost.y = game.level.player.position
    game._handle_collisions(game.level.player.position, [ghost.position])
    assert game.score == game.config.points_per_ghost
    assert ghost.mode is GhostMode.EATEN


def test_pacgum_scores_and_is_removed(tmp_path: object) -> None:
    game = _new_game(tmp_path)
    assert game.level is not None
    cell = game.level.player.position
    game.level.pacgums.add(cell)
    game._handle_pellets()
    assert game.score == game.config.points_per_pacgum
    assert cell not in game.level.pacgums


def test_clearing_pellets_advances_level(tmp_path: object) -> None:
    game = _new_game(tmp_path)
    assert game.level is not None
    game.level.pacgums.clear()
    game.level.super_pacgums.clear()
    game._check_level_end()
    assert game.level_index == 1
    assert game.state is GameState.PLAYING
