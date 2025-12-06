# Changelog

## 1.15.0 - 2025-12-04
- Added SMB staging allowlist: only files copied via the app are permitted in `/mnt/smb_staging`; foreign files are removed, and the allowlist persists in a named volume (`autoencoder_state`).

## 1.15.1 - 2025-12-04
- Fixed circular import crash by moving SMB allowlist helpers into a dedicated module.

## 1.15.2 - 2025-12-04
- Added SMB mount helper with validation and credential-file handling; web app now calls the helper (no shell), and creds are kept out of logs. Staging allowlist unchanged.

## 1.15.3 - 2025-12-06
- Fix: SMB mount now imports sys and logs sanitized mount failures instead of returning empty 400s.

## 1.15.4 - 2025-12-06
- SMB mount helper now strips trailing slashes from UNC roots and returns sanitized diagnostics (UNC/options, no creds) to help troubleshoot mount error(22) cases.

## 1.15.5 - 2025-12-06
- SMB mount helper now normalizes paths more strictly and retries with SMB versions 3.0 → 2.1 → 2.0 to avoid mount error(22) defaults.

## 1.15.6 - 2025-12-06
- Fixed SMB UNC normalization to avoid double slashes in paths and fixed SMB unmount when mount entries include labels.

## 1.15.7 - 2025-12-06
- SMB mount helper now allows parentheses in paths (removed them from the disallowed character set).

## 1.14.5 - 2025-12-04
- Added documentation that the UI is intended for LAN/VPN use and should not be exposed directly to the public internet; recommend accessing via a LAN reverse proxy (e.g., Nginx Proxy Manager).

## 1.14.4 - 2025-12-04
- Enlarged the header icon to better fill the top bar.

## 1.14.3 - 2025-12-04
- Swapped header logo to the updated `linux-video-encoder-icon.svg`, baked into the image (assets now copied in Dockerfile; compose bind removed).

## 1.14.2 - 2025-12-04
- Added the new SVG logo to the dashboard and settings headers; static assets are now served from `/assets` and mounted via compose.

## 1.14.1 - 2025-12-04
- Added a lightweight SVG logo (DVD + shrinking file motif) at `assets/logo.svg` for branding use.

## 1.14.0 - 2025-12-04
- Split UI into a main dashboard and a dedicated `/settings` page for HandBrake, MakeMKV, and Authentication panels (Settings link in header).
- Web server now serves templates from `src/templates.py` so the settings layout stays separate from the main status view.

## 1.9.0 - 2025-12-04
- Added SMB staging path (default /mnt/smb_staging) for SMB browser copies plus Samba share `smbstaging`; installer now provisions the share and compose mounts ./SMBStaging.
- SMB queue now respects the configurable staging path instead of hardcoding /mnt/input.
- Added helper script `scripts/setup_smbstaging_share.sh` to create the smbstaging share and restart the stack.

## 1.9.1 - 2025-12-04
- SMB browser copies now log as staged and the scanner includes the staging path so staged files are picked up.

## 1.9.2 - 2025-12-04
- SMB connect now responds to Enter within the SMB form; mount list shows the share name (last path segment) instead of the UUID.
- Status Messages wrap long lines to avoid horizontal scrolling.

## 1.9.3 - 2025-12-04
- SMB mounts now carry a readable label derived from the share path (instead of the UUID) and are displayed accordingly in the UI.

## 1.9.4 - 2025-12-04
- Fix: SMB listing/queue now handles labeled mounts correctly so share contents show up again.

## 1.10.0 - 2025-12-04
- Added MakeMKV registration input/button; backend endpoint calls `makemkvcon reg` and logs success/failure.

## 1.10.1 - 2025-12-04
- MakeMKV registration now also writes the key to settings.conf as a fallback when makemkvcon reg returns an error, and reports the underlying error/warning.

## 1.10.2 - 2025-12-04
- MakeMKV registration now always reports failure on non-zero makemkvcon exit (still writes key to settings.conf for persistence), avoiding false-success messages.

## 1.10.3 - 2025-12-04
- MakeMKV registration failure messages now include stderr/stdout and exit code for clearer diagnostics in Status Messages.

## 1.10.4 - 2025-12-04
- MakeMKV registration now strips surrounding quotes from pasted keys to avoid invalid key errors.

## 1.11.0 - 2025-12-04
- MakeMKV update check endpoint/button added (runs makemkvcon --update and surfaces the message in UI).
- Added host-side helper script `scripts/update_makemkv.sh` to rebuild/restart with a chosen MakeMKV version.

## 1.11.1 - 2025-12-04
- Fix: update check now uses makemkvcon --version (since --update isn’t supported) and UI button label clarified.

## 1.11.2 - 2025-12-04
- Fix: MakeMKV update check now uses a version-bearing info call (avoids unsupported flags) and still surfaces stdout/stderr.

## 1.11.3 - 2025-12-04
- MakeMKV update check now surfaces only the version line (truncates noisy output) for a clearer status message.

## 1.12.0 - 2025-12-04
- MakeMKV panel now shows the installed version, lets you enter the latest version from makemkv.com, and generates a host update command accordingly; update check parses version line instead of dumping full output.

## 1.12.1 - 2025-12-04
- MakeMKV update check UI now only reports “installed version checked” (drops noisy makemkvcon messages).

## 1.12.2 - 2025-12-04
- Added copy button for the host MakeMKV update command in the MakeMKV panel.

## 1.13.0 - 2025-12-04
- Added HTTP Basic auth for UI/API (configurable user/pass) with an Authentication panel to update credentials.

## 1.13.1 - 2025-12-04
- Added chat5.txt transition notes for next chat (summaries, preferences, pending UI split).
## 1.8.0 - 2025-12-04
- MakeMKV: added disc detection info fetch, configurable preferred audio/subtitle languages (default eng), commentary exclusion flag, surround preference, and auto-rip toggle.
- UI now shows disc status/info with a manual "Start rip" button when auto-rip is off; rip requests trigger on next scan.
- Rip flow uses preferred language lists when explicit lists are unset.

## 1.8.1 - 2025-12-04
- Fix: resolved an indentation error in autoencoder.py that caused container restart loops.

## 1.8.2 - 2025-12-04
- Fix: /api/config no longer crashes when HandBrake payload is omitted (guarded missing dict keys).

## 1.8.3 - 2025-12-04
- MakeMKV Save now posts a “settings saved” event and alert so the change is visible in Status Messages.

## 1.7.1 - 2025-12-04
- Clarified in the HandBrake UI that Audio mode overrides the Audio encoder when set.

## 1.7.0 - 2025-12-04
- Added HandBrake "Auto Dolby" audio mode: copy AC3/E-AC3 (all channel counts) and re-encode other codecs to E-AC3 (no upmix for sub-5.1 sources). UI option added alongside existing modes.

## 1.6.0 - 2025-12-04
- HandBrake audio controls expanded: encoder choice (AAC/HE-AAC/Opus/AC3/E-AC3/copy), mixdown, sample rate, DRC, gain, language filter, and track list; all wired into config, presets, and UI.

## 1.5.0 - 2025-12-04
- MakeMKV now supports per-rip title selection plus audio/subtitle language filters; UI fields added for titles and language codes.
- Added option to keep ripped MKVs after encoding (or reuse an existing rip instead of failing).
- Config fields normalized for MakeMKV titles/language/keep flags; rip events include selected options.

## 1.0.0 - 2025-12-04
- Stable release of Linux Video Encoder with web UI (active encodes, recent jobs, logs, metrics, HandBrake/MakeMKV settings).
- Improved progress/ETA parsing for HandBrake output; Stop button wired to active job keys.
- Scanner avoids /mnt/output, temp “._*” files, and system paths; auto-mounts removable media with exfat support.
- Output naming reuses source names with collision suffixes; source is deleted after successful encode; Blu-ray ripping via MakeMKV supported.
- Docker Compose binds config/media dirs, runs privileged with optical devices and NVIDIA runtime; config persisted via /api/config.

## 1.0.1 - 2025-12-04
- Added Blu-ray passthrough notes for Proxmox: require real drive exposure (no virtual QEMU CD), recommend ASM1166 HBA, and documented IOMMU/hostpci steps.

## 1.0.2 - 2025-12-04
- Installer now prompts to install the NVIDIA Container Toolkit and runs the bundled pinned helper when accepted (avoids failing stock apt flow).

## 1.0.3 - 2025-12-04
- NVIDIA toolkit prompt moved to the end of the installer; if selected, installs via the bundled helper after the stack is up and restarts the stack so Docker picks up the NVIDIA runtime.

## 1.0.4 - 2025-12-04
- Installer now optionally sets up Samba shares for lv_file and output (prompts for yes/no and SMB username/password; installs samba if missing) before the NVIDIA prompt.

## 1.0.5 - 2025-12-04
- Renamed Samba share to `input` (from `lv_file`) across installer/scripts; optional Samba setup now provisions `input` and `output`.
- Added `scripts/update_samba_shares.sh` to migrate existing hosts (removes legacy `lv_file`, prompts for SMB user/password).

## 1.0.6 - 2025-12-04
- Installer now prints the detected host IP (best effort) for the UI URL after the stack starts.

## 1.1.0 - 2025-12-04
- Added optional SMB browser panel (connect with URL/user/pass, browse mounts, queue files) before Logs.
- Backend supports SMB mount/list/unmount/queue via new APIs; manual queued files are processed by the main loop.
- Docker image now includes cifs-utils; SMB mount root at /mnt/smb tracked via StatusTracker.

## 1.1.1 - 2025-12-04
- SMB queue now copies the selected file into `/mnt/input` (preserves the source on the SMB share) and queues the local copy for encoding.

## 1.1.2 - 2025-12-04
- Encoding now runs one file at a time (FIFO), ignoring configured max_threads to avoid concurrent encodes.

## 1.1.3 - 2025-12-04
- Active list now shows queued jobs; jobs start as `queued` then move to `running`.
- Manual stop marks jobs as `canceled` and adds a Clear Canceled button in Recent Jobs; badges added for queued/canceled.

## 1.1.4 - 2025-12-04
- Fix: queued jobs now retain their eta/progress keys in snapshots (ensuring Active Encodes shows queued items reliably).

## 1.1.5 - 2025-12-04
- Stop API now honors delete_source and removes the source file when cancellation requests deletion.

## 1.1.6 - 2025-12-04
- Pre-register queued files into Active with a queued state and destination hint so they show up immediately while waiting.

## 1.1.7 - 2025-12-04
- Prevent fallback/success entries after user cancellation; honor delete-source during stop; queued pre-registration avoids duplicates.

## 1.1.8 - 2025-12-04
- SMB mount normalization now escapes spaces (`\040`) so shares/paths with multiple spaces connect correctly.

## 1.1.9 - 2025-12-04
- SMB URL normalization rolled back to avoid breaking mounts with spaces (subprocess arg list handles spaces without escaping).

## 1.2.0 - 2025-12-04
- UI polish with icons/gradients/panel styling while keeping layout; badges updated for queued/canceled; header branding tweaked.

## 1.2.1 - 2025-12-04
- Logs copy button now falls back to a hidden textarea when `navigator.clipboard` is unavailable.

## 1.2.2 - 2025-12-04
- Scanner now skips system paths (`/linux-video-encoder/src`, `/mnt/auto_media`) and avoids auto-mounting common system block devices (sd*/nvme*/vd*/dm*), reducing noisy mounts like /dev/sda1.

## 1.2.3 - 2025-12-04
- Added recommendations.txt to track future feature ideas (queue controls, presets, SMB staging, filters, MakeMKV options, etc.).

## 1.3.0 - 2025-12-04
- UI/Backend: HandBrake presets (save/load/delete) persisted in config; UI controls added.
- Audio/Subtitles: New options to include all audio tracks and copy/burn subtitles (none/copy-all/burn forced).
- Version bumped to 1.3.0.

## 1.3.1 - 2025-12-04
- Low-bitrate guard: jobs with source bitrate below target now require user confirmation (Proceed/Cancel) in Active; cancel stops without success entry.

## 1.3.2 - 2025-12-04
- Confirmation loop fix: proceeding marks the job as allowed (no repeat warning) and resumes queue; cancel clears confirm flags.

## 1.3.3 - 2025-12-04
- Added interim `starting` state between queued and running to avoid apparent freezes after proceeding from low-bitrate warnings; badge added.

## 1.3.4 - 2025-12-04
- Proceed now immediately marks jobs as `starting` (instead of queued) after low-bitrate confirmation to make state change visible.

## 1.4.0 - 2025-12-04
- Added target bitrate options (High/Med/Low/custom) with optional two-pass; when set, overrides RF.
- Presets now include bitrate/two-pass settings; UI fields for bitrate ladder and two-pass.
- Low-bitrate check uses explicit target bitrate when provided.

## 1.4.1 - 2025-12-04
- Expanded bitrate ladder to 500–8000 kbps in 500 kbps steps (plus custom).

## 1.4.2 - 2025-12-04
- Added chat4.txt transition doc summarizing app state, preferences, and next steps.

## 1.4.3 - 2025-12-04
- Updated chat4.txt with explicit versioning rules (patch/minor/major per user policy).
