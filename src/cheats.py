"""Cheat toggles for peer review; the game loop reads them (keys in README)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheatState:
    """Toggleable cheats consulted by the game each tick."""

    invincible: bool = False       # ghosts cannot take a life
    freeze_ghosts: bool = False    # ghosts stop moving
    speed_boost: bool = False      # player moves faster
    request_level_skip: bool = False  # consumed to win the level instantly

    def toggle_invincible(self) -> None:
        """Flip invincibility."""
        self.invincible = not self.invincible

    def toggle_freeze(self) -> None:
        """Flip ghost freeze."""
        self.freeze_ghosts = not self.freeze_ghosts

    def toggle_speed(self) -> None:
        """Flip the player speed boost."""
        self.speed_boost = not self.speed_boost

    def skip_level(self) -> None:
        """Request an instant win of the current level."""
        self.request_level_skip = True

    def consume_level_skip(self) -> bool:
        """Return and clear a pending level-skip request."""
        pending = self.request_level_skip
        self.request_level_skip = False
        return pending
