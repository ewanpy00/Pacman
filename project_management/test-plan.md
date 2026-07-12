# Acceptance Test Plan

Two layers: automated unit tests (`make test`) and manual acceptance checks
run before the defense.

## Automated tests (`tests/`, 18 cases)

| Suite | Covers |
|-------|--------|
| `test_config.py` | comment stripping, defaults, clamping, bad types, unknown keys |
| `test_maze_loader.py` | reproducible seed, dimensions, walkable centre, wall respect |
| `test_highscores.py` | name sanitising, top-10 cap, persistence, missing file |
| `test_game.py` | same-cell hit, **swap hit**, eating a frightened ghost, pacgum scoring, level advance |

Run: `make test` → all green; `make lint` → flake8 + mypy clean.

## Manual acceptance checklist

| # | Feature | Steps | Expected | Result |
|---|---------|-------|----------|--------|
| 1 | Launch | `make run` | Main menu appears | ☐ |
| 2 | Menu nav | Up/Down + Enter | Highlight moves; items open | ☐ |
| 3 | Highscores screen | Menu → View Highscores | Top-10 shown; any key returns | ☐ |
| 4 | Instructions screen | Menu → Instructions | Controls/rules shown | ☐ |
| 5 | Movement | Arrows / WASD | Pac-Man moves in corridors only | ☐ |
| 6 | Pacgum | Eat a dot | Score += points_per_pacgum | ☐ |
| 7 | Super-pacgum | Eat a corner pellet | Ghosts turn frightened | ☐ |
| 8 | Eat ghost | Touch a frightened ghost | Score += points_per_ghost; ghost respawns | ☐ |
| 9 | Death | Touch a chasing ghost | Lose a life; respawn in centre | ☐ |
| 10 | Swap | Head-on into a ghost | Life lost (no pass-through) | ☐ |
| 11 | Timer | Wait out `level_max_time` | Life lost / level restarts | ☐ |
| 12 | Level clear | Eat all pellets | Next level loads, score kept | ☐ |
| 13 | Win | Clear all 10 levels (use F4) | Victory screen + name entry | ☐ |
| 14 | Pause | `P` / `Esc` | Pause overlay; resume works | ☐ |
| 15 | Pause → menu | `M` while paused | Returns to main menu | ☐ |
| 16 | Cheats | F1/F2/F3/F4 | Invincible / freeze / speed / skip | ☐ |
| 17 | Highscore save | Finish a game, enter name | Score persists after restart | ☐ |
| 18 | Bad config | Corrupt a value in config.json | Warning printed, defaults used, no crash | ☐ |
| 19 | Missing file | `python3 pac-man.py nope.json` | Clean error, no traceback | ☐ |

## Bugs found & fixed

- **Player/ghost pass-through:** discrete cell steps let the two swap cells
  without landing together, so a head-on hit was missed. Fixed by comparing
  pre-move positions (swap detection); covered by `test_swap_is_detected...`.
- **`font` module crash on Python 3.14:** switched to `pygame-ce`.
