"""pygame front end: window, input and the main loop.

Draws every frame but steps the sim at a fixed rate (from ``player_speed``),
so speed is independent of frame rate. pygame is imported inside ``run`` so
headless environments don't need a display (they get the text demo).
"""

from __future__ import annotations

from src.config import Config
from src.game import Game, GameState
from src.highscores import HighScoreStore
from src.maze_loader import Direction


def run(config: Config) -> int:
    """Launch the graphical application. Returns a process exit code."""
    try:
        import pygame
    except ImportError:
        print("[ui] pygame is not installed; run `make install`.")
        print("[ui] falling back to a headless text demo.\n")
        from src.ui.headless import run_headless_demo
        return run_headless_demo(config)

    from src.ui.render import Renderer

    highscores = HighScoreStore(config.highscore_filename)
    game = Game(config, highscores)

    pygame.init()
    cell = config.cell_size
    max_w = max(level.width for level in config.levels)
    max_h = max(level.height for level in config.levels)
    screen = pygame.display.set_mode((max_w * cell, max_h * cell + 2 * cell))
    pygame.display.set_caption("Pac-Man")
    clock = pygame.time.Clock()
    renderer = Renderer(config)

    # Arrow keys and WASD both steer Pac-Man.
    turn_keys = {
        pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
        pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
        pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
        pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
    }

    # Simulation step: player_speed cells per second (doubled by the F3 cheat).
    accumulator = 0.0

    running = True
    while running:
        frame_dt = clock.tick(config.fps) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type != pygame.KEYDOWN:
                continue
            elif game.state is GameState.MENU:
                if event.key in (pygame.K_UP, pygame.K_w):
                    game.menu_move(-1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    game.menu_move(1)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if game.menu_select() == "Exit":
                        running = False
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif game.state in (GameState.HIGHSCORES, GameState.INSTRUCTIONS):
                # Any key returns to the main menu.
                game.return_to_menu()
            elif game.state in (GameState.PLAYING, GameState.PAUSED):
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    game.toggle_pause()
                elif (event.key == pygame.K_m
                        and game.state is GameState.PAUSED):
                    game.return_to_menu()
                elif event.key in turn_keys and game.level is not None:
                    game.level.player.request_direction(turn_keys[event.key])
                elif event.key == pygame.K_F1:
                    game.cheats.toggle_invincible()
                elif event.key == pygame.K_F2:
                    game.cheats.toggle_freeze()
                elif event.key == pygame.K_F3:
                    game.cheats.toggle_speed()
                elif event.key == pygame.K_F4:
                    game.cheats.skip_level()
            elif game.state in (GameState.GAME_OVER, GameState.VICTORY):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    game.submit_score()
                    game.return_to_menu()
                elif event.key == pygame.K_BACKSPACE:
                    game.name_backspace()
                elif event.unicode:
                    game.name_append(event.unicode)

        # Advance the simulation in fixed steps while playing.
        if game.state is GameState.PLAYING:
            speed = config.player_speed * (2 if game.cheats.speed_boost else 1)
            step_dt = 1.0 / max(1, speed)
            accumulator += frame_dt
            while accumulator >= step_dt:
                game.tick(step_dt)
                accumulator -= step_dt
        else:
            accumulator = 0.0

        renderer.draw(screen, game)
        pygame.display.flip()

    pygame.quit()
    return 0
