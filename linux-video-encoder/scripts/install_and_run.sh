#!/usr/bin/env bash
set -euo pipefail

# This script installs Docker, Docker Compose plugin, NVIDIA Container Toolkit,
# then builds and runs the linux-video-encoder stack.
# Tunable vars (override with env):
#   REPO_URL  - Git URL to clone (set to your fork if publishing)
#   REPO_DIR  - directory to clone into
#   IMAGE_TAG - image name:tag to build

REPO_URL="${REPO_URL:-https://github.com/thashiznit2003/AutoEncoder.git}"
REPO_TARBALL_URL="${REPO_TARBALL_URL:-https://github.com/thashiznit2003/AutoEncoder/archive/refs/heads/main.tar.gz}"
REPO_DIR="${REPO_DIR:-$HOME/AutoEncoder}"
IMAGE_TAG="${IMAGE_TAG:-linux-video-encoder:latest}"
# Default NVIDIA driver for Quadro P600 (Linux x86_64)
NVIDIA_DRIVER_URL="${NVIDIA_DRIVER_URL:-https://us.download.nvidia.com/XFree86/Linux-x86_64/470.239.06/NVIDIA-Linux-x86_64-470.239.06.run}"
# Set INSTALL_NVIDIA_DRIVER=1 to force a driver install; default skips if already installed.
INSTALL_NVIDIA_DRIVER="${INSTALL_NVIDIA_DRIVER:-0}"

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[installer] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

log() { printf '[installer] %s\n' "$*"; }

ensure_base_tools() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
    log "Installing curl and tar..."
    $SUDO apt-get update
    $SUDO apt-get install -y curl tar
  fi
}

install_nvidia_driver() {
  if [ "$INSTALL_NVIDIA_DRIVER" != "1" ]; then
    log "Skipping NVIDIA driver install (INSTALL_NVIDIA_DRIVER!=1)."
    return
  fi
  if command -v nvidia-smi >/dev/null 2>&1; then
    log "NVIDIA driver already present."
    return
  fi
  log "Installing NVIDIA driver from $NVIDIA_DRIVER_URL ..."
  $SUDO apt-get update
  $SUDO apt-get install -y build-essential dkms linux-headers-$(uname -r) perl
  tmpdir="$(mktemp -d)"
  curl -L "$NVIDIA_DRIVER_URL" -o "$tmpdir/driver.run"
  chmod +x "$tmpdir/driver.run"
  # Silent install with DKMS; may require reboot if kernel modules are updated.
  if ! $SUDO sh "$tmpdir/driver.run" --silent --dkms; then
    log "NVIDIA driver installer failed."
    exit 1
  fi
  rm -rf "$tmpdir"
  log "NVIDIA driver installed. A reboot may be required for modules to load."
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

install_nvidia_toolkit() {
  if dpkg -s nvidia-container-toolkit >/dev/null 2>&1; then
    log "NVIDIA Container Toolkit already installed."
  else
    log "Installing NVIDIA Container Toolkit..."

    # Remove any existing repo file (to avoid HTML/invalid content breaking apt)
    if [ -f /etc/apt/sources.list.d/nvidia-container-toolkit.list ]; then
      log "Removing existing nvidia-container-toolkit.list to ensure a clean add."
      $SUDO rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list
    fi
    # Also remove any old NVIDIA lines from /etc/apt/sources.list to avoid bad entries
    if grep -q "nvidia.github.io/libnvidia-container" /etc/apt/sources.list 2>/dev/null; then
      log "Removing stale NVIDIA repo entries from /etc/apt/sources.list."
      $SUDO cp /etc/apt/sources.list /etc/apt/sources.list.bak
      $SUDO sed -i '/nvidia.github.io\\/libnvidia-container/d' /etc/apt/sources.list
    fi

    $SUDO apt-get update
    $SUDO apt-get install -y curl gnupg
    arch=$(dpkg --print-architecture)
    # Install key without prompting for overwrite
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | $SUDO gpg --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    # Build repo lines for Ubuntu based on VERSION_ID (force 22.04 repo for all Ubuntu until 24.04 is published)
    . /etc/os-release
    case "${ID:-}" in
      ubuntu) repo_path="ubuntu22.04" ;;
      *)
        log "Unsupported distro for manual repo creation; please add repo manually."
        exit 1
        ;;
    esac
    # Add repo directly to main sources.list to avoid bad .list files getting reused
    repo_line="deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/${repo_path}/${arch} /"
    log "Adding NVIDIA repo to /etc/apt/sources.list: $repo_line"
    # Remove any stale NVIDIA entries (any line containing nvidia.github.io/libnvidia-container)
    $SUDO sed -i '/nvidia.github.io\\/libnvidia-container/d' /etc/apt/sources.list
    printf '%s\n' "$repo_line" | $SUDO tee -a /etc/apt/sources.list >/dev/null

    # Temporarily allow insecure updates (NVIDIA repo lacks Release for Ubuntu 24.04); will remove after install
    ALLOW_CONF="/etc/apt/apt.conf.d/99allow-insecure-nvidia"
    echo 'Acquire::AllowInsecureRepositories "true";' | $SUDO tee "$ALLOW_CONF" >/dev/null
    echo 'Acquire::AllowDowngradeToInsecureRepositories "true";' | $SUDO tee -a "$ALLOW_CONF" >/dev/null

    $SUDO apt-get update
    $SUDO apt-get install -y nvidia-container-toolkit
    # Remove insecure override
    $SUDO rm -f "$ALLOW_CONF"
    $SUDO nvidia-ctk runtime configure --runtime=docker || true
    log "NVIDIA Container Toolkit installed."
  fi
  log "Restarting Docker to pick up NVIDIA runtime..."
  $SUDO systemctl restart docker
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
  log "Building image $IMAGE_TAG ..."
  $SUDO docker build -t "$IMAGE_TAG" .
  log "Starting stack with docker compose..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose up -d
  log "Stack is running. Web UI: http://<host>:5959"
}

main() {
  ensure_base_tools
  install_docker
  install_nvidia_driver
  install_nvidia_toolkit
  fetch_repo
  build_and_run
}

main "$@"
