#!/usr/bin/env bash
# Upload the packaged build to Itch.io using butler.
#
# Prerequisites (one-time):
#   1. Create a free Itch.io account and a new (unlisted) project page.
#   2. Install butler:  https://itch.io/docs/butler/installing.html
#   3. Authenticate:    butler login
#
# Usage:
#   make package                     # build dist/pacman first
#   ITCH_USER=<you> ITCH_GAME=pacman ./scripts/deploy_itch.sh
#
# Channel encodes the platform so Itch serves the right build.

set -euo pipefail

ITCH_USER="${ITCH_USER:?set ITCH_USER to your itch.io username}"
ITCH_GAME="${ITCH_GAME:-pacman}"

case "$(uname -s)" in
    Darwin) CHANNEL="osx" ;;
    Linux)  CHANNEL="linux" ;;
    MINGW*|MSYS*|CYGWIN*) CHANNEL="windows" ;;
    *)      CHANNEL="unknown" ;;
esac

if [ ! -e "dist/pacman" ] && [ ! -e "dist/pacman.exe" ]; then
    echo "error: no build in dist/. Run 'make package' first." >&2
    exit 1
fi

echo "Pushing dist/ to ${ITCH_USER}/${ITCH_GAME}:${CHANNEL} ..."
butler push dist "${ITCH_USER}/${ITCH_GAME}:${CHANNEL}"
echo "Done. Check the page's build status on itch.io."
