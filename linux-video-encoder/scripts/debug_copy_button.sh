#!/usr/bin/env bash
# Fetch and compare the running UI HTML vs the on-disk web_server.py inside the container.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/debug_copy_button.sh -o /tmp/debug_copy_button.sh
#   bash /tmp/debug_copy_button.sh

set -euo pipefail

log() { printf '[debug-copy] %s\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

require_cmd docker

log "Checking served HTML for \"Copy last 300\"..."
docker exec -it linux-video-encoder sh -c "curl -s http://localhost:5959 | grep -n 'Copy last 300' || echo 'NOT FOUND in served HTML'"

log "Inspecting web_server.HTML_PAGE inside the container..."
docker exec -it linux-video-encoder sh -c "python3 - <<'PY'\nimport web_server\nprint('copy-logs present in HTML_PAGE:', 'Copy last 300' in web_server.HTML_PAGE)\nfor i, line in enumerate(web_server.HTML_PAGE.splitlines()[120:150], start=121):\n    print(f\"{i:03}: {line}\")\nPY"

log "Done. If served HTML still lacks the button, restart from the updated repo and hard reload the browser."
