# Progress Tracking (plan vs actual)

Updated as work lands. Keep the "Notes" column honest — it is what the
defense looks at.

| Area | Planned | Actual | Notes |
|------|---------|--------|-------|
| Config loader | Week 1 | ✅ | JSON + `#` comments, clamp-to-default, unknown keys ignored |
| Maze adapter | Week 1 | ✅ | All coupling to the assigned package isolated in `maze_loader.py` |
| Rendering | Week 1 | ✅ | pygame; terminal wall-logic ported to `draw.line` |
| Player | Week 2 | ✅ | Buffered-turn movement |
| Ghosts | Week 2 | ✅ | BFS chase / flee, frightened + eaten modes, respawn |
| Pellets/scoring | Week 2 | ✅ | pacgums, super-pacgums in corners |
| Progression | Week 2 | ✅ | 10 levels, per-level timer, lives |
| Menus/HUD | Week 3 | ✅ | Main/pause/highscores/instructions, HUD, name entry |
| Cheats | Week 3 | ✅ | F1 invincible, F2 freeze, F3 speed, F4 skip |
| Highscores | Week 3 | ✅ | Top-10 JSON, tolerant to bad files |
| Packaging | Week 4 | ⏳ | `pacman.spec` + launcher ready; build/upload pending |
| Tests | ongoing | ✅ | 18 pytest cases (config, maze, highscores, game rules) |
| Lint/types | ongoing | ✅ | flake8 clean, mypy clean |

## Deviations from plan

- Switched `pygame` → `pygame-ce`: the classic package's `font` module is
  broken on Python 3.14. No schedule impact.
- Added swap-collision handling late (found during review) — see
  [test-plan.md](test-plan.md).
