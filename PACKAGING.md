# Packaging & Deployment

How to turn the source into a standalone build and publish it (Chapter VII).

## Build a standalone executable

```bash
make package        # installs pyinstaller into .venv and runs pacman.spec
# or manually:
.venv/bin/pyinstaller pacman.spec --noconfirm
```

The result is a single windowed executable in `dist/`:

- macOS / Linux: `dist/pacman`
- Windows: `dist/pacman.exe`

What the spec ([pacman.spec](pacman.spec)) bundles:

- `scripts/launcher.py` — the packaged entry point. Unlike `pac-man.py` (which
  requires a `config.json` argument), the launcher loads the **bundled**
  config and redirects highscores to a per-user folder (`~/.pacman/`), since
  an app bundle is read-only.
- `config.json` — the default configuration.
- `src/` — the game package.
- `mazegenerator`, `pygame` — declared as `hiddenimports` (imported lazily).

## In-package instructions

Controls and rules are available in-game via **Main Menu → Instructions**.
Keys: arrows / WASD to move, `P`/`Esc` to pause, `F1`–`F4` cheats.

## Publish to Itch.io (unlisted)

One-time setup:

1. Create a free Itch.io account and a new project page; set it to
   **Restricted / unlisted** and the price to **free**.
2. Install `butler`: <https://itch.io/docs/butler/installing.html>
3. `butler login`

Then, after `make package`:

```bash
ITCH_USER=<your-username> ITCH_GAME=pacman make deploy
```

[scripts/deploy_itch.sh](scripts/deploy_itch.sh) detects your OS and pushes
`dist/` to the channel `windows` / `osx` / `linux` accordingly. Repeat the
build+deploy on each target OS to cover all platforms.

## Notes

- The build must be regenerable during peer review — that is exactly what
  `make package` does from a clean checkout.
- Steam is an alternative to Itch.io; it needs a paid developer account and
  `steamcmd`. Itch.io is the lighter path for this project.
