"""Cheat toggles used to make peer review of the game easy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheatState:
    """Toggles and one-shot requests driven by the F1-F5 keys.

    Attributes:
        invincible: When true, chasing ghosts cannot cost a life.
        freeze_ghosts: When true, ghosts stop moving entirely.
        speed_boost: When true, the player (and only the player) moves
            at double speed.
        request_level_skip: One-shot flag: clear the current level.
        request_extra_life: One-shot flag: grant one extra life.
    """

    invincible: bool = False
    freeze_ghosts: bool = False
    speed_boost: bool = False
    request_level_skip: bool = False
    request_extra_life: bool = False

    def toggle_invincible(self) -> None:
        """Turn player invincibility on or off."""
        self.invincible = not self.invincible

    def toggle_freeze(self) -> None:
        """Turn the ghost freeze on or off."""
        self.freeze_ghosts = not self.freeze_ghosts

    def toggle_speed(self) -> None:
        """Turn the player speed boost on or off."""
        self.speed_boost = not self.speed_boost

    def skip_level(self) -> None:
        """Request that the current level be cleared on the next tick."""
        self.request_level_skip = True

    def consume_level_skip(self) -> bool:
        """Return whether a skip was requested, clearing the request."""
        pending = self.request_level_skip
        self.request_level_skip = False
        return pending

    def grant_extra_life(self) -> None:
        """Request one extra life on the next tick."""
        self.request_extra_life = True

    def consume_extra_life(self) -> bool:
        """Return whether a life was requested, clearing the request."""
        pending = self.request_extra_life
        self.request_extra_life = False
        return pending
