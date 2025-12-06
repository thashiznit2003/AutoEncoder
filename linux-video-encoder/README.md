# Linux Video Encoder (v1.15.4)

This project provides a Python-based solution for finding and encoding video files on a Linux machine using FFmpeg and HandBrakeCLI. It consists of several modules that work together to scan for video files, encode them, and provide a user-friendly interface for operation.

Logo: `assets/linux-video-encoder-icon.svg` (DVD + shrinking file motif) is used in the UI header and baked into the image.

Current release notes live in `CHANGELOG.md`. The UI header shows the running version pulled from `src/version.py`.


## Installation

To install the necessary dependencies, run:

```
sudo apt-get install -y python3 ffmpeg libdvdread4 libbluray-bdj libdvdcss2 udisks2
pip install -r requirements.txt
```

If you are working with blurays you'll need 'makemkv'. Depending on your OS you will have different [installation methods](https://makemkv.com/downloads)


## Usage

To find and encode video files, you can run the script using python

```
sudo python3 path/to/your/directory/autoencoder.py
```

This will initiate the scanning of connected video files and encode them using the specified settings in the `config.json` file.

## Docker / Portainer

You can run the app in a container (for Portainer, import the compose file below).

1. Edit `config.json` so `search_path`, `output_dir`, `rip_dir`, and `final_dir` match the host paths you will mount.
2. Build the image (Ubuntu 20.04 base with FFmpeg, HandBrakeCLI, and MakeMKV 1.18.2 baked in): `docker build -t linux-video-encoder .`
3. Start with Docker Compose: `docker compose up -d` (uses the provided `docker-compose.yml`).

Compose highlights:
- `volumes` map host paths into `/mnt/input`, `/mnt/output`, and `/mnt/ripped`. Keep `config.json` in sync with the same paths.
- `devices` maps the optical drive (`/dev/sr0`) and generic SCSI node (`/dev/sg0`) into the container for MakeMKV/HandBrakeCLI. Adjust if your device names differ.
- NVIDIA GPU: install NVIDIA drivers + NVIDIA Container Toolkit on the Ubuntu VM, pass the P600 through from Proxmox to the VM, then the container will see NVENC/NVDEC via `NVIDIA_VISIBLE_DEVICES=all`. You can also uncomment explicit `/dev/nvidia*` device mappings if desired.
- Intel GPU: uncomment the `/dev/dri` device mapping if you need Intel QuickSync (or add other GPU devices as needed).
- If you need the container to mount/unmount drives itself, add `privileged: true`; otherwise mount your media paths from the host.
- Web UI: port `5959` is exposed; open `http://<host>:5959` for the dashboard or `/settings` for HandBrake/MakeMKV/auth settings (logo served from baked `/assets` path).

### Proxmox -> Ubuntu VM -> Docker optical drive passthrough
1. In Proxmox, passthrough the SATA Blu-Ray/DVD drive to the Ubuntu VM (e.g., `qm set <VMID> -scsi1 /dev/disk/by-id/<your-drive-id>`).
2. Inside the Ubuntu VM, confirm you see the drive: `ls -l /dev/sr* /dev/sg*` and `udevadm info /dev/sr0`.
3. In `docker-compose.yml`, leave the `devices` entries for `/dev/sr0` and `/dev/sg0` (or adjust to your actual nodes).
4. Bring the stack up: `docker compose up -d`. The container will have MakeMKV 1.18.2 and HandBrakeCLI with access to the optical drive.

### Proxmox -> Ubuntu VM -> Docker NVIDIA P600 passthrough
1. In Proxmox, passthrough the P600 to the Ubuntu VM (e.g., add a PCIe passthrough device for the GPU).
2. Inside the Ubuntu VM, install the NVIDIA driver and NVIDIA Container Toolkit (`nvidia-container-toolkit`), then reboot/restart Docker.
3. Confirm GPU visibility on the host: `nvidia-smi`.
4. Use the provided `docker-compose.yml` (it sets `NVIDIA_VISIBLE_DEVICES=all` and `NVIDIA_DRIVER_CAPABILITIES=compute,video,utility`). If you prefer explicit devices, uncomment the `/dev/nvidia*` entries.
5. Start: `docker compose up -d`. FFmpeg in the image will see NVENC/NVDEC (e.g., `hevc_nvenc`, `h264_nvenc`).

### Web UI (port 5959)
- The app hosts a dashboard at `http://<host>:5959` (inside the container it binds to `0.0.0.0:5959`) plus a dedicated Settings page at `/settings`.
- Dashboard layout: active encodes, recent jobs, status messages, metrics, SMB browser, and a live log tail pulled from the application log.
- Settings page: HandBrake defaults/presets, MakeMKV options/registration/update helper, and HTTP Basic Auth credentials.
- Basic auth is enabled by default (`admin` / `changeme`); update on the Settings page and reload with the new credentials.
- Security posture: this app is intended for LAN/VPN access. Do not expose it directly to the public internet. If you want a friendly name/HTTPS, front it with a reverse proxy like Nginx Proxy Manager on your LAN and restrict direct port access.
- SMB staging: files copied via the app are allowlisted; foreign files in `/mnt/smb_staging` are removed automatically. Allowlist state is stored in a named volume (`autoencoder_state`) so it survives rebuilds.
- SMB mounts: the app uses a helper to validate SMB URLs and mount with a temporary credential file (kept in the state volume and deleted after use) to avoid leaking credentials.

### Installer script defaults
- `scripts/install_and_run.sh` defaults `REPO_URL` to your fork (`https://github.com/thashiznit2003/AutoEncoder.git`). Override with `REPO_URL=...` if needed.

### Run the installer on Ubuntu (CLI)
1. SSH into your Ubuntu VM/host.
2. Option A (no git required; curl only):
   ```bash
   curl -LO https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/install_and_run.sh
   chmod +x install_and_run.sh
   sudo ./install_and_run.sh
   ```
   - The script will download the repo tarball via curl if git is not present.
   - To use a different fork: `REPO_URL=https://github.com/<you>/<repo>.git REPO_TARBALL_URL=https://github.com/<you>/<repo>/archive/refs/heads/main.tar.gz ./install_and_run.sh`
3. Option B (if you have git):
   ```bash
   git clone https://github.com/thashiznit2003/AutoEncoder.git
   cd AutoEncoder/linux-video-encoder
   chmod +x scripts/install_and_run.sh
   ./scripts/install_and_run.sh
   ```
4. After completion, Docker will be installed (if missing), the image built, and the stack started.
5. Open `http://<host>:5959` to view the web UI.

NVIDIA Container Toolkit (offline .deb, no apt repo)
- The installer defaults `INSTALL_NVIDIA_TOOLKIT=1` and downloads the toolkit .deb packages from NVIDIA GitHub releases (default version: `1.14.3`) and installs via `dpkg`.
- If `dpkg` reports missing dependencies, set `ALLOW_APT_FIX=1` to allow a one-time `apt-get -f install` to resolve them.
- Override version with `NVIDIA_TOOLKIT_VERSION=<version>` if needed (matching filenames on https://github.com/NVIDIA/libnvidia-container/releases).

MakeMKV downloads note:
- The Dockerfile now builds MakeMKV from source tarballs. If the tarballs cannot be fetched during build, it will skip building MakeMKV and continue (FFmpeg/HandBrakeCLI will still be present). To force a specific MakeMKV version, pass `--build-arg MAKEMKV_VERSION=1.18.2` to `docker build`.

## Config

* __search_path__ - You can specify a specific directory to search if the scan doesn't find your files.
* __output_dir__ - Where your videos will be encoded to
* __rip_dir__ - Where your ripped blurays will be saved
* __final_dir__ - Where you encoded video are sent after a sucessful run. Set to null if the output_dir if where you want them to stay.
* __makemkv_minlength__ - Minimum title length (seconds) for MakeMKV to consider.
* __makemkv_titles__ - Optional comma-separated list of title numbers to rip instead of all (empty = all).
* __makemkv_audio_langs__ / __makemkv_subtitle_langs__ - Optional comma-separated language codes (e.g., `eng,fre`) to keep when ripping discs.
* __makemkv_keep_ripped__ - When true, keep the ripped MKV after encoding (and reuse existing rips if present).
* __max_threads__ - How many simulaneous encodes you want running
* __rescan_interval__ - Wait time between scans in seconds
* __min_size_mb__ - The minimum size in Megabytes for a video to be encoded
* __video_extensions__ - A list of video extensions that will be encoded
* __profile__ - The profile you want to use for encoding
* __profiles__ - These are examples created that use the ffmpeg and HandBrakeCLI commands. See their docs for other parameters.
* __auth_user__ / __auth_password__ - HTTP Basic credentials for the UI/API (set via Authentication panel).
* HandBrake audio options now include encoder (AAC/HE-AAC/Opus/AC3/E-AC3/copy), mixdown, sample rate, DRC, gain, optional language filter, track list, and “Auto Dolby” mode (copy AC3/E-AC3 else encode to E-AC3; no upmix for sub-5.1).
* MakeMKV: preferred audio/subtitle languages (default eng), commentary exclusion flag, surround preference, auto-rip toggle, disc info display, manual “Start rip” button when auto-rip is off, in-app registration key entry, and a UI update check/installed-version display with a helper command generator for host updates.
* SMB staging: `smb_staging_dir` (default /mnt/smb_staging) used for SMB browser copies; exported as Samba share `smbstaging` via installer; mounted from host `./SMBStaging` in compose. A helper script `scripts/setup_smbstaging_share.sh` can add the share and restart the stack.

### Defaults and profiles
- Default HandBrake profile: x264, RF 20, 1080p output, `.mkv`, AAC audio 128 kbps (DVD uses the same, Blu-ray uses RF 25 at 2160p).
- Profiles `ffmpeg`, `ffmpeg_nvenc`, and `ffmpeg_qsv` are sample CPU/NVIDIA/Intel QuickSync presets; pick by setting `profile` in `config.json` or via the UI.
- RF is “constant quality” (lower number = higher quality/larger file). The HandBrake UI dropdowns include approximate bitrates as a guide.

## Blu-ray drive (Proxmox passthrough)
- The VM must see the real optical drive (not a virtual “QEMU DVD-ROM”). Pass through the physical device or its controller.
- Best practice: attach the drive to a passthrough-capable SATA HBA such as an ASM1166-based 6-port card (PCIe x4/x8/x16; ODD/ATAPI friendly) and pass the entire PCIe device to the VM (`hostpci` in Proxmox).
- If the drive shares the host’s boot SATA controller, passthrough won’t expose raw SCSI commands—move the drive to the HBA or use a USB Blu-ray drive with USB passthrough.
- Proxmox checklist: enable IOMMU, identify the HBA with `lspci -nn | grep -i asm1166`, pass it with `qm set <VMID> -hostpci1 0000:XX:YY.Z,pcie=1`, remove virtual CD entries, then confirm inside the VM that `makemkvcon -r info disc:0` shows the real drive model.

## Samba shares
- Installer can optionally create SMB shares: `input` (maps to `linux-video-encoder/File`) and `output` (maps to `linux-video-encoder/Output`), prompting for SMB username/password and installing Samba if needed.
- To update an existing host from the legacy `lv_file` share, run the provided script (on the host): \
  `curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/update_samba_shares.sh -o /tmp/update_samba_shares.sh && sudo bash /tmp/update_samba_shares.sh`

## SMB browser (in UI)
- New SMB panel (above Logs): connect to `smb://server/share[/path]` with username/password, browse directories, and queue files for encoding. Mounts are temporary under `/mnt/smb`. Selected files are copied into `/mnt/input` before encoding to preserve the originals on the SMB share.

## Versioning
- Current version: 1.0.0 (defined in `src/version.py` and shown in the UI header).
- Release notes live in `CHANGELOG.md`; bump `VERSION` and append to the changelog for future updates.


## License

This project is licensed under the MIT License. See the LICENSE file for more details.
