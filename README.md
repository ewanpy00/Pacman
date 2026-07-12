*This project has been created as part of the 42 curriculum by ipykhtin.*

# Pac-Man

> Waka-waka! A modern, modular reimplementation of the 1980 arcade classic in
> Python, with a data-driven configuration, procedurally generated mazes and a
> persistent highscore table.

## Description

The goal is to recreate the famous Pac-Man arcade game with a clean,
object-oriented, testable architecture. The player navigates procedurally
generated mazes eating pacgums while four ghosts give chase; power pellets
(super-pacgums) briefly turn the ghosts edible. The game runs across at least
ten levels of increasing size, each with a time limit, tracks a top-10
highscore table, and ships with a cheat mode to make peer review painless.

## Instructions

Requires **Python 3.10+**.

```bash
make install      # create .venv, install deps + the assigned maze generator
make run          # launch the game: python3 pac-man.py config.json
make debug        # run under pdb
make lint         # flake8 . && mypy . (project flags)
make lint-strict  # flake8 . && mypy . --strict
make test         # run the pytest suite
make package      # build a standalone executable (see PACKAGING.md)
make clean        # remove caches and build artifacts
```

You can also run it directly:

```bash
python3 pac-man.py config.json
```

The program takes **exactly one argument**: a `.json` configuration file. Any
error (missing file, bad JSON, invalid value) prints a clear message and exits
cleanly — never a traceback. (If pygame is unavailable, launching falls back
to a headless text demo instead of crashing.)

For building and publishing the standalone game, see [PACKAGING.md](PACKAGING.md).

### Controls

| Action              | Keys                     |
|---------------------|--------------------------|
| Navigate menus      | Up / Down + `Enter`      |
| Move                | Arrow keys / WASD        |
| Pause / resume      | `P` or `Esc`             |
| Return to menu (paused) | `M`                  |
| Cheat: invincible   | `F1`                     |
| Cheat: freeze ghosts| `F2`                     |
| Cheat: speed boost  | `F3`                     |
| Cheat: skip level   | `F4`                     |

## Configuration

The config file is standard JSON extended with `#` line comments (a line whose
first non-whitespace character is `#` is ignored). Unknown keys are ignored;
any missing or out-of-range value is **clamped to a safe default** and logged,
so the game never crashes on a bad config.

| Key | Default | Meaning |
|-----|---------|---------|
| `highscore_filename` | `highscores.json` | Where scores are stored |
| `cell_size` | 24 | Pixel size of a maze cell |
| `fps` | 60 | Target frame rate |
| `lives` | 3 | Starting lives |
| `player_speed` / `ghost_speed` | 5 / 4 | Cells per second |
| `points_per_pacgum` | 10 | Score for a pacgum |
| `points_per_super_pacgum` | 50 | Score for a super-pacgum |
| `points_per_ghost` | 200 | Score for eating an edible ghost |
| `frightened_duration` | 8 | Seconds ghosts stay edible |
| `ghost_respawn_delay` | 6 | Seconds before an eaten ghost returns |
| `seed` | 42 | Fixed seed for level 1 (others are random) |
| `level_max_time` | 90 | Per-level time limit (seconds) |
| `levels` | 10 entries | Array of `{width, height, pacgum}` |

See [config.json](config.json) for a fully commented example.

## Highscore

Scores live in a JSON file (default `highscores.json`) as a list of
`{"name", "points"}` objects. The store keeps the **top 10**, sorts on every
insert, sanitises names (alphanumeric + spaces, max 10 chars) and rejects
negative scores. It is loaded at game start and saved at game end. **Why JSON
on disk:** it is human-readable, trivially portable with the packaged game,
needs no external database, and is easy to validate defensively against a
corrupted or missing file (which yields an empty table rather than a crash).

## Maze Generation

We **do not** write our own generator: the game consumes the assigned
`mazegenerator` package (installed from the local wheel by `make install`) *as
is*. All knowledge of its interface is isolated in
[src/maze_loader.py](src/maze_loader.py), so the rest of the game depends only
on our own `Maze` model.

The generator returns a 2-D grid where each cell is an int whose low 4 bits
encode walls (**N=1, E=2, S=4, W=8**; a set bit blocks movement). We call it
with `perfect=False` for Pac-Man-compatible corridors (loops), pass the
configured seed for level 1 and a random seed thereafter, then adapt its
`(x, y)` / `grid[y][x]` coordinate convention behind a small, well-typed API
(`can_move`, `neighbors`, `corners`, `center_corridor`, ...). Because the
generator embeds a "42" logo of walls in the centre, the player spawn is found
by a BFS outward from the geometric centre to the nearest open corridor. Any
generator failure is caught and surfaced as a clean `MazeError`.

## Implementation

- **Language/tooling:** Python 3.10+, `flake8` + `mypy` clean, full type hints
  and PEP 257 docstrings.
- **Rendering:** pygame-ce, plus a dependency-free ASCII renderer used for
  smoke tests and the headless fallback.
- **Separation of concerns:** all game *rules* live in pure, UI-free modules
  (`game`, `level`, `entities`, ...) so they are unit-testable headlessly; the
  UI only maps input and draws state.

## General Software Architecture

```
pac-man.py            Entry point: arg parsing, clean error handling
config.json           Commented JSON configuration
src/
  config.py           Load / decomment / validate config -> Config
  maze_loader.py      Adapter over the assigned MazeGenerator -> Maze
  highscores.py       Persistent top-10 store
  cheats.py           Toggleable cheat state
  level.py            One level: maze + pellets + actors + timer
  game.py             State machine, scoring, collision & progression rules
  entities/
    entity.py         Grid actor base class
    player.py         Pac-Man (buffered-turn movement)
    ghost.py          Ghost AI (BFS chase / flee, modes, respawn)
  ui/
    app.py            pygame front end: window, input, main loop
    render.py         pygame renderer: maze, pellets, actors, HUD, screens
    ascii_view.py     Text renderer for tests/headless
    headless.py       No-display demo / smoke test
scripts/
    launcher.py       Packaged-build entry point (bundled config)
    deploy_itch.sh    Upload the build to itch.io (butler)
pacman.spec           PyInstaller build spec
tests/                pytest suite (config, maze, highscores, game rules)
project_management/   Planning, tracking, risk & test docs
```

Data flows one way: `pac-man.py` → `Config` → `Game` (owns a `Level`, which
owns a `Maze`, `Player` and `Ghost`s) ← driven by the UI each tick.

## Project Management

Planning, progress tracking, risk analysis, team organisation and the
acceptance-test plan live in [project_management/](project_management/).

## Resources

- Pac-Man Dossier (ghost AI reference): https://pacman.holenet.info/
- pygame / pygame-ce documentation: https://www.pygame.org/docs/
- PyInstaller: https://pyinstaller.org/ · itch.io butler: https://itch.io/docs/butler/
- PEP 8 / PEP 257 / `typing` module documentation

### AI usage

AI (Claude Code) was used as an assistant, with every suggestion reviewed,
tested and understood before keeping it. Specifically:

- **Scaffolding & architecture** — proposing the module layout and the
  UI/logic split.
- **Adapter design** — reading the assigned `mazegenerator` interface and
  isolating it in `maze_loader.py` (including the wall-bit encoding).
- **Rendering** — porting the terminal wall-drawing to pygame `draw` calls.
- **Review & debugging** — surfacing the player/ghost pass-through bug and the
  pygame `font` crash on Python 3.14 (→ `pygame-ce`).
- **Boilerplate** — Makefile, config validation, docstrings, packaging spec
  and the project-management document templates.

Core game logic was written and verified by hand; AI was not used to generate
code we could not explain.
