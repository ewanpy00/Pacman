"""Maze actors: the shared base entity, the player and the ghosts."""

from .entity import Entity
from .player import Player
from .ghost import Ghost, GhostMode

__all__ = ["Entity", "Player", "Ghost", "GhostMode"]
