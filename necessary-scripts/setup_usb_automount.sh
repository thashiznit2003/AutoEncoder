#!/usr/bin/env bash
set -euo pipefail

# Set up udev-based automount for USB storage partitions to the AutoEncoder USB path.
# This mounts any USB partition to /linux-video-encoder/AutoEncoder/linux-video-encoder/USB
# so the container (bind-mounted to /mnt/usb with rslave) can see files without restarts.

TARGET="${TARGET:-/linux-video-encoder/AutoEncoder/linux-video-encoder/USB}"
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

cat > "$HELPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
SRC="/dev/$1"
TARGET="${TARGET}"
LOG_TAG="autoencoder-usb"

mkdir -p "$TARGET"
$MOUNT --make-rshared "$TARGET" || true

# absolute paths for udev environment
LOGGER=/usr/bin/logger
MOUNT=/bin/mount
UMOUNT=/bin/umount
FINDMNT=/usr/bin/findmnt
MOUNTPOINT=/bin/mountpoint
BLKID=/usr/sbin/blkid

logger -t "$LOG_TAG" "Attempting mount of $SRC -> $TARGET"

if [ ! -b "$SRC" ]; then
  $LOGGER -t "$LOG_TAG" "Skipping mount; $SRC is not a block device"
  exit 0
fi

# Detect filesystem type (required for consistent mount options)
FSTYPE=$($BLKID -o value -s TYPE "$SRC" 2>/dev/null || true)
if [ -z "$FSTYPE" ]; then
  $LOGGER -t "$LOG_TAG" "Skipping mount; could not detect filesystem type for $SRC"
  exit 0
fi

if mountpoint -q "$TARGET"; then
  current=$($FINDMNT -n -o SOURCE --target "$TARGET" || true)
  if [ "$current" = "$SRC" ]; then
    exit 0
  else
    $UMOUNT "$TARGET" || true
  fi
fi

opts="uid=1000,gid=1000,fmask=0022,dmask=0022,iocharset=utf8"
attempt=1
max_attempts=3
while [ "$attempt" -le "$max_attempts" ]; do
  if output=$($MOUNT -t "$FSTYPE" -o "$opts" "$SRC" "$TARGET" 2>&1); then
    $LOGGER -t "$LOG_TAG" "Mounted $SRC -> $TARGET (type=$FSTYPE, attempt=$attempt)"
    exit 0
  fi
  if output2=$($MOUNT -o "$opts" "$SRC" "$TARGET" 2>&1); then
    $LOGGER -t "$LOG_TAG" "Mounted $SRC -> $TARGET (auto type fallback, attempt=$attempt)"
    exit 0
  fi
  $LOGGER -t "$LOG_TAG" "Mount attempt $attempt failed for $SRC -> $TARGET (type=$FSTYPE): ${output:-${output2:-unknown error}}"
  attempt=$((attempt + 1))
  sleep 1
done
exit 0
EOF
chmod +x "$HELPER"

echo "[usb-auto] Writing udev rules..."
cat > "$RULE_FILE" <<EOF
# AutoEncoder USB automount
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", RUN+="/usr/local/bin/autoencoder_usb_mount.sh %k"
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ATTR{removable}=="1", RUN+="/usr/local/bin/autoencoder_usb_mount.sh %k"
ACTION=="remove", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", RUN+="/bin/umount -l ${TARGET}"
ACTION=="remove", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ATTR{removable}=="1", RUN+="/bin/umount -l ${TARGET}"
EOF

echo "[usb-auto] Reloading udev rules..."
udevadm control --reload
udevadm trigger -s block

echo "[usb-auto] USB automount configured. Plug a stick; it will mount to $TARGET"
