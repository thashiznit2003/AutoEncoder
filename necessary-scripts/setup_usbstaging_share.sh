#!/usr/bin/env bash
set -euo pipefail

# Setup Samba share "usbstaging" and restart the stack.
# Defaults:
#   BASE_DIR=/linux-video-encoder
#   REPO_DIR=$BASE_DIR/AutoEncoder/linux-video-encoder
#   USB_STAGING_DIR=$REPO_DIR/USBStaging
# Provide SMB_USER/SMB_PASS via env to skip prompts.

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
  if ! command -v sudo >/dev/null 2>&1; then
    printf '[usbstaging] sudo not found; please run as root.\n' >&2
    exit 1
  fi
fi

BASE_DIR="${BASE_DIR:-/linux-video-encoder}"
REPO_DIR="${REPO_DIR:-$BASE_DIR/AutoEncoder/linux-video-encoder}"
USB_STAGING_DIR="${USB_STAGING_DIR:-$REPO_DIR/USBStaging}"
SMB_USER=""
SMB_PASS=""

log() { printf '[usbstaging] %s\n' "$*"; }

prompt_creds() {
  printf "Enter Samba username (will be created if missing): "
  read -r SMB_USER
  if [ -z "$SMB_USER" ]; then
    log "No Samba user provided; aborting."
    exit 1
  fi
  printf "Enter Samba password for %s: " "$SMB_USER"
  read -rs SMB_PASS
  printf "\n"
  if [ -z "$SMB_PASS" ]; then
    log "No Samba password provided; aborting."
    exit 1
  fi
}

setup_samba() {
  log "Installing Samba if needed..."
  $SUDO apt-get update
  $SUDO apt-get install -y samba samba-common

  log "Ensuring Samba user $SMB_USER exists..."
  if ! id -u "$SMB_USER" >/dev/null 2>&1; then
    $SUDO useradd -m "$SMB_USER"
  fi

  log "Setting Samba password for $SMB_USER..."
  printf "%s\n%s\n" "$SMB_PASS" "$SMB_PASS" | $SUDO smbpasswd -a "$SMB_USER" -s

  log "Preparing USB staging directory at $USB_STAGING_DIR ..."
  $SUDO mkdir -p "$USB_STAGING_DIR"
  $SUDO chown -R "$SMB_USER":"$SMB_USER" "$USB_STAGING_DIR"
  $SUDO chmod -R 775 "$USB_STAGING_DIR"

  log "Backing up /etc/samba/smb.conf to /etc/samba/smb.conf.bak (once)..."
  if [ ! -f /etc/samba/smb.conf.bak ]; then
    $SUDO cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
  fi

  samba_share_exists() {
    $SUDO test -f /etc/samba/smb.conf && $SUDO grep -q "^\[$1\]" /etc/samba/smb.conf
  }

  if samba_share_exists usbstaging; then
    log "Samba share usbstaging already exists; leaving smb.conf unchanged."
  else
    cat <<CONFIG | $SUDO tee -a /etc/samba/smb.conf >/dev/null

[usbstaging]
   path = $USB_STAGING_DIR
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SMB_USER
   force user = $SMB_USER
   create mask = 0664
   directory mask = 0775
CONFIG
    log "Restarting Samba services..."
    $SUDO systemctl restart smbd nmbd || $SUDO systemctl restart smbd || true
    log "Samba share usbstaging configured. Access smb://<host>/usbstaging with user '$SMB_USER'."
  fi
}

update_app() {
  if [ -d "$REPO_DIR/.git" ] && command -v git >/dev/null 2>&1; then
    log "Updating repository at $REPO_DIR ..."
    git -C "$REPO_DIR" pull --ff-only || true
  fi
  if [ -f "$REPO_DIR/docker-compose.yml" ]; then
    log "Restarting stack with docker compose..."
    (cd "$REPO_DIR" && IMAGE_TAG=linux-video-encoder:latest $SUDO docker compose down && IMAGE_TAG=linux-video-encoder:latest $SUDO docker compose up -d)
  else
    log "docker-compose.yml not found at $REPO_DIR; skipping stack restart."
  fi
}

prompt_creds
setup_samba
update_app
log "Done."
