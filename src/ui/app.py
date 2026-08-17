"""pygame front end: window, input handling and the frame loop.

pygame is imported lazily so that a machine without it (or without a
display) still gets clean config errors and the headless demo instead of
an import traceback.
"""

from __future__ import annotations

from src.config import Config
from src.game import Game, GameState
from src.highscores import HighScoreStore
from src.maze_loader import Direction


def run(config: Config) -> int:
    """Open the window and run the game until the player quits.

    Args:
        config: Validated game settings.

    Returns:
        A process exit code: ``0`` on a normal quit.
    """
    try:
        import pygame
    except ImportError:
        print("[ui] pygame is not installed; run `make install`.")
        print("[ui] falling back to a headless text demo.\n")
        from src.ui.headless import run_headless_demo
        return run_headless_demo(config)

    from src.ui.render import Renderer, window_size

    highscores = HighScoreStore(config.highscore_filename)
    game = Game(config, highscores)

    pygame.init()
    screen = pygame.display.set_mode(window_size(config))
    pygame.display.set_caption("Pac-Man")
    clock = pygame.time.Clock()
    renderer = Renderer(config)

    turn_keys = {
        pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
        pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
        pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
        pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
    }
    up_keys = (pygame.K_UP, pygame.K_w)
    down_keys = (pygame.K_DOWN, pygame.K_s)
    enter_keys = (pygame.K_RETURN, pygame.K_KP_ENTER)
    cheat_keys = {
        pygame.K_F1: lambda: game.cheats.toggle_invincible(),
        pygame.K_F2: lambda: game.cheats.toggle_freeze(),
        pygame.K_F3: lambda: game.cheats.toggle_speed(),
        pygame.K_F4: lambda: game.cheats.skip_level(),
        pygame.K_F5: lambda: game.cheats.grant_extra_life(),
    }

    running = True
    while running:
        frame_dt = clock.tick(config.fps) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type != pygame.KEYDOWN:
                continue
            elif game.state is GameState.MENU:
                if event.key in up_keys:
                    game.menu_move(-1)
                elif event.key in down_keys:
                    game.menu_move(1)
                elif event.key in enter_keys:
                    if game.menu_select() == "Exit":
                        running = False
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif game.state is GameState.DIFFICULTY:
                if event.key in up_keys:
                    game.difficulty_move(-1)
                elif event.key in down_keys:
                    game.difficulty_move(1)
                elif event.key in enter_keys:
                    game.difficulty_select()
                elif event.key == pygame.K_ESCAPE:
                    game.return_to_menu()
            elif game.state in (GameState.HIGHSCORES, GameState.INSTRUCTIONS):
                game.return_to_menu()
            elif game.state is GameState.PAUSED:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    game.toggle_pause()
                elif event.key in up_keys:
                    game.pause_move(-1)
                elif event.key in down_keys:
                    game.pause_move(1)
                elif event.key in enter_keys:
                    game.pause_select()
                elif event.key in cheat_keys:
                    cheat_keys[event.key]()
            elif game.state is GameState.PLAYING:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    game.toggle_pause()
                elif event.key in turn_keys and game.level is not None:
                    game.level.player.request_direction(turn_keys[event.key])
                elif event.key in cheat_keys:
                    cheat_keys[event.key]()
            elif game.state in (GameState.GAME_OVER, GameState.VICTORY):
                if event.key in enter_keys:
                    game.submit_score()
                    game.return_to_menu()
                elif event.key == pygame.K_BACKSPACE:
                    game.name_backspace()
                elif event.unicode:
                    game.name_append(event.unicode)

        game.tick(frame_dt)
        renderer.draw(screen, game)
        pygame.display.flip()

    pygame.quit()
    return 0
