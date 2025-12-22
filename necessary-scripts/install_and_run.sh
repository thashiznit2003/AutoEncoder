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

detect_host_ip() {
  local host_ip=""
  if command -v hostname >/dev/null 2>&1; then
    host_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  fi
  if [ -z "$host_ip" ] && command -v ip >/dev/null 2>&1; then
    host_ip=$(ip -4 route show default 2>/dev/null | awk '{print $3}')
  fi
  printf '%s' "$host_ip"
}

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
  mkdir -p "$base/USB" "$base/DVD" "$base/Bluray" "$base/File" "$base/Output" "$base/Ripped" "$base/SMBStaging" "$base/USBStaging"
}

setup_usb_automount() {
  local script="$REPO_DIR/necessary-scripts/setup_usb_automount.sh"
  if [ ! -x "$script" ]; then
    log "USB automount script missing; skipping."
    return
  fi
  log "Configuring USB automount..."
  $SUDO "$script" || log "USB automount setup exited non-zero (continuing)."
}

install_usb_host_helper() {
  local helper_url="https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/usb_host_helper.py"
  local target_dir="/usr/local/lib/autoencoder"
  local helper_path="${target_dir}/usb_host_helper.py"
  local service_path="/etc/systemd/system/autoencoder-usb-helper.service"
  local listen_addr="${HELPER_LISTEN_ADDR:-0.0.0.0}"
  local listen_port="${HELPER_LISTEN_PORT:-8765}"
  local mountpoint="${HELPER_MOUNTPOINT:-$REPO_DIR/linux-video-encoder/USB}"

  log "Installing USB host helper service (downloaded from GitHub)..."
  $SUDO mkdir -p "$target_dir"
  $SUDO curl -fsSL "$helper_url" -o "$helper_path"
  $SUDO chmod 755 "$helper_path"

  local python_bin
  python_bin="$(command -v python3 || true)"
  if [ -z "$python_bin" ]; then
    log "python3 not found; skipping USB host helper install."
    return
  fi

  $SUDO tee "$service_path" >/dev/null <<EOF
[Unit]
Description=AutoEncoder USB Host Helper
After=network.target

[Service]
Type=simple
ExecStart=${python_bin} ${helper_path} --listen ${listen_addr} --port ${listen_port} --mountpoint ${mountpoint}
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF

  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now autoencoder-usb-helper.service
  $SUDO systemctl status --no-pager autoencoder-usb-helper.service || true
  log "USB host helper running on ${listen_addr}:${listen_port}"
}

build_and_run() {
  ensure_media_dirs
  setup_usb_automount
  install_usb_host_helper
  setup_samba_shares
  log "Stopping any existing stack (docker compose down)..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose -f "$REPO_DIR/linux-video-encoder/docker-compose.yml" down || true
  # Pre-download MakeMKV tarballs from your GitHub to ensure they are available during build
  log "Ensuring MakeMKV tarballs are present (version ${MAKEMKV_VERSION})..."
  cd "$REPO_DIR"
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

    # Force extraction test: unpack to a temp dir; if it fails, re-download once from MAKEMKV_BASE_URL and retry.
    tmp_extract="$(mktemp -d)"
    force_ok=0
    if tar -xzf "$f" -C "$tmp_extract" >/dev/null 2>&1; then
      force_ok=1
    else
      log "Forced extraction failed for ${f}; re-downloading from ${url} and retrying..."
      rm -f "$f"
      download_tarball || { log "Aborting build (second download failed for ${f})."; rm -rf "$tmp_extract"; exit 1; }
      if tar -xzf "$f" -C "$tmp_extract" >/dev/null 2>&1; then
        force_ok=1
      fi
    fi
    if [ "$force_ok" -ne 1 ]; then
      log "ERROR: ${f} could not be extracted even after re-download. Aborting."
      rm -rf "$tmp_extract"
      exit 1
    fi
    rm -rf "$tmp_extract"

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
    -f "$REPO_DIR/linux-video-encoder/Dockerfile" \
    -t "$IMAGE_TAG" "$REPO_DIR" 2>&1 | tee "$build_log"; then
    log "Docker build failed. Showing tail of $build_log"
    tail -n 200 "$build_log" || true
    exit 1
  fi
  log "Starting stack with docker compose..."
  IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose -f "$REPO_DIR/linux-video-encoder/docker-compose.yml" up -d --no-build
  log "Stack is running. Web UI: http://<host>:5959"
  # Best-effort to show host IP
  host_ip="$(detect_host_ip)"
  if [ -n "$host_ip" ]; then
    log "Access the UI at: http://${host_ip}:5959"
  fi
}

maybe_install_nvidia_toolkit() {
  local helper="$REPO_DIR/necessary-scripts/install_nvidia_toolkit.sh"
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
      IMAGE_TAG="$IMAGE_TAG" $SUDO docker compose -f "$REPO_DIR/linux-video-encoder/docker-compose.yml" up -d --no-build
      ;;
    *)
      log "Skipping NVIDIA toolkit install."
      ;;
  esac
}

setup_samba_shares() {
  local base="$REPO_DIR/linux-video-encoder"
  local file_share_path="$base/File"
  local output_share_path="$base/Output"
  local smb_staging_path="$base/SMBStaging"
  local usb_staging_path="$base/USBStaging"
  local ripped_share_path="$base/Ripped"

  printf "Enter Samba username for share access (will be created if missing): "
  local smb_user
  read -r smb_user || true
  if [ -z "${smb_user:-}" ]; then
    log "No Samba user provided; cannot configure shares."
    exit 1
  fi
  printf "Enter Samba password for %s: " "$smb_user"
  local smb_pass
  read -rs smb_pass || true
  printf "\n"
  if [ -z "${smb_pass:-}" ]; then
    log "No Samba password provided; cannot configure shares."
    exit 1
  fi

  log "Installing Samba if needed..."
  $SUDO apt-get update
  $SUDO apt-get install -y samba samba-common

  log "Ensuring Samba user $smb_user exists..."
  if ! id -u "$smb_user" >/dev/null 2>&1; then
    $SUDO useradd -m "$smb_user"
  fi

  log "Setting Samba password for $smb_user..."
  printf "%s\n%s\n" "$smb_pass" "$smb_pass" | $SUDO smbpasswd -a "$smb_user" -s

  log "Preparing share directories..."
  $SUDO mkdir -p "$file_share_path" "$output_share_path" "$smb_staging_path" "$usb_staging_path" "$ripped_share_path"
  $SUDO chown -R "$smb_user":"$smb_user" "$file_share_path" "$output_share_path" "$smb_staging_path" "$usb_staging_path" "$ripped_share_path"
  $SUDO chmod -R 775 "$file_share_path" "$output_share_path" "$smb_staging_path" "$usb_staging_path" "$ripped_share_path"

  log "Backing up /etc/samba/smb.conf to /etc/samba/smb.conf.bak (once)..."
  if [ ! -f /etc/samba/smb.conf.bak ]; then
    $SUDO cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
  fi

  # Remove existing share blocks if present, then append fresh ones.
  for share in lv_file input output smbstaging usbstaging ripped; do
    $SUDO sed -i "/^\[$share\]/,/^\[/d" /etc/samba/smb.conf
  done

  cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

[input]
   path = $file_share_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775

[output]
   path = $output_share_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775

[smbstaging]
   path = $smb_staging_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775

[usbstaging]
   path = $usb_staging_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775

[ripped]
   path = $ripped_share_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775
CONFIG

  log "Restarting Samba services..."
  $SUDO systemctl restart smbd nmbd || $SUDO systemctl restart smbd || true
  local host_ip
  host_ip="$(detect_host_ip)"
  if [ -z "$host_ip" ]; then
    host_ip="<host>"
  fi
  log "Samba shares configured for user '$smb_user':"
  log "  smb://${host_ip}/input"
  log "  smb://${host_ip}/output"
  log "  smb://${host_ip}/ripped"
  log "  smb://${host_ip}/smbstaging"
  log "  smb://${host_ip}/usbstaging"
}

main() {
  ensure_base_tools
  install_docker
  fetch_repo
  build_and_run
  maybe_install_nvidia_toolkit
}

main "$@"
