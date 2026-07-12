"""pygame renderer. Same wall-bit walk as the terminal view, but each set
wall becomes a draw.line instead of an ASCII segment.
"""

from __future__ import annotations

import pygame

from src.config import Config
from src.entities import GhostMode
from src.game import MENU_ITEMS, Game, GameState
from src.level import Level
from src.maze_loader import Direction, Maze

Color = tuple[int, int, int]

_BG: Color = (0, 0, 0)
_WALL: Color = (33, 33, 222)        # classic Pac-Man maze blue
_PACGUM: Color = (255, 214, 170)
_SUPER: Color = (255, 184, 82)
_PLAYER: Color = (255, 224, 0)
_TEXT: Color = (255, 255, 255)
_DIM: Color = (170, 170, 170)
_FRIGHT: Color = (40, 60, 255)
_EATEN: Color = (110, 110, 110)

_GHOST_COLORS: dict[str, Color] = {
    "red": (255, 0, 0),
    "pink": (255, 140, 200),
    "cyan": (0, 220, 220),
    "orange": (255, 160, 40),
}

# Rows reserved at the top of the window for the HUD.
_HUD_CELLS = 2

# Which way Pac-Man's mouth points, in degrees, per facing direction.
_MOUTH_ANGLE: dict[Direction, float] = {
    Direction.RIGHT: 0.0,
    Direction.UP: 90.0,
    Direction.LEFT: 180.0,
    Direction.DOWN: 270.0,
}


class Renderer:
    """Draws :class:`~src.game.Game` state onto a pygame surface."""

    def __init__(self, config: Config) -> None:
        """Prepare fonts and cached metrics from ``config``."""
        self.cell = config.cell_size
        self.hud_h = _HUD_CELLS * self.cell
        self.font = pygame.font.SysFont("menlo,consolas,monospace",
                                        int(self.cell * 0.75))
        self.big = pygame.font.SysFont("menlo,consolas,monospace",
                                       int(self.cell * 1.5), bold=True)

    # -- public ----------------------------------------------------------

    def draw(self, surface: pygame.Surface, game: Game) -> None:
        """Render the whole frame for the game's current state."""
        surface.fill(_BG)
        if game.level is not None and game.state in (
                GameState.PLAYING, GameState.PAUSED):
            self._draw_level(surface, game.level)
            self._draw_hud(surface, game)

        if game.state is GameState.MENU:
            self._draw_menu(surface, game)
        elif game.state is GameState.HIGHSCORES:
            self._draw_highscores(surface, game)
        elif game.state is GameState.INSTRUCTIONS:
            self._draw_instructions(surface)
        elif game.state is GameState.PAUSED:
            self._draw_center_overlay(surface, "PAUSED",
                                      "P / Esc: resume    M: main menu")
        elif game.state is GameState.GAME_OVER:
            self._draw_end(surface, game, "GAME OVER")
        elif game.state is GameState.VICTORY:
            self._draw_end(surface, game, "YOU WIN!")

    # -- maze (the ported wall drawing) ----------------------------------

    def _draw_level(self, surface: pygame.Surface, level: Level) -> None:
        self._draw_maze(surface, level.maze)
        self._draw_pellets(surface, level)
        self._draw_ghosts(surface, level)
        self._draw_player(surface, level)

    def _draw_maze(self, surface: pygame.Surface, maze: Maze) -> None:
        """Draw a line on every cell edge whose wall bit is set."""
        s = self.cell
        for y in range(maze.height):
            for x in range(maze.width):
                px = x * s
                py = y * s + self.hud_h
                if maze.is_wall_between(x, y, Direction.UP):
                    pygame.draw.line(surface, _WALL,
                                     (px, py), (px + s, py), 2)
                if maze.is_wall_between(x, y, Direction.LEFT):
                    pygame.draw.line(surface, _WALL,
                                     (px, py), (px, py + s), 2)
                if maze.is_wall_between(x, y, Direction.RIGHT):
                    pygame.draw.line(surface, _WALL,
                                     (px + s, py), (px + s, py + s), 2)
                if maze.is_wall_between(x, y, Direction.DOWN):
                    pygame.draw.line(surface, _WALL,
                                     (px, py + s), (px + s, py + s), 2)

    def _cell_center(self, x: int, y: int) -> tuple[int, int]:
        """Return the pixel centre of grid cell ``(x, y)``."""
        s = self.cell
        return (x * s + s // 2, y * s + s // 2 + self.hud_h)

    def _draw_pellets(self, surface: pygame.Surface, level: Level) -> None:
        for (x, y) in level.pacgums:
            pygame.draw.circle(surface, _PACGUM,
                               self._cell_center(x, y),
                               max(2, self.cell // 8))
        for (x, y) in level.super_pacgums:
            pygame.draw.circle(surface, _SUPER,
                               self._cell_center(x, y),
                               max(4, self.cell // 4))

    def _draw_player(self, surface: pygame.Surface, level: Level) -> None:
        """Draw Pac-Man: a circle with a wedge mouth facing his direction."""
        cx, cy = self._cell_center(level.player.x, level.player.y)
        radius = self.cell // 2 - 2
        pygame.draw.circle(surface, _PLAYER, (cx, cy), radius)
        # Cut a mouth: a black triangle from the centre facing the direction.
        import math
        base = _MOUTH_ANGLE[level.player.direction]
        half = 28.0  # half-mouth aperture in degrees
        points = [(cx, cy)]
        for angle in (base - half, base + half):
            rad = math.radians(angle)
            points.append((cx + int(radius * math.cos(rad)),
                           cy - int(radius * math.sin(rad))))
        pygame.draw.polygon(surface, _BG, points)

    def _draw_ghosts(self, surface: pygame.Surface, level: Level) -> None:
        radius = self.cell // 2 - 2
        for ghost in level.ghosts:
            if ghost.mode is GhostMode.FRIGHTENED:
                color = _FRIGHT
            elif ghost.mode is GhostMode.EATEN:
                color = _EATEN
            else:
                color = _GHOST_COLORS.get(ghost.color, (255, 0, 0))
            pygame.draw.circle(surface, color,
                               self._cell_center(ghost.x, ghost.y), radius)

    # -- HUD & overlays --------------------------------------------------

    def _draw_hud(self, surface: pygame.Surface, game: Game) -> None:
        assert game.level is not None
        parts = [
            f"SCORE {game.score}",
            f"LIVES {game.lives}",
            f"LEVEL {game.level_index + 1}/{len(game.config.levels)}",
            f"TIME {int(max(0, game.level.time_left)):>3}",
        ]
        text = self.font.render("   ".join(parts), True, _TEXT)
        surface.blit(text, (8, (self.hud_h - text.get_height()) // 2))

    def _draw_menu(self, surface: pygame.Surface, game: Game) -> None:
        w = surface.get_width()
        title = self.big.render("PAC-MAN", True, _PLAYER)
        surface.blit(title, ((w - title.get_width()) // 2, self.cell * 3))

        y = self.cell * 7
        for i, item in enumerate(MENU_ITEMS):
            selected = i == game.menu_index
            label = f"> {item} <" if selected else item
            color = _PLAYER if selected else _TEXT
            surf = self.font.render(label, True, color)
            surface.blit(surf, ((w - surf.get_width()) // 2, y))
            y += int(self.cell * 1.4)

        hint = self.font.render("Up/Down + ENTER", True, _DIM)
        surface.blit(hint, ((w - hint.get_width()) // 2, y + self.cell))

    def _draw_highscores(self, surface: pygame.Surface, game: Game) -> None:
        w = surface.get_width()
        title = self.big.render("HIGHSCORES", True, _PLAYER)
        surface.blit(title, ((w - title.get_width()) // 2, self.cell * 2))

        top = game.highscores.scores[:10]
        if top:
            lines = [f"{i + 1:>2}. {s.name:<10} {s.points:>7}"
                     for i, s in enumerate(top)]
        else:
            lines = ["(no scores yet)"]
        lines += ["", "any key to go back"]
        self._draw_lines(surface, lines, self.cell * 5)

    def _draw_instructions(self, surface: pygame.Surface) -> None:
        w = surface.get_width()
        title = self.big.render("INSTRUCTIONS", True, _PLAYER)
        surface.blit(title, ((w - title.get_width()) // 2, self.cell * 2))

        lines = [
            "Eat all pacgums to clear a level.",
            "Super-pacgums make ghosts edible.",
            "Avoid ghosts - contact costs a life.",
            "",
            "Move: arrows / WASD    Pause: P / Esc",
            "",
            "Cheats (for review):",
            "F1 invincible   F2 freeze ghosts",
            "F3 speed        F4 skip level",
            "",
            "any key to go back",
        ]
        self._draw_lines(surface, lines, self.cell * 5)

    def _draw_end(self, surface: pygame.Surface, game: Game,
                  heading: str) -> None:
        w = surface.get_width()
        title = self.big.render(heading, True, _PLAYER)
        surface.blit(title, ((w - title.get_width()) // 2, self.cell * 3))
        lines = [
            f"Final score: {game.score}",
            "",
            f"Enter your name: {game.pending_name}_",
            "(letters/spaces, max 10, then ENTER)",
        ]
        self._draw_lines(surface, lines, self.cell * 5)

    def _draw_center_overlay(self, surface: pygame.Surface,
                             heading: str, subtitle: str) -> None:
        w, h = surface.get_width(), surface.get_height()
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surface.blit(veil, (0, 0))
        title = self.big.render(heading, True, _TEXT)
        sub = self.font.render(subtitle, True, _DIM)
        surface.blit(title, ((w - title.get_width()) // 2, h // 2 - 40))
        surface.blit(sub, ((w - sub.get_width()) // 2, h // 2 + 10))

    def _draw_lines(self, surface: pygame.Surface, lines: list[str],
                    top: int) -> None:
        w = surface.get_width()
        y = top
        for line in lines:
            surf = self.font.render(line, True, _TEXT)
            surface.blit(surf, ((w - surf.get_width()) // 2, y))
            y += int(self.cell * 1.1)
