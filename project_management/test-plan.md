# Acceptance Test Plan

Two layers: automated unit tests (`make test`) and manual acceptance checks
run before the defense.

## Automated tests (`tests/`, 72 cases)

| Suite | Covers |
|-------|--------|
| `test_config.py` | comment stripping (`#`, `//`, blocks, markers inside strings), defaults, clamping, bad types, unknown keys, `ghost_speed` validation |
| `test_maze_loader.py` | reproducible seed, dimensions, walkable centre, wall respect, neighbour symmetry |
| `test_highscores.py` | name sanitising, top-10 cap, persistence, missing file, corrupt file, malformed rows |
| `test_canvas.py` | span clipping and inclusivity, out-of-bounds writes, rects, Bresenham endpoints, disc symmetry, polygon fill, degenerate shapes, dimming, buffer copy, font metrics and glyph fallback |
| `test_entities.py` | buffered turns, blocked turns, dead ends, respawn, BFS chase step, unreachable target, flee step, target resolution, no-U-turn wandering, eaten-ghost rules |
| `test_game.py` | same-cell hit, **swap hit**, invincibility, eating a frightened ghost, pellet scoring, step rates, **speed cheat isolation**, real-time ghost timers, extra life, level skip, time-out, pause menu |

Run: `make test` → all green; `make lint` → flake8 + mypy clean.

## Manual acceptance checklist

| # | Feature | Steps | Expected | Result |
|---|---------|-------|----------|--------|
| 1 | Launch | `make run` | Main menu appears | ☐ |
| 2 | Menu nav | Up/Down + Enter | Highlight moves; items open | ☐ |
| 2b | Difficulty screen | Menu → Start Game | Easy/Normal/Hard; Enter starts, Esc back | ☐ |
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
| 14 | Pause | `P` / `Esc` | Pause menu over dimmed level; resume works | ☐ |
| 15 | Pause → menu | Select *Return to main menu* | Returns to main menu | ☐ |
| 16 | Cheats | F1/F2/F3/F4/F5 | Invincible / freeze / player speed / skip / +1 life | ☐ |
| 16b | Cheat HUD | Toggle F1-F3 | Active cheats listed top-right | ☐ |
| 17 | Highscore save | Finish a game, enter name | Score persists after restart | ☐ |
| 17b | Menu highscores | Return to main menu | Top-5 shown under the menu | ☐ |
| 18 | Bad config | Corrupt a value in config.json | Warning printed, defaults used, no crash | ☐ |
| 19 | Missing file | `python3 pac-man.py nope.json` | Clean error, no traceback | ☐ |
| 20 | Ghost pacing | Run away down a long corridor | The gap widens; a ghost behind you can be shaken off | ☐ |

## Bugs found & fixed

- **Player/ghost pass-through:** discrete cell steps let the two swap cells
  without landing together, so a head-on hit was missed. Fixed by comparing
  pre-move positions (swap detection); covered by `test_swap_is_detected...`.
- **`font` module crash on Python 3.14:** switched to `pygame-ce`.
- **`ghost_speed` was dead config:** the key was parsed, clamped and
  documented, but the loop stepped every actor once per tick, so ghosts always
  matched the player exactly. With optimal BFS chasing this made a ghost on
  your tail impossible to escape — measured in a straight corridor, the gap
  stayed pinned at 1 cell indefinitely. Fixed by giving the player and the
  ghosts separate step accumulators in `Game.tick()`; with the shipped 5-vs-4
  the same test now opens a 7-cell gap in six seconds. Covered by
  `test_step_durations_follow_the_configured_speeds`.
- **Speed cheat (F3) did nothing useful:** it doubled the tick rate, which
  moved the ghosts faster too, so the player gained no advantage. Fixed by the
  same split; covered by `test_speed_cheat_only_affects_the_player`.
- **Level skip (F4) lagged by up to one player step**, because the request was
  only consumed inside a movement step. Now consumed at the top of
  `Game.tick()`, so it fires on the next frame.

- **Dropped turns when rounding a corner:** the player held a *single*
  turn slot, so every key press overwrote the previous one. At 5 steps/s
  there are 12 frames between steps, and a player who presses "up, then
  right" to round a corner had the "up" silently discarded. Replaced with
  a two-entry queue applied on consecutive steps
  (`test_two_quick_presses_are_both_honoured`).
- **Phantom turns:** the same slot never expired, so a direction pressed
  into a wall could fire seconds later at an unrelated junction. Queued
  turns now expire after three steps and are cleared on respawn
  (`test_stale_turn_is_forgotten`, `test_respawn_clears_queued_turns`).
- **Stale turn blocking a newer one:** with a queue, an illegal request at
  the head would hold up the direction the player actually wants. The
  first *legal* request wins and everything older is dropped
  (`test_newer_turn_wins_over_a_blocked_one`).

## Change: subject v1.5 (graphics library constraint)

Subject 1.5 added one requirement to chapter IV: a library counts as *similar
to MLX* only if every function used has an MLX equivalent. Our renderer relied
on `pygame.draw.circle/line/polygon/rect` (15 call sites), `pygame.font` and an
alpha surface for the pause veil — none of which MLX provides.

Reworked the graphics layer to draw every pixel ourselves (`ui/canvas.py`,
`ui/font.py`) and hand the finished buffer to the window as a single image,
which is precisely the MLX image workflow. Game logic was untouched: all
existing tests still pass unchanged, and 20 new cases cover the primitives.

Audited afterwards: the only pygame calls left are window creation, image
blit, display flip, event polling, key constants and the frame clock.

Risk checked: pure-Python pixel work could have been too slow. Mitigated with
span-based fills and a per-level cached maze layer; measured 1.6 ms/frame on
the largest level (see README → Graphics layer).
