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
USB_HELPER_URL="${USB_HELPER_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/usb_host_helper.py}"
USB_AUTOMOUNT_URL="${USB_AUTOMOUNT_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/setup_usb_automount.sh}"
NVIDIA_TOOLKIT_URL="${NVIDIA_TOOLKIT_URL:-https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/install_nvidia_toolkit.sh}"

log() { printf '[host-setup] %s\n' "$*"; }

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
    $SUDO apt-get update
    $SUDO apt-get install -y curl
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    log "Installing python3..."
    $SUDO apt-get update
    $SUDO apt-get install -y python3
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
  local target_dir="/usr/local/lib/autoencoder"
  local helper_path="${target_dir}/usb_host_helper.py"
  local service_path="/etc/systemd/system/autoencoder-usb-helper.service"
  local listen_addr="${HELPER_LISTEN_ADDR:-0.0.0.0}"
  local listen_port="${HELPER_LISTEN_PORT:-8765}"
  local mountpoint="${HELPER_MOUNTPOINT:-$APP_DIR/USB}"

  log "Installing USB host helper from GitHub..."
  $SUDO mkdir -p "$target_dir"
  $SUDO curl -fsSL "$USB_HELPER_URL" -o "$helper_path"
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

maybe_install_nvidia_toolkit() {
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

main() {
  ensure_base_tools
  prepare_dirs
  setup_usb_automount
  install_usb_host_helper
  setup_samba_shares
  maybe_install_nvidia_toolkit
  log "Host setup complete. Paste the docker-compose.yml into Portainer and deploy."
}

main "$@"
