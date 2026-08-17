"""Game state machine: rules, scoring, timers and screen transitions.

The simulation is deliberately UI-free so it can be driven by pygame, by
the headless demo, or straight from the tests.

Movement is discrete but the player and the ghosts advance on separate
schedules, driven by ``player_speed`` and ``ghost_speed``: each keeps its
own accumulator of elapsed real time and takes a one-cell step whenever
that accumulator reaches its step duration.
"""

from __future__ import annotations

from enum import Enum, auto

from src.cheats import CheatState
from src.config import Config
from src.entities import GhostMode
from src.highscores import HighScoreStore
from src.level import Level
from src.maze_loader import MazeError


class GameState(Enum):
    """Which screen the game is currently on."""

    MENU = auto()
    DIFFICULTY = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()


MENU_ITEMS = ("Start Game", "View Highscores", "Instructions", "Exit")

PAUSE_ITEMS = ("Resume", "Return to main menu")

DIFFICULTIES = (
    ("Easy  -  ghosts wander", "random"),
    ("Normal  -  classic ghosts", "classic"),
    ("Hard  -  all ghosts chase", "chase"),
)

_MAX_FRAME_DT = 0.25


class Game:
    """Owns the score, the lives, the current level and the screen state."""

    def __init__(self, config: Config, highscores: HighScoreStore):
        """Start on the main menu with the configured defaults.

        Args:
            config: Validated game settings.
            highscores: The persistent top-ten table.
        """
        self.config = config
        self.highscores = highscores
        self.cheats = CheatState()
        self.state = GameState.MENU

        self.score = 0
        self.lives = config.lives
        self.level_index = 0
        self.level: Level | None = None
        self._frightened_timer: float = 0.0
        self._player_accum: float = 0.0
        self._ghost_accum: float = 0.0
        self.pending_name = ""
        self.menu_index = 0
        self.pause_index = 0
        self.ghost_mode = config.ghost_mode
        self.difficulty_index = 0

    def start_new_game(self) -> None:
        """Reset score, lives and cheats, then load the first level."""
        self.score = 0
        self.lives = self.config.lives
        self.level_index = 0
        self.cheats = CheatState()
        self.pending_name = ""
        self._load_current_level()
        self.state = GameState.PLAYING

    @property
    def player_step(self) -> float:
        """Seconds between two player steps, halved by the speed cheat."""
        speed = self.config.player_speed
        if self.cheats.speed_boost:
            speed *= 2
        return 1.0 / max(1, speed)

    @property
    def ghost_step(self) -> float:
        """Seconds between two ghost steps."""
        return 1.0 / max(1, self.config.ghost_speed)

    @property
    def player_alpha(self) -> float:
        """How far the player is between its previous and current cell."""
        return min(1.0, self._player_accum / self.player_step)

    @property
    def ghost_alpha(self) -> float:
        """How far the ghosts are between their previous and current cell."""
        return min(1.0, self._ghost_accum / self.ghost_step)

    def _level_seed(self) -> int:
        """Return the seed for the current level.

        Level one uses the configured seed so it is reproducible; every
        later level passes ``0``, which the generator reads as "random".
        """
        return self.config.seed if self.level_index == 0 else 0

    def _load_current_level(self) -> None:
        """Build the level at ``level_index``, ending the game on failure."""
        spec = self.config.levels[self.level_index]
        try:
            self.level = Level(self.config, spec, self._level_seed())
        except MazeError as exc:
            print(f"[game] level generation failed: {exc}")
            self.state = GameState.GAME_OVER
            return
        self._frightened_timer = 0.0
        self._reset_accumulators()

    def _reset_accumulators(self) -> None:
        """Drop any buffered movement time, e.g. after a respawn."""
        self._player_accum = 0.0
        self._ghost_accum = 0.0

    def tick(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds of real time.

        Long frames are clamped so that a stalled window cannot make the
        game fast-forward through several seconds at once.

        Args:
            dt: Seconds elapsed since the previous call.
        """
        if self.state is not GameState.PLAYING or self.level is None:
            return

        dt = min(max(0.0, dt), _MAX_FRAME_DT)
        if self.cheats.consume_extra_life():
            self.lives += 1
        if self.cheats.consume_level_skip():
            self._advance_level()
            if self.state is not GameState.PLAYING or self.level is None:
                return

        self._update_timers(dt)
        if self.state is not GameState.PLAYING or self.level is None:
            return

        self._player_accum += dt
        self._ghost_accum += dt
        while self.state is GameState.PLAYING:
            player_due = self._player_accum >= self.player_step
            ghost_due = self._ghost_accum >= self.ghost_step
            if not player_due and not ghost_due:
                break
            if player_due:
                self._player_accum -= self.player_step
            if ghost_due:
                self._ghost_accum -= self.ghost_step
            self._step(player_due, ghost_due)

    def _step(self, move_player: bool, move_ghosts: bool) -> None:
        """Run one simulation step for whichever actors are due.

        Positions are captured before anything moves so that a player and
        a ghost swapping cells still registers as a collision.

        Args:
            move_player: Whether the player takes a step now.
            move_ghosts: Whether the ghosts take a step now.
        """
        assert self.level is not None
        player_prev = self.level.player.position
        ghost_prev = [g.position for g in self.level.ghosts]

        if move_player:
            self.level.player.mark_prev()
            self.level.player.update(self.level.maze)
        if move_ghosts:
            self._update_ghosts()

        self._handle_pellets()
        self._handle_collisions(player_prev, ghost_prev)
        if self.state is not GameState.PLAYING:
            return
        self._check_level_end()

    def _update_timers(self, dt: float) -> None:
        """Count down the level clock and the frightened window.

        Args:
            dt: Seconds elapsed since the previous call.
        """
        assert self.level is not None
        self.level.time_left -= dt
        if self.level.time_left <= 0:
            self._lose_life()
            return
        if self._frightened_timer > 0:
            self._frightened_timer -= dt
            if self._frightened_timer <= 0:
                for ghost in self.level.ghosts:
                    ghost.set_frightened(False)

    def _update_ghosts(self) -> None:
        """Advance every ghost by one cell, unless frozen by a cheat."""
        assert self.level is not None
        if self.cheats.freeze_ghosts:
            return
        for ghost in self.level.ghosts:
            ghost.mark_prev()
        player_pos = self.level.player.position
        player_dir = self.level.player.direction
        blinky_pos = self.level.ghosts[0].position
        for ghost in self.level.ghosts:
            ghost.update(self.level.maze, player_pos, player_dir,
                         blinky_pos, self.ghost_mode, self.ghost_step)

    def _handle_pellets(self) -> None:
        """Eat whatever pellet sits on the player's cell."""
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
        """Make every ghost edible for the configured duration."""
        assert self.level is not None
        self._frightened_timer = float(self.config.frightened_duration)
        for ghost in self.level.ghosts:
            ghost.set_frightened(True)

    def _handle_collisions(self, player_prev: tuple[int, int],
                           ghost_prev: list[tuple[int, int]]) -> None:
        """Resolve player-versus-ghost contact for this step.

        Two cases count as contact: sharing a cell, and swapping cells,
        which happens when the two walk through each other head-on in the
        same step.

        Args:
            player_prev: The player's cell before this step.
            ghost_prev: Each ghost's cell before this step.
        """
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
        """Drop a life and restart the level, or end the game at zero."""
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
        self._reset_accumulators()

    def _check_level_end(self) -> None:
        """Move on once every pellet of the current level is eaten."""
        assert self.level is not None
        if self.level.cleared:
            self._advance_level()

    def _advance_level(self) -> None:
        """Load the next level, or win the game if that was the last."""
        self.level_index += 1
        if self.level_index >= len(self.config.levels):
            self.state = GameState.VICTORY
            return
        self._load_current_level()

    def menu_move(self, delta: int) -> None:
        """Move the main-menu cursor by ``delta``, wrapping around."""
        self.menu_index = (self.menu_index + delta) % len(MENU_ITEMS)

    def menu_select(self) -> str:
        """Activate the highlighted main-menu entry.

        Returns:
            The label of the chosen entry, so the caller can react to
            ``Exit`` by closing the window.
        """
        item = MENU_ITEMS[self.menu_index]
        if item == "Start Game":
            self._open_difficulty()
        elif item == "View Highscores":
            self.state = GameState.HIGHSCORES
        elif item == "Instructions":
            self.state = GameState.INSTRUCTIONS
        return item

    def _open_difficulty(self) -> None:
        """Show the difficulty screen, preselecting the current mode."""
        modes = [mode for _, mode in DIFFICULTIES]
        self.difficulty_index = (modes.index(self.ghost_mode)
                                 if self.ghost_mode in modes else 1)
        self.state = GameState.DIFFICULTY

    def difficulty_move(self, delta: int) -> None:
        """Move the difficulty cursor by ``delta``, wrapping around."""
        self.difficulty_index = (
            (self.difficulty_index + delta) % len(DIFFICULTIES))

    def difficulty_select(self) -> None:
        """Apply the highlighted difficulty and start playing."""
        self.ghost_mode = DIFFICULTIES[self.difficulty_index][1]
        self.start_new_game()

    def toggle_pause(self) -> None:
        """Switch between playing and the pause menu."""
        if self.state is GameState.PLAYING:
            self.pause_index = 0
            self.state = GameState.PAUSED
        elif self.state is GameState.PAUSED:
            self._reset_accumulators()
            self.state = GameState.PLAYING

    def pause_move(self, delta: int) -> None:
        """Move the pause-menu cursor by ``delta``, wrapping around."""
        self.pause_index = (self.pause_index + delta) % len(PAUSE_ITEMS)

    def pause_select(self) -> str:
        """Activate the highlighted pause-menu entry.

        Returns:
            The label of the chosen entry.
        """
        item = PAUSE_ITEMS[self.pause_index]
        if item == "Resume":
            self._reset_accumulators()
            self.state = GameState.PLAYING
        else:
            self.return_to_menu()
        return item

    def name_append(self, char: str) -> None:
        """Append ``char`` to the pending highscore name if allowed."""
        if len(self.pending_name) >= 10:
            return
        if char.isalnum() or char == " ":
            self.pending_name += char

    def name_backspace(self) -> None:
        """Delete the last character of the pending highscore name."""
        self.pending_name = self.pending_name[:-1]

    def submit_score(self, name: str | None = None) -> None:
        """Store the final score under ``name`` and persist the table.

        Args:
            name: Name to record; the name typed on the end screen is
                used when omitted.
        """
        self.highscores.add(name if name is not None else self.pending_name,
                            self.score)
        self.highscores.save()

    def return_to_menu(self) -> None:
        """Clear the pending name and go back to the main menu."""
        self.pending_name = ""
        self.state = GameState.MENU
