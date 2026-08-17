"""Text-mode fallback used when pygame is unavailable.

It proves that config loading, maze generation and the simulation all
work even on a machine with no display, which makes it a useful smoke
test during setup.
"""

from __future__ import annotations

from src.config import Config
from src.game import Game, GameState
from src.highscores import HighScoreStore
from src.ui.ascii_view import render_level

_DEMO_TICKS = 200
_DEMO_DT = 1.0 / 60.0


def run_headless_demo(config: Config) -> int:
    """Print the first level and simulate a few seconds of play.

    Args:
        config: Validated game settings.

    Returns:
        A process exit code: ``0`` on success, ``1`` if the first level
        could not be generated.
    """
    highscores = HighScoreStore(config.highscore_filename)
    game = Game(config, highscores)
    game.start_new_game()

    if game.level is None:
        print("[headless] could not build the first level.")
        return 1

    print("First level (fixed seed) opening frame:\n")
    print(render_level(game.level))
    print(f"\nplayer spawn: {game.level.player.position}")
    print(f"ghosts:       {[g.position for g in game.level.ghosts]}")
    print(f"pellets:      {game.level.remaining_pellets()}")

    for _ in range(_DEMO_TICKS):
        if game.state is not GameState.PLAYING:
            break
        game.tick(_DEMO_DT)

    print(f"\nafter {_DEMO_TICKS} ticks -> "
          f"state={game.state.name} score={game.score} lives={game.lives}")
    return 0
