#!/usr/bin/env bash
set -euo pipefail

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[host-setup] sudo not found; please install sudo or run as root.\n' >&2
    exit 1
  fi
fi

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder}"
APP_DIR="${APP_DIR:-$REPO_DIR/linux-video-encoder}"

CONFIG_URL="${CONFIG_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/config.json}"
USB_HELPER_INSTALL_URL="${USB_HELPER_INSTALL_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/install_usb_host_helper.sh}"
OPTICAL_HELPER_INSTALL_URL="${OPTICAL_HELPER_INSTALL_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/install_optical_host_helper.sh}"
USB_AUTOMOUNT_URL="${USB_AUTOMOUNT_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/setup_usb_automount.sh}"
NVIDIA_TOOLKIT_URL="${NVIDIA_TOOLKIT_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/install_nvidia_toolkit.sh}"

log() { printf '[host-setup] %s\n' "$*"; }

APT_UPDATED=0
HAS_NVIDIA=0
HAS_INTEL=0
HAS_AMD=0
GPU_SUMMARY="unknown"
WANT_OPTICAL=0

apt_update_once() {
  if [ "$APT_UPDATED" -eq 0 ]; then
    $SUDO apt-get update
    APT_UPDATED=1
  fi
}

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
  if ! command -v curl >/dev/null 2>&1; then
    log "Installing curl..."
    apt_update_once
    $SUDO apt-get install -y curl
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    log "Installing python3..."
    apt_update_once
    $SUDO apt-get install -y python3
  fi
  if ! command -v lspci >/dev/null 2>&1; then
    log "Installing pciutils for GPU detection..."
    apt_update_once
    $SUDO apt-get install -y pciutils
  fi
}

ensure_optical_tools() {
  if ! command -v sg_reset >/dev/null 2>&1 || ! command -v eject >/dev/null 2>&1; then
    log "Installing optical tooling (sg3-utils, eject)..."
    apt_update_once
    $SUDO apt-get install -y sg3-utils eject
  fi
}

detect_gpu() {
  HAS_NVIDIA=0
  HAS_INTEL=0
  HAS_AMD=0

  if command -v lspci >/dev/null 2>&1; then
    local gpu_lines
    gpu_lines="$(lspci -nn | grep -Ei 'vga|3d|display' || true)"
    if echo "$gpu_lines" | grep -qi 'nvidia'; then
      HAS_NVIDIA=1
    fi
    if echo "$gpu_lines" | grep -qi 'intel'; then
      HAS_INTEL=1
    fi
    if echo "$gpu_lines" | grep -Eqi 'amd|ati|advanced micro devices'; then
      HAS_AMD=1
    fi
  fi

  if [ "$HAS_NVIDIA" -eq 0 ] && [ "$HAS_INTEL" -eq 0 ] && [ "$HAS_AMD" -eq 0 ]; then
    local vendor_file
    for vendor_file in /sys/class/drm/card*/device/vendor; do
      [ -f "$vendor_file" ] || continue
      case "$(cat "$vendor_file" 2>/dev/null)" in
        0x10de) HAS_NVIDIA=1 ;;
        0x8086) HAS_INTEL=1 ;;
        0x1002|0x1022) HAS_AMD=1 ;;
      esac
    done
  fi

  local parts=()
  if [ "$HAS_NVIDIA" -eq 1 ]; then parts+=("NVIDIA"); fi
  if [ "$HAS_INTEL" -eq 1 ]; then parts+=("Intel"); fi
  if [ "$HAS_AMD" -eq 1 ]; then parts+=("AMD"); fi
  if [ "${#parts[@]}" -eq 0 ]; then
    GPU_SUMMARY="none"
  else
    GPU_SUMMARY="$(IFS=', '; echo "${parts[*]}")"
  fi
}

prompt_optical_drive() {
  printf "Do you have a Blu-ray/DVD drive attached to this host? [y/N]: "
  local ans
  if ! read -r ans; then
    log "No input detected; assuming no optical drive."
    WANT_OPTICAL=0
    return
  fi
  case "$ans" in
    [yY]|[yY][eE][sS])
      WANT_OPTICAL=1
      ;;
    *)
      WANT_OPTICAL=0
      ;;
  esac
}

print_optical_summary() {
  if [ "$WANT_OPTICAL" -eq 1 ]; then
    log "Optical drive: enabled. Optical helper installed."
    log "MakeMKV is required for ripping. Install it separately using the MakeMKV overlay script."
    log "Example (run on the Docker host):"
    log "  curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/dockerhub/with-makemkv/build_with_makemkv.sh -o /tmp/build_with_makemkv.sh"
    log "  chmod +x /tmp/build_with_makemkv.sh"
    log "  sudo /tmp/build_with_makemkv.sh"
  else
    log "Optical drive: disabled. Optical helper skipped; MakeMKV not required."
  fi
}

install_intel_vaapi() {
  log "Installing Intel VAAPI packages..."
  apt_update_once
  if ! $SUDO apt-get install -y intel-media-va-driver libva-utils; then
    log "Intel VAAPI install failed; install intel-media-va-driver/libva-utils manually."
  fi
}

install_amd_vaapi() {
  log "Installing AMD/mesa VAAPI packages..."
  apt_update_once
  if ! $SUDO apt-get install -y mesa-va-drivers libva-utils; then
    log "AMD VAAPI install failed; install mesa-va-drivers/libva-utils manually."
  fi
}

prepare_dirs() {
  log "Preparing host directories under $APP_DIR"
  $SUDO mkdir -p "$APP_DIR"
  $SUDO mkdir -p "$APP_DIR/USB" "$APP_DIR/DVD" "$APP_DIR/Bluray" "$APP_DIR/File" "$APP_DIR/Output" \
    "$APP_DIR/Ripped" "$APP_DIR/SMBStaging" "$APP_DIR/USBStaging"
  $SUDO chmod 755 "$BASE_DIR" "$REPO_DIR" "$APP_DIR"
  if [ ! -f "$APP_DIR/config.json" ]; then
    log "Downloading default config.json from GitHub..."
    $SUDO curl -fsSL "$CONFIG_URL" -o "$APP_DIR/config.json"
    $SUDO chmod 644 "$APP_DIR/config.json"
  fi
}

setup_usb_automount() {
  log "Configuring USB automount via GitHub script..."
  tmp="$(mktemp)"
  $SUDO curl -fsSL "$USB_AUTOMOUNT_URL" -o "$tmp"
  $SUDO chmod 755 "$tmp"
  TARGET="$APP_DIR/USB" $SUDO bash "$tmp"
  rm -f "$tmp"
}

install_usb_host_helper() {
  log "Installing USB host helper (separate script)..."
  tmp="$(mktemp)"
  $SUDO curl -fsSL "$USB_HELPER_INSTALL_URL" -o "$tmp"
  $SUDO chmod 755 "$tmp"
  $SUDO bash "$tmp"
  rm -f "$tmp"
}

install_optical_host_helper() {
  log "Installing optical host helper (separate script)..."
  tmp="$(mktemp)"
  $SUDO curl -fsSL "$OPTICAL_HELPER_INSTALL_URL" -o "$tmp"
  $SUDO chmod 755 "$tmp"
  $SUDO bash "$tmp"
  rm -f "$tmp"
}
setup_samba_shares() {
  local file_share_path="$APP_DIR/File"
  local output_share_path="$APP_DIR/Output"
  local smb_staging_path="$APP_DIR/SMBStaging"
  local usb_staging_path="$APP_DIR/USBStaging"
  local ripped_share_path="$APP_DIR/Ripped"

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

  log "Installing Samba..."
  apt_update_once
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

  samba_share_exists() {
    $SUDO test -f /etc/samba/smb.conf && $SUDO grep -q "^\[$1\]" /etc/samba/smb.conf
  }

  local shares_added=0
  if samba_share_exists input; then
    log "Share [input] already exists; leaving as-is."
  else
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
CONFIG
    shares_added=1
  fi

  if samba_share_exists output; then
    log "Share [output] already exists; leaving as-is."
  else
    cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

[output]
   path = $output_share_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775
CONFIG
    shares_added=1
  fi

  if samba_share_exists smbstaging; then
    log "Share [smbstaging] already exists; leaving as-is."
  else
    cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

[smbstaging]
   path = $smb_staging_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775
CONFIG
    shares_added=1
  fi

  if samba_share_exists usbstaging; then
    log "Share [usbstaging] already exists; leaving as-is."
  else
    cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

[usbstaging]
   path = $usb_staging_path
   browseable = yes
   read only = no
   guest ok = no
   valid users = $smb_user
   force user = $smb_user
   create mask = 0664
   directory mask = 0775
CONFIG
    shares_added=1
  fi

  if samba_share_exists ripped; then
    log "Share [ripped] already exists; leaving as-is."
  else
    cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

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
    shares_added=1
  fi

  if [ "$shares_added" -eq 1 ]; then
    log "Restarting Samba services..."
    $SUDO systemctl restart smbd nmbd || $SUDO systemctl restart smbd || true
  else
    log "Samba shares already present; skipping smb.conf update."
  fi
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

maybe_install_nvidia_toolkit() {
  if [ "$HAS_NVIDIA" -ne 1 ]; then
    log "No NVIDIA GPU detected; skipping NVIDIA toolkit install."
    return
  fi
  if command -v nvidia-container-cli >/dev/null 2>&1; then
    log "NVIDIA Container Toolkit already installed; skipping."
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
      log "Installing NVIDIA Container Toolkit from GitHub script..."
      tmp="$(mktemp)"
      $SUDO curl -fsSL "$NVIDIA_TOOLKIT_URL" -o "$tmp"
      $SUDO chmod 755 "$tmp"
      $SUDO bash "$tmp"
      rm -f "$tmp"
      ;;
    *)
      log "Skipping NVIDIA toolkit install."
      ;;
  esac
}

maybe_install_gpu_prereqs() {
  if [ "$HAS_INTEL" -eq 1 ]; then
    install_intel_vaapi
  fi
  if [ "$HAS_AMD" -eq 1 ]; then
    install_amd_vaapi
  fi
  maybe_install_nvidia_toolkit
}

print_gpu_summary() {
  log "GPU detection: ${GPU_SUMMARY}"
  if [ "$HAS_NVIDIA" -eq 1 ]; then
    log "NVIDIA: uncomment runtime + NVIDIA_* env + deploy block in docker-compose.yml."
    if ! command -v nvidia-smi >/dev/null 2>&1; then
      log "NVIDIA driver not detected. On Ubuntu: 'sudo ubuntu-drivers autoinstall' or install nvidia-driver-<version>."
    fi
    log "NVIDIA: ensure NVIDIA Container Toolkit is installed for container GPU access."
  fi
  if [ "$HAS_INTEL" -eq 1 ]; then
    log "Intel: uncomment /dev/dri mapping in docker-compose.yml."
    if [ ! -e /dev/dri ]; then
      log "Intel: /dev/dri not found. Install intel-media-va-driver + libva-utils and reboot if needed."
    fi
  fi
  if [ "$HAS_AMD" -eq 1 ]; then
    log "AMD: uncomment /dev/dri mapping in docker-compose.yml."
    if [ ! -e /dev/dri ]; then
      log "AMD: /dev/dri not found. Install mesa-va-drivers + libva-utils and reboot if needed."
    fi
  fi
  if [ "$HAS_NVIDIA" -eq 0 ] && [ "$HAS_INTEL" -eq 0 ] && [ "$HAS_AMD" -eq 0 ]; then
    log "No GPU detected; keep GPU settings commented for CPU-only usage."
  fi
}

main() {
  ensure_base_tools
  detect_gpu
  prompt_optical_drive
  if [ "$WANT_OPTICAL" -eq 1 ]; then
    ensure_optical_tools
  fi
  prepare_dirs
  setup_usb_automount
  install_usb_host_helper
  if [ "$WANT_OPTICAL" -eq 1 ]; then
    install_optical_host_helper
  fi
  setup_samba_shares
  maybe_install_gpu_prereqs
  print_gpu_summary
  print_optical_summary
  log "Host setup complete. Paste the docker-compose.yml into Portainer and deploy."
}

main "$@"
