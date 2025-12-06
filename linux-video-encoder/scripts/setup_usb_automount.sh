#!/usr/bin/env bash
set -euo pipefail

# Set up udev-based automount for USB storage partitions to the AutoEncoder USB path.
# This mounts any USB partition to /linux-video-encoder/AutoEncoder/linux-video-encoder/USB
# so the container (bind-mounted to /mnt/usb with rslave) can see files without restarts.

TARGET="/linux-video-encoder/AutoEncoder/linux-video-encoder/USB"
RULE_FILE="/etc/udev/rules.d/99-autoencoder-usb.rules"
HELPER="/usr/local/bin/autoencoder_usb_mount.sh"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Please run as root (use sudo)." >&2
  exit 1
fi

echo "[usb-auto] Installing exFAT tools and creating mountpoint..."
apt-get update -y >/dev/null 2>&1 || true
apt-get install -y exfatprogs >/dev/null 2>&1 || true
mkdir -p "$TARGET"

cat > "$HELPER" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SRC="/dev/$1"
TARGET="/linux-video-encoder/AutoEncoder/linux-video-encoder/USB"
LOG_TAG="autoencoder-usb"

mkdir -p "$TARGET"

logger -t "$LOG_TAG" "Attempting mount of $SRC -> $TARGET"

if mountpoint -q "$TARGET"; then
  current=$(findmnt -n -o SOURCE --target "$TARGET" || true)
  if [ "$current" = "$SRC" ]; then
    exit 0
  else
    umount "$TARGET" || true
  fi
fi

opts="uid=1000,gid=1000,fmask=0022,dmask=0022,iocharset=utf8"
if mount -o "$opts" "$SRC" "$TARGET"; then
  logger -t "$LOG_TAG" "Mounted $SRC -> $TARGET"
else
  logger -t "$LOG_TAG" "Failed to mount $SRC -> $TARGET"
fi
EOF
chmod +x "$HELPER"

echo "[usb-auto] Writing udev rules..."
cat > "$RULE_FILE" <<'EOF'
# AutoEncoder USB automount
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", RUN+="/usr/local/bin/autoencoder_usb_mount.sh %k"
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ATTR{removable}=="1", RUN+="/usr/local/bin/autoencoder_usb_mount.sh %k"
ACTION=="remove", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", RUN+="/bin/umount -l /linux-video-encoder/AutoEncoder/linux-video-encoder/USB"
ACTION=="remove", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ATTR{removable}=="1", RUN+="/bin/umount -l /linux-video-encoder/AutoEncoder/linux-video-encoder/USB"
EOF

echo "[usb-auto] Reloading udev rules..."
udevadm control --reload
udevadm trigger -s block

echo "[usb-auto] USB automount configured. Plug a stick; it will mount to $TARGET"
