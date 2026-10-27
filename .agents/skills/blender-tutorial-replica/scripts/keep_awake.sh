#!/usr/bin/env bash
# Run a long render without the machine sleeping or the screen waking/locking it.
# Usage: keep_awake.sh blender -b scene.blend -a
#   macOS: caffeinate (no display/idle/system sleep while the command runs)
#   Linux: systemd-inhibit (blocks sleep/idle) if available
#   Windows: use keep_awake.ps1 instead
# Turn off notifications / Focus mode as well: notifications can wake the display all night.
set -euo pipefail
if [[ $# -eq 0 ]]; then echo "usage: $0 <command...>"; exit 2; fi
case "$(uname -s)" in
  Darwin) exec caffeinate -dims "$@" ;;
  Linux)
    if command -v systemd-inhibit >/dev/null 2>&1 && systemd-inhibit --what=idle true >/dev/null 2>&1; then
      exec systemd-inhibit --what=sleep:idle --who=blender-render --why="overnight render" "$@"
    fi
    echo "systemd-inhibit unavailable; running without sleep inhibition" >&2
    exec "$@" ;;
  *) exec "$@" ;;
esac
