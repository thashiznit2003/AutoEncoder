from flask import Flask, jsonify, Response, request
import time
import json
import subprocess
import os
import sys
from version import VERSION
import uuid
import pathlib
from pathlib import Path
import shutil
from functools import wraps
import logging
from templates import MAIN_PAGE_TEMPLATE, SETTINGS_PAGE_TEMPLATE
from smb_allowlist import save_smb_allowlist, load_smb_allowlist, remove_from_allowlist
from makemkv_parser import parse_makemkv_info_output

SMB_MOUNT_ROOT = pathlib.Path("/mnt/smb")
ASSETS_ROOT = pathlib.Path("/linux-video-encoder/assets")
DIAG_REPO_URL = os.environ.get("DIAG_REPO_URL", "https://github.com/thashiznit2003/AutoEncoder-Diagnostics.git")
DIAG_REPO_PATH = pathlib.Path(os.environ.get("DIAG_REPO_PATH", "/var/lib/autoencoder/state/diagnostics-repo"))
DIAG_CRED_FILE = pathlib.Path("/var/lib/autoencoder/state/git/credentials")
DIAG_GIT_NAME = os.environ.get("DIAG_GIT_NAME", "Diagnostics Bot")
DIAG_GIT_EMAIL = os.environ.get("DIAG_GIT_EMAIL", "diagnostics@example.com")
STATE_ROOT = Path(os.environ.get("AE_STATE_DIR", "/var/lib/autoencoder/state"))
TIMING_PATH = STATE_ROOT / "timing.log"
MAKEMKV_TIMEOUT_EVENT_TS = 0.0

def log_timing(label: str, started_at: float, extra: str = ""):
    """Append simple timing entries for diagnostics, ignore failures."""
    try:
        dur = time.time() - started_at
        TIMING_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TIMING_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {label} {dur:.3f}s {extra}\n")
    except Exception:
        pass
STATE_ROOT = Path(os.environ.get("AE_STATE_DIR", "/var/lib/autoencoder/state"))
TIMING_PATH = STATE_ROOT / "timing.log"

HTML_PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Linux Video Encoder v__VERSION__</title>
  <style>
    :root { color-scheme: dark; font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: radial-gradient(circle at 18% 20%, rgba(59,130,246,0.12), transparent 40%), radial-gradient(circle at 80% 10%, rgba(94,234,212,0.12), transparent 32%), #0b1220; color: #e2e8f0; }
    header { padding: 14px 16px; background: linear-gradient(120deg, #0f172a, #0c1425); border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 28px rgba(0,0,0,0.35); }
    h1 { font-size: 18px; margin: 0; letter-spacing: 0.3px; display:flex; align-items:center; gap:10px; }
    .logo-dot { width: 10px; height: 10px; border-radius: 50%; background: linear-gradient(135deg,#60a5fa,#a78bfa); box-shadow: 0 0 10px rgba(96,165,250,0.8); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: linear-gradient(145deg, #111827, #0d1528); border: 1px solid #1f2937; border-radius: 14px; padding: 12px; box-shadow: 0 16px 38px rgba(0,0,0,0.35), inset 0 0 0 1px rgba(255,255,255,0.03); }
    .panel h2 { margin: 0 0 10px 0; font-size: 15px; color: #a5b4fc; letter-spacing: 0.4px; display:flex; align-items:center; gap:8px; }
    form { display: grid; gap: 8px; margin-top: 8px; }
    label { font-size: 12px; color: #cbd5e1; display: grid; gap: 4px; }
    input, select { padding: 9px 11px; border-radius: 10px; border: 1px solid #1f2937; background: #0b1220; color: #e2e8f0; transition: border 0.2s ease, box-shadow 0.2s ease; }
    input:focus, select:focus { outline: none; border-color: #60a5fa; box-shadow: 0 0 0 1px rgba(96,165,250,0.5); }
    button { padding: 9px 12px; border: 0; border-radius: 10px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; font-weight: 700; cursor: pointer; transition: transform 0.08s ease, box-shadow 0.2s; }
    button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(79,70,229,0.35); }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 12px; padding: 10px; overflow: auto; height: 320px; border: 1px solid #1f2937; white-space: pre-wrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .log { word-break: break-word; overflow-wrap: anywhere; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; color: #0f172a; font-weight: 700; }
    .badge.running { background: #fde047; }
    .badge.starting { background: #fb923c; color:#0b1220; }
    .badge.success { background: #34d399; }
    .badge.error { background: #f87171; }
    .badge.queued { background: #60a5fa; color: #0b1220; }
    .badge.canceled { background: #cbd5e1; color: #0b1220; }
    .progress { background: #1f2937; border-radius: 8px; height: 9px; overflow: hidden; margin-top: 6px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .progress-bar { background: linear-gradient(90deg, #22c55e, #4ade80); height: 100%; transition: width 0.2s ease; }
    .item { padding: 9px; border-bottom: 1px solid #1f2937; }
    .item:last-child { border-bottom: 0; }
    .muted { color: #94a3b8; }
    .flex-between { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .path { word-break: break-all; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 6px; }
    .metric-card { background: rgba(255,255,255,0.03); border: 1px solid #1f2937; border-radius: 10px; padding: 6px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03); }
    .metric-label { font-size: 10px; color: #8ea0bd; text-transform: uppercase; letter-spacing: 0.8px; display: flex; align-items: center; gap: 6px; }
    .metric-value { font-size: 13px; font-weight: 700; color: #e5edff; margin-top: 2px; font-family: Arial, "Helvetica Neue", sans-serif; }
    .smb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
    .smb-list { max-height: 220px; overflow-y: auto; border: 1px solid #1f2937; border-radius: 10px; padding: 8px; background: #0b1220; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .smb-item { padding: 6px 0; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .smb-item:last-child { border-bottom: 0; }
    .smb-btn { padding: 7px 10px; border: 0; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; cursor: pointer; }
    .smb-path { word-break: break-all; flex: 1; }
    .icon { width: 16px; height: 16px; display:inline-block; }
  </style>
</head>
<body>
  <header>
    <h1><span class="logo-dot"></span> Linux Video Encoder v__VERSION__</h1>
    <div style="display:flex; gap:10px; align-items:center;">
      <button onclick="window.location.reload(true)">Hard Reload</button>
      <div id="clock" class="muted"></div>
    </div>
    <div class="panel">
      <h2>🔒 Authentication</h2>
      <div class="muted" style="margin-bottom:6px;">HTTP Basic auth for this UI/API.</div>
      <label>Username <input id="auth-user" placeholder="admin" /></label>
      <label>Password <input id="auth-pass" type="password" placeholder="changeme" /></label>
      <button type="button" id="auth-save">Save Auth</button>
      <div class="muted" style="margin-top:6px;">After changing, reload the page and use the new credentials.</div>
    </div>
  </header>
    <div class="grid">
      <div class="panel">
        <h2>🟢 Active Encodes</h2>
        <div class="muted" id="hb-runtime"></div>
        <div id="active"></div>
      </div>
      <div class="panel">
        <h2>📊 System Metrics</h2>
        <div id="metrics" class="log"></div>
        <div class="metric-grid" style="margin-top:8px;">
          <div class="metric-card">
            <div class="metric-icon">📀</div>
            <div class="metric-text">
              <div class="metric-value" style="display:flex; align-items:center; gap:6px;">
                <span id="disc-card-light" style="width:10px;height:10px;border-radius:50%;display:inline-block;background:#ef4444;"></span>
                <span id="disc-card-label">Disc: unknown</span>
              </div>
              <div class="metric-label" id="disc-card-info" style="margin-top:4px;">No disc info.</div>
              <button id="disc-card-eject" class="smb-btn" style="margin-top:6px;">Eject</button>
            </div>
          </div>
        </div>
        <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
          <button id="usb-force-remount" type="button">Force Remount</button>
          <button id="usb-refresh" type="button">Refresh USB</button>
          <div id="usb-status" class="muted">USB status: unknown</div>
        </div>
      </div>
      <div class="panel">
        <h2>🕒 Recent Jobs</h2>
        <div id="recent" style="max-height: 260px; overflow-y: auto;"></div>
        <div style="margin-top:8px; display:flex; gap:6px; flex-wrap: wrap;">
          <button data-clear="success" class="clear-btn">Clear Success</button>
        <button data-clear="error" class="clear-btn">Clear Error</button>
        <button data-clear="running" class="clear-btn">Clear Running</button>
        <button data-clear="canceled" class="clear-btn">Clear Canceled</button>
        <button data-clear="all" class="clear-btn">Clear All</button>
      </div>
    </div>
    <div class="panel">
      <h2>📣 Status Messages</h2>
      <div id="events" class="log"></div>
    </div>
    <div class="panel">
      <h2>🌐 SMB Browser</h2>
      <form id="smb-form" style="display:grid; gap:6px;">
        <input id="smb-url" placeholder="smb://server/share[/path]" />
        <input id="smb-user" placeholder="Username" />
        <input id="smb-pass" placeholder="Password" type="password" />
        <button type="button" id="smb-connect">Connect</button>
      </form>
      <div class="smb-grid" style="margin-top:8px;">
        <div>
          <div class="muted">Mounts</div>
          <div id="smb-mounts" class="smb-list"></div>
        </div>
        <div>
          <div class="muted">Browse</div>
          <div id="smb-browse" class="smb-list"></div>
        </div>
      </div>
      <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
        <input id="smb-current-path" readonly placeholder="Path" style="flex:1;"/>
        <button class="smb-btn" id="smb-up">Up</button>
      </div>
      <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
        <button class="smb-btn" id="smb-queue">Queue selected for encode</button>
        <button class="smb-btn" id="smb-refresh">Refresh</button>
      </div>
    </div>
    <div class="panel">
      <h2>🎛️ HandBrake Settings</h2>
      <div class="muted" id="hb-summary" style="margin-bottom:6px;"></div>
      <form id="handbrake-form">
        <label>Default encoder
          <select id="hb-encoder" name="encoder">
            <option value="x264">x264</option>
            <option value="x265">x265</option>
            <option value="qsv_h264">qsv_h264</option>
            <option value="qsv_h265">qsv_h265</option>
            <option value="nvenc_h264">nvenc_h264</option>
            <option value="nvenc_h265">nvenc_h265</option>
          </select>
        </label>
        <label>Default quality (constant quality RF, lower = higher quality)
          <select id="hb-quality" name="quality">
            <option value="16">RF 16 (~4000 kbps)</option>
            <option value="18">RF 18 (~3500 kbps)</option>
            <option value="20">RF 20 (~3000 kbps)</option>
            <option value="22">RF 22 (~2500 kbps)</option>
            <option value="24">RF 24 (~2000 kbps)</option>
            <option value="25">RF 25 (~1750 kbps)</option>
            <option value="26">RF 26 (~1500 kbps)</option>
            <option value="28">RF 28 (~1200 kbps)</option>
            <option value="30">RF 30 (~1000 kbps)</option>
          </select>
        </label>
        <label>Target bitrate (overrides RF when set)
          <select id="hb-bitrate">
            <option value="">None (use RF)</option>
            <option value="500">500 kbps</option>
            <option value="1000">1000 kbps</option>
            <option value="1500">1500 kbps</option>
            <option value="2000">2000 kbps</option>
            <option value="2500">Low ~2500 kbps</option>
            <option value="3000">3000 kbps</option>
            <option value="3500">3500 kbps</option>
            <option value="4000">4000 kbps</option>
            <option value="4500">4500 kbps</option>
            <option value="5000">Medium ~5000 kbps</option>
            <option value="5500">5500 kbps</option>
            <option value="6000">6000 kbps</option>
            <option value="6500">6500 kbps</option>
            <option value="7000">7000 kbps</option>
            <option value="7500">7500 kbps</option>
            <option value="8000">High ~8000 kbps</option>
            <option value="custom">Custom (enter below)</option>
          </select>
          <input id="hb-bitrate-custom" placeholder="Custom kbps" type="number" min="500" step="100" />
          <label style="display:flex; align-items:center; gap:6px;">
            <input type="checkbox" id="hb-two-pass" /> Two-pass when bitrate set
          </label>
        </label>
        <label>Audio tracks
          <select id="hb-audio-all">
            <option value="false">First track</option>
            <option value="true">All audio tracks</option>
          </select>
        </label>
        <label>Audio encoder (when encoding)
          <select id="hb-audio-encoder" name="audio_encoder">
            <option value="av_aac">AAC (av_aac)</option>
            <option value="av_aac_he">AAC HE</option>
            <option value="opus">Opus</option>
            <option value="ac3">AC3</option>
            <option value="eac3">E-AC3</option>
            <option value="copy">Copy (passthrough)</option>
          </select>
        </label>
        <label>Mixdown
          <select id="hb-audio-mix">
            <option value="">Auto</option>
            <option value="stereo">Stereo</option>
            <option value="dpl2">Dolby Surround</option>
            <option value="5point1">5.1</option>
            <option value="7point1">7.1</option>
          </select>
        </label>
        <label>Sample rate
          <select id="hb-audio-rate">
            <option value="">Auto</option>
            <option value="44100">44.1 kHz</option>
            <option value="48000">48 kHz</option>
          </select>
        </label>
        <label>DRC (0-4)
          <input id="hb-audio-drc" type="number" min="0" max="4" step="0.5" placeholder="0 (off)" />
        </label>
        <label>Gain (dB)
          <input id="hb-audio-gain" type="number" step="0.5" placeholder="0" />
        </label>
        <label>Language filter (comma codes, e.g., eng,fre)
          <input id="hb-audio-lang" placeholder="eng,fre" />
        </label>
        <label>Track list (comma indexes, blank=auto)
          <input id="hb-audio-tracks" placeholder="1,2" />
        </label>
        <label>DVD quality (constant quality RF, lower = higher quality)
          <select id="hb-dvd-quality" name="quality_dvd">
            <option value="16">RF 16 (~4000 kbps)</option>
            <option value="18">RF 18 (~3500 kbps)</option>
            <option value="20">RF 20 (~3000 kbps)</option>
            <option value="22">RF 22 (~2500 kbps)</option>
            <option value="24">RF 24 (~2000 kbps)</option>
            <option value="25">RF 25 (~1750 kbps)</option>
            <option value="26">RF 26 (~1500 kbps)</option>
            <option value="28">RF 28 (~1200 kbps)</option>
            <option value="30">RF 30 (~1000 kbps)</option>
          </select>
        </label>
        <label>Blu-ray quality (constant quality RF, lower = higher quality)
          <select id="hb-br-quality" name="quality_br">
            <option value="16">RF 16 (~4000 kbps)</option>
            <option value="18">RF 18 (~3500 kbps)</option>
            <option value="20">RF 20 (~3000 kbps)</option>
            <option value="22">RF 22 (~2500 kbps)</option>
            <option value="24">RF 24 (~2000 kbps)</option>
            <option value="25">RF 25 (~1750 kbps)</option>
            <option value="26">RF 26 (~1500 kbps)</option>
            <option value="28">RF 28 (~1200 kbps)</option>
            <option value="30">RF 30 (~1000 kbps)</option>
          </select>
        </label>
        <label>Output extension
          <select id="hb-ext" name="extension">
            <option value=".mkv">.mkv</option>
            <option value=".mp4">.mp4</option>
            <option value=".m4v">.m4v</option>
          </select>
        </label>
        <label>Subtitles
          <select id="hb-subs">
            <option value="none">None</option>
            <option value="copy_all">Copy all subtitles</option>
            <option value="burn_forced">Burn forced (first track)</option>
          </select>
        </label>
        <label>Audio mode (overrides Audio encoder when set)
          <select id="hb-audio-mode" name="audio_mode">
            <option value="encode">Encode (AAC)</option>
            <option value="copy">Copy original</option>
            <option value="auto_dolby">Auto Dolby (copy AC3/E-AC3; else E-AC3)</option>
          </select>
        </label>
        <label>Audio bitrate (if encoding)
          <select id="hb-audio-bitrate" name="audio_bitrate_kbps">
            <option value="128">128 kbps</option>
            <option value="160">160 kbps</option>
            <option value="192">192 kbps</option>
            <option value="256">256 kbps</option>
            <option value="320">320 kbps</option>
          </select>
        </label>
        <button type="button" id="hb-save">Save HandBrake</button>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-top:4px;">
          <select id="hb-preset-select" style="flex:1;">
            <option value="">Load preset...</option>
          </select>
          <input id="hb-preset-name" placeholder="Preset name" style="flex:1;"/>
          <button type="button" id="hb-preset-save">Save Preset</button>
          <button type="button" id="hb-preset-delete">Delete Preset</button>
        </div>
        <div class="muted">Applies: Default for regular files, DVD for VIDEO_TS, BR for BDMV/STREAM.</div>
      </form>
    </div>
    <div class="panel">
      <h2>📀 MakeMKV Settings</h2>
      <form id="makemkv-form">
        <label>Rip directory <input id="mk-ripdir" name="rip_dir" /></label>
        <label>Min title length (seconds) <input id="mk-minlen" name="min_length" type="number" step="60" /></label>
        <label>Titles to rip (comma-separated, blank = all) <input id="mk-titles" name="titles" placeholder="e.g. 0,1,2" /></label>
        <label>Audio languages to keep (comma codes, blank = all) <input id="mk-audio-langs" name="audio_langs" placeholder="e.g. eng,fre,jpn" /></label>
        <label>Subtitle languages to keep (comma codes, blank = all) <input id="mk-sub-langs" name="subtitle_langs" placeholder="e.g. eng,spa" /></label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-keep" /> Keep ripped MKVs after encode
        </label>
        <label>Preferred audio language(s) <input id="mk-pref-audio" placeholder="eng" /></label>
        <label>Preferred subtitle language(s) <input id="mk-pref-sub" placeholder="eng" /></label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-exclude-commentary" /> Exclude commentary tracks when choosing
        </label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-prefer-surround" /> Prefer surround audio (5.1+) when available
        </label>
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="mk-auto-rip" /> Auto-start rip when disc detected
        </label>
        <button type="button" id="mk-save">Save MakeMKV</button>
      </form>
      <div style="margin-top:8px;">
        <div class="muted" id="mk-disc-status">Disc status: unknown</div>
        <div style="display:flex; gap:6px; align-items:center; margin:6px 0; flex-wrap:wrap;">
          <span id="mk-disc-light" style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;" aria-label="disc-present-indicator"></span>
          <button type="button" id="mk-refresh-info">Refresh disc info</button>
          <button type="button" id="mk-start-rip">Start rip</button>
          <button type="button" id="mk-stop-rip">Stop rip</button>
          <button type="button" id="mk-eject">Eject</button>
        </div>
        <textarea id="mk-info" class="log" style="height:160px; margin-top:4px;" readonly placeholder="Disc info will appear here after detection."></textarea>
      </div>
      <div style="margin-top:8px; display:grid; gap:6px;">
        <label>MakeMKV registration key (paste monthly key)
          <input id="mk-key" placeholder="T-XXXX-..." />
        </label>
        <button type="button" id="mk-register">Register MakeMKV</button>
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
          <button type="button" id="mk-update-check">Check for MakeMKV update</button>
          <span class="muted" id="mk-update-status">Update status: unknown</span>
        </div>
        <div class="muted">Installed MakeMKV: <span id="mk-installed">unknown</span></div>
        <label>Latest MakeMKV version (from makemkv.com)
          <input id="mk-latest" placeholder="e.g., 1.18.3" />
        </label>
        <label>Host update command (run on Ubuntu host)
          <textarea id="mk-update-cmd" class="log" style="height:70px;" readonly></textarea>
          <button type="button" id="mk-copy-update">Copy update command</button>
        </label>
      </div>
    </div>
    <div class="panel" style="grid-column: 1 / -1;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px; justify-content: space-between;">
        <h2 style="margin:0;">🧾 Logs</h2>
        <button id="copy-logs" style="padding:6px 10px; background:#2563eb; color:#fff; border:0; border-radius:6px; cursor:pointer;">Copy last 300</button>
      </div>
      <div id="logs" class="log"></div>
    </div>
  </div>
  <script>
    let hbDirty = false;
    let mkDirty = false;
    let authDirty = false;
    loadPresets();
    const smbForm = document.getElementById("smb-form");
    function connectSmb() {
      document.getElementById("smb-connect").click();
    }

    async function fetchJSON(url, opts) {
      const res = await fetch(url, opts);
      return res.json();
    }

    async function fetchJSONWithTimeout(url, opts, ms = 6000) {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), ms);
      try {
        const res = await fetch(url, { ...(opts || {}), signal: controller.signal });
        return await res.json();
      } finally {
        clearTimeout(id);
      }
    }

    function applyDiscInfo(discInfo, discPending) {
      const discStatusEl = document.getElementById("mk-disc-status");
      const discInfoEl = document.getElementById("mk-info");
      const discLight = document.getElementById("mk-disc-light");
      const discCardLight = document.getElementById("disc-card-light");
      const discCardLabel = document.getElementById("disc-card-label");
      const discCardInfo = document.getElementById("disc-card-info");
      const discText = buildDiscInfoText(discInfo) || (discPending ? "Disc detected; info not available yet." : "No disc info.");
      const discColor = discPending ? "#22c55e" : "#ef4444";
      const discLabelText = (() => {
        const payload = discInfo && (discInfo.info || discInfo);
        const summary = payload && (payload.summary || discInfo.summary);
        const label = summary && (summary.disc_label || summary.volume_label);
        const dtype = discInfo.disc_type || (summary && summary.disc_type);
        if (label && dtype) return `Disc: ${label} (${dtype})`;
        if (label) return `Disc: ${label}`;
        if (discPending) return "Disc present";
        return "No disc";
      })();
      if (discStatusEl) {
        discStatusEl.textContent = discPending ? ("Disc present (index " + ((discInfo && discInfo.disc_index !== undefined) ? discInfo.disc_index : "?") + ")") : "No disc detected.";
      }
      if (discInfoEl) {
        discInfoEl.value = discText;
      }
      if (discLight) {
        discLight.style.background = discColor;
      }
      if (discCardLight) {
        discCardLight.style.background = discColor;
      }
      if (discCardLabel) {
        discCardLabel.textContent = discLabelText;
      }
      if (discCardInfo) {
        discCardInfo.innerHTML = discText.replace(/\\n/g, "<br>");
      }
    }

    function buildDiscInfoText(info) {
      if (!info) return "";
      const payload = info.info ? info.info : info;
      const summary = (payload && payload.summary) || info.summary || null;
      const formatted = (payload && payload.formatted) || "";
      const raw = (payload && payload.raw) || info.raw || "";
      const error = (payload && payload.error) || info.error || "";
      let summaryLine = "";
      if (!formatted && summary) {
        const parts = [];
        if (summary.disc_label) parts.push("Label: " + summary.disc_label);
        if (summary.drive) parts.push("Drive: " + summary.drive);
        if (summary.titles_detected || summary.title_count) parts.push("Titles: " + (summary.titles_detected || summary.title_count));
        if (summary.main_feature && summary.main_feature.duration) parts.push("Main: " + summary.main_feature.duration);
        summaryLine = parts.join(" | ");
      }
      if (formatted) return formatted;
      const chunks = [];
      if (summaryLine) chunks.push(summaryLine);
      if (error) chunks.push("Error: " + error);
      if (raw && !formatted) chunks.push(raw);
      return chunks.filter(Boolean).join("\\n\\n");
    }

    function renderMetrics(metrics) {
      const el = document.getElementById("metrics");
      if (!metrics) {
        el.textContent = "Metrics unavailable.";
        return;
      }
      const cards = [];
      const cpuPct = (metrics.cpu_pct !== undefined && metrics.cpu_pct !== null) ? metrics.cpu_pct.toFixed(1) + "%" : "n/a";
      // Order: CPU, GPU, Memory, Disk, Output, Net
      cards.push({ icon: "🖥️", label: "CPU", value: cpuPct });
      if (metrics.gpu) {
        const g = metrics.gpu;
        cards.push({ icon: "🎞️", label: "GPU", value: g.util + "% util | " + g.mem_used_mb + " / " + g.mem_total_mb + " MB" });
      }
      if (metrics.mem) {
        cards.push({ icon: "💾", label: "Memory", value: metrics.mem.used_mb + " / " + metrics.mem.total_mb + " MB" });
      }
      if (metrics.block) {
        cards.push({ icon: "🗄️", label: "Disk", value: metrics.block.read_mb + " MB r / " + metrics.block.write_mb + " MB w" });
      }
      if (metrics.fs) {
        cards.push({ icon: "📂", label: "Output FS", value: metrics.fs.free_gb + " / " + metrics.fs.total_gb + " GB free" });
      }
      if (metrics.net) {
        cards.push({ icon: "🌐", label: "Net", value: metrics.net.rx_mb + " MB rx / " + metrics.net.tx_mb + " MB tx" });
      }
      el.innerHTML = '<div class="metric-grid">' + cards.map(c => `
        <div class="metric-card">
          <div class="metric-label">${c.icon} ${c.label}</div>
          <div class="metric-value">${c.value}</div>
        </div>
      `).join("") + '</div>';
    }

    function renderLogs(lines) {
      const el = document.getElementById("logs");
      const atBottom = (el.scrollTop + el.clientHeight) >= (el.scrollHeight - 20);
      el.textContent = (lines && lines.length ? lines : ["Ready to encode"]).join("\\n");
      if (atBottom) {
        el.scrollTop = el.scrollHeight;
      }
    }

    function fmtDuration(sec) {
      if (!sec && sec !== 0) return "";
      const s = Math.floor(sec % 60);
      const m = Math.floor(sec / 60) % 60;
      const h = Math.floor(sec / 3600);
      return [h, m, s].map(v => String(v).padStart(2, "0")).join(":");
    }

    async function renameRip(src) {
      const newName = prompt("Enter new filename (no path; extension optional):");
      if (!newName) return;
      const res = await fetch("/api/makemkv/rename", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src, name: newName }) });
      const data = await res.json();
      if (!data.ok) {
        alert("Rename request failed: " + (data.error || "unknown error"));
      } else {
        alert("Will rename to: " + data.name);
      }
    }

    function renderList(container, items, empty) {
      if (!items || items.length === 0) {
        container.innerHTML = '<div class="muted">' + empty + '</div>';
        return;
      }
      container.innerHTML = items.map(function(item) {
        const state = item.state || "";
        const badge = '<span class="badge ' + state + '">' + state.toUpperCase() + '</span>';
        const duration = item.duration_sec ? fmtDuration(item.duration_sec) : ((item.finished_at && item.started_at) ? fmtDuration(item.finished_at - (item.started_at || item.finished_at)) : "");
        const hasProgress = item.progress || item.progress === 0;
        const progress = hasProgress ? Math.min(100, Math.max(0, item.progress)).toFixed(0) : null;
        let etaText = "";
        if (item.eta_sec !== undefined && item.eta_sec !== null) {
          const eta = Math.max(0, Math.round(item.eta_sec));
          const h = Math.floor(eta / 3600);
          const m = Math.floor((eta % 3600) / 60);
          const s = eta % 60;
          const parts = [];
          if (h) parts.push(h + "h");
          if (m || h) parts.push(m + "m");
          parts.push(s + "s");
          etaText = "ETA " + parts.join(" ");
        }
        const progBar = progress !== null ? '<div class="progress"><div class="progress-bar" style="width:' + progress + '%"></div></div><div class="muted">Progress: ' + progress + '%</div>' : "";
        let controls = "";
        const isDisc = (item.source || "").startsWith("disc:");
        if (state === "running" || state === "ripping" || isDisc) {
          const stopLabel = state === "ripping" ? "Stop Rip" : "Stop";
          controls = '<button class="stop-btn" data-src="' + encodeURIComponent(item.source || "") + '">' + stopLabel + '</button>';
          if (state === "ripping" || isDisc) {
            controls += ' <button class="rename-btn" data-src="' + encodeURIComponent(item.source || "") + '">Set Name</button>';
          }
        } else if (state === "confirm") {
          controls = '<button class="confirm-btn" data-action="proceed" data-src="' + encodeURIComponent(item.source || "") + '">Proceed</button> '
                   + '<button class="confirm-btn" data-action="cancel" data-src="' + encodeURIComponent(item.source || "") + '">Cancel</button>';
        } else if (state === "canceled" || state === "error" || isDisc) {
          controls = '<button class="retry-btn" data-src="' + encodeURIComponent(item.source || "") + '">Retry</button>';
        }
        const infoLine = item.info ? '<div class="muted">' + item.info + '</div>' : "";
        const renameLine = item.rename_to ? '<div class="muted">Will rename to: ' + item.rename_to + '</div>' : "";
        return [
          '<div class="item">',
          '  <div class="flex-between">',
          '    <div class="path">' + (item.source || "") + '</div>',
          '    <div>' + badge + ' ' + controls + '</div>',
          '  </div>',
          '  <div class="muted">-> ' + (item.destination || "") + '</div>',
          '  <div class="muted">' + (item.message || "") + '</div>',
          infoLine,
          renameLine,
          '  <div class="muted">' + (etaText || (duration ? "Encode elapsed: " + duration : "")) + '</div>',
          '  ' + progBar,
          '</div>'
        ].join("");
      }).join("");
    }

    async function refresh() {
      try {
        const status = await fetchJSON("/api/status");
        renderList(document.getElementById("active"), status.active, "No active encodes.");
        renderList(document.getElementById("recent"), status.recent, "No recent jobs.");
        const hbCfg = status.handbrake_config || {};
        const hb = hbCfg.handbrake || {};
        const hbDvd = hbCfg.handbrake_dvd || {};
        const hbBr = hbCfg.handbrake_br || {};
        const hbExt = hb.extension || ".mkv";
        const usb = status.usb_status || {};
        const usbEl = document.getElementById("usb-status");
        if (usbEl) {
          const state = (usb.state || "unknown").toLowerCase();
          const msg = usb.message || "";
          let color = "#cbd5e1";
          if (state === "ready") color = "#22c55e";
          else if (state === "missing") color = "#fbbf24";
          else if (state === "error") color = "#f87171";
          usbEl.style.color = color;
          usbEl.textContent = "USB " + state + (msg ? (": " + msg) : "");
        }
        document.getElementById("hb-runtime").textContent =
          "Runtime HB settings: Encoder=" + (hb.encoder || "x264") +
          " | Default RF=" + (hb.quality ?? 20) +
          " | DVD RF=" + (hbDvd.quality ?? 20) +
          " | BR RF=" + (hbBr.quality ?? 25) +
          " | Ext=" + hbExt +
          " | Audio=" + ((hb.audio_mode === "copy") ? "copy" : ((hb.audio_bitrate_kbps || "128") + " kbps"));
      const discInfoRaw = status.disc_info || {};
      const discPending = !!status.disc_pending;
      // Apply immediately with whatever we have
      applyDiscInfo(discInfoRaw, discPending);
      // Non-blocking fallback: fetch detailed info with timeout, then update card
      if (discPending && (!discInfoRaw || !discInfoRaw.info)) {
        fetchJSONWithTimeout("/api/makemkv/info", {}, 20000)
          .then((di) => applyDiscInfo(di || discInfoRaw, discPending))
          .catch((err) => console.warn("Fallback disc info fetch failed", err));
      }
      const discCardEject = document.getElementById("disc-card-eject");
      if (discCardEject) {
        discCardEject.onclick = async () => { await ejectDisc(); refresh(); };
      }
      const startBtn = document.getElementById("mk-start-rip");
      const autoRipEnabled = document.getElementById("mk-auto-rip").checked;
      startBtn.disabled = !discPending || autoRipEnabled;
      } catch (e) {
        document.getElementById("active").innerHTML = "<div class='muted'>Status unavailable.</div>";
        document.getElementById("recent").innerHTML = "<div class='muted'>Status unavailable.</div>";
      }
      try {
        const logs = await fetchJSON("/api/logs");
        const lines = Array.isArray(logs.lines) ? logs.lines : [];
        renderLogs(lines);
      } catch (e) {
        document.getElementById("logs").textContent = "Logs unavailable.";
      }
      try {
        const events = await fetchJSON("/api/events");
        const lines = (events || []).map(function(ev) {
          return "[" + new Date(ev.ts * 1000).toLocaleTimeString() + "] " + ev.message;
        });
        document.getElementById("events").textContent = lines.join("\\n") || "No recent events.";
      } catch (e) {
        document.getElementById("events").textContent = "Events unavailable.";
      }
      try {
        const metrics = await fetchJSON("/api/metrics");
        renderMetrics(metrics);
      } catch (e) {
        document.getElementById("metrics").textContent = "Metrics unavailable.";
      }
      try {
      const cfg = await fetchJSON("/api/config");
      if (!hbDirty) {
        populateHandbrakeForm(cfg);
      }
        if (!mkDirty) {
          document.getElementById("mk-ripdir").value = (cfg.rip_dir || "/mnt/ripped");
          document.getElementById("mk-minlen").value = (cfg.makemkv_minlength !== undefined && cfg.makemkv_minlength !== null) ? cfg.makemkv_minlength : 1200;
          document.getElementById("mk-titles").value = (cfg.makemkv_titles || []).join(", ");
          document.getElementById("mk-audio-langs").value = (cfg.makemkv_audio_langs || []).join(", ");
          document.getElementById("mk-sub-langs").value = (cfg.makemkv_subtitle_langs || []).join(", ");
          document.getElementById("mk-keep").checked = !!cfg.makemkv_keep_ripped;
          document.getElementById("mk-pref-audio").value = (cfg.makemkv_preferred_audio_langs || []).join(", ") || "eng";
          document.getElementById("mk-pref-sub").value = (cfg.makemkv_preferred_subtitle_langs || []).join(", ") || "eng";
          document.getElementById("mk-exclude-commentary").checked = !!cfg.makemkv_exclude_commentary;
          document.getElementById("mk-prefer-surround").checked = cfg.makemkv_prefer_surround !== false;
          document.getElementById("mk-auto-rip").checked = !!cfg.makemkv_auto_rip;
        }
        const hb = cfg.handbrake || {};
        const hbDvd = cfg.handbrake_dvd || {};
        const hbBr = cfg.handbrake_br || {};
        document.getElementById("hb-summary").textContent = "Encoder: " + (hb.encoder || "x264")
          + " | Default RF: " + (hb.quality !== undefined && hb.quality !== null ? hb.quality : 20)
          + " | DVD RF: " + (hbDvd.quality !== undefined && hbDvd.quality !== null ? hbDvd.quality : 20)
          + " | BR RF: " + (hbBr.quality !== undefined && hbBr.quality !== null ? hbBr.quality : 25)
          + " | Ext: " + (hb.extension || ".mkv");
        if (!authDirty) {
          document.getElementById("auth-user").value = cfg.auth_user || "";
          document.getElementById("auth-pass").value = cfg.auth_password || "";
        }
      } catch (e) {
        console.error("Failed to load config", e);
      }
    }

    function tickClock() {
      const now = new Date();
      document.getElementById("clock").textContent = now.toLocaleString();
    }

    function setSelectValue(sel, value, fallback) {
      if (!sel) return;
      const val = (value === undefined || value === null) ? fallback : value;
      const valStr = val.toString();
      const has = Array.from(sel.options).some(o => o.value === valStr);
      sel.value = has ? valStr : fallback.toString();
    }

    function populateHandbrakeForm(cfg) {
      cfg = cfg || {};
      cfg.handbrake = cfg.handbrake || { encoder: "x264", quality: 20, extension: ".mkv", audio_mode: "encode", audio_bitrate_kbps: 128 };
      cfg.handbrake_dvd = cfg.handbrake_dvd || { quality: 20, audio_mode: "encode", audio_bitrate_kbps: 128 };
      cfg.handbrake_br = cfg.handbrake_br || { quality: 25, audio_mode: "encode", audio_bitrate_kbps: 128 };
      setSelectValue(document.getElementById("hb-encoder"), cfg.handbrake.encoder, "x264");
      setSelectValue(document.getElementById("hb-quality"), cfg.handbrake.quality, 20);
      const hbBitrate = cfg.handbrake.video_bitrate_kbps;
      if (hbBitrate === 8000 || hbBitrate === 5000 || hbBitrate === 2500) {
        document.getElementById("hb-bitrate").value = hbBitrate.toString();
        document.getElementById("hb-bitrate-custom").value = "";
      } else if (hbBitrate) {
        document.getElementById("hb-bitrate").value = "custom";
        document.getElementById("hb-bitrate-custom").value = hbBitrate;
      } else {
        document.getElementById("hb-bitrate").value = "";
        document.getElementById("hb-bitrate-custom").value = "";
      }
      document.getElementById("hb-two-pass").checked = !!cfg.handbrake.two_pass;
      setSelectValue(document.getElementById("hb-dvd-quality"), cfg.handbrake_dvd.quality, 20);
      setSelectValue(document.getElementById("hb-br-quality"), cfg.handbrake_br.quality, 25);
      setSelectValue(document.getElementById("hb-ext"), cfg.handbrake.extension, ".mkv");
      setSelectValue(document.getElementById("hb-audio-mode"), cfg.handbrake.audio_mode || "encode", "encode");
      setSelectValue(document.getElementById("hb-audio-bitrate"), cfg.handbrake.audio_bitrate_kbps || 128, 128);
      setSelectValue(document.getElementById("hb-audio-all"), cfg.handbrake.audio_all ? "true" : "false", "false");
      setSelectValue(document.getElementById("hb-subs"), cfg.handbrake.subtitle_mode || "none", "none");
      setSelectValue(document.getElementById("hb-audio-encoder"), cfg.handbrake.audio_encoder || "av_aac", "av_aac");
      setSelectValue(document.getElementById("hb-audio-mix"), cfg.handbrake.audio_mixdown || "", "");
      setSelectValue(document.getElementById("hb-audio-rate"), cfg.handbrake.audio_samplerate || "", "");
      document.getElementById("hb-audio-drc").value = (cfg.handbrake.audio_drc !== undefined && cfg.handbrake.audio_drc !== null) ? cfg.handbrake.audio_drc : "";
      document.getElementById("hb-audio-gain").value = (cfg.handbrake.audio_gain !== undefined && cfg.handbrake.audio_gain !== null) ? cfg.handbrake.audio_gain : "";
      document.getElementById("hb-audio-lang").value = (cfg.handbrake.audio_lang_list || []).join(", ");
      document.getElementById("hb-audio-tracks").value = cfg.handbrake.audio_track_list || "";
    }

    document.getElementById("hb-save").addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const qDefault = parseInt(document.getElementById("hb-quality").value || "20", 10) || 20;
      const qDvd = parseInt(document.getElementById("hb-dvd-quality").value || "20", 10) || 20;
      const qBr = parseInt(document.getElementById("hb-br-quality").value || "25", 10) || 25;
      const ext = document.getElementById("hb-ext").value;
      const audioMode = document.getElementById("hb-audio-mode").value;
      const audioBitrate = parseInt(document.getElementById("hb-audio-bitrate").value || "128", 10) || 128;
      const audioAll = document.getElementById("hb-audio-all").value === "true";
      const subtitleMode = document.getElementById("hb-subs").value || "none";
      const audioEncoder = document.getElementById("hb-audio-encoder").value || "av_aac";
      const audioMix = document.getElementById("hb-audio-mix").value || "";
      const audioRate = document.getElementById("hb-audio-rate").value || "";
      const audioDrcRaw = document.getElementById("hb-audio-drc").value;
      const audioDrc = audioDrcRaw === "" ? null : Number(audioDrcRaw);
      const audioGainRaw = document.getElementById("hb-audio-gain").value;
      const audioGain = audioGainRaw === "" ? null : Number(audioGainRaw);
      const audioLang = (document.getElementById("hb-audio-lang").value || "").split(",").map(v => v.trim()).filter(Boolean);
      const audioTracks = document.getElementById("hb-audio-tracks").value || "";
      let targetBitrate = document.getElementById("hb-bitrate").value;
      const customBitrate = parseInt(document.getElementById("hb-bitrate-custom").value || "0", 10) || 0;
      if (targetBitrate === "custom" && customBitrate > 0) {
        targetBitrate = customBitrate;
      } else if (targetBitrate === "") {
        targetBitrate = null;
      } else {
        targetBitrate = parseInt(targetBitrate, 10) || null;
      }
      const twoPass = document.getElementById("hb-two-pass").checked;
      const body = {
        profile: "handbrake",
        handbrake: {
          encoder: document.getElementById("hb-encoder").value,
          quality: qDefault,
          video_bitrate_kbps: targetBitrate,
          two_pass: twoPass,
          extension: ext,
          audio_mode: audioMode,
          audio_bitrate_kbps: audioBitrate,
          audio_encoder: audioEncoder,
          audio_mixdown: audioMix,
          audio_samplerate: audioRate,
          audio_drc: audioDrc,
          audio_gain: audioGain,
          audio_lang_list: audioLang,
          audio_track_list: audioTracks,
          audio_all: audioAll,
          subtitle_mode: subtitleMode
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode, video_bitrate_kbps: targetBitrate, two_pass: twoPass },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode, video_bitrate_kbps: targetBitrate, two_pass: twoPass }
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      hbDirty = false;
      refresh();
    });

    document.addEventListener("click", async (e) => {
      if (e.target.classList.contains("clear-btn")) {
        const status = e.target.getAttribute("data-clear");
        await fetch("/api/clear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
        refresh();
      }
      if (e.target.classList.contains("confirm-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        const action = e.target.getAttribute("data-action");
        await fetch("/api/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src, action }) });
        refresh();
      }
      if (e.target.classList.contains("stop-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        const ok = confirm("Stop this encode?\\nAre you sure?");
        if (!ok) return;
        let deleteSrc = false;
        if (confirm("Delete the source file too?\\nChoose OK to delete, Cancel to keep.")) {
          deleteSrc = true;
        }
        await fetch("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src, delete_source: deleteSrc }) });
        refresh();
      }
      if (e.target.classList.contains("rename-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        await renameRip(src);
        refresh();
      }
      if (e.target.classList.contains("retry-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        try {
          const res = await fetch("/api/retry", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: src }),
          });
          const data = await res.json();
          if (!res.ok || data.error) {
            alert("Retry failed: " + (data.error || res.statusText));
          } else {
            alert("Retry queued.");
          }
        } catch (err) {
          alert("Retry failed: " + err);
        }
        refresh();
      }
    });

    document.getElementById("mk-save").addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const csvToList = (val) => (val || "").split(",").map(v => v.trim()).filter(Boolean);
      const body = {
        rip_dir: document.getElementById("mk-ripdir").value,
        makemkv_minlength: Number(document.getElementById("mk-minlen").value),
        makemkv_titles: csvToList(document.getElementById("mk-titles").value),
        makemkv_audio_langs: csvToList(document.getElementById("mk-audio-langs").value),
        makemkv_subtitle_langs: csvToList(document.getElementById("mk-sub-langs").value),
        makemkv_keep_ripped: document.getElementById("mk-keep").checked,
        makemkv_preferred_audio_langs: csvToList(document.getElementById("mk-pref-audio").value || "eng"),
        makemkv_preferred_subtitle_langs: csvToList(document.getElementById("mk-pref-sub").value || "eng"),
        makemkv_exclude_commentary: document.getElementById("mk-exclude-commentary").checked,
        makemkv_prefer_surround: document.getElementById("mk-prefer-surround").checked,
        makemkv_auto_rip: document.getElementById("mk-auto-rip").checked,
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      try { await fetch("/api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: "MakeMKV settings saved", level: "info" }) }); } catch (err) {}
      alert("MakeMKV settings saved");
      mkDirty = false;
    });

    document.getElementById("handbrake-form").addEventListener("input", () => { hbDirty = true; });
    document.getElementById("makemkv-form").addEventListener("input", () => { mkDirty = true; });
    document.getElementById("makemkv-form").addEventListener("change", () => { mkDirty = true; });
    document.getElementById("handbrake-form").addEventListener("change", () => { hbDirty = true; });
    const authDirtyFlag = () => { authDirty = true; };
    document.getElementById("auth-user").addEventListener("input", authDirtyFlag);
    document.getElementById("auth-pass").addEventListener("input", authDirtyFlag);

    document.getElementById("copy-logs").addEventListener("click", async () => {
      try {
        const logs = await fetchJSON("/api/logs");
        const lines = (logs.lines || []).slice(-300);
        const text = lines.join("\\n");
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          const ta = document.createElement("textarea");
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        }
        alert("Copied last " + lines.length + " log lines to clipboard.");
      } catch (e) {
        alert("Failed to copy logs: " + e);
      }
    });

    const usbRefreshBtn = document.getElementById("usb-refresh");
    if (usbRefreshBtn) {
      usbRefreshBtn.addEventListener("click", async () => {
        const prev = usbRefreshBtn.textContent;
        usbRefreshBtn.disabled = true;
        usbRefreshBtn.textContent = "Refreshing...";
        try {
          await fetchJSON("/api/usb/refresh", { method: "POST" });
        } catch (e) {
          console.error("USB refresh failed", e);
          alert("USB refresh failed: " + e);
        } finally {
          usbRefreshBtn.disabled = false;
          usbRefreshBtn.textContent = prev;
          refresh();
        }
      });
    }

    const usbForceBtn = document.getElementById("usb-force-remount");
    if (usbForceBtn) {
      usbForceBtn.addEventListener("click", async () => {
        const prev = usbForceBtn.textContent;
        usbForceBtn.disabled = true;
        usbForceBtn.textContent = "Remounting...";
        try {
          await fetchJSON("/api/usb/force_remount", { method: "POST" });
        } catch (e) {
          console.error("USB force remount failed", e);
          alert("USB force remount failed: " + e);
        } finally {
          usbForceBtn.disabled = false;
          usbForceBtn.textContent = prev;
          refresh();
        }
      });
    }

    // Presets
    async function loadPresets() {
      try {
        const res = await fetch("/api/presets");
        const data = await res.json();
        const sel = document.getElementById("hb-preset-select");
        const current = sel.value;
        sel.innerHTML = '<option value=\"\">Load preset...</option>' + (data.presets || []).map(p => '<option value=\"' + p.name + '\">' + p.name + '</option>').join(\"\\n\");
        if (current) { sel.value = current; }
      } catch (e) {
        console.error(\"Failed to load presets\", e);
      }
    }

    document.getElementById(\"hb-preset-save\").addEventListener(\"click\", async () => {
      const name = document.getElementById(\"hb-preset-name\").value.trim();
      if (!name) { alert(\"Enter a preset name\"); return; }
      // reuse save handler body composition
      const qDefault = parseInt(document.getElementById(\"hb-quality\").value || \"20\", 10) || 20;
      const qDvd = parseInt(document.getElementById(\"hb-dvd-quality\").value || \"20\", 10) || 20;
      const qBr = parseInt(document.getElementById(\"hb-br-quality\").value || \"25\", 10) || 25;
      const ext = document.getElementById(\"hb-ext\").value;
      const audioMode = document.getElementById(\"hb-audio-mode\").value;
      const audioBitrate = parseInt(document.getElementById(\"hb-audio-bitrate\").value || \"128\", 10) || 128;
      const audioAll = document.getElementById(\"hb-audio-all\").value === \"true\";
      const subtitleMode = document.getElementById(\"hb-subs\").value || \"none\";
      const audioEncoder = document.getElementById(\"hb-audio-encoder\").value || \"av_aac\";
      const audioMix = document.getElementById(\"hb-audio-mix\").value || \"\";
      const audioRate = document.getElementById(\"hb-audio-rate\").value || \"\";
      const audioLang = (document.getElementById(\"hb-audio-lang\").value || \"\").split(\",\").map(v => v.trim()).filter(Boolean);
      const audioTracks = document.getElementById(\"hb-audio-tracks\").value || \"\";
      const audioDrcRaw = document.getElementById(\"hb-audio-drc\").value;
      const audioDrc = audioDrcRaw === \"\" ? null : Number(audioDrcRaw);
      const audioGainRaw = document.getElementById(\"hb-audio-gain\").value;
      const audioGain = audioGainRaw === \"\" ? null : Number(audioGainRaw);
      const body = {
        name,
        handbrake: {
          encoder: document.getElementById(\"hb-encoder\").value,
          quality: qDefault,
          extension: ext,
          audio_mode: audioMode,
          audio_bitrate_kbps: audioBitrate,
          audio_encoder: audioEncoder,
          audio_mixdown: audioMix,
          audio_samplerate: audioRate,
          audio_drc: audioDrc,
          audio_gain: audioGain,
          audio_lang_list: audioLang,
          audio_track_list: audioTracks,
          audio_all: audioAll,
          subtitle_mode: subtitleMode
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode }
      };
      await fetch(\"/api/presets\", { method: \"POST\", headers: { \"Content-Type\": \"application/json\" }, body: JSON.stringify(body) });
      await loadPresets();
    });

    document.getElementById(\"hb-preset-delete\").addEventListener(\"click\", async () => {
      const sel = document.getElementById(\"hb-preset-select\");
      const name = sel.value;
      if (!name) { alert(\"Select a preset to delete\"); return; }
      await fetch(\"/api/presets\", { method: \"DELETE\", headers: { \"Content-Type\": \"application/json\" }, body: JSON.stringify({ name }) });
      document.getElementById(\"hb-preset-name\").value = \"\";
      await loadPresets();
    });

    document.getElementById(\"hb-preset-select\").addEventListener(\"change\", async () => {
      const sel = document.getElementById(\"hb-preset-select\");
      const name = sel.value;
      if (!name) return;
      const res = await fetch(\"/api/presets\");
      const data = await res.json();
      const preset = (data.presets || []).find(p => p.name === name);
      if (!preset) return;
      populateHandbrakeForm({ handbrake: preset.handbrake, handbrake_dvd: preset.handbrake_dvd, handbrake_br: preset.handbrake_br });
    });

    // SMB helpers
    let smbMountId = null;
    let smbPath = "/";
    let smbSelected = null;

    async function smbList(pathOverride) {
      if (!smbMountId) { return; }
      const path = pathOverride || smbPath || "/";
      const res = await fetch("/api/smb/list?mount_id=" + encodeURIComponent(smbMountId) + "&path=" + encodeURIComponent(path));
      const data = await res.json();
      smbPath = data.path || "/";
      document.getElementById("smb-current-path").value = smbPath;
      const entries = data.entries || [];
      smbSelected = null;
      document.getElementById("smb-browse").innerHTML = entries.map(e => {
        const icon = e.is_dir ? "📁" : "📄";
        return '<div class="smb-item" data-path="' + e.path + '" data-dir="' + (e.is_dir ? "1" : "0") + '"><span>' + icon + '</span><div class="smb-path">' + e.name + '</div></div>';
      }).join("");
    }

    async function smbRefreshMounts() {
      const res = await fetch("/api/smb/mounts");
      const data = await res.json();
      const mounts = data.mounts || {};
      const mountItems = Object.keys(mounts).map(id => {
        const m = mounts[id];
        const path = (m && m.path) ? m.path : m;
        const label = (m && m.label) ? m.label : (path ? path.split("/").filter(Boolean).pop() : id);
        return '<div class="smb-item"><div class="smb-path">' + (label || id) + '</div><button class="smb-btn smb-unmount" data-id="' + id + '">Unmount</button></div>';
      }).join("");
      document.getElementById("smb-mounts").innerHTML = mountItems || "<div class='muted'>No mounts</div>";
    }

    document.getElementById("smb-connect").addEventListener("click", async () => {
      const body = {
        url: document.getElementById("smb-url").value,
        username: document.getElementById("smb-user").value,
        password: document.getElementById("smb-pass").value
      };
      const res = await fetch("/api/smb/mount", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      smbMountId = data.mount_id;
      smbPath = "/";
      await smbRefreshMounts();
      await smbList("/");
    });
    smbForm.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        connectSmb();
      }
    });

    document.getElementById("smb-refresh").addEventListener("click", async () => {
      await smbRefreshMounts();
      await smbList();
    });

    document.getElementById("mk-refresh-info").addEventListener("click", async () => {
      try {
        const info = await fetchJSON("/api/makemkv/info");
        const discInfoEl = document.getElementById("mk-info");
        const discStatusEl = document.getElementById("mk-disc-status");
        const discText = buildDiscInfoText(info) || "No disc info.";
        discInfoEl.value = discText;
        if (discStatusEl) {
          const idx = (info && info.disc_index !== undefined) ? info.disc_index : null;
          discStatusEl.textContent = idx !== null ? ("Disc present (index " + idx + ")") : "Disc info refreshed.";
        }
      } catch (e) {
        alert("Failed to fetch disc info: " + e);
      }
    });

    document.getElementById("mk-register").addEventListener("click", async () => {
      const key = (document.getElementById("mk-key").value || "").trim();
      if (!key) { alert("Enter a MakeMKV key"); return; }
      try {
        const res = await fetch("/api/makemkv/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key }) });
        const data = await res.json();
        if (data.registered) {
          alert("MakeMKV registered");
        } else {
          alert("Registration failed: " + (data.error || "unknown error"));
        }
      } catch (e) {
        alert("Failed to register: " + e);
      }
    });

    function refreshUpdateCommand() {
      const latest = (document.getElementById("mk-latest").value || "").trim();
      const cmdEl = document.getElementById("mk-update-cmd");
      if (!latest) {
        cmdEl.value = "";
        return;
      }
      cmdEl.value = 'curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/linux-video-encoder/scripts/update_makemkv.sh -o /tmp/update_makemkv.sh && chmod +x /tmp/update_makemkv.sh && MAKEMKV_VERSION=' + latest + ' /tmp/update_makemkv.sh';
    }

    document.getElementById("mk-latest").addEventListener("input", refreshUpdateCommand);

    document.getElementById("mk-update-check").addEventListener("click", async () => {
      const statusEl = document.getElementById("mk-update-status");
      statusEl.textContent = "Update status: checking...";
      try {
        const res = await fetch("/api/makemkv/update_check");
        const data = await res.json();
        const msg = data.message || data.stdout || data.error || "";
        if (data.installed_version) {
          document.getElementById("mk-installed").textContent = data.installed_version;
        }
        statusEl.textContent = "MakeMKV installed version checked.";
      } catch (e) {
        statusEl.textContent = "Update status: failed to check";
      }
    });

    document.getElementById("auth-save").addEventListener("click", async () => {
      const body = {
        auth_user: document.getElementById("auth-user").value,
        auth_password: document.getElementById("auth-pass").value
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      authDirty = false;
      alert("Auth settings saved. Reload and use the new credentials.");
    });

    document.getElementById("mk-copy-update").addEventListener("click", async () => {
      const cmd = (document.getElementById("mk-update-cmd").value || "").trim();
      if (!cmd) { alert("No update command to copy."); return; }
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(cmd);
        } else {
          const ta = document.createElement("textarea");
          ta.value = cmd;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        }
        alert("Update command copied.");
      } catch (e) {
        alert("Failed to copy: " + e);
      }
    });

    document.getElementById("mk-start-rip").addEventListener("click", async () => {
      try {
        await fetch("/api/makemkv/rip", { method: "POST" });
        alert("Rip requested. It will start on next scan if a disc is present.");
      } catch (e) {
        alert("Failed to request rip: " + e);
      }
    });

    document.getElementById("mk-stop-rip").addEventListener("click", async () => {
      try {
        const res = await fetch("/api/makemkv/stop", { method: "POST" });
        const data = await res.json();
        if (data.stopped) {
          alert("MakeMKV rip stopped.");
        } else {
          alert("No active MakeMKV rip to stop.");
        }
      } catch (e) {
        alert("Failed to stop rip: " + e);
      }
    });

    async function ejectDisc() {
      try {
        const res = await fetch("/api/makemkv/eject", { method: "POST" });
        const data = await res.json();
        if (data.ok) {
          alert("Disc ejected.");
        } else {
          alert("Eject failed: " + (data.error || "unknown error"));
        }
      } catch (e) {
        alert("Failed to eject: " + e);
      }
    }

    document.getElementById("mk-eject").addEventListener("click", ejectDisc);

    document.getElementById("smb-up").addEventListener("click", async () => {
      if (!smbMountId || !smbPath || smbPath === "/") return;
      const up = smbPath.replace(/\\/+$/, "").split("/").slice(0, -1).join("/") || "/";
      await smbList(up);
    });

    document.getElementById("smb-browse").addEventListener("click", async (e) => {
      const item = e.target.closest(".smb-item");
      if (!item) return;
      const path = item.getAttribute("data-path");
      const isDir = item.getAttribute("data-dir") === "1";
      if (isDir) {
        await smbList(path);
      } else {
        smbSelected = path;
        document.querySelectorAll("#smb-browse .smb-item").forEach(el => el.style.background = "");
        item.style.background = "#1f2937";
      }
    });

    document.getElementById("smb-mounts").addEventListener("click", async (e) => {
      if (e.target.classList.contains("smb-unmount")) {
        const id = e.target.getAttribute("data-id");
        await fetch("/api/smb/unmount", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mount_id: id }) });
        if (smbMountId === id) { smbMountId = null; smbSelected = null; smbPath = "/"; document.getElementById("smb-browse").innerHTML = ""; }
        await smbRefreshMounts();
      }
    });

    document.getElementById("smb-queue").addEventListener("click", async () => {
      if (!smbMountId || !smbSelected) { alert("Select a file first."); return; }
      await fetch("/api/smb/queue", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mount_id: smbMountId, path: smbSelected }) });
      alert("Queued: " + smbSelected);
    });

    smbRefreshMounts();

    setInterval(refresh, 2000);
    setInterval(tickClock, 1000);
    refresh();
    tickClock();
  </script>
</body>
</html>
"""
HTML_PAGE = HTML_PAGE_TEMPLATE.replace("__VERSION__", VERSION)
MAIN_PAGE = MAIN_PAGE_TEMPLATE.replace("__VERSION__", VERSION)
SETTINGS_PAGE = SETTINGS_PAGE_TEMPLATE.replace("__VERSION__", VERSION)


def create_app(tracker, config_manager=None):
    app = Flask(
        __name__,
        static_folder=str(ASSETS_ROOT),
        static_url_path="/assets",
    )
    ASSETS_ROOT.mkdir(parents=True, exist_ok=True)
    SMB_MOUNT_ROOT.mkdir(parents=True, exist_ok=True)

    def require_auth(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cfg = config_manager.read() if config_manager else {}
            expected_user = cfg.get("auth_user") or ""
            expected_pass = cfg.get("auth_password") or ""
            auth = request.authorization
            if expected_user and expected_pass:
                if not auth or auth.username != expected_user or auth.password != expected_pass:
                    resp = Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})
                    return resp
            return f(*args, **kwargs)
        return wrapper

    def log_timing(label: str, started_at: float, extra: str = ""):
        try:
            dur = time.time() - started_at
            TIMING_PATH.parent.mkdir(parents=True, exist_ok=True)
            with TIMING_PATH.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {label} {dur:.3f}s {extra}\n")
        except Exception:
            pass

    def normalize_smb_url(url: str) -> str:
        url = url.strip()
        if url.startswith("smb://"):
            url = "//" + url[len("smb://") :]
        return url

    def ensure_under(base: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
        try:
            target = target.resolve()
            base = base.resolve()
            if base in target.parents or target == base:
                return target
        except Exception:
            pass
        return base

    def _sanitize_config(cfg: dict) -> dict:
        try:
            safe = json.loads(json.dumps(cfg))
        except Exception:
            return {}
        safe.pop("auth_password", None)
        safe.pop("auth_user", None)
        return safe

    def _run_git(args, cwd: Path):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)

    def _diagnostic_remote_url():
        """
        Build a remote URL for the diagnostics repo using stored credentials if available.
        Credentials file format: https://user:token@github.com
        """
        try:
            if DIAG_CRED_FILE.exists():
                raw = DIAG_CRED_FILE.read_text(encoding="utf-8").strip().splitlines()
                if raw:
                    base = raw[0].strip().rstrip("/")
                    if base.startswith("https://"):
                        suffix = DIAG_REPO_URL.split("github.com/", 1)[-1]
                        return f"{base}/{suffix}"
        except Exception:
            logging.debug("Failed to build diagnostic remote URL from credentials", exc_info=True)
        return DIAG_REPO_URL

    def _set_origin(repo_path: Path, url: str):
        res = _run_git(["remote", "set-url", "origin", url], cwd=repo_path)
        if res.returncode != 0:
            logging.warning("Failed to set diagnostics origin: %s", res.stderr or res.stdout)

    def _ensure_git_identity(repo_path: Path):
        # Set user.name and user.email if missing
        name = _run_git(["config", "--get", "user.name"], cwd=repo_path)
        email = _run_git(["config", "--get", "user.email"], cwd=repo_path)
        need_name = (name.returncode != 0) or not (name.stdout or "").strip()
        need_email = (email.returncode != 0) or not (email.stdout or "").strip()
        if need_name:
            _run_git(["config", "--global", "user.name", DIAG_GIT_NAME], cwd=repo_path)
        if need_email:
            _run_git(["config", "--global", "user.email", DIAG_GIT_EMAIL], cwd=repo_path)

    def _ensure_diag_repo() -> Path:
        repo_path = DIAG_REPO_PATH
        try:
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            repo_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            logging.error("Failed to create diagnostics repo path %s", repo_path)
            return None
        remote_url = _diagnostic_remote_url()
        if not (repo_path / ".git").exists():
            res = _run_git(["clone", remote_url, str(repo_path)], cwd=repo_path.parent)
            if res.returncode != 0:
                logging.error("Diagnostics repo clone failed: %s", res.stderr or res.stdout)
                return None
        else:
            _set_origin(repo_path, remote_url)
            _run_git(["pull", "--ff-only"], cwd=repo_path)
        _ensure_git_identity(repo_path)
        return repo_path

    def mount_smb(url: str, username: str = "", password: str = "", domain: str = "", vers: str = "") -> str:
        mid = uuid.uuid4().hex
        mnt = SMB_MOUNT_ROOT / mid
        mnt.mkdir(parents=True, exist_ok=True)
        label = url.rstrip("/").split("/")[-1] if url else mid
        helper = [sys.executable, "/linux-video-encoder/scripts/mount_smb_helper.py", "--url", url, "--mountpoint", str(mnt)]
        if username:
            helper += ["--username", username]
        if password:
            helper += ["--password", password]
        if domain:
            helper += ["--domain", domain]
        if vers:
            helper += ["--vers", vers]
        res = subprocess.run(helper, capture_output=True, text=True)
        if res.returncode != 0:
            try:
                mnt.rmdir()
            except Exception:
                pass
            raise RuntimeError(f"Failed to mount SMB: {res.stderr.strip() or res.stdout.strip() or res.returncode}")
        tracker.add_smb_mount(mid, str(mnt), label=label)
        return mid

    def unmount_smb(mount_id: str):
        mounts = tracker.list_smb_mounts()
        entry = mounts.get(mount_id)
        mnt = entry.get("path") if isinstance(entry, dict) else entry
        if not mnt:
            return
        subprocess.run(["umount", mnt], capture_output=True, text=True)
        try:
            shutil.rmtree(mnt, ignore_errors=True)
        except Exception:
            pass
        tracker.remove_smb_mount(mount_id)

    def cleanup_staged_file(path: str):
        """Remove a staged file and any matching sidecar .srt files; drop from allowlist."""
        if not path:
            return
        try:
            p = Path(path)
            parent = p.parent
            names = [p.name]
            if p.exists():
                try:
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink()
                except Exception:
                    pass
            stem = p.stem
            # exact .srt
            exact = parent / f"{stem}.srt"
            if exact.exists():
                names.append(exact.name)
                try:
                    exact.unlink()
                except Exception:
                    pass
            for cand in parent.glob(f"{stem}.*.srt"):
                if cand.is_file():
                    names.append(cand.name)
                    try:
                        cand.unlink()
                    except Exception:
                        pass
            remove_from_allowlist(names)
        except Exception:
            pass

    def list_smb(mount_id: str, rel_path: str = "/"):
        mounts = tracker.list_smb_mounts()
        entry = mounts.get(mount_id)
        mnt = entry.get("path") if isinstance(entry, dict) else entry
        if not mnt:
            raise FileNotFoundError("mount not found")
        base = pathlib.Path(mnt)
        target = ensure_under(base, base / rel_path.lstrip("/"))
        if not target.exists():
            target = base
        entries = []
        allowed_exts = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".srt", ".ass", ".ssa", ".sub", ".vtt"}
        try:
            for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if entry.is_file():
                    if entry.suffix.lower() not in allowed_exts:
                        continue
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "path": "/" + entry.relative_to(base).as_posix()
                })
        except Exception:
            pass
        return {"path": "/" + target.relative_to(base).as_posix() if target != base else "/", "entries": entries}

    def read_meminfo():
        mem = {"total_mb": None, "used_mb": None}
        try:
            info = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) < 2:
                        continue
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    info[key] = int(val)
            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", 0)
            used_kb = total_kb - avail_kb
            mem["total_mb"] = round(total_kb / 1024, 1)
            mem["used_mb"] = round(used_kb / 1024, 1)
        except Exception:
            pass
        return mem

    def read_netdev():
        rx = tx = 0
        try:
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    iface, rest = line.split(":", 1)
                    parts = rest.strip().split()
                    if len(parts) >= 8:
                        rx += int(parts[0])
                        tx += int(parts[8])
        except Exception:
            pass
        return {"rx_mb": round(rx / (1024 * 1024), 1), "tx_mb": round(tx / (1024 * 1024), 1)}

    def read_diskstats():
        rd = wr = 0
        try:
            with open("/proc/diskstats", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 14:
                        continue
                    # sectors read at index 5, written at index 9
                    try:
                        sectors_rd = int(parts[5])
                        sectors_wr = int(parts[9])
                        rd += sectors_rd
                        wr += sectors_wr
                    except Exception:
                        continue
            # assume 512 bytes per sector
            rd_mb = round((rd * 512) / (1024 * 1024), 1)
            wr_mb = round((wr * 512) / (1024 * 1024), 1)
            return {"read_mb": rd_mb, "write_mb": wr_mb}
        except Exception:
            return None

    def read_gpu():
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0 or not res.stdout.strip():
                return None
            line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                util = int(parts[0])
                mem_used = int(parts[1])
                mem_total = int(parts[2])
                return {"util": util, "mem_used_mb": mem_used, "mem_total_mb": mem_total}
        except Exception:
            pass
        return None

    def read_fs(path="/mnt/output"):
        try:
            st = os.statvfs(path)
            total = st.f_frsize * st.f_blocks
            free = st.f_frsize * st.f_bavail
            return {
                "path": path,
                "free_gb": round(free / (1024 ** 3), 1),
                "total_gb": round(total / (1024 ** 3), 1),
            }
        except Exception:
            return None

    @app.route("/")
    @require_auth
    def index():
        return Response(MAIN_PAGE, mimetype="text/html")

    @app.route("/settings")
    @require_auth
    def settings():
        return Response(SETTINGS_PAGE, mimetype="text/html")

    @app.route("/api/status")
    @require_auth
    def status():
        t0 = time.time()
        data = tracker.snapshot()
        data["version"] = VERSION
        if config_manager:
            cfg = config_manager.read()
            data["handbrake_config"] = {
                "profile": cfg.get("profile"),
                "handbrake": cfg.get("handbrake", {}),
                "handbrake_dvd": cfg.get("handbrake_dvd", {}),
                "handbrake_br": cfg.get("handbrake_br", {}),
                "low_bitrate_auto_proceed": cfg.get("low_bitrate_auto_proceed", False),
                "low_bitrate_auto_skip": cfg.get("low_bitrate_auto_skip", False),
            }
        resp = jsonify(data)
        log_timing("api/status", t0)
        return resp

    @app.route("/api/logs")
    @require_auth
    def logs():
        t0 = time.time()
        lines = tracker.tail_logs()
        resp = jsonify({"lines": lines})
        log_timing("api/logs", t0, f"lines={len(lines)}")
        return resp

    @app.route("/api/events")
    @require_auth
    def events():
        t0 = time.time()
        ev = tracker.events()
        resp = jsonify(ev)
        log_timing("api/events", t0, f"events={len(ev)}")
        return resp

    @app.route("/api/diagnostics/push", methods=["POST"])
    @require_auth
    def push_diagnostics():
        repo_path = _ensure_diag_repo()
        if not repo_path:
            return jsonify({"ok": False, "error": "Diagnostics repo unavailable"}), 500
        ts = time.strftime("%Y%m%d-%H%M%S")
        dest = repo_path / "diagnostics" / f"diag_{ts}"
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Failed to create diagnostics folder: {exc}"}), 500
        try:
            status = tracker.snapshot()
            status["version"] = VERSION
            if config_manager:
                cfg = config_manager.read()
                status["config"] = _sanitize_config(cfg)
            (dest / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
            events_data = tracker.events()
            (dest / "events.json").write_text(json.dumps(events_data, indent=2), encoding="utf-8")
            logs = tracker.tail_logs(lines=400)
            (dest / "app_log_tail.txt").write_text("\n".join(logs), encoding="utf-8")
            try:
                timing_src = TIMING_PATH
                if timing_src.exists():
                    (dest / "timing.log").write_text(timing_src.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
            except Exception:
                pass
            # Collect quick drive diagnostics to help debug unresponsive optical drive
            try:
                drive_diag = []
                diag_cmds = [
                    ("ls -l /dev/sr* /dev/sg*", ["sh", "-c", "ls -l /dev/sr* /dev/sg* 2>/dev/null"]),
                    ("sg_map -i", ["sg_map", "-i"]),
                    ("lsblk -nP", ["lsblk", "-nP", "-o", "NAME,TYPE,RM,MOUNTPOINT,FSTYPE,TRAN"]),
                    ("udevadm info /dev/sr0", ["udevadm", "info", "--query=all", "--name=/dev/sr0"]),
                    ("sg_inq /dev/sg1", ["sg_inq", "/dev/sg1"]),
                    ("makemkvcon info disc:0", ["makemkvcon", "-r", "--cache=1", "info", "disc:0"]),
                ]
                for label, cmd in diag_cmds:
                    try:
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
                        out = (res.stdout or "") + (res.stderr or "")
                        drive_diag.append(f"$ {label}\n{out.strip()}\n")
                    except FileNotFoundError:
                        drive_diag.append(f"$ {label}\n(command not found)\n")
                    except subprocess.TimeoutExpired:
                        drive_diag.append(f"$ {label}\n(timeout)\n")
                (dest / "drive_diag.txt").write_text("\n".join(drive_diag), encoding="utf-8")
            except Exception:
                pass
        except Exception as exc:
            logging.exception("Failed to write diagnostics")
            return jsonify({"ok": False, "error": f"Failed to collect diagnostics: {exc}"}), 500
        rel = dest.relative_to(repo_path)
        add = _run_git(["add", str(rel)], cwd=repo_path)
        if add.returncode != 0:
            return jsonify({"ok": False, "error": add.stderr or add.stdout or "git add failed"}), 500
        _set_origin(repo_path, _diagnostic_remote_url())
        commit = _run_git(["commit", "-m", f"Diagnostics {ts}"], cwd=repo_path)
        if commit.returncode != 0:
            return jsonify({"ok": False, "error": commit.stderr or commit.stdout or "git commit failed"}), 500
        push = _run_git(["push", "origin", "main"], cwd=repo_path)
        if push.returncode != 0:
            return jsonify({"ok": False, "error": push.stderr or push.stdout or "git push failed"}), 500
        head = _run_git(["rev-parse", "HEAD"], cwd=repo_path)
        sha = (head.stdout or "").strip()
        return jsonify({"ok": True, "message": f"Diagnostics pushed at {ts}", "commit": sha})

    @app.route("/api/events", methods=["POST"])
    @require_auth
    def add_event():
        payload = request.get_json(force=True) or {}
        msg = payload.get("message", "")
        level = payload.get("level", "info")
        if msg:
            tracker.add_event(msg, level=level)
            return jsonify({"added": True})
        return jsonify({"added": False}), 400

    @app.route("/api/metrics")
    @require_auth
    def metrics():
        t0 = time.time()
        import os
        load1, load5, load15 = os.getloadavg()
        cores = os.cpu_count() or 1
        data = {
            "cpu_load": [round(load1, 2), round(load5, 2), round(load15, 2)],
            "cpu_pct": round((load1 / cores) * 100, 1),
            "mem": read_meminfo(),
            "net": read_netdev(),
            "block": read_diskstats(),
            "gpu": read_gpu(),
            "fs": read_fs(),
            "ts": time.time(),
        }
        resp = jsonify(data)
        log_timing("api/metrics", t0)
        return resp

    helper_mountpoint = os.environ.get("USB_HELPER_MOUNTPOINT", "/linux-video-encoder/AutoEncoder/linux-video-encoder/USB")
    container_usb_mount = "/mnt/usb"

    @app.route("/api/usb/refresh", methods=["POST"])
    @require_auth
    def usb_refresh():
        # Best-effort mount of first removable partition via host helper to helper_mountpoint,
        # falling back to in-container mount at container_usb_mount.
        try:
            helper_url = os.environ.get("USB_HELPER_URL", "http://host.docker.internal:8765")
            target = helper_mountpoint
            logger = logging.getLogger(__name__)

            # Try host helper first (if reachable), then fall back to in-container logic.
            if helper_url:
                try:
                    import urllib.request
                    payload = json.dumps({"target": target}).encode("utf-8")
                    req = urllib.request.Request(
                        helper_url.rstrip("/") + "/usb/refresh",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        body = resp.read().decode("utf-8")
                        data = json.loads(body or "{}")
                        attempts = data.get("attempts") or []
                        helper_lsblk = []
                        if attempts:
                            helper_lsblk = (attempts[-1].get("lsblk") or "").splitlines()
                    helper_snippet = "\\n".join(helper_lsblk[:6])
                    if data.get("ok"):
                        dev = data.get("device")
                        vid_ct = data.get("video_count")
                        logger.info("USB helper mounted %s -> %s (fs=%s)%s", dev, target, data.get("fstype", "auto"),
                                    f" [{vid_ct} video files]" if vid_ct is not None else "")
                        if helper_snippet:
                            logger.info("USB helper lsblk:\n%s", helper_snippet)
                        tracker.set_usb_status("ready", f"Mounted {dev} (host helper)")
                        logger.info("USB refresh (helper): %s", body)
                        return jsonify({"ok": True, "device": dev, "fs": data.get("fstype", "auto"), "helper": True})
                    else:
                        msg = data.get("error") or body or "host helper mount failed"
                        logger.warning("USB refresh (helper) failed: %s", msg)
                        if helper_snippet:
                            logger.warning("USB helper lsblk:\n%s", helper_snippet)
                        logger.warning("USB refresh (helper) failed: %s", body)
                except Exception as helper_exc:
                    logger.warning("USB refresh: host helper unavailable (%s); falling back", helper_exc)

            # discover first removable partition (fallback in-container)
            dev = None
            fstype = None
            res = subprocess.run(
                ["lsblk", "-nP", "-o", "NAME,TYPE,RM,MOUNTPOINT,FSTYPE,TRAN"],
                capture_output=True,
                text=True,
                check=False,
            )
            if not res.stdout.strip():
                logger.info("USB refresh: lsblk returned empty output (rc=%s, stderr=%s). Retrying without -P.", res.returncode, res.stderr.strip())
                res = subprocess.run(
                    ["lsblk", "-nr", "-o", "NAME,TYPE,RM,MOUNTPOINT,FSTYPE,TRAN"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            logger.info("USB refresh: lsblk output:\n%s", res.stdout)
            disk_transport = {}

            def parse_lsblk_line(line: str) -> dict:
                parsed = {}
                for token in line.split():
                    if "=" not in token:
                        continue
                    k, v = token.split("=", 1)
                    parsed[k] = v.strip('"')
                return parsed

            lines = res.stdout.splitlines()
            if not lines:
                msg = res.stderr.strip() or "no lsblk output"
                logger.error("USB refresh: lsblk produced no parseable lines (%s)", msg)
                tracker.add_event("USB refresh: lsblk produced no output", level="error")
                tracker.set_usb_status("missing", "No block devices detected")
                return jsonify({"ok": False, "error": "lsblk returned no output"}), 500

            for line in lines:
                entry = parse_lsblk_line(line)
                name = entry.get("NAME", "")
                typ = entry.get("TYPE", "")
                rm = entry.get("RM", "")
                mp = entry.get("MOUNTPOINT", "") or ""
                fs = entry.get("FSTYPE", "") or ""
                tran = entry.get("TRAN", "") or ""
                if not name or not typ:
                    continue
                if typ == "disk":
                    disk_transport[name] = tran
                    continue
                if typ != "part":
                    continue
                if not tran:
                    for disk_name, disk_tran in disk_transport.items():
                        if name.startswith(disk_name):
                            tran = disk_tran
                            break
                if not (rm == "1" or tran.lower() == "usb"):
                    continue
                dev = f"/dev/{name}"
                fstype = fs or None
                if mp == container_usb_mount:
                    logger.info("USB refresh: already mounted %s at %s", dev, container_usb_mount)
                    tracker.add_event(f"USB already mounted at {container_usb_mount}: {dev}")
                    tracker.set_usb_status("ready", f"Mounted {dev}")
                    return jsonify({"ok": True, "device": dev, "fs": fstype or "unknown"})
                break
            if not dev:
                logger.info("USB refresh: no removable/usb partition detected; lsblk output:\n%s", res.stdout)
                os.makedirs(container_usb_mount, exist_ok=True)
                subprocess.run(["mount", "--make-rshared", container_usb_mount], check=False)
                tracker.add_event("USB refresh: no removable partition found.", level="error")
                tracker.set_usb_status("missing", "No removable partition detected")
                return jsonify({"ok": False, "error": "no removable partition"})

            # ensure target exists and is shared
            os.makedirs(container_usb_mount, exist_ok=True)
            subprocess.run(["mount", "--make-rshared", container_usb_mount], check=False)
            # unmount previous if any
            subprocess.run(["umount", container_usb_mount], check=False)

            opts = "uid=1000,gid=1000,fmask=0022,dmask=0022,iocharset=utf8"
            logger.info("USB refresh: mounting %s -> %s (fstype=%s) [fallback]", dev, container_usb_mount, fstype or "auto")
            cmd = ["mount", "-o", opts]
            if fstype:
                cmd += ["-t", fstype]
            cmd += [dev, container_usb_mount]
            rc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if rc.returncode != 0:
                # retry without explicit fs type
                logger.info("USB refresh: retry mount %s -> %s without fstype [fallback]", dev, container_usb_mount)
                rc = subprocess.run(["mount", "-o", opts, dev, container_usb_mount], capture_output=True, text=True, check=False)
            if rc.returncode == 0:
                logger.info("USB refresh: mounted %s -> %s [fallback]", dev, container_usb_mount)
                tracker.add_event(f"USB mounted: {dev} -> {container_usb_mount}")
                tracker.set_usb_status("ready", f"Mounted {dev}")
                return jsonify({"ok": True, "device": dev, "fs": fstype or "auto"})
            else:
                msg = rc.stderr.strip() or rc.stdout.strip() or "unknown error"
                logger.error("USB refresh: failed to mount %s -> %s: %s", dev, container_usb_mount, msg)
                tracker.add_event(f"USB refresh failed to mount {dev}: {msg}", level="error")
                tracker.set_usb_status("error", f"Mount failed: {msg}")
                return jsonify({"ok": False, "error": msg}), 500
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception("USB refresh request failed")
            tracker.add_event(f"USB refresh request failed: {e}", level="error")
            tracker.set_usb_status("error", "Refresh failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/usb/force_remount", methods=["POST"])
    @require_auth
    def usb_force_remount():
        helper_url = os.environ.get("USB_HELPER_URL", "http://host.docker.internal:8765")
        helper_mount = os.environ.get("USB_HELPER_MOUNTPOINT", "/linux-video-encoder/AutoEncoder/linux-video-encoder/USB")
        logger = logging.getLogger(__name__)
        try:
            if helper_url:
                try:
                    import urllib.request
                    payload = json.dumps({"target": helper_mount, "attempts": 5, "delay": 1.5}).encode("utf-8")
                    req = urllib.request.Request(
                        helper_url.rstrip("/") + "/usb/force_remount",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    resp = None
                    body = ""
                    try:
                        resp = urllib.request.urlopen(req, timeout=15)
                        body = resp.read().decode("utf-8")
                    except urllib.error.HTTPError as he:
                        body = he.read().decode("utf-8")
                    data = json.loads(body or "{}")
                    attempts = data.get("attempts") or []
                    helper_lsblk = ""
                    if attempts:
                        helper_lsblk = (attempts[-1].get("lsblk") or "").splitlines()
                        helper_lsblk = "\\n".join(helper_lsblk[:6])
                    if data.get("ok"):
                        dev = data.get("device")
                        vid_ct = data.get("video_count")
                        logger.info("USB force-remount mounted %s -> %s (fs=%s)%s", dev, helper_mount, data.get("fstype", "auto"),
                                    f" [{vid_ct} video files]" if vid_ct is not None else "")
                        if helper_lsblk:
                            logger.info("USB helper lsblk:\n%s", helper_lsblk)
                        tracker.set_usb_status("ready", f"Mounted {dev} (force remount)")
                        return jsonify({"ok": True, "device": dev, "fs": data.get("fstype", "auto"), "helper": True, "attempts": attempts})
                    else:
                        msg = data.get("error") or body or "host helper mount failed"
                        logger.warning("USB force-remount failed: %s", msg)
                        if helper_lsblk:
                            logger.warning("USB helper lsblk:\n%s", helper_lsblk)
                        return jsonify({"ok": False, "error": msg, "attempts": attempts}), 500
                except Exception as helper_exc:
                    logger.warning("USB force-remount: host helper unavailable (%s)", helper_exc)
                    tracker.add_event(f"USB force-remount: helper unavailable ({helper_exc})", level="error")
                    tracker.set_usb_status("error", "Helper unavailable")
                    return jsonify({"ok": False, "error": str(helper_exc)}), 500
            return jsonify({"ok": False, "error": "helper not configured"}), 500
        except Exception as e:
            logger.exception("USB force remount failed")
            tracker.add_event(f"USB force remount failed: {e}", level="error")
            tracker.set_usb_status("error", "Force remount failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/usb/eject", methods=["POST"])
    @require_auth
    def usb_eject():
        helper_url = os.environ.get("USB_HELPER_URL", "http://host.docker.internal:8765")
        helper_mount = os.environ.get("USB_HELPER_MOUNTPOINT", "/linux-video-encoder/AutoEncoder/linux-video-encoder/USB")
        logger = logging.getLogger(__name__)
        try:
            if helper_url:
                try:
                    import urllib.request
                    payload = json.dumps({"target": helper_mount}).encode("utf-8")
                    req = urllib.request.Request(
                        helper_url.rstrip("/") + "/usb/eject",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        body = resp.read().decode("utf-8")
                        data = json.loads(body or "{}")
                        if data.get("ok"):
                            tracker.add_event(f"USB ejected at {helper_mount}")
                            tracker.set_usb_status("missing", "Ejected")
                            return jsonify({"ok": True, "helper": True, "mountpoint": helper_mount})
                        else:
                            msg = data.get("error") or body or "host helper eject failed"
                            tracker.add_event(f"USB eject failed: {msg}", level="error")
                            return jsonify({"ok": False, "error": msg}), 500
                except Exception as helper_exc:
                    logger.warning("USB eject: host helper unavailable (%s)", helper_exc)
                    tracker.add_event(f"USB eject: helper unavailable ({helper_exc})", level="error")
                    tracker.set_usb_status("error", "Eject failed")
                    return jsonify({"ok": False, "error": str(helper_exc)}), 500
            # fallback: in-container unmount (best effort)
            rc = subprocess.run(["umount", container_usb_mount], capture_output=True, text=True, check=False)
            if rc.returncode == 0:
                tracker.add_event(f"USB ejected at {container_usb_mount}")
                tracker.set_usb_status("missing", "Ejected")
                return jsonify({"ok": True, "helper": False, "mountpoint": container_usb_mount})
            msg = rc.stderr.strip() or rc.stdout.strip() or "umount failed"
            tracker.add_event(f"USB eject failed: {msg}", level="error")
            tracker.set_usb_status("error", "Eject failed")
            return jsonify({"ok": False, "error": msg}), 500
        except Exception as e:
            logger.exception("USB eject failed")
            tracker.add_event(f"USB eject failed: {e}", level="error")
            tracker.set_usb_status("error", "Eject failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    if config_manager:
        @app.route("/api/config", methods=["GET", "POST"])
        @require_auth
        def config():
            if request.method == "GET":
                return jsonify(config_manager.read())
            payload = request.get_json(force=True) or {}
            updated = config_manager.update(payload)
            return jsonify(updated)

    @app.route("/api/smb/mount", methods=["POST"])
    @require_auth
    def smb_mount():
        payload = request.get_json(force=True) or {}
        url = payload.get("url", "")
        username = payload.get("username", "")
        password = payload.get("password", "")
        domain = payload.get("domain", "")
        vers = payload.get("vers", "")
        if not url:
            return jsonify({"error": "url required"}), 400
        try:
            mid = mount_smb(url, username, password, domain, vers)
            return jsonify({"mount_id": mid, "path": tracker.list_smb_mounts().get(mid)})
        except Exception as e:
            err = str(e)
            try:
                tracker.add_event(f"SMB mount failed: {err}", level="error")
            except Exception:
                pass
            return jsonify({"error": err}), 400

    @app.route("/api/smb/mounts")
    @require_auth
    def smb_mounts():
        return jsonify({"mounts": tracker.list_smb_mounts()})

    @app.route("/api/smb/unmount", methods=["POST"])
    @require_auth
    def smb_unmount():
        payload = request.get_json(force=True) or {}
        mid = payload.get("mount_id")
        if not mid:
            return jsonify({"error": "mount_id required"}), 400
        unmount_smb(mid)
        return jsonify({"unmounted": mid})

    @app.route("/api/smb/list")
    @require_auth
    def smb_list():
        mid = request.args.get("mount_id")
        path = request.args.get("path", "/")
        if not mid:
            return jsonify({"error": "mount_id required"}), 400
        try:
            data = list_smb(mid, path)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/smb/queue", methods=["POST"])
    @require_auth
    def smb_queue():
        try:
            payload = request.get_json(force=True) or {}
            mid = payload.get("mount_id")
            rel_path = payload.get("path", "/")
            if not mid:
                return jsonify({"error": "mount_id required"}), 400
            mounts = tracker.list_smb_mounts()
            entry = mounts.get(mid)
            mnt = entry.get("path") if isinstance(entry, dict) else entry
            if not mnt:
                return jsonify({"error": "mount not found"}), 400
            base = pathlib.Path(mnt)
            target = ensure_under(base, base / rel_path.lstrip("/"))
            if not target.is_file():
                return jsonify({"error": "file not found"}), 400
            staging_dir = "/mnt/smb_staging"
            if config_manager:
                try:
                    cfg = config_manager.read()
                    staging_dir = cfg.get("smb_staging_dir", staging_dir) or staging_dir
                except Exception:
                    pass
            dest_root = pathlib.Path(staging_dir)
            dest_root.mkdir(parents=True, exist_ok=True)
            def unique_path(root: pathlib.Path, name: str) -> pathlib.Path:
                cand = root / name
                stem = cand.stem
                suffix = cand.suffix
                idx = 1
                while cand.exists():
                    cand = root / f"{stem}({idx}){suffix}"
                    idx += 1
                return cand
            dest = unique_path(dest_root, target.name)
            dest_path = dest
            staging_busy = tracker.has_active_nonqueued() or dest_root.exists() and any(dest_root.iterdir())
            # detect matching sidecar .srt to copy alongside
            sidecar = None
            try:
                stem = target.stem
                exact = target.parent / f"{stem}.srt"
                if exact.is_file():
                    sidecar = exact
                else:
                    for cand in sorted(target.parent.glob(f"{stem}.*.srt")):
                        if cand.is_file():
                            sidecar = cand
                            break
            except Exception:
                sidecar = None
            if staging_busy:
                tracker.add_smb_pending({"mount_id": mid, "source": str(target), "dest": str(dest_path), "sidecar": str(sidecar) if sidecar else None})
                if not tracker.has_active(str(dest_path)):
                    tracker.start(str(dest_path), str(dest_path), info=None, state="queued")
                    tracker.set_message(str(dest_path), "SMB copy queued (encoder busy)")
                tracker.add_event(f"Queued SMB copy until encoder idle: {target} -> {dest_path}")
                return jsonify({"queued": str(dest_path), "source": str(target), "pending": True})
            allowlist = load_smb_allowlist()
            allowlist.add(dest_path.name)
            if sidecar:
                allowlist.add(Path(dest_path.parent, Path(sidecar).name).name)
            save_smb_allowlist(allowlist)
            shutil.copy2(target, dest_path)
            if sidecar:
                try:
                    shutil.copy2(sidecar, dest_path.parent / Path(sidecar).name)
                    tracker.add_event(f"Copied external subtitle: {sidecar}")
                except Exception:
                    tracker.add_event(f"Failed to copy external subtitle: {sidecar}", level="error")
            tracker.add_manual_file(str(dest_path))
            tracker.add_event(f"Copied from SMB and staged: {target} -> {dest_path}")
            if not tracker.has_active(str(dest_path)):
                tracker.start(str(dest_path), str(dest_path), info=None, state="queued")
            return jsonify({"queued": str(dest_path), "source": str(target), "pending": False})
        except Exception as exc:
            try:
                tracker.add_event(f"SMB queue failed: {exc}", level="error")
            except Exception:
                pass
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/makemkv/info")
    @require_auth
    def makemkv_info():
        t0 = time.time()
        try:
            force = str(request.args.get("force", "")).lower() in ("1", "true", "yes")
            if not force and tracker.disc_scan_paused():
                cached = tracker.disc_info() or {}
                cached["paused"] = True
                return jsonify(cached)
            proc = subprocess.Popen(
                ["makemkvcon", "-r", "--cache=1", "info", "disc:0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                raw_output, _ = proc.communicate(timeout=15)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    proc.kill()
                except Exception:
                    pass
                raw_output, _ = proc.communicate()
            raw_output = raw_output or ""
            if not raw_output:
                raw_output = "No output from makemkvcon (disc:0)."
            try:
                parsed = parse_makemkv_info_output(raw_output)
            except Exception as exc:
                parsed = {"raw": raw_output, "error": str(exc)}
            if not parsed.get("raw"):
                parsed["raw"] = raw_output
            disc_type = ""
            ro_low = raw_output.lower()
            if "blu-ray disc" in ro_low or "bluray" in ro_low:
                disc_type = "bluray"
            elif "dvd" in ro_low:
                disc_type = "dvd"
            info_payload = {
                "disc_index": 0,
                "info": parsed,
                "raw": parsed.get("raw", raw_output),
            }
            if parsed.get("summary"):
                info_payload["summary"] = parsed["summary"]
            if parsed.get("formatted"):
                info_payload["formatted"] = parsed["formatted"]
            if disc_type:
                info_payload["disc_type"] = disc_type
            if timed_out:
                info_payload["pending"] = True
                info_payload["note"] = "MakeMKV scan still in progress"
                global MAKEMKV_TIMEOUT_EVENT_TS
                now = time.time()
                if now - MAKEMKV_TIMEOUT_EVENT_TS > 30:
                    tracker.add_event("MakeMKV info scan timed out; returning partial output")
                    MAKEMKV_TIMEOUT_EVENT_TS = now
            tracker.set_disc_info(info_payload)
            if force:
                try:
                    tracker.set_disc_preserve(True)
                except Exception:
                    pass
            rc = proc.returncode if not timed_out else 124
            if rc and rc != 0 and not timed_out:
                info_payload["error"] = parsed.get("error") or "info failed"
                info_payload["rc"] = rc
                tracker.add_event(f"MakeMKV info failed (rc={rc})", level="error")
            return jsonify(info_payload)
        except FileNotFoundError:
            tracker.add_event("MakeMKV not found when fetching disc info", level="error")
            return jsonify({"error": "makemkvcon not found"}), 500
        except Exception as exc:
            tracker.add_event(f"MakeMKV info error: {exc}", level="error")
            return jsonify({"error": str(exc)}), 500
        finally:
            log_timing("api/makemkv/info", t0)

    @app.route("/api/retry", methods=["POST"])
    @require_auth
    def retry_job():
        payload = request.get_json(force=True) or {}
        src = (payload.get("source") or "").strip()
        if not src:
            return jsonify({"queued": False, "error": "source required"}), 400
        try:
            if src.startswith("disc:"):
                tracker.request_disc_rip("manual")
                tracker.add_event(f"Retry requested for disc rip ({src})")
                return jsonify({"queued": True, "type": "disc"})
            p = Path(src)
            if not p.exists():
                return jsonify({"queued": False, "error": "source missing"}), 400
            tracker.clear_canceled(src)
            tracker.add_manual_file(src)
            tracker.add_event(f"Retry queued: {src}")
            return jsonify({"queued": True, "type": "file"})
        except Exception as exc:
            return jsonify({"queued": False, "error": str(exc)}), 500

    @app.route("/api/makemkv/rip", methods=["POST"])
    @require_auth
    def makemkv_rip():
        try:
            tracker.allow_disc_rip()
            tracker.resume_disc_scan()
        except Exception:
            pass
        tracker.request_disc_rip("manual")
        tracker.add_event("Manual MakeMKV rip requested.")
        return jsonify({"requested": True})

    @app.route("/api/makemkv/stop", methods=["POST"])
    @require_auth
    def makemkv_stop():
        snap = tracker.snapshot()
        stopped = 0
        for item in snap.get("active", []):
            src = (item.get("source") or "").strip()
            state = (item.get("state") or "").strip().lower()
            if src.startswith("disc:") or state == "ripping":
                tracker.stop_proc(src)
                stopped += 1
        if stopped:
            tracker.add_event(f"MakeMKV rip canceled ({stopped} task{'s' if stopped != 1 else ''}).")
            try:
                tracker.clear_disc_info()
            except Exception:
                pass
        return jsonify({"stopped": stopped})

    @app.route("/api/makemkv/stop_all", methods=["POST"])
    @require_auth
    def makemkv_stop_all():
        snap = tracker.snapshot()
        stopped = 0
        for item in snap.get("active", []):
            src = (item.get("source") or "").strip()
            state = (item.get("state") or "").strip().lower()
            if src.startswith("disc:") or state == "ripping":
                tracker.stop_proc(src)
                stopped += 1
        try:
            tracker.block_disc_rip()
            tracker.pause_disc_scan()
        except Exception:
            pass
        tracker.add_event("Stop All Ripping enabled; auto-rip paused.")
        return jsonify({"stopped": stopped, "blocked": True})

    @app.route("/api/makemkv/rename", methods=["POST"])
    @require_auth
    def makemkv_rename():
        payload = request.get_json(force=True) or {}
        src = (payload.get("source") or "").strip() or "disc:0"
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"ok": False, "error": "name required"}), 400
        safe = Path(name).name.strip()
        if not safe:
            return jsonify({"ok": False, "error": "invalid name"}), 400
        tracker.set_rename(src, safe)
        tracker.add_event(f"Rip rename set for {src}: {safe}")
        return jsonify({"ok": True, "name": safe})

    @app.route("/api/makemkv/eject", methods=["POST"])
    @require_auth
    def makemkv_eject():
        dev = request.json.get("device") if request.is_json else None
        device = dev or "/dev/sr0"
        # Build candidate device list: primary + inferred sg sibling + common fallbacks
        candidates = [device]
        try:
            if device.startswith("/dev/sr"):
                num = "".join(ch for ch in device if ch.isdigit())
                if num:
                    candidates.append(f"/dev/sg{num}")
        except Exception:
            pass
        candidates.extend(["/dev/sr0", "/dev/sg1", "/dev/sg0"])
        seen = []
        dedup = []
        for c in candidates:
            if c and c not in seen:
                dedup.append(c)
                seen.append(c)
        candidates = dedup
        try:
            attempts = []
            for devnode in candidates:
                attempts.extend([
                    ["eject", "-i", "off", devnode],
                    ["sg_prevent", "--allow", devnode],
                    ["sg_start", "--stop", devnode],
                    ["eject", "-v", "-F", devnode],
                    ["eject", devnode],
                    ["sg_raw", devnode, "1b", "00", "00", "00", "02", "00"],
                ])
            errors = []
            for cmd in attempts:
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        tracker.add_event(f"Ejected disc ({device}) via {' '.join(cmd)}.")
                        tracker.clear_disc_info()
                        return jsonify({"ok": True})
                    errors.append(res.stderr.strip() or res.stdout.strip() or f"{cmd} rc={res.returncode}")
                except FileNotFoundError:
                    errors.append(f"{cmd[0]} missing")
                except Exception as exc:
                    errors.append(f"{cmd}: {exc}")
            msg = "; ".join([e for e in errors if e]) or "eject failed"
            tracker.add_event(f"Eject failed: {msg}", level="error")
            return jsonify({"ok": False, "error": msg}), 500
        except FileNotFoundError as fe:
            tracker.add_event(f"Eject tool missing: {fe}", level="error")
            return jsonify({"ok": False, "error": "eject/sg_raw not found"}), 500
        except Exception as exc:
            tracker.add_event(f"Eject error: {exc}", level="error")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/makemkv/register", methods=["POST"])
    @require_auth
    def makemkv_register():
        payload = request.get_json(force=True) or {}
        raw_key = (payload.get("key") or "")
        def sanitize_key(k: str) -> str:
            s = (k or "").strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1].strip()
            return s
        key = sanitize_key(raw_key)
        if not key:
            return jsonify({"error": "key required"}), 400
        settings_path = pathlib.Path("/root/.MakeMKV/settings.conf")
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        def write_key_to_settings(k: str):
            try:
                lines = []
                if settings_path.exists():
                    for ln in settings_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if not ln.strip().startswith("app_Key"):
                            lines.append(ln)
                lines.append(f'app_Key = "{k}"')
                settings_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return True
            except Exception:
                return False
        try:
            res = subprocess.run(["makemkvcon", "reg", key], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                tracker.add_event("MakeMKV registered successfully.")
                return jsonify({"registered": True})
            stderr = res.stderr.strip() if res.stderr else ""
            stdout = res.stdout.strip() if res.stdout else ""
            msg = "; ".join([p for p in [stderr, stdout] if p]) or f"exit code {res.returncode}"
            # Always persist key even if makemkvcon rejects it, but report failure
            write_key_to_settings(key)
            tracker.add_event(f"MakeMKV registration failed: {msg}", level="error")
            return jsonify({"registered": False, "error": msg}), 400
        except FileNotFoundError:
            tracker.add_event("MakeMKV registration failed: makemkvcon not found", level="error")
            return jsonify({"registered": False, "error": "makemkvcon not found"}), 500

    @app.route("/api/makemkv/update_check")
    @require_auth
    def makemkv_update_check():
        try:
            res = subprocess.run(
                ["makemkvcon", "-r", "--cache=1", "info", "disc:0"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            stdout = res.stdout.strip() if res.stdout else ""
            stderr = res.stderr.strip() if res.stderr else ""
            version_line = ""
            for ln in (stdout.splitlines() if stdout else []):
                if "MakeMKV v" in ln:
                    version_line = ln
                    break
            msg = version_line or (stderr or "") or (stdout or "") or f"exit code {res.returncode}"
            ok = res.returncode == 0 and bool(version_line)
            installed_version = None
            if version_line:
                try:
                    installed_version = version_line.split("MakeMKV")[1].strip().split()[0]
                except Exception:
                    installed_version = None
            return jsonify({"ok": ok, "stdout": stdout, "stderr": stderr, "message": msg, "returncode": res.returncode, "installed_version": installed_version})
        except FileNotFoundError:
            return jsonify({"ok": False, "error": "makemkvcon not found"}), 500
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/presets", methods=["GET", "POST", "DELETE"])
    def hb_presets():
        if not config_manager:
            return jsonify({"presets": []})
        if request.method == "GET":
            cfg = config_manager.read()
            return jsonify({"presets": cfg.get("handbrake_presets", [])})
        payload = request.get_json(force=True) or {}
        if request.method == "POST":
            name = (payload.get("name") or "").strip()
            if not name:
                return jsonify({"error": "name required"}), 400
            cfg = config_manager.read()
            presets = cfg.get("handbrake_presets", [])
            # replace if exists
            presets = [p for p in presets if p.get("name") != name]
            presets.append({
                "name": name,
                "handbrake": payload.get("handbrake", {}),
                "handbrake_dvd": payload.get("handbrake_dvd", {}),
                "handbrake_br": payload.get("handbrake_br", {}),
            })
            cfg["handbrake_presets"] = presets
            config_manager.update(cfg)
            return jsonify({"saved": name})
        if request.method == "DELETE":
            name = (payload.get("name") or "").strip()
            cfg = config_manager.read()
            presets = [p for p in cfg.get("handbrake_presets", []) if p.get("name") != name]
            cfg["handbrake_presets"] = presets
            config_manager.update(cfg)
            return jsonify({"deleted": name})

    @app.route("/api/stop", methods=["POST"])
    def stop():
        payload = request.get_json(force=True) or {}
        src = payload.get("source")
        delete_src = payload.get("delete_source", False)
        if src:
            tracker.stop_proc(src)
            tracker.add_event(f"Stopped encode: {src}")
            if delete_src:
                cleanup_staged_file(src)
                tracker.add_event(f"Deleted staged source: {src}")
        return jsonify({"stopped": bool(src)})

    @app.route("/api/confirm", methods=["POST"])
    def confirm_job():
        payload = request.get_json(force=True) or {}
        src = payload.get("source")
        action = payload.get("action", "cancel")
        if not src:
            return jsonify({"error": "source required"}), 400
        if action == "proceed":
            tracker.clear_confirm_required(src)
            tracker.add_confirm_ok(src)
            tracker.set_state(src, "starting")
            tracker.set_message(src, "")
            tracker.add_event(f"Proceeding with encode: {src}")
            return jsonify({"proceeded": src})
        else:
            tracker.stop_proc(src)
            tracker.clear_confirm_required(src)
            tracker.clear_confirm_ok(src)
            cleanup_staged_file(src)
            tracker.add_event(f"Canceled encode after warning: {src}")
            return jsonify({"canceled": src})

    @app.route("/api/clear", methods=["POST"])
    def clear():
        payload = request.get_json(force=True) or {}
        status = payload.get("status")
        if status == "all":
            tracker.clear_history(None)
        else:
            tracker.clear_history(status)
        return jsonify({"cleared": status or "all"})

    return app


def start_web_server(tracker, config_manager=None, port: int = 5959):
    app = create_app(tracker, config_manager=config_manager)

    def _run():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

    import threading

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
