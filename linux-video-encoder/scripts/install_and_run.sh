#!/usr/bin/env bash
SUDO=""
set -euo pipefail

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[installer] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

# Prepare working directory at /linux-video-encoder (wipe and recreate)
if [ -d "$BASE_DIR" ]; then
  printf '[installer] Removing existing %s\n' "$BASE_DIR"
  $SUDO rm -rf "$BASE_DIR"
fi
$SUDO mkdir -p "$BASE_DIR"
$SUDO chmod 755 "$BASE_DIR"
# ensure files we create are owned by the invoking user (if run via sudo)
TARGET_OWNER="${SUDO_USER:-$USER}"
$SUDO chown "$TARGET_OWNER":"$TARGET_OWNER" "$BASE_DIR"

# Log everything to /linux-video-encoder/installer.log (or override with LOG_FILE) as early as possible
LOG_FILE="${LOG_FILE:-$BASE_DIR/installer.log}"
exec > >(tee -a "$LOG_FILE") 2>&1

# This script installs Docker, Docker Compose plugin,
# then builds and runs the linux-video-encoder stack.
# Tunable vars (override with env):
#   REPO_URL  - Git URL to clone (set to your fork if publishing)
#   REPO_DIR  - directory to clone into
#   IMAGE_TAG - image name:tag to build
#
# MakeMKV tarballs:
#   MAKEMKV_VERSION (default 1.18.2)
#   MAKEMKV_BASE_URL (default raw link to your repo)

REPO_URL="${REPO_URL:-https://github.com/thashiznit2003/AutoEncoder.git}"
REPO_TARBALL_URL="${REPO_TARBALL_URL:-https://github.com/thashiznit2003/AutoEncoder/archive/refs/heads/main.tar.gz}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"
MAKEMKV_VERSION="${MAKEMKV_VERSION:-1.18.2}"
MAKEMKV_BASE_URL="${MAKEMKV_BASE_URL:-https://www.makemkv.com/download}"
# Explicit tarball URLs (override if hosting elsewhere)
MAKEMKV_BIN_URL="${MAKEMKV_BIN_URL:-${MAKEMKV_BASE_URL}/makemkv-bin-${MAKEMKV_VERSION}.tar.gz}"
MAKEMKV_OSS_URL="${MAKEMKV_OSS_URL:-${MAKEMKV_BASE_URL}/makemkv-oss-${MAKEMKV_VERSION}.tar.gz}"

if [ "${TRACE:-0}" = "1" ]; then
  set -x
fi

log() { printf '[installer] %s\n' "$*"; }

ensure_base_tools() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1 || ! command -v file >/dev/null 2>&1; then
    log "Installing curl, tar, and file..."
    $SUDO apt-get update
    $SUDO apt-get install -y curl tar file
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed."
    return
  fi
  log "Installing Docker..."
  $SUDO apt-get update
  $SUDO apt-get install -y ca-certificates curl gnupg lsb-release
  $SUDO install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
  $SUDO apt-get update
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  log "Docker installed."
}

fetch_repo() {
  # If repo already exists and is a git repo, update it; otherwise download a tarball via curl.
  if [ -d "$REPO_DIR/.git" ] && command -v git >/dev/null 2>&1; then
    log "Repo already present at $REPO_DIR; pulling latest..."
    git -C "$REPO_DIR" pull --ff-only || true
    return
  fi

  if [ -d "$REPO_DIR" ] && [ ! -d "$REPO_DIR/linux-video-encoder" ]; then
    log "Found existing $REPO_DIR but no git metadata. Replacing with fresh download."
    rm -rf "$REPO_DIR"
  fi

  if command -v git >/dev/null 2>&1; then
    log "Cloning repo from $REPO_URL..."
    git clone "$REPO_URL" "$REPO_DIR"
    return
  fi

  log "Git not available; downloading tarball via curl."
  tmpdir="$(mktemp -d)"
  curl -L "$REPO_TARBALL_URL" -o "$tmpdir/repo.tar.gz"
  mkdir -p "$REPO_DIR"
  tar -xzf "$tmpdir/repo.tar.gz" -C "$tmpdir"
  extracted="$(find "$tmpdir" -maxdepth 1 -type d -name 'AutoEncoder*' | head -n 1)"
  if [ -z "$extracted" ] || [ ! -d "$extracted" ]; then
    log "Failed to find extracted repo folder in tarball."
    exit 1
  fi
  rm -rf "$REPO_DIR"
  mv "$extracted" "$REPO_DIR"
  rm -rf "$tmpdir"
}

ensure_media_dirs() {
  # Create standard media/output folders under the repo for compose binds.
  local base="$REPO_DIR/linux-video-encoder"
  mkdir -p "$base/USB" "$base/DVD" "$base/Bluray" "$base/File" "$base/Output" "$base/Ripped"
}

build_and_run() {
  cd "$REPO_DIR/linux-video-encoder" || cd "$REPO_DIR"
  ensure_media_dirs
  log "Stopping any existing stack (docker compose down)..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose -f "$REPO_DIR/linux-video-encoder/docker-compose.yml" down || true
  # Pre-download MakeMKV tarballs from your GitHub to ensure they are available during build
  log "Ensuring MakeMKV tarballs are present (version ${MAKEMKV_VERSION})..."
  for f in "makemkv-bin-${MAKEMKV_VERSION}.tar.gz" "makemkv-oss-${MAKEMKV_VERSION}.tar.gz"; do
    url="$MAKEMKV_BIN_URL"
    if echo "$f" | grep -q "oss"; then
      url="$MAKEMKV_OSS_URL"
    fi
    download_tarball() {
      log "Downloading $f from $url"
      if ! curl -fL --retry 3 --retry-delay 2 "$url" -o "$f"; then
        log "Failed to download ${f} from ${url}."
        return 1
      fi
      mime="$(file -b --mime-type "$f" || true)"
      case "$mime" in application/gzip|application/x-gzip) ;; *)
        log "Downloaded $f has unexpected MIME type: ${mime:-unknown}"
        return 1
      esac
      $SUDO chown "$TARGET_OWNER":"$TARGET_OWNER" "$f" || true
      $SUDO chmod 644 "$f" || true
    }

    # If present and valid, keep it; otherwise download and validate.
    needs_download=1
    if [ -s "$f" ] && tar -tzf "$f" >/dev/null 2>&1; then
      needs_download=0
    fi

    if [ "$needs_download" -eq 1 ]; then
      log "$f missing or invalid; fetching..."
      rm -f "$f"
      download_tarball || { log "Aborting build (download failed for ${f})."; exit 1; }
    else
      log "$f already present and gzip-valid; reusing."
    fi

    # Do a lightweight check but don't abort if it fails—proceed to tar regardless, per request.
    if ! tar -tzf "$f" >/dev/null 2>&1; then
      log "Warning: ${f} failed gzip/tar listing; proceeding anyway per relaxed validation."
    fi

    # Best-effort content sanity: warn if expected markers are missing, but do not abort.
    if echo "$f" | grep -q "oss"; then
      if ! tar -tzf "$f" 2>/dev/null | grep -q "makemkv-oss-${MAKEMKV_VERSION}/configure"; then
        log "Warning: ${f} missing expected configure inside makemkv-oss-${MAKEMKV_VERSION}; continuing."
      fi
    else
      # Prefer configure, but accept Makefile or makefile.linux as fallbacks.
      if ! tar -tzf "$f" 2>/dev/null | grep -E -q "makemkv-bin-${MAKEMKV_VERSION}/configure"; then
        if tar -tzf "$f" 2>/dev/null | grep -E -q "makemkv-bin-${MAKEMKV_VERSION}/(Makefile|makefile\\.linux)"; then
          log "Warning: ${f} missing configure but has Makefile/makefile.linux; continuing."
        else
          log "Warning: ${f} missing configure/Makefile/makefile.linux inside makemkv-bin-${MAKEMKV_VERSION}; continuing."
        fi
      fi
    fi
  done

  log "Building image $IMAGE_TAG ..."
  build_log="$BASE_DIR/build.log"
  if ! $SUDO docker build \
    --build-arg MAKEMKV_VERSION="$MAKEMKV_VERSION" \
    --build-arg MAKEMKV_BASE_URL="$MAKEMKV_BASE_URL" \
    -t "$IMAGE_TAG" . 2>&1 | tee "$build_log"; then
    log "Docker build failed. Showing tail of $build_log"
    tail -n 200 "$build_log" || true
    exit 1
  fi
  log "Starting stack with docker compose..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose up -d
  log "Stack is running. Web UI: http://<host>:5959"
}

maybe_install_nvidia_toolkit() {
  local helper="$REPO_DIR/linux-video-encoder/scripts/install_nvidia_toolkit.sh"
  if [ ! -f "$helper" ]; then
    log "NVIDIA toolkit helper not found at $helper; skipping prompt."
    return
  fi
  printf "Install NVIDIA Container Toolkit for NVENC? [y/N]: "
  local ans
  if ! read -r ans; then
    log "No input detected; skipping NVIDIA toolkit install."
    return
  fi
  case "$ans" in
    [yY]|[yY][eE][sS])
      log "Installing NVIDIA Container Toolkit via bundled helper..."
      $SUDO bash "$helper"
      log "NVIDIA toolkit installed; restarting stack to ensure runtime picks up changes..."
      cd "$REPO_DIR/linux-video-encoder" || cd "$REPO_DIR"
      IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose up -d
      ;;
    *)
      log "Skipping NVIDIA toolkit install."
      ;;
  esac
}

main() {
  ensure_base_tools
  install_docker
  fetch_repo
  build_and_run
  maybe_install_nvidia_toolkit
}

main "$@"
