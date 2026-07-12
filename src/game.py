"""State machine, scoring and rules -- no rendering, so testable headless."""

from __future__ import annotations

from enum import Enum, auto

from src.cheats import CheatState
from src.config import Config
from src.entities import GhostMode
from src.highscores import HighScoreStore
from src.level import Level
from src.maze_loader import MazeError


class GameState(Enum):
    """Top-level screens / phases of the application."""

    MENU = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()


# Main-menu items, in display order.
MENU_ITEMS = ("Start Game", "View Highscores", "Instructions", "Exit")


class Game:
    """Cross-level state; ``tick(dt)`` advances timers, ghosts and rules."""

    def __init__(self, config: Config, highscores: HighScoreStore):
        """Create a game bound to ``config`` and a highscore store."""
        self.config = config
        self.highscores = highscores
        self.cheats = CheatState()
        self.state = GameState.MENU

        self.score = 0
        self.lives = config.lives
        self.level_index = 0
        self.level: Level | None = None
        self._frightened_timer: float = 0.0
        # Buffer for the name typed on the game-over / victory screen.
        self.pending_name = ""
        # Highlighted item on the main menu.
        self.menu_index = 0

    # -- lifecycle -------------------------------------------------------

    def start_new_game(self) -> None:
        """Reset all progress and load the first level."""
        self.score = 0
        self.lives = self.config.lives
        self.level_index = 0
        self.cheats = CheatState()
        self.pending_name = ""
        self._load_current_level()
        self.state = GameState.PLAYING

    def _level_seed(self) -> int:
        """Level 0 -> fixed config seed; later levels -> random (0)."""
        return self.config.seed if self.level_index == 0 else 0

    def _load_current_level(self) -> None:
        """Instantiate the level for :attr:`level_index`, or end the game."""
        spec = self.config.levels[self.level_index]
        try:
            self.level = Level(self.config, spec, self._level_seed())
        except MazeError as exc:
            print(f"[game] level generation failed: {exc}")
            self.state = GameState.GAME_OVER
            return
        self._frightened_timer = 0.0

    # -- per-tick simulation --------------------------------------------

    def tick(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds when playing."""
        if self.state is not GameState.PLAYING or self.level is None:
            return

        self._update_timers(dt)
        # Remember pre-move positions so a player<->ghost cell swap counts
        # as a hit (they would otherwise pass through each other).
        player_prev = self.level.player.position
        ghost_prev = [g.position for g in self.level.ghosts]
        self.level.player.update(self.level.maze)
        self._update_ghosts(dt)
        self._handle_pellets()
        self._handle_collisions(player_prev, ghost_prev)
        self._check_level_end()

    def _update_timers(self, dt: float) -> None:
        """Advance the level clock and the frightened window."""
        assert self.level is not None
        self.level.time_left -= dt
        if self.level.time_left <= 0:
            # Time out: lose a life and respawn (design choice per subject).
            self._lose_life()
        if self._frightened_timer > 0:
            self._frightened_timer -= dt
            if self._frightened_timer <= 0:
                for ghost in self.level.ghosts:
                    ghost.set_frightened(False)

    def _update_ghosts(self, dt: float) -> None:
        """Move each ghost unless frozen by a cheat."""
        assert self.level is not None
        if self.cheats.freeze_ghosts:
            return
        target = self.level.player.position
        for ghost in self.level.ghosts:
            ghost.update(self.level.maze, target, dt)

    def _handle_pellets(self) -> None:
        """Eat any pellet under the player and award points."""
        assert self.level is not None
        cell = self.level.player.position
        if cell in self.level.pacgums:
            self.level.pacgums.discard(cell)
            self.score += self.config.points_per_pacgum
        elif cell in self.level.super_pacgums:
            self.level.super_pacgums.discard(cell)
            self.score += self.config.points_per_super_pacgum
            self._trigger_frightened()

    def _trigger_frightened(self) -> None:
        """Start the frightened window and flag ghosts as edible."""
        assert self.level is not None
        self._frightened_timer = float(self.config.frightened_duration)
        for ghost in self.level.ghosts:
            ghost.set_frightened(True)

    def _handle_collisions(self, player_prev: tuple[int, int],
                           ghost_prev: list[tuple[int, int]]) -> None:
        """Resolve player/ghost overlaps (same cell or a swap): eat or die."""
        assert self.level is not None
        player_cell = self.level.player.position
        for ghost, prev in zip(self.level.ghosts, ghost_prev):
            same_cell = ghost.position == player_cell
            swapped = ghost.position == player_prev and prev == player_cell
            if not (same_cell or swapped):
                continue
            if ghost.mode is GhostMode.FRIGHTENED:
                ghost.get_eaten(self.config.ghost_respawn_delay)
                self.score += self.config.points_per_ghost
            elif ghost.mode is GhostMode.CHASE:
                if not self.cheats.invincible:
                    self._lose_life()
                    return

    def _lose_life(self) -> None:
        """Deduct a life and respawn, or end the game at zero."""
        assert self.level is not None
        self.lives -= 1
        if self.lives <= 0:
            self.state = GameState.GAME_OVER
            return
        self.level.player.reset_to_spawn()
        for ghost in self.level.ghosts:
            ghost.reset_to_spawn()
            ghost.mode = GhostMode.CHASE
        self._frightened_timer = 0.0
        self.level.time_left = float(self.config.level_max_time)

    def _check_level_end(self) -> None:
        """Advance to the next level on clear (or via cheat), or win."""
        assert self.level is not None
        if not (self.level.cleared or self.cheats.consume_level_skip()):
            return
        self.level_index += 1
        if self.level_index >= len(self.config.levels):
            self.state = GameState.VICTORY
            return
        self._load_current_level()

    # -- menu navigation -------------------------------------------------

    def menu_move(self, delta: int) -> None:
        """Move the main-menu highlight up/down, wrapping around."""
        self.menu_index = (self.menu_index + delta) % len(MENU_ITEMS)

    def menu_select(self) -> str:
        """Act on the highlighted menu item; return its label."""
        item = MENU_ITEMS[self.menu_index]
        if item == "Start Game":
            self.start_new_game()
        elif item == "View Highscores":
            self.state = GameState.HIGHSCORES
        elif item == "Instructions":
            self.state = GameState.INSTRUCTIONS
        return item

    # -- transitions -----------------------------------------------------

    def toggle_pause(self) -> None:
        """Switch between PLAYING and PAUSED."""
        if self.state is GameState.PLAYING:
            self.state = GameState.PAUSED
        elif self.state is GameState.PAUSED:
            self.state = GameState.PLAYING

    def name_append(self, char: str) -> None:
        """Append a character to the pending name (alnum/space, max 10)."""
        if len(self.pending_name) >= 10:
            return
        if char.isalnum() or char == " ":
            self.pending_name += char

    def name_backspace(self) -> None:
        """Delete the last character of the pending name."""
        self.pending_name = self.pending_name[:-1]

    def submit_score(self, name: str | None = None) -> None:
        """Record the final score (``name`` or the buffer) and persist."""
        self.highscores.add(name if name is not None else self.pending_name,
                            self.score)
        self.highscores.save()

    def return_to_menu(self) -> None:
        """Go back to the main menu and clear the name buffer."""
        self.pending_name = ""
        self.state = GameState.MENU
