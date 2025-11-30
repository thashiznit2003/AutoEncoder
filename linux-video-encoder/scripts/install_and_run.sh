#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"

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
# NVIDIA Container Toolkit (offline .deb install, no apt repo):
#   INSTALL_NVIDIA_TOOLKIT=1 to enable (default: 1)
#   NVIDIA_TOOLKIT_VERSION (default 1.14.3)
#   ALLOW_APT_FIX=1 to allow apt-get -f install if dpkg reports missing deps
# MakeMKV tarballs:
#   MAKEMKV_VERSION (default 1.18.2)
#   MAKEMKV_BASE_URL (default raw link to your repo)

REPO_URL="${REPO_URL:-https://github.com/thashiznit2003/AutoEncoder.git}"
REPO_TARBALL_URL="${REPO_TARBALL_URL:-https://github.com/thashiznit2003/AutoEncoder/archive/refs/heads/main.tar.gz}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"
INSTALL_NVIDIA_TOOLKIT="${INSTALL_NVIDIA_TOOLKIT:-1}"
NVIDIA_TOOLKIT_VERSION="${NVIDIA_TOOLKIT_VERSION:-1.14.3}"
ALLOW_APT_FIX="${ALLOW_APT_FIX:-0}"
MAKEMKV_VERSION="${MAKEMKV_VERSION:-1.18.2}"
MAKEMKV_BASE_URL="${MAKEMKV_BASE_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main}"

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[installer] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

if [ "${TRACE:-0}" = "1" ]; then
  set -x
fi

log() { printf '[installer] %s\n' "$*"; }

ensure_base_tools() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
    log "Installing curl and tar..."
    $SUDO apt-get update
    $SUDO apt-get install -y curl tar
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

install_nvidia_toolkit_offline() {
  if [ "$INSTALL_NVIDIA_TOOLKIT" != "1" ]; then
    log "Skipping NVIDIA Container Toolkit install (INSTALL_NVIDIA_TOOLKIT!=1)."
    return
  fi

  if dpkg -s nvidia-container-toolkit >/dev/null 2>&1; then
    log "NVIDIA Container Toolkit already installed."
    return
  fi

  arch=$(dpkg --print-architecture)
  base_url="https://github.com/NVIDIA/libnvidia-container/releases/download/v${NVIDIA_TOOLKIT_VERSION}"
  pkgs=(
    "nvidia-container-toolkit-base_${NVIDIA_TOOLKIT_VERSION}-1_${arch}.deb"
    "nvidia-container-runtime-hook_${NVIDIA_TOOLKIT_VERSION}-1_${arch}.deb"
    "nvidia-container-toolkit_${NVIDIA_TOOLKIT_VERSION}-1_${arch}.deb"
  )

  tmpdir="$(mktemp -d)"
  log "Downloading NVIDIA toolkit packages (version ${NVIDIA_TOOLKIT_VERSION})..."
  for pkg in "${pkgs[@]}"; do
    url="${base_url}/${pkg}"
    log "Fetching ${url}"
    if ! curl -fL "$url" -o "${tmpdir}/${pkg}"; then
      log "Failed to download ${url}"
      rm -rf "$tmpdir"
      return
    fi
  done

  log "Installing NVIDIA toolkit packages with dpkg..."
  if ! $SUDO dpkg -i "${tmpdir}"/nvidia-container-*.deb; then
    log "dpkg reported missing dependencies."
    if [ "$ALLOW_APT_FIX" = "1" ]; then
      log "Attempting apt-get -f install to fix dependencies..."
      $SUDO apt-get -f install -y
      $SUDO dpkg -i "${tmpdir}"/nvidia-container-*.deb || log "dpkg still failing after apt fix."
    else
      log "Skipping NVIDIA toolkit install (set ALLOW_APT_FIX=1 to let apt fix dependencies)."
      rm -rf "$tmpdir"
      return
    fi
  fi
  rm -rf "$tmpdir"

  if command -v nvidia-ctk >/dev/null 2>&1; then
    $SUDO nvidia-ctk runtime configure --runtime=docker || true
  fi
  $SUDO systemctl restart docker || true
  log "NVIDIA Container Toolkit installation attempt complete."
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

build_and_run() {
  cd "$REPO_DIR/linux-video-encoder" || cd "$REPO_DIR"
  # Pre-download MakeMKV tarballs from your GitHub to ensure they are available during build
  log "Ensuring MakeMKV tarballs are present (version ${MAKEMKV_VERSION})..."
  for f in "makemkv-bin-${MAKEMKV_VERSION}.tar.gz" "makemkv-oss-${MAKEMKV_VERSION}.tar.gz"; do
    if [ ! -s "$f" ]; then
      log "Downloading $f from $MAKEMKV_BASE_URL"
      if ! curl -fL "${MAKEMKV_BASE_URL}/${f}" -o "$f"; then
        log "Failed to download ${f} from ${MAKEMKV_BASE_URL}. Aborting build."
        exit 1
      fi
    else
      log "$f already present; skipping download."
    fi
    if [ ! -s "$f" ]; then
      log "Download check failed for ${f} (file missing or empty). Aborting build."
      exit 1
    fi
    $SUDO chown "$TARGET_OWNER":"$TARGET_OWNER" "$f" || true
    $SUDO chmod 644 "$f" || true
  done

  log "Building image $IMAGE_TAG ..."
  $SUDO docker build \
    --build-arg MAKEMKV_VERSION="$MAKEMKV_VERSION" \
    --build-arg MAKEMKV_BASE_URL="$MAKEMKV_BASE_URL" \
    -t "$IMAGE_TAG" .
  log "Starting stack with docker compose..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose up -d
  log "Stack is running. Web UI: http://<host>:5959"
}

main() {
  ensure_base_tools
  install_docker
  install_nvidia_toolkit_offline
  fetch_repo
  build_and_run
}

main "$@"
