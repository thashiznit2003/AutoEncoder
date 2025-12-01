#!/usr/bin/env bash
# Install NVIDIA Container Toolkit from upstream .deb packages (no APT repo needed).
# Usage (as root or with sudo privileges):
#   curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/install_nvidia_toolkit.sh -o /tmp/install_nvidia_toolkit.sh
#   sudo bash /tmp/install_nvidia_toolkit.sh
#
# Tunables:
#   NVIDIA_TOOLKIT_VERSION   Version to install (default: 1.14.3; script will fallback to a small list)
#   RUN_NVIDIA_TEST=1        After install, run a test container (docker run --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi)

set -euo pipefail

REQUESTED_VER="${NVIDIA_TOOLKIT_VERSION:-1.14.3}"
FALLBACK_VERSIONS=("1.14.5" "1.14.4" "1.14.3" "1.13.5")
ARCH="$(dpkg --print-architecture)"
TMPDIR="$(mktemp -d /tmp/nvidia-ctk.XXXXXX)"
SUDO=""

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
fi

log() { printf '[nvidia-ctk] %s\n' "$*"; }

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

ensure_tools() {
  if ! command -v curl >/dev/null 2>&1; then
    log "Installing curl..."
    $SUDO apt-get update
    $SUDO apt-get install -y curl
  fi
}

clean_bad_lists() {
  local lst="/etc/apt/sources.list.d/nvidia-container-toolkit.list"
  if [ -f "$lst" ]; then
    if grep -qi '<!doctype' "$lst"; then
      log "Detected invalid nvidia-container-toolkit list (HTML); moving aside."
      $SUDO mv "$lst" "${lst}.bak.$(date +%s)" || true
    fi
  fi
}

download_debs() {
  local versions=()
  versions+=("$REQUESTED_VER")
  for v in "${FALLBACK_VERSIONS[@]}"; do
    if [[ ! " ${versions[*]} " =~ " ${v} " ]]; then
      versions+=("$v")
    fi
  done

  for ver in "${versions[@]}"; do
    local base_url="https://github.com/NVIDIA/libnvidia-container/releases/download/v${ver}"
    local files=(
      "libnvidia-container1_${ver}-1_${ARCH}.deb"
      "libnvidia-container-tools_${ver}-1_${ARCH}.deb"
      "nvidia-container-toolkit-base_${ver}-1_${ARCH}.deb"
      "nvidia-container-toolkit_${ver}-1_${ARCH}.deb"
    )
    log "Attempting download for version ${ver}..."
    local ok=1
    for f in "${files[@]}"; do
      local url="${base_url}/${f}"
      log "  downloading ${f}"
      if ! curl -fL --retry 3 --retry-delay 2 "$url" -o "${TMPDIR}/${f}"; then
        log "  failed to fetch ${url}"
        ok=0
        break
      fi
    done
    if [ "$ok" -eq 1 ]; then
      VER="$ver"
      return 0
    else
      log "Version ${ver} failed, trying next fallback..."
      rm -f "${TMPDIR}"/*.deb
    fi
  done

  log "All download attempts failed. Check connectivity or specify NVIDIA_TOOLKIT_VERSION to a valid release."
  exit 1
}

install_debs() {
  log "Installing NVIDIA Container Toolkit .deb packages..."
  if ! $SUDO dpkg -i "${TMPDIR}"/*.deb; then
    log "dpkg reported missing deps; attempting apt-get -f install..."
    $SUDO apt-get -f install -y
    $SUDO dpkg -i "${TMPDIR}"/*.deb
  fi
}

configure_docker() {
  if ! command -v nvidia-ctk >/dev/null 2>&1; then
    log "nvidia-ctk not found after install; aborting runtime configuration."
    return 1
  fi
  log "Configuring Docker runtime for NVIDIA..."
  $SUDO nvidia-ctk runtime configure --runtime=docker
  log "Restarting Docker..."
  if command -v systemctl >/dev/null 2>&1; then
    $SUDO systemctl restart docker
  else
    $SUDO service docker restart
  fi
}

test_gpu() {
  if [ "${RUN_NVIDIA_TEST:-0}" != "1" ]; then
    log "Skipping GPU test (set RUN_NVIDIA_TEST=1 to enable)."
    return
  fi
  log "Running test container (docker run --gpus all ... nvidia-smi)..."
  docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
}

ensure_tools
clean_bad_lists
download_debs
install_debs
configure_docker
test_gpu

log "Done. If you want to test inside your container, run: docker exec -it linux-video-encoder nvidia-smi"
