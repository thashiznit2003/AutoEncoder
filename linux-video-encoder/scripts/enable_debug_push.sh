#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/linux-video-encoder/AutoEncoder/linux-video-encoder}"
cd "$REPO_DIR"

if [ ! -f docker-compose.yml ]; then
  echo "docker-compose.yml not found in $REPO_DIR"
  exit 1
fi

if ! command -v docker >/dev/null; then
  echo "docker is required"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required"
  exit 1
fi

ts=$(date +%Y%m%d-%H%M%S)
cp docker-compose.yml "docker-compose.yml.bak.$ts"
echo "Backed up compose to docker-compose.yml.bak.$ts"

mkdir -p debug_uploads
touch debug_uploads/.keep

# Determine where the .git directory lives (current dir or parent)
GIT_SRC="./.git"
if [ ! -d "$GIT_SRC" ] && [ -d "../.git" ]; then
  GIT_SRC="../.git"
fi

needs_git=1
needs_dbg=1
grep -q "$GIT_SRC:/linux-video-encoder/.git" docker-compose.yml && needs_git=0
grep -q '\./debug_uploads:/linux-video-encoder/debug_uploads' docker-compose.yml && needs_dbg=0

if [ $needs_git -eq 1 ] || [ $needs_dbg -eq 1 ]; then
  awk -v add_git=$needs_git -v add_dbg=$needs_dbg -v git_src="$GIT_SRC" '
    /^      - \.\/scripts:\/linux-video-encoder\/scripts/ && !inserted {
      print
      if (add_git) print "      - " git_src ":/linux-video-encoder/.git:ro"
      if (add_dbg) print "      - ./debug_uploads:/linux-video-encoder/debug_uploads"
      inserted=1
      next
    }
    {print}
    END {
      if (!inserted && (add_git || add_dbg)) {
        if (add_git) print "      - ./.git:/linux-video-encoder/.git:ro"
        if (add_dbg) print "      - ./debug_uploads:/linux-video-encoder/debug_uploads"
      }
    }
  ' docker-compose.yml > docker-compose.yml.tmp
  mv docker-compose.yml.tmp docker-compose.yml
  echo "Updated compose to mount .git (ro) and debug_uploads"
else
  echo "Compose already has required mounts; leaving as-is"
fi

echo "Restarting stack..."
docker compose down
docker compose up -d

echo "Running debug git setup inside the container (will prompt for username/PAT)..."
docker compose exec -it autoencoder bash -lc "curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/setup_debug_git.sh -o /tmp/setup_debug_git.sh && chmod +x /tmp/setup_debug_git.sh && REPO_DIR=/linux-video-encoder /tmp/setup_debug_git.sh"

echo "Done. Toggle Debug Mode ON in the Settings page to start auto-pushing snapshots."
