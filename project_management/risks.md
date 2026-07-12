# Risk Analysis

| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|------------|--------|
| Assigned maze package re-installed at review with a different build | Medium | High | All coupling isolated in `maze_loader.py`; output validated in `_validate_grid`; failure surfaced as `MazeError` | Mitigated |
| Config changed live during defense | High | Medium | Everything data-driven; missing/invalid values clamp to defaults, never crash | Mitigated |
| pygame incompatibility on the grading machine | Medium | High | Pinned `pygame-ce`; headless fallback demo if no display; only stdlib + pygame used | Mitigated |
| Packaging fails to bundle lazy imports | Medium | Medium | `hiddenimports=['mazegenerator','pygame']` in the spec; launcher resolves config/highscore paths | Mitigated |
| Read-only app bundle can't write highscores | Medium | Low | Launcher redirects highscores to `~/.pacman/` | Mitigated |
| Ghosts too hard / too easy | Low | Low | Speeds and frightened window are config-tunable | Accepted |
| Team member unavailable | Low | Medium | Modular architecture lets work proceed in parallel; document decisions | Accepted |

## Top residual risk

Regenerating and uploading the platform build under time pressure at the
defense. Mitigation: `make package` + `make deploy` are scripted and tested
from a clean checkout ahead of time.
