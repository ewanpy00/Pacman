"""Tests for the game rules: collisions, scoring, pacing and menus."""

import os

from src.config import load_config
from src.entities import GhostMode
from src.game import PAUSE_ITEMS, Game, GameState
from src.highscores import HighScoreStore


def _new_game(tmp_path: object) -> Game:
    """Return a game started on the first level, saving to ``tmp_path``."""
    cfg = load_config("config.json")
    store = HighScoreStore(os.path.join(str(tmp_path), "hs.json"))
    game = Game(cfg, store)
    game.start_new_game()
    return game


def test_same_cell_chase_costs_a_life(tmp_path: object) -> None:
    """Sharing a cell with a chasing ghost costs one life."""
    game = _new_game(tmp_path)
    assert game.level is not None
    lives = game.lives
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.CHASE
    ghost.x, ghost.y = game.level.player.position
    game._handle_collisions(game.level.player.position, [ghost.position])
    assert game.lives == lives - 1


def test_swap_is_detected_as_a_hit(tmp_path: object) -> None:
    """Walking through a ghost head-on counts as contact."""
    game = _new_game(tmp_path)
    assert game.level is not None
    lives = game.lives
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.CHASE
    player_prev = (5, 5)
    ghost_prev = (6, 5)
    game.level.player.x, game.level.player.y = ghost_prev
    ghost.x, ghost.y = player_prev
    game._handle_collisions(player_prev, [ghost_prev])
    assert game.lives == lives - 1


def test_invincibility_cheat_prevents_the_hit(tmp_path: object) -> None:
    """With F1 on, a chasing ghost is harmless."""
    game = _new_game(tmp_path)
    assert game.level is not None
    game.cheats.toggle_invincible()
    lives = game.lives
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.CHASE
    ghost.x, ghost.y = game.level.player.position
    game._handle_collisions(game.level.player.position, [ghost.position])
    assert game.lives == lives


def test_eating_frightened_ghost_scores(tmp_path: object) -> None:
    """An edible ghost scores points and is sent home."""
    game = _new_game(tmp_path)
    assert game.level is not None
    ghost = game.level.ghosts[0]
    ghost.mode = GhostMode.FRIGHTENED
    ghost.x, ghost.y = game.level.player.position
    game._handle_collisions(game.level.player.position, [ghost.position])
    assert game.score == game.config.points_per_ghost
    assert ghost.mode is GhostMode.EATEN


def test_pacgum_scores_and_is_removed(tmp_path: object) -> None:
    """Eating a pacgum adds points and clears the cell."""
    game = _new_game(tmp_path)
    assert game.level is not None
    cell = game.level.player.position
    game.level.pacgums.add(cell)
    game._handle_pellets()
    assert game.score == game.config.points_per_pacgum
    assert cell not in game.level.pacgums


def test_super_pacgum_frightens_every_ghost(tmp_path: object) -> None:
    """A super-pacgum scores more and makes the ghosts edible."""
    game = _new_game(tmp_path)
    assert game.level is not None
    cell = game.level.player.position
    game.level.super_pacgums.add(cell)
    game._handle_pellets()
    assert game.score == game.config.points_per_super_pacgum
    assert all(g.mode is GhostMode.FRIGHTENED for g in game.level.ghosts)


def test_ghost_personality_targets() -> None:
    """Each personality aims at its own cell, and ``chase`` overrides all."""
    from src.entities.ghost import Ghost
    from src.maze_loader import Direction
    player = (10, 10)
    blinky_at = (2, 2)

    blinky = Ghost(0, 0, "red", "blinky")
    assert blinky._raw_target(player, Direction.RIGHT, blinky_at,
                              "classic") == (10, 10)

    pinky = Ghost(0, 0, "pink", "pinky")
    assert pinky._raw_target(player, Direction.RIGHT, blinky_at,
                             "classic") == (14, 10)
    assert pinky._raw_target(player, Direction.UP, blinky_at,
                             "classic") == (6, 6)

    inky = Ghost(0, 0, "cyan", "inky")
    pivot = (12, 10)
    assert inky._raw_target(player, Direction.RIGHT, blinky_at,
                            "classic") == (2 * pivot[0] - 2,
                                           2 * pivot[1] - 2)

    clyde = Ghost(20, 20, "orange", "clyde", scatter_corner=(0, 20))
    assert clyde._raw_target(player, Direction.RIGHT, blinky_at,
                             "classic") == player
    clyde.x, clyde.y = 11, 11
    assert clyde._raw_target(player, Direction.RIGHT, blinky_at,
                             "classic") == (0, 20)

    assert pinky._raw_target(player, Direction.RIGHT, blinky_at,
                             "chase") == player


def test_clearing_pellets_advances_level(tmp_path: object) -> None:
    """An empty level moves the game on, keeping score and lives."""
    game = _new_game(tmp_path)
    assert game.level is not None
    game.level.pacgums.clear()
    game.level.super_pacgums.clear()
    game._check_level_end()
    assert game.level_index == 1
    assert game.state is GameState.PLAYING


def test_step_durations_follow_the_configured_speeds(
        tmp_path: object) -> None:
    """``player_speed`` and ``ghost_speed`` each drive their own clock."""
    game = _new_game(tmp_path)
    game.config.player_speed = 5
    game.config.ghost_speed = 4
    assert abs(game.player_step - 0.2) < 1e-9
    assert abs(game.ghost_step - 0.25) < 1e-9


def test_speed_cheat_only_affects_the_player(tmp_path: object) -> None:
    """F3 must not drag the ghosts along with it."""
    game = _new_game(tmp_path)
    player_before = game.player_step
    ghost_before = game.ghost_step
    game.cheats.toggle_speed()
    assert abs(game.player_step - player_before / 2) < 1e-9
    assert game.ghost_step == ghost_before


def test_ghost_timers_count_real_seconds(tmp_path: object) -> None:
    """Respawn delays are in seconds, whatever the ghost step rate is."""
    game = _new_game(tmp_path)
    assert game.level is not None
    game.cheats.toggle_invincible()
    ghost = game.level.ghosts[0]
    ghost.get_eaten(5.0)
    for _ in range(60):
        game.tick(1.0 / 60.0)
    assert abs(ghost.respawn_timer - 4.0) < 0.3


def test_extra_life_cheat_grants_one_life(tmp_path: object) -> None:
    """F5 adds exactly one life, and only once per press."""
    game = _new_game(tmp_path)
    lives = game.lives
    game.cheats.grant_extra_life()
    game.tick(1.0 / 60.0)
    assert game.lives == lives + 1
    game.tick(1.0 / 60.0)
    assert game.lives == lives + 1


def test_level_skip_cheat_advances_the_level(tmp_path: object) -> None:
    """F4 clears the current level without eating everything."""
    game = _new_game(tmp_path)
    game.cheats.skip_level()
    game.tick(1.0 / 60.0)
    assert game.level_index == 1


def test_running_out_of_time_costs_a_life(tmp_path: object) -> None:
    """The level clock ending is treated as a death, not a game over."""
    game = _new_game(tmp_path)
    assert game.level is not None
    lives = game.lives
    game.level.time_left = 0.01
    game.tick(0.1)
    assert game.lives == lives - 1
    assert game.state is GameState.PLAYING
    assert game.level.time_left == float(game.config.level_max_time)


def test_pause_menu_resumes_and_exits(tmp_path: object) -> None:
    """Both pause entries do what they say."""
    game = _new_game(tmp_path)
    game.toggle_pause()
    assert game.state is GameState.PAUSED
    assert PAUSE_ITEMS[game.pause_index] == "Resume"
    game.pause_select()
    assert game.state.name == "PLAYING"

    game.toggle_pause()
    game.pause_move(1)
    assert PAUSE_ITEMS[game.pause_index] == "Return to main menu"
    game.pause_select()
    assert game.state.name == "MENU"


def test_paused_game_does_not_advance(tmp_path: object) -> None:
    """No time passes and nothing moves while paused."""
    game = _new_game(tmp_path)
    assert game.level is not None
    game.toggle_pause()
    before = game.level.time_left
    position = game.level.player.position
    for _ in range(60):
        game.tick(1.0 / 60.0)
    assert game.level.time_left == before
    assert game.level.player.position == position
