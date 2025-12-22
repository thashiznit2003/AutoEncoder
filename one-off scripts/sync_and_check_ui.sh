#!/usr/bin/env bash
# Sync the repo to latest main, restart the stack (no rebuild), and verify the running UI shows the copy-logs button.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/one-off%20scripts/sync_and_check_ui.sh -o /tmp/sync_and_check_ui.sh
#   bash /tmp/sync_and_check_ui.sh

set -euo pipefail

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"
REPO_DIR="${BASE_DIR}/AutoEncoder"
STACK_DIR="${REPO_DIR}/linux-video-encoder"

log() { printf '[sync-check] %s\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

require_cmd git
require_cmd docker

log "Using BASE_DIR=${BASE_DIR}"
mkdir -p "$BASE_DIR"

if [ -d "$REPO_DIR/.git" ]; then
  log "Repo exists; fetching latest..."
  git -C "$REPO_DIR" fetch origin
  git -C "$REPO_DIR" reset --hard origin/main
else
  log "Cloning repo..."
  git clone https://github.com/thashiznit2003/AutoEncoder.git "$REPO_DIR"
fi

cd "$STACK_DIR"

log "Stopping stack..."
docker compose down || true

log "Starting stack (no rebuild)..."
docker compose up -d --force-recreate

log "Checking running container for copy-logs button..."
docker exec -it linux-video-encoder sh -c "grep -n 'copy-logs' /linux-video-encoder/src/web_server.py || echo 'NOT FOUND'"

log "Testing served HTML for copy-logs text..."
curl -s http://localhost:5959 | grep -n "Copy last 300" || echo "Copy button text not found in served HTML"

log "Done. Hard reload the UI in your browser if needed (Ctrl+Shift+R/Cmd+Shift+R)."
