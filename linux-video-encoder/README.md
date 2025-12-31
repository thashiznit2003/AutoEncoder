# Linux Video Encoder (v1.25.186)

Linux Video Encoder (AutoEncoder) scans local folders and discs, rips with MakeMKV, and encodes with HandBrakeCLI or FFmpeg. The web UI runs on port 5959.

- Release notes: `CHANGELOG.md`
- Third-party notices: `THIRD_PARTY_NOTICES.md`
- Version source: `src/version.py` (shown in the UI header)
- Logo: `assets/linux-video-encoder-icon.svg`
- This application was entirely Vibe-Coded with ChatGPT Codex.

## Prerequisites

### Docker host (recommended)
- Ubuntu 20.04+ or similar Linux.
- Docker Engine + Docker Compose plugin.
- Optical drive passthrough (e.g., `/dev/sr0` and `/dev/sgX`) if ripping discs.
- Host storage for bind mounts under `/linux-video-encoder/AutoEncoder/linux-video-encoder`.
- Optional GPU: NVIDIA Container Toolkit for NVENC; Intel QuickSync uses `/dev/dri`.
- `curl` and `tar` for helper scripts (git optional).

### Bare metal (advanced / unsupported)
- `python3`, `ffmpeg`, `handbrake-cli`, `makemkv`, `cifs-utils`, `udev`, `sg3-utils`.
- `pip install -r ../txt/requirements.txt`

## Install paths

### 1) Docker Hub image (no MakeMKV)
Use this if you only need to encode files and do not need disc ripping.
- Compose: `dockerhub/docker-compose.yml` (image `thashiznit2003/autoencoder:beta`).

### 2) Docker Hub + MakeMKV overlay (recommended for ripping)
Build a local image that layers MakeMKV on top of the public Docker Hub image.
- Build script: `dockerhub/with-makemkv/build_with_makemkv.sh` (downloads MakeMKV tarballs from makemkv.com).
- Compose: `dockerhub/with-makemkv/docker-compose.yml` (non-dev).
- Resulting image tag: `linux-video-encoder:latest`.

### 3) Local/Portainer build (from source)
Full local build using the repo Dockerfile.
- Requires MakeMKV tarballs in the repo root: `makemkv-oss-<ver>.tar.gz` and `makemkv-bin-<ver>.tar.gz`.
- Portainer stack: `portainer/docker-compose.yml` (see `portainer/README.md`).

## Helper apps (host-side)
These are optional but strongly recommended for reliable USB and optical behavior.

- USB host helper (`autoencoder-usb-helper.service`)
  - Listens on `0.0.0.0:8765` and mounts/unmounts USB media when the UI requests a refresh.
  - Default mountpoint: `/linux-video-encoder/AutoEncoder/linux-video-encoder/USB`.
  - Env overrides: `HELPER_LISTEN_ADDR`, `HELPER_LISTEN_PORT`, `HELPER_MOUNTPOINT`.
- Optical host helper (`autoencoder-optical-helper.service`)
  - Listens on `0.0.0.0:8767` and reports optical drive presence and mapping.
  - Env overrides: `OPTICAL_HELPER_LISTEN_ADDR`, `OPTICAL_HELPER_LISTEN_PORT`.
- USB automount helper
  - udev rule + script that mounts USB drives to the USB folder automatically.
- SMB mount helper (container-side)
  - `necessary-scripts/mount_smb_helper.py` mounts SMB shares for the UI SMB browser using temp credentials and an allowlist.

The host setup scripts install the helpers and systemd services:
- `necessary-scripts/host_setup_portainer.sh`
- `necessary-scripts/install_and_run.sh`

Compose files include a `host.docker.internal` mapping so the container can reach the host helpers.

## Compose files
- `dockerhub/docker-compose.yml`: public Docker Hub image (no MakeMKV).
- `dockerhub/with-makemkv/docker-compose.yml`: local MakeMKV overlay image (non-dev).
- `linux-video-encoder/docker-compose.yml`: local build from source (includes optional dev bind mounts).
- `portainer/docker-compose.yml`: Portainer stack for local images.

## Web UI
- Dashboard: `http://<host>:5959`
- Settings: `http://<host>:5959/settings`
- Basic auth defaults: `admin` / `changeme` (update in Settings).

## Data paths and staging
- USB: mount to `/mnt/usb`; files are copied into `/mnt/usb_staging` before encoding so originals remain untouched.
- SMB staging: UI copies into `/mnt/smb_staging` with an allowlist; originals stay on the share.
- State volume: `/var/lib/autoencoder/state` stores config, allowlists, and history.

## MakeMKV notes
- MakeMKV cannot be redistributed, so only local builds or overlays include it.
- CSS/region-protected DVDs require a drive that matches the disc region or a region-free drive/firmware.

## Config (config.json)
- `search_path`: optional override for scan roots.
- `output_dir`: encoded output.
- `rip_dir`: MakeMKV output.
- `final_dir`: optional move destination after encode.
- `makemkv_minlength`: minimum title length in seconds.
- `makemkv_titles`: list of title IDs to rip (empty = auto).
- `makemkv_audio_langs` / `makemkv_subtitle_langs`: language filters.
- `makemkv_keep_ripped`: keep MKV after encode.
- `profile`: `handbrake`, `handbrake_dvd`, `handbrake_br`, `ffmpeg`, `ffmpeg_nvenc`, `ffmpeg_qsv`.

## License
MIT. See `LICENSE`.
