"""All drawing: the maze, the actors, the HUD and every screen.

Nothing here uses a drawing primitive from the graphics library. The
whole frame is composed in our own :class:`~src.ui.canvas.Canvas` with
hand-written spans, discs, polygons and bitmap text, and the finished
buffer is handed to the window as a single image. That keeps the
graphics layer down to what MiniLibX itself offers: open a window, put
an image, read events.

The renderer is read-only with respect to the game: it never mutates
state, it only asks :class:`~src.game.Game` where things are. Because the
player and the ghosts step on different schedules, each is interpolated
with its own alpha so both move smoothly between logic steps.
"""

from __future__ import annotations

import math

import pygame

from src.config import Config
from src.entities import Entity, GhostMode
from src.game import DIFFICULTIES, MENU_ITEMS, PAUSE_ITEMS, Game, GameState
from src.level import Level
from src.maze_loader import Direction, Maze
from src.ui.canvas import Canvas, Color
from src.ui.font import draw_text, text_height, text_width

_BG: Color = (0, 0, 0)
_WALL: Color = (33, 33, 222)
_PACGUM: Color = (255, 214, 170)
_SUPER: Color = (255, 184, 82)
_PLAYER: Color = (255, 224, 0)
_TEXT: Color = (255, 255, 255)
_DIM: Color = (170, 170, 170)
_FRIGHT: Color = (40, 60, 255)
_CHEAT: Color = (120, 255, 140)
_EYE: Color = (255, 255, 255)
_PUPIL: Color = (20, 20, 130)

_GHOST_COLORS: dict[str, Color] = {
    "red": (255, 0, 0),
    "pink": (255, 140, 200),
    "cyan": (0, 220, 220),
    "orange": (255, 160, 40),
}

_HUD_CELLS = 2

_MENU_SCORES = 5

_PAUSE_KEEP_PERCENT = 35

_WALL_THICKNESS = 2

_MOUTH_ANGLE: dict[Direction, float] = {
    Direction.RIGHT: 0.0,
    Direction.UP: 90.0,
    Direction.LEFT: 180.0,
    Direction.DOWN: 270.0,
}


def window_size(config: Config) -> tuple[int, int]:
    """Return the window size that fits the largest configured level.

    Args:
        config: Validated game settings.

    Returns:
        The ``(width, height)`` of the window in pixels, including the
        HUD strip above the maze.
    """
    cell = config.cell_size
    width = max(level.width for level in config.levels) * cell
    height = max(level.height for level in config.levels) * cell
    return (width, height + _HUD_CELLS * cell)


class Renderer:
    """Composes each frame into a pixel buffer and shows it as an image."""

    def __init__(self, config: Config) -> None:
        """Allocate the frame buffer and pick the two text sizes.

        Args:
            config: Validated game settings.
        """
        self.cell = config.cell_size
        self.hud_h = _HUD_CELLS * self.cell
        self.width, self.height = window_size(config)
        self.canvas = Canvas(self.width, self.height)
        self.small = max(1, self.cell // 12)
        self.big = max(2, self.cell // 6)
        self._maze_layer: Canvas | None = None
        self._maze_owner: Level | None = None

    def draw(self, surface: pygame.Surface, game: Game) -> None:
        """Compose the current screen and blit it to ``surface``.

        Args:
            surface: The display surface to show the frame on.
            game: The game to read state from.
        """
        if game.level is not None and game.state in (
                GameState.PLAYING, GameState.PAUSED):
            self.canvas.copy_from(self._maze_layer_for(game.level))
            self._draw_pellets(game.level)
            self._draw_ghosts(game.level, game.ghost_alpha)
            self._draw_player(game.level, game.player_alpha)
            self._draw_hud(game)
        else:
            self.canvas.clear(_BG)

        if game.state is GameState.MENU:
            self._draw_menu(game)
        elif game.state is GameState.DIFFICULTY:
            self._draw_difficulty(game)
        elif game.state is GameState.HIGHSCORES:
            self._draw_highscores(game)
        elif game.state is GameState.INSTRUCTIONS:
            self._draw_instructions()
        elif game.state is GameState.PAUSED:
            self._draw_pause(game)
        elif game.state is GameState.GAME_OVER:
            self._draw_end(game, "GAME OVER")
        elif game.state is GameState.VICTORY:
            self._draw_end(game, "YOU WIN!")

        frame = pygame.image.frombuffer(
            self.canvas.to_bytes(), (self.width, self.height), "RGB")
        surface.blit(frame, (0, 0))

    def _maze_layer_for(self, level: Level) -> Canvas:
        """Return the cached wall drawing for ``level``, building it once.

        The maze never changes while a level is being played, so it is
        drawn a single time and copied into the frame afterwards. That
        keeps the tens of thousands of wall pixels out of the per-frame
        budget.

        Args:
            level: The level whose maze is being drawn.

        Returns:
            A canvas holding just the background and the walls.
        """
        if self._maze_layer is None or self._maze_owner is not level:
            layer = Canvas(self.width, self.height)
            layer.clear(_BG)
            self._draw_maze(layer, level.maze)
            self._maze_layer = layer
            self._maze_owner = level
        return self._maze_layer

    def _draw_maze(self, canvas: Canvas, maze: Maze) -> None:
        """Draw one line per wall of every cell.

        Args:
            canvas: The buffer to draw into.
            maze: The maze whose walls to trace.
        """
        s = self.cell
        for y in range(maze.height):
            for x in range(maze.width):
                px = x * s
                py = y * s + self.hud_h
                if maze.is_wall_between(x, y, Direction.UP):
                    canvas.line(px, py, px + s, py, _WALL, _WALL_THICKNESS)
                if maze.is_wall_between(x, y, Direction.LEFT):
                    canvas.line(px, py, px, py + s, _WALL, _WALL_THICKNESS)
                if maze.is_wall_between(x, y, Direction.RIGHT):
                    canvas.line(px + s, py, px + s, py + s,
                                _WALL, _WALL_THICKNESS)
                if maze.is_wall_between(x, y, Direction.DOWN):
                    canvas.line(px, py + s, px + s, py + s,
                                _WALL, _WALL_THICKNESS)

    def _cell_center(self, x: int, y: int) -> tuple[int, int]:
        """Return the pixel centre of cell ``(x, y)``."""
        s = self.cell
        return (x * s + s // 2, y * s + s // 2 + self.hud_h)

    def _actor_center(self, e: Entity, alpha: float) -> tuple[int, int]:
        """Return an entity's pixel centre, interpolated by ``alpha``.

        A jump of more than one cell means the entity was teleported by a
        respawn rather than walked, so interpolation is skipped to avoid
        it sliding across the whole maze.

        Args:
            e: The entity to locate.
            alpha: How far it is between its previous and current cell.

        Returns:
            The pixel coordinates to draw the entity at.
        """
        if abs(e.x - e.prev_x) + abs(e.y - e.prev_y) > 1:
            return self._cell_center(e.x, e.y)
        fx = e.prev_x + (e.x - e.prev_x) * alpha
        fy = e.prev_y + (e.y - e.prev_y) * alpha
        s = self.cell
        return (int(fx * s + s // 2), int(fy * s + s // 2 + self.hud_h))

    def _draw_pellets(self, level: Level) -> None:
        """Draw the small pacgums and the larger super-pacgums."""
        small = max(2, self.cell // 8)
        large = max(4, self.cell // 4)
        for (x, y) in level.pacgums:
            cx, cy = self._cell_center(x, y)
            self.canvas.filled_circle(cx, cy, small, _PACGUM)
        for (x, y) in level.super_pacgums:
            cx, cy = self._cell_center(x, y)
            self.canvas.filled_circle(cx, cy, large, _SUPER)

    def _draw_player(self, level: Level, alpha: float) -> None:
        """Draw Pac-Man as a disc with a wedge cut out for the mouth.

        Args:
            level: The level holding the player.
            alpha: The player's interpolation factor.
        """
        cx, cy = self._actor_center(level.player, alpha)
        radius = self.cell // 2 - 2
        self.canvas.filled_circle(cx, cy, radius, _PLAYER)
        base = _MOUTH_ANGLE[level.player.direction]
        half = 28.0
        points = [(cx, cy)]
        for angle in (base - half, base + half):
            rad = math.radians(angle)
            points.append((cx + int(radius * math.cos(rad)),
                           cy - int(radius * math.sin(rad))))
        self.canvas.filled_polygon(points, _BG)

    def _draw_ghosts(self, level: Level, alpha: float) -> None:
        """Draw every ghost in its current mode.

        Args:
            level: The level holding the ghosts.
            alpha: The ghosts' shared interpolation factor.
        """
        radius = self.cell // 2 - 2
        for ghost in level.ghosts:
            cx, cy = self._actor_center(ghost, alpha)
            body = _GHOST_COLORS.get(ghost.color, (255, 0, 0))
            self._draw_ghost_sprite(cx, cy, radius, body,
                                    ghost.direction, ghost.mode)

    def _draw_ghost_sprite(self, cx: int, cy: int, r: int, color: Color,
                           direction: Direction, mode: GhostMode) -> None:
        """Draw one ghost: a domed body, a scalloped skirt and a face.

        An eaten ghost is drawn as a pair of eyes only.

        Args:
            cx: Centre x in pixels.
            cy: Centre y in pixels.
            r: Body radius in pixels.
            color: The ghost's own colour, used when chasing.
            direction: Facing, which the pupils follow.
            mode: The ghost's behavioural state.
        """
        if mode is GhostMode.EATEN:
            self._draw_ghost_eyes(cx, cy, r, direction)
            return
        body = _FRIGHT if mode is GhostMode.FRIGHTENED else color
        self.canvas.filled_circle(cx, cy, r, body)
        self.canvas.filled_rect(cx - r, cy, 2 * r, r, body)
        feet = 4
        foot_w = 2 * r / feet
        base = cy + r
        for i in range(feet):
            left = cx - r + i * foot_w
            self.canvas.filled_polygon([
                (int(left), int(base)),
                (int(left + foot_w), int(base)),
                (int(left + foot_w / 2), int(base - r * 0.5)),
            ], _BG)
        if mode is GhostMode.FRIGHTENED:
            self._draw_scared_face(cx, cy, r)
        else:
            self._draw_ghost_eyes(cx, cy, r, direction)

    def _draw_ghost_eyes(self, cx: int, cy: int, r: int,
                         direction: Direction) -> None:
        """Draw two eyes whose pupils look along ``direction``."""
        eye_r = max(2, r // 3)
        pupil_r = max(1, eye_r // 2)
        px = direction.dx * (eye_r - pupil_r)
        py = direction.dy * (eye_r - pupil_r)
        ey = cy - r // 4
        for ex in (cx - eye_r, cx + eye_r):
            self.canvas.filled_circle(ex, ey, eye_r, _EYE)
            self.canvas.filled_circle(ex + px, ey + py, pupil_r, _PUPIL)

    def _draw_scared_face(self, cx: int, cy: int, r: int) -> None:
        """Draw the small eyes and flat mouth of a frightened ghost."""
        for ex in (cx - r // 2, cx + r // 2):
            self.canvas.filled_circle(ex, cy - r // 5, max(1, r // 5), _EYE)
        self.canvas.filled_rect(cx - r // 2, cy + r // 3, r, 2, _EYE)

    def _text(self, text: str, x: int, y: int, color: Color,
              scale: int) -> None:
        """Draw a string with its top-left corner at ``(x, y)``."""
        draw_text(self.canvas, text, x, y, color, scale)

    def _centered(self, text: str, y: int, color: Color, scale: int) -> None:
        """Draw a string centred horizontally on row ``y``."""
        x = (self.width - text_width(text, scale)) // 2
        draw_text(self.canvas, text, x, y, color, scale)

    def _draw_hud(self, game: Game) -> None:
        """Draw score, lives, level and remaining time, plus any cheats.

        Args:
            game: The game to read the counters from.
        """
        assert game.level is not None
        parts = [
            f"SCORE {game.score}",
            f"LIVES {game.lives}",
            f"LEVEL {game.level_index + 1}/{len(game.config.levels)}",
            f"TIME {int(max(0, game.level.time_left)):>3}",
        ]
        line = "   ".join(parts)
        top = (self.hud_h - text_height(self.small)) // 2
        self._text(line, 8, top, _TEXT, self.small)

        active = self._active_cheats(game)
        if active:
            note = f"CHEATS {' '.join(active)}"
            x = self.width - text_width(note, self.small) - 8
            self._text(note, x, top, _CHEAT, self.small)

    @staticmethod
    def _active_cheats(game: Game) -> list[str]:
        """Return short labels for the cheats currently switched on."""
        labels = []
        if game.cheats.invincible:
            labels.append("INV")
        if game.cheats.freeze_ghosts:
            labels.append("FRZ")
        if game.cheats.speed_boost:
            labels.append("SPD")
        return labels

    def _draw_menu(self, game: Game) -> None:
        """Draw the title, the main menu entries and the best scores.

        Args:
            game: The game holding the cursor and the highscore table.
        """
        self._centered("PAC-MAN", self.cell * 2, _PLAYER, self.big)

        y = self.cell * 5
        for i, item in enumerate(MENU_ITEMS):
            selected = i == game.menu_index
            label = f"> {item} <" if selected else item
            color = _PLAYER if selected else _TEXT
            self._centered(label, y, color, self.small)
            y += int(self.cell * 1.4)

        self._centered("Up/Down + ENTER", y, _DIM, self.small)
        self._draw_menu_scores(game, y + int(self.cell * 2))

    def _draw_menu_scores(self, game: Game, top: int) -> None:
        """Draw a short highscore preview under the main menu.

        Args:
            game: The game holding the highscore table.
            top: Y coordinate to start drawing at.
        """
        self._centered("highscores:", top, _PLAYER, self.small)
        best = game.highscores.scores[:_MENU_SCORES]
        lines = ([f"{i + 1}. {s.name} - {s.points} pts"
                  for i, s in enumerate(best)]
                 if best else ["(no scores yet)"])
        self._draw_lines(lines, top + int(self.cell * 1.2))

    def _draw_difficulty(self, game: Game) -> None:
        """Draw the difficulty picker.

        Args:
            game: The game holding the difficulty cursor.
        """
        self._centered("DIFFICULTY", self.cell * 3, _PLAYER, self.big)

        y = self.cell * 7
        for i, (label, _mode) in enumerate(DIFFICULTIES):
            selected = i == game.difficulty_index
            text = f"> {label} <" if selected else label
            color = _PLAYER if selected else _TEXT
            self._centered(text, y, color, self.small)
            y += int(self.cell * 1.4)

        self._centered("Up/Down + ENTER    Esc: back",
                       y + self.cell, _DIM, self.small)

    def _draw_highscores(self, game: Game) -> None:
        """Draw the full top-ten table.

        Args:
            game: The game holding the highscore table.
        """
        self._centered("HIGHSCORES", self.cell * 2, _PLAYER, self.big)
        top = game.highscores.scores[:10]
        if top:
            lines = [f"{i + 1:>2}. {s.name:<10} {s.points:>7}"
                     for i, s in enumerate(top)]
        else:
            lines = ["(no scores yet)"]
        lines += ["", "any key to go back"]
        self._draw_lines(lines, self.cell * 5)

    def _draw_instructions(self) -> None:
        """Draw the rules, the controls and the cheat keys."""
        self._centered("INSTRUCTIONS", self.cell * 2, _PLAYER, self.big)
        lines = [
            "Eat all pacgums to clear a level.",
            "Super-pacgums make ghosts edible.",
            "Avoid ghosts - contact costs a life.",
            "",
            "Move: arrows / WASD    Pause: P / Esc",
            "",
            "Cheats (for review):",
            "F1 invincible   F2 freeze ghosts",
            "F3 player speed x2   F4 skip level",
            "F5 extra life",
            "",
            "any key to go back",
        ]
        self._draw_lines(lines, self.cell * 5)

    def _draw_pause(self, game: Game) -> None:
        """Draw the pause menu over a dimmed copy of the level.

        Args:
            game: The game holding the pause cursor.
        """
        self.canvas.darken(_PAUSE_KEEP_PERCENT)
        self._centered("PAUSED", self.height // 2 - self.cell * 3,
                       _TEXT, self.big)

        y = self.height // 2 - self.cell
        for i, item in enumerate(PAUSE_ITEMS):
            selected = i == game.pause_index
            label = f"> {item} <" if selected else item
            color = _PLAYER if selected else _TEXT
            self._centered(label, y, color, self.small)
            y += int(self.cell * 1.4)

        self._centered("Up/Down + ENTER    P / Esc: resume",
                       y + self.cell, _DIM, self.small)

    def _draw_end(self, game: Game, heading: str) -> None:
        """Draw the game-over or victory screen with the name prompt.

        Args:
            game: The game holding the score and the typed name.
            heading: Title to show above the score.
        """
        self._centered(heading, self.cell * 3, _PLAYER, self.big)
        lines = [
            f"Final score: {game.score}",
            "",
            f"Enter your name: {game.pending_name}_",
            "(letters/spaces, max 10, then ENTER)",
        ]
        self._draw_lines(lines, self.cell * 5)

    def _draw_lines(self, lines: list[str], top: int) -> None:
        """Draw centred lines of text stacked downwards from ``top``.

        Args:
            lines: The lines to render, in order.
            top: Y coordinate of the first line.
        """
        y = top
        for line in lines:
            self._centered(line, y, _TEXT, self.small)
            y += int(self.cell * 1.1)
