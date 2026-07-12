# Retrospective: blocking points & decisions

## Key technical decisions

- **Adapter isolation.** All knowledge of the assigned `mazegenerator` lives
  in `maze_loader.py`, exposing our own `Maze` model. Swapping generators (or
  surviving a re-install at review) touches one file.
- **UI/logic split.** `game.py`/`level.py`/`entities/` contain no pygame, so
  the rules are unit-testable headlessly and the renderer stays thin.
- **Fixed-step simulation.** The window redraws at `fps`, but the sim advances
  in one-cell steps at `player_speed`, decoupling speed from frame rate.

## Blocking points and how we resolved them

| Blocker | Resolution |
|---------|-----------|
| `pygame` `font` module crashed on Python 3.14 (circular import) | Switched to `pygame-ce`, which ships working 3.14 wheels |
| Player spawned inside the generator's walled-off "42" logo | BFS outward from the geometric centre to the nearest open corridor |
| Ghosts passed through the player on head-on collisions | Track pre-move positions and treat a cell swap as a hit |
| Packaged app can't pass a config arg / can't write to its bundle | Dedicated launcher: bundled config + highscores in `~/.pacman/` |

## What we'd do next (out of scope)

- Smooth pixel interpolation between cells (currently steps).
- Distinct ghost personalities (Blinky/Pinky/Inky/Clyde).
- Sound effects and mouth animation.
