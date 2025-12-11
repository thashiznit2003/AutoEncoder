MAIN_PAGE_TEMPLATE = """
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
    .brand { display:flex; align-items:center; gap:12px; }
    .logo-img { height: 48px; width: auto; filter: drop-shadow(0 0 6px rgba(79,70,229,0.4)); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: linear-gradient(145deg, #111827, #0d1528); border: 1px solid #1f2937; border-radius: 14px; padding: 12px; box-shadow: 0 16px 38px rgba(0,0,0,0.35), inset 0 0 0 1px rgba(255,255,255,0.03); }
    .panel h2 { margin: 0 0 10px 0; font-size: 15px; color: #a5b4fc; letter-spacing: 0.4px; display:flex; align-items:center; gap:8px; }
    form { display: grid; gap: 8px; margin-top: 8px; }
    label { font-size: 12px; color: #cbd5e1; display: grid; gap: 4px; }
    input, select, textarea { padding: 9px 11px; border-radius: 10px; border: 1px solid #1f2937; background: #0b1220; color: #e2e8f0; transition: border 0.2s ease, box-shadow 0.2s ease; }
    textarea { font-family: "SFMono-Regular", Menlo, Consolas, monospace; }
    input:focus, select:focus, textarea:focus { outline: none; border-color: #60a5fa; box-shadow: 0 0 0 1px rgba(96,165,250,0.5); }
    button { padding: 9px 12px; border: 0; border-radius: 10px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; font-weight: 700; cursor: pointer; transition: transform 0.08s ease, box-shadow 0.2s; }
    button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(79,70,229,0.35); }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 12px; padding: 10px; overflow: auto; height: 320px; border: 1px solid #1f2937; white-space: pre-wrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); word-break: break-word; overflow-wrap: anywhere; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; color: #0f172a; font-weight: 700; }
    .badge.running { background: #fde047; }
    .badge.starting { background: #fb923c; color:#0b1220; }
    .badge.success { background: #34d399; }
    .badge.error { background: #f87171; }
    .badge.queued { background: #60a5fa; color: #0b1220; }
    .badge.canceled { background: #cbd5e1; color: #0b1220; }
    .badge.ripping { background: #38bdf8; color:#0b1220; }
    .progress { background: #1f2937; border-radius: 8px; height: 9px; overflow: hidden; margin-top: 6px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .progress-bar { background: linear-gradient(90deg, #22c55e, #4ade80); height: 100%; transition: width 0.2s ease; }
    .item { padding: 9px; border-bottom: 1px solid #1f2937; }
    .item:last-child { border-bottom: 0; }
    .muted { color: #94a3b8; }
    .flex-between { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .path { word-break: break-all; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 6px; }
    .metric-card { background: linear-gradient(145deg, #0f1b2e, #0c1626); border: 1px solid #1d2a40; border-radius: 12px; padding: 12px 14px; min-height: 78px; display: flex; align-items: center; gap: 10px; box-shadow: 0 10px 24px rgba(0,0,0,0.35), inset 0 0 0 1px rgba(255,255,255,0.02); }
    .metric-card.metric-standard { align-items: center; padding: 6px 8px; min-height: 44px; gap: 8px; }
    .metric-card.usb-card { background: #0f172a; border: 1px solid #1f2937; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03); padding: 10px 12px; min-height: 64px; gap: 6px; }
    .metric-icon { width: 28px; height: 28px; border-radius: 999px; background: linear-gradient(135deg, #60a5fa, #a78bfa); color: #0b1220; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; box-shadow: 0 6px 14px rgba(79,70,229,0.35); }
    .metric-icon svg { width: 100%; height: 100%; }
    .usb-card .metric-icon { width: 24px; height: 24px; font-size: 12px; background: linear-gradient(135deg, #60a5fa, #a78bfa); color: #0b1220; box-shadow: 0 6px 14px rgba(79,70,229,0.35); }
    .metric-text { display: flex; flex-direction: column; line-height: 1.15; white-space: normal; word-break: break-word; overflow-wrap: anywhere; }
    .metric-label { font-size: 14px; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.8px; }
    .usb-card .metric-label { letter-spacing: 0.6px; }
    .metric-value { font-size: 10px; font-weight: 700; color: #e5edff; }
    .smb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
    .smb-list { max-height: 220px; overflow-y: auto; border: 1px solid #1f2937; border-radius: 10px; padding: 8px; background: #0b1220; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .smb-item { padding: 6px 0; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .smb-item:last-child { border-bottom: 0; }
    .smb-btn { padding: 7px 10px; border: 0; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; cursor: pointer; }
    .smb-path { word-break: break-all; flex: 1; }
    .icon { width: 16px; height: 16px; display:inline-block; }
    .icon.mario-icon svg { width: 100%; height: 100%; image-rendering: pixelated; }
  </style>
</head>
<body>
  <header>
    <h1 class="brand"><img src="/assets/linux-video-encoder-icon.svg" alt="Logo" class="logo-img" /> <span>Linux Video Encoder v__VERSION__</span></h1>
    <div style="display:flex; gap:10px; align-items:center;">
      <a href="/settings" style="color:#fff; text-decoration:none;"><button type="button">Settings</button></a>
      <button onclick="window.location.reload(true)">Hard Reload</button>
      <div id="clock" class="muted"></div>
    </div>
  </header>
  <div class="grid">
    <div class="panel">
      <h2>🟢 Active Encodes</h2>
      <div class="muted" id="hb-runtime"></div>
      <div id="active"></div>
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
      <div style="display:flex; align-items:center; gap:8px; justify-content: space-between; margin-bottom:6px;">
        <h2 style="margin:0;">📣 Status Messages</h2>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <button id="copy-event-last" class="smb-btn" style="padding:6px 8px;">Copy Last</button>
          <button id="copy-event-last10" class="smb-btn" style="padding:6px 8px;">Copy Last 10</button>
        </div>
      </div>
      <div id="events" class="log"></div>
    </div>
    <div class="panel">
      <h2>📊 System Metrics</h2>
      <div id="metrics" class="log"></div>
    </div>
    <div class="panel">
      <h2><span class="icon mario-icon" aria-hidden="true"><svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
        <rect width="16" height="16" fill="none"/>
        <rect x="2" y="0" width="12" height="1" fill="#d62828"/>
        <rect x="1" y="1" width="14" height="1" fill="#d62828"/>
        <rect x="1" y="2" width="7" height="1" fill="#d62828"/><rect x="9" y="2" width="6" height="1" fill="#d62828"/>
        <rect x="0" y="3" width="4" height="1" fill="#7c4a1d"/><rect x="4" y="3" width="8" height="1" fill="#f2c29c"/><rect x="12" y="3" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="4" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="4" width="10" height="1" fill="#f2c29c"/><rect x="12" y="4" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="5" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="5" width="2" height="1" fill="#f2c29c"/><rect x="4" y="5" width="2" height="1" fill="#0b1220"/><rect x="6" y="5" width="2" height="1" fill="#f2c29c"/><rect x="8" y="5" width="2" height="1" fill="#0b1220"/><rect x="10" y="5" width="2" height="1" fill="#f2c29c"/><rect x="12" y="5" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="6" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="6" width="4" height="1" fill="#f2c29c"/><rect x="6" y="6" width="2" height="1" fill="#3b2a1a"/><rect x="8" y="6" width="4" height="1" fill="#f2c29c"/><rect x="12" y="6" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="7" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="7" width="2" height="1" fill="#f2c29c"/><rect x="4" y="7" width="6" height="1" fill="#3b2a1a"/><rect x="10" y="7" width="2" height="1" fill="#f2c29c"/><rect x="12" y="7" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="8" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="8" width="10" height="1" fill="#f2c29c"/><rect x="12" y="8" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="9" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="9" width="2" height="1" fill="#f2c29c"/><rect x="4" y="9" width="6" height="1" fill="#2563eb"/><rect x="10" y="9" width="2" height="1" fill="#f2c29c"/><rect x="12" y="9" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="10" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="10" width="2" height="1" fill="#f2c29c"/><rect x="4" y="10" width="6" height="1" fill="#2563eb"/><rect x="10" y="10" width="2" height="1" fill="#f2c29c"/><rect x="12" y="10" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="11" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="11" width="2" height="1" fill="#f2c29c"/><rect x="4" y="11" width="6" height="1" fill="#2563eb"/><rect x="10" y="11" width="2" height="1" fill="#f2c29c"/><rect x="12" y="11" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="12" width="2" height="1" fill="#7c4a1d"/><rect x="2" y="12" width="2" height="1" fill="#f2c29c"/><rect x="4" y="12" width="6" height="1" fill="#2563eb"/><rect x="10" y="12" width="2" height="1" fill="#f2c29c"/><rect x="12" y="12" width="4" height="1" fill="#7c4a1d"/>
        <rect x="0" y="13" width="3" height="1" fill="#7c4a1d"/><rect x="3" y="13" width="8" height="1" fill="#2563eb"/><rect x="11" y="13" width="5" height="1" fill="#7c4a1d"/>
        <rect x="0" y="14" width="1" height="1" fill="none"/><rect x="1" y="14" width="1" height="1" fill="#7c4a1d"/><rect x="2" y="14" width="2" height="1" fill="#2563eb"/><rect x="4" y="14" width="6" height="1" fill="none"/><rect x="10" y="14" width="2" height="1" fill="#2563eb"/><rect x="12" y="14" width="2" height="1" fill="#7c4a1d"/>
        <rect x="0" y="15" width="1" height="1" fill="none"/><rect x="1" y="15" width="2" height="1" fill="#7c4a1d"/><rect x="3" y="15" width="2" height="1" fill="#2563eb"/><rect x="5" y="15" width="4" height="1" fill="none"/><rect x="9" y="15" width="2" height="1" fill="#2563eb"/><rect x="11" y="15" width="2" height="1" fill="#7c4a1d"/>
      </svg></span> SMB Browser</h2>
      <form id="smb-form" style="display:grid; gap:6px;">
        <input id="smb-url" placeholder="smb://server/share[/path]" />
        <input id="smb-user" placeholder="Username" />
        <input id="smb-pass" placeholder="Password" type="password" />
        <button type="button" id="smb-connect">Connect</button>
      </form>
      <div class="smb-grid" style="margin-top:8px;">
        <div>
          <div class="muted">Mounts (click to browse)</div>
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
    let eventsCache = [];
    const smbForm = document.getElementById("smb-form");
    function connectSmb() {
      document.getElementById("smb-connect").click();
    }

    async function fetchJSON(url, opts) {
      const res = await fetch(url, opts);
      return res.json();
    }

    function renderMetrics(metrics) {
      const el = document.getElementById("metrics");
      if (!metrics) {
        el.textContent = "Metrics unavailable.";
        return;
      }
      const icons = {
        cpu: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="8.5" y="8.5" width="15" height="15" rx="2"/><rect x="12" y="12" width="9" height="9" rx="1"/><path d="M12 4v3m4-3v3m4-3v3M12 28v-3m4 3v-3m4 3v-3M4 12h3m-3 4h3m-3 4h3M28 12h-3m3 4h-3m3 4h-3"/></svg>`,
        gpu: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="9" width="22" height="14" rx="2.5"/><circle cx="12" cy="16" r="3.5"/><path d="M22 12h3v8h-3zM8 12h2M8 16h2M8 20h2M26 14h2m-2 4h2m-8 6v-4m-4 4v-4"/></svg>`,
        memory: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="24" height="10" rx="2"/><path d="M8 11v-2m4 2v-2m4 2v-2m4 2v-2M8 23v-2m4 2v-2m4 2v-2m4 2v-2M8 15h16"/></svg>`,
        disk: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="6.5" y="6.5" width="19" height="19" rx="3"/><circle cx="16" cy="16" r="4.5"/><circle cx="16" cy="16" r="1"/><path d="M22 22.5h-5"/></svg>`,
        output: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9h9l2 3h9v11a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9Z"/><path d="M6 9h7"/></svg>`,
        network: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="16" cy="8" r="3.5"/><circle cx="8.5" cy="22" r="3.5"/><circle cx="23.5" cy="22" r="3.5"/><path d="M14.5 11.5 10 18.5m7-7 4.5 7"/></svg>`,
        usb: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 6h4v6h-4z"/><path d="M12 7h2M18 7h2"/><path d="M16 12v8"/><rect x="13" y="20" width="6" height="5" rx="1.2"/><path d="M16 25v3"/></svg>`
      };
      const cards = [];
      const cpuPct = (metrics.cpu_pct !== undefined && metrics.cpu_pct !== null) ? metrics.cpu_pct.toFixed(1) + "%" : "n/a";
      const toGb = (mb) => (mb === undefined || mb === null) ? "n/a" : (mb / 1024).toFixed(1) + " GB";
      cards.push({ icon: icons.cpu, label: "CPU", value: cpuPct });
      if (metrics.gpu) {
        const g = metrics.gpu;
        cards.push({ icon: icons.gpu, label: "GPU", value: g.util + "%<br>" + toGb(g.mem_used_mb) + " / " + toGb(g.mem_total_mb) });
      }
      if (metrics.mem) {
        cards.push({ icon: icons.memory, label: "Memory", value: toGb(metrics.mem.used_mb) + " / " + toGb(metrics.mem.total_mb) });
      }
      if (metrics.block) {
        cards.push({ icon: icons.disk, label: "Disk", value: toGb(metrics.block.read_mb) + " r / " + toGb(metrics.block.write_mb) + " w" });
      }
      if (metrics.fs) {
        cards.push({ icon: icons.output, label: "Output", value: metrics.fs.free_gb + " / " + metrics.fs.total_gb + " GB" });
      }
      if (metrics.net) {
        cards.push({ icon: icons.network, label: "Network", value: metrics.net.rx_mb + "MB ↓ / " + metrics.net.tx_mb + "MB ↑" });
      }
      const prevUsb = document.getElementById("usb-status") || {};
      const usbStatusText = prevUsb.textContent || "USB status: unknown";
      const usbStatusColor = prevUsb.style ? (prevUsb.style.color || "#94a3b8") : "#94a3b8";
      const cardsHtml = cards.map(c => `
        <div class="metric-card metric-standard">
          <div class="metric-icon">${c.icon}</div>
          <div class="metric-text">
            <div class="metric-value">${c.value}</div>
            <div class="metric-label">${c.label}</div>
          </div>
        </div>
      `).join("");
      const usbCard = `
        <div class="metric-card usb-card" style="grid-column: 1 / -1;">
          <div class="metric-icon">${icons.usb}</div>
          <div style="display:flex; flex-direction:column; flex:1; gap:4px;">
            <div class="metric-label" style="margin-bottom:2px;">USB Controls</div>
            <div style="display:flex; flex-wrap:nowrap; gap:6px; align-items:center; width:100%;">
              <button type="button" id="usb-refresh" style="padding:4px 6px; font-size:9px; flex:1 1 0; min-width:0; white-space:nowrap;">Refresh</button>
              <button type="button" id="usb-force-remount" style="padding:4px 6px; font-size:9px; flex:1 1 0; min-width:0; white-space:nowrap;">Force Remount</button>
              <button type="button" id="usb-eject" style="padding:4px 6px; font-size:9px; flex:1 1 0; min-width:0; white-space:nowrap;">Eject</button>
            </div>
            <div id="usb-status" class="muted" style="min-height:14px; color:${usbStatusColor};">${usbStatusText}</div>
          </div>
        </div>`;
      el.innerHTML = '<div class="metric-grid">' + cardsHtml + usbCard + '</div>';
      bindUsbButtons();
    }

    function renderLogs(lines) {
      const el = document.getElementById("logs");
      const atBottom = (el.scrollTop + el.clientHeight) >= (el.scrollHeight - 20);
      el.textContent = (lines && lines.length ? lines : ["Ready to encode"]).join("\\n");
      if (atBottom) {
        el.scrollTop = el.scrollHeight;
      }
    }

    function bindUsbButtons() {
      const refreshBtn = document.getElementById("usb-refresh");
      const forceBtn = document.getElementById("usb-force-remount");
      const ejectBtn = document.getElementById("usb-eject");
      if (refreshBtn) {
        refreshBtn.onclick = async function() {
          const prev = refreshBtn.textContent;
          refreshBtn.disabled = true;
          refreshBtn.textContent = "Refreshing...";
          try {
            await fetchJSON("/api/usb/refresh", { method: "POST" });
          } catch (err) {
            console.error("USB refresh failed", err);
          } finally {
            refreshBtn.disabled = false;
            refreshBtn.textContent = prev;
          }
        };
      }
      if (ejectBtn) {
        ejectBtn.onclick = async function() {
          const prev = ejectBtn.textContent;
          ejectBtn.disabled = true;
          ejectBtn.textContent = "Ejecting...";
          try {
            await fetchJSON("/api/usb/eject", { method: "POST" });
          } catch (err) {
            console.error("USB eject failed", err);
          } finally {
            ejectBtn.disabled = false;
            ejectBtn.textContent = prev;
          }
        };
      }
      if (forceBtn) {
        forceBtn.onclick = async function() {
          const prev = forceBtn.textContent;
          forceBtn.disabled = true;
          forceBtn.textContent = "Remounting...";
          try {
            await fetchJSON("/api/usb/force_remount", { method: "POST" });
          } catch (err) {
            console.error("USB force remount failed", err);
          } finally {
            forceBtn.disabled = false;
            forceBtn.textContent = prev;
          }
        };
      }
    }

    function fmtDuration(sec) {
      if (!sec && sec !== 0) return "";
      const s = Math.floor(sec % 60);
      const m = Math.floor(sec / 60) % 60;
      const h = Math.floor(sec / 3600);
      return [h, m, s].map(v => String(v).padStart(2, "0")).join(":");
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
        if (state === "running") {
          controls = '<button class="stop-btn" data-src="' + encodeURIComponent(item.source || "") + '">Stop</button>';
        } else if (state === "confirm") {
          controls = '<button class="confirm-btn" data-action="proceed" data-src="' + encodeURIComponent(item.source || "") + '">Proceed</button> '
                   + '<button class="confirm-btn" data-action="cancel" data-src="' + encodeURIComponent(item.source || "") + '">Cancel</button>';
        } else if (state === "queued") {
          controls = '<button class="remove-queued-btn" data-src="' + encodeURIComponent(item.source || "") + '">Remove</button>';
        }
        const infoLine = item.info ? '<div class="muted">' + item.info + '</div>' : "";
        return [
          '<div class="item">',
          '  <div class="flex-between">',
          '    <div class="path">' + (item.source || "") + '</div>',
          '    <div>' + badge + ' ' + controls + '</div>',
          '  </div>',
          '  <div class="muted">-> ' + (item.destination || "") + '</div>',
          '  <div class="muted">' + (item.message || "") + '</div>',
          infoLine,
          '  <div class="muted">' + (etaText || (duration ? ((state === "queued") ? "Queued for: " + duration : "Encode elapsed: " + duration) : "")) + '</div>',
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
        const lbNote = (hbCfg.low_bitrate_auto_skip ? "Low bitrate: auto-skip" : (hbCfg.low_bitrate_auto_proceed ? "Low bitrate: auto-proceed" : "Low bitrate: ask"));
        const audioModeLabel = (hb.audio_mode === "auto_dolby") ? "Auto Dolby" : (hb.audio_mode === "copy" ? "copy" : ((hb.audio_bitrate_kbps || "128") + " kbps"));
        const audioOffsetLabel = (hb.audio_offset_ms !== undefined && hb.audio_offset_ms !== null) ? (hb.audio_offset_ms + " ms (single)") : "0 ms (single)";
        document.getElementById("hb-runtime").textContent =
          "Runtime HB settings: Encoder=" + (hb.encoder || "x264") +
          " | Default RF=" + (hb.quality ?? 20) +
          " | DVD RF=" + (hbDvd.quality ?? 20) +
          " | BR RF=" + (hbBr.quality ?? 25) +
          " | Ext=" + hbExt +
          " | " + lbNote +
          " | Audio=" + audioModeLabel +
          " | Offset=" + audioOffsetLabel;
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
        eventsCache = events || [];
        const lines = (eventsCache || []).map(function(ev) {
          return "[" + new Date(ev.ts * 1000).toLocaleTimeString() + "] " + ev.message;
        });
        document.getElementById("events").textContent = lines.join("\\n") || "No recent events.";
      } catch (e) {
        document.getElementById("events").textContent = "Events unavailable.";
      }
      try {
        bindUsbButtons();
      } catch (e) {
        console.error("USB refresh/force setup failed", e);
      }
      try {
        const metrics = await fetchJSON("/api/metrics");
        renderMetrics(metrics);
      } catch (e) {
        document.getElementById("metrics").textContent = "Metrics unavailable.";
      }
    }

    function tickClock() {
      const now = new Date();
      document.getElementById("clock").textContent = now.toLocaleString();
    }

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
      if (e.target.classList.contains("remove-queued-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        const ok = confirm("Remove this queued item and delete the staged file?");
        if (!ok) return;
        await fetch("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src, delete_source: true }) });
        refresh();
      }
    });

    document.getElementById("handbrake-form")?.addEventListener("input", () => { hbDirty = true; });
    document.getElementById("makemkv-form")?.addEventListener("input", () => { mkDirty = true; });
    document.getElementById("makemkv-form")?.addEventListener("change", () => { mkDirty = true; });
    document.getElementById("handbrake-form")?.addEventListener("change", () => { hbDirty = true; });

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
        const selected = (id === smbMountId) ? "background:#1f2937;" : "";
        return '<div class="smb-item smb-select" data-id="' + id + '" style="' + selected + '"><div class="smb-path">' + (label || id) + '</div><button class="smb-btn smb-unmount" data-id="' + id + '">Unmount</button></div>';
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

    async function copyEvents(count) {
      const lines = (eventsCache || []).slice(-count).map(ev => "[" + new Date(ev.ts * 1000).toLocaleTimeString() + "] " + ev.message);
      const text = lines.join("\\n");
      try {
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
      } catch (err) {
        alert("Failed to copy: " + err);
      }
    }

    document.getElementById("copy-event-last").addEventListener("click", () => copyEvents(1));
    document.getElementById("copy-event-last10").addEventListener("click", () => copyEvents(10));

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
      const unmountBtn = e.target.closest(".smb-unmount");
      if (unmountBtn) {
        const id = unmountBtn.getAttribute("data-id");
        await fetch("/api/smb/unmount", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mount_id: id }) });
        if (smbMountId === id) { smbMountId = null; smbSelected = null; smbPath = "/"; document.getElementById("smb-browse").innerHTML = ""; }
        await smbRefreshMounts();
        return;
      }
      const mountItem = e.target.closest(".smb-select");
      if (mountItem) {
        const id = mountItem.getAttribute("data-id");
        smbMountId = id;
        smbSelected = null;
        smbPath = "/";
        await smbList("/");
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

SETTINGS_PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Settings - Linux Video Encoder v__VERSION__</title>
  <style>
    :root { color-scheme: dark; font-family: "Inter", "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: radial-gradient(circle at 18% 20%, rgba(59,130,246,0.12), transparent 40%), radial-gradient(circle at 80% 10%, rgba(94,234,212,0.12), transparent 32%), #0b1220; color: #e2e8f0; }
    header { padding: 14px 16px; background: linear-gradient(120deg, #0f172a, #0c1425); border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 28px rgba(0,0,0,0.35); }
    h1 { font-size: 18px; margin: 0; letter-spacing: 0.3px; display:flex; align-items:center; gap:10px; }
    .brand { display:flex; align-items:center; gap:10px; }
    .logo-img { height: 32px; width: auto; filter: drop-shadow(0 0 6px rgba(79,70,229,0.4)); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: linear-gradient(145deg, #111827, #0d1528); border: 1px solid #1f2937; border-radius: 14px; padding: 12px; box-shadow: 0 16px 38px rgba(0,0,0,0.35), inset 0 0 0 1px rgba(255,255,255,0.03); }
    .panel h2 { margin: 0 0 10px 0; font-size: 15px; color: #a5b4fc; letter-spacing: 0.4px; display:flex; align-items:center; gap:8px; }
    form { display: grid; gap: 8px; margin-top: 8px; }
    label { font-size: 12px; color: #cbd5e1; display: grid; gap: 4px; }
    input, select, textarea { padding: 9px 11px; border-radius: 10px; border: 1px solid #1f2937; background: #0b1220; color: #e2e8f0; transition: border 0.2s ease, box-shadow 0.2s ease; }
    textarea { font-family: "SFMono-Regular", Menlo, Consolas, monospace; }
    input:focus, select:focus, textarea:focus { outline: none; border-color: #60a5fa; box-shadow: 0 0 0 1px rgba(96,165,250,0.5); }
    button { padding: 9px 12px; border: 0; border-radius: 10px; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; font-weight: 700; cursor: pointer; transition: transform 0.08s ease, box-shadow 0.2s; }
    button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(79,70,229,0.35); }
    .muted { color: #94a3b8; }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 12px; padding: 10px; overflow: auto; border: 1px solid #1f2937; white-space: pre-wrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); word-break: break-word; overflow-wrap: anywhere; }
  </style>
</head>
<body>
  <header>
    <h1 class="brand"><img src="/assets/linux-video-encoder-icon.svg" alt="Logo" class="logo-img" /> <span>Settings – Linux Video Encoder v__VERSION__</span></h1>
    <div style="display:flex; gap:10px; align-items:center;">
      <a href="/" style="color:#fff; text-decoration:none;"><button type="button">Back to Main</button></a>
    </div>
  </header>
  <div class="grid">
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
        <label>Audio offset (ms, applies only when a single file is queued)
          <input id="hb-audio-offset" type="number" step="10" min="-2000" max="2000" placeholder="0" />
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
        <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin:6px 0;">
          <label style="display:flex; align-items:center; gap:6px; margin:0;">
            <input type="checkbox" id="lb-auto-proceed" /> Auto-proceed low bitrate
          </label>
          <label style="display:flex; align-items:center; gap:6px; margin:0;">
            <input type="checkbox" id="lb-auto-skip" /> Auto-skip low bitrate
          </label>
          <span id="lb-save-status" class="muted"></span>
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
        <h3 style="margin:0 0 6px 0; color:#cbd5e1; font-size:13px;">Disc Info</h3>
        <div class="muted" id="mk-disc-status">Disc status: unknown</div>
        <div style="display:flex; gap:6px; margin:6px 0; flex-wrap:wrap;">
          <button type="button" id="mk-refresh-info">Refresh disc info</button>
          <button type="button" id="mk-start-rip">Start rip</button>
          <button type="button" id="mk-copy-info">Copy disc info</button>
        </div>
        <textarea id="mk-info" class="log" style="height:160px; margin-top:4px; width:100%; box-sizing:border-box;" readonly placeholder="Disc info will appear here after detection."></textarea>
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
    <div class="panel">
      <h2>🐞 Diagnostics</h2>
      <div class="muted" style="margin-bottom:8px;">Push status, events, and log tail to the diagnostics repo using stored credentials.</div>
      <button type="button" id="diag-push">Push Diagnostics to GitHub</button>
      <div class="muted" id="diag-status" style="margin-top:6px;">Idle.</div>
    </div>
    <div class="panel">
      <h2>🔒 Authentication</h2>
      <div class="muted" style="margin-bottom:6px;">HTTP Basic auth for this UI/API.</div>
      <label>Username <input id="auth-user" placeholder="admin" /></label>
      <label>Password <input id="auth-pass" type="password" placeholder="changeme" /></label>
      <button type="button" id="auth-save">Save Auth</button>
      <div class="muted" style="margin-top:6px;">After changing, reload the page and use the new credentials.</div>
    </div>
  </div>
  <script>
    let hbDirty = false;
    let mkDirty = false;
    let authDirty = false;

    async function fetchJSON(url) {
      const res = await fetch(url);
      return res.json();
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
      document.getElementById("hb-audio-offset").value = (cfg.handbrake.audio_offset_ms !== undefined && cfg.handbrake.audio_offset_ms !== null) ? cfg.handbrake.audio_offset_ms : 0;
      document.getElementById("hb-audio-lang").value = (cfg.handbrake.audio_lang_list || []).join(", ");
      document.getElementById("hb-audio-tracks").value = cfg.handbrake.audio_track_list || "";
    }

    async function refreshSettings() {
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
        const lbNote = cfg.low_bitrate_auto_skip ? "Low bitrate: auto-skip" : (cfg.low_bitrate_auto_proceed ? "Low bitrate: auto-proceed" : "Low bitrate: ask");
        const audioModeLabel = (hb.audio_mode === "auto_dolby") ? "Auto Dolby" : (hb.audio_mode === "copy" ? "copy" : ((hb.audio_bitrate_kbps || "128") + " kbps"));
        const audioOffsetLabel = (hb.audio_offset_ms !== undefined && hb.audio_offset_ms !== null) ? (hb.audio_offset_ms + " ms (single file)") : "0 ms (single file)";
        document.getElementById("hb-summary").textContent = "Encoder: " + (hb.encoder || "x264")
          + " | Default RF: " + (hb.quality !== undefined && hb.quality !== null ? hb.quality : 20)
          + " | DVD RF: " + (hbDvd.quality !== undefined && hbDvd.quality !== null ? hbDvd.quality : 20)
          + " | BR RF: " + (hbBr.quality !== undefined && hbBr.quality !== null ? hbBr.quality : 25)
          + " | Ext: " + (hb.extension || ".mkv")
          + " | " + lbNote
          + " | Audio: " + audioModeLabel
          + " | Offset: " + audioOffsetLabel;
        document.getElementById("lb-auto-proceed").checked = !!cfg.low_bitrate_auto_proceed;
        document.getElementById("lb-auto-skip").checked = !!cfg.low_bitrate_auto_skip;
        if (!authDirty) {
          document.getElementById("auth-user").value = cfg.auth_user || "";
          document.getElementById("auth-pass").value = cfg.auth_password || "";
        }
      } catch (e) {
        console.error("Failed to load config", e);
      }
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
      const audioOffset = parseInt(document.getElementById("hb-audio-offset").value || "0", 10) || 0;
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
        low_bitrate_auto_proceed: document.getElementById("lb-auto-proceed").checked,
        low_bitrate_auto_skip: document.getElementById("lb-auto-skip").checked,
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
          audio_offset_ms: audioOffset,
          audio_lang_list: audioLang,
          audio_track_list: audioTracks,
          audio_all: audioAll,
          subtitle_mode: subtitleMode
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_offset_ms: audioOffset, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode, video_bitrate_kbps: targetBitrate, two_pass: twoPass },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_offset_ms: audioOffset, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode, video_bitrate_kbps: targetBitrate, two_pass: twoPass }
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      hbDirty = false;
      const lbStatus = document.getElementById("lb-save-status");
      if (lbStatus) {
        lbStatus.textContent = "Saved";
        setTimeout(() => { lbStatus.textContent = ""; }, 3000);
      }
      refreshSettings();
    });

    document.getElementById("hb-preset-save").addEventListener("click", async () => {
      const name = document.getElementById("hb-preset-name").value.trim();
      if (!name) { alert("Enter a preset name"); return; }
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
      const audioLang = (document.getElementById("hb-audio-lang").value || "").split(",").map(v => v.trim()).filter(Boolean);
      const audioTracks = document.getElementById("hb-audio-tracks").value || "";
      const audioDrcRaw = document.getElementById("hb-audio-drc").value;
      const audioDrc = audioDrcRaw === "" ? null : Number(audioDrcRaw);
      const audioGainRaw = document.getElementById("hb-audio-gain").value;
      const audioGain = audioGainRaw === "" ? null : Number(audioGainRaw);
      const audioOffset = parseInt(document.getElementById("hb-audio-offset").value || "0", 10) || 0;
      const body = {
        name,
        handbrake: {
          encoder: document.getElementById("hb-encoder").value,
          quality: qDefault,
          extension: ext,
          audio_mode: audioMode,
          audio_bitrate_kbps: audioBitrate,
          audio_encoder: audioEncoder,
          audio_mixdown: audioMix,
          audio_samplerate: audioRate,
          audio_drc: audioDrc,
          audio_gain: audioGain,
          audio_offset_ms: audioOffset,
          audio_lang_list: audioLang,
          audio_track_list: audioTracks,
          audio_all: audioAll,
          subtitle_mode: subtitleMode
        },
        handbrake_dvd: { quality: qDvd, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_offset_ms: audioOffset, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode },
        handbrake_br: { quality: qBr, extension: ext, audio_mode: audioMode, audio_bitrate_kbps: audioBitrate, audio_encoder: audioEncoder, audio_mixdown: audioMix, audio_samplerate: audioRate, audio_drc: audioDrc, audio_gain: audioGain, audio_offset_ms: audioOffset, audio_lang_list: audioLang, audio_track_list: audioTracks, audio_all: audioAll, subtitle_mode: subtitleMode }
      };
      await fetch("/api/presets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      await loadPresets();
    });

    document.getElementById("hb-preset-delete").addEventListener("click", async () => {
      const sel = document.getElementById("hb-preset-select");
      const name = sel.value;
      if (!name) { alert("Select a preset to delete"); return; }
      await fetch("/api/presets", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
      document.getElementById("hb-preset-name").value = "";
      await loadPresets();
    });

    document.getElementById("hb-preset-select").addEventListener("change", async () => {
      const sel = document.getElementById("hb-preset-select");
      const name = sel.value;
      if (!name) return;
      const res = await fetch("/api/presets");
      const data = await res.json();
      const preset = (data.presets || []).find(p => p.name === name);
      if (!preset) return;
      populateHandbrakeForm({ handbrake: preset.handbrake, handbrake_dvd: preset.handbrake_dvd, handbrake_br: preset.handbrake_br });
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

    document.getElementById("mk-copy-info").addEventListener("click", async () => {
      const text = (document.getElementById("mk-info").value || "").trim();
      if (!text) { alert("No disc info to copy."); return; }
      try {
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
        alert("Disc info copied.");
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

    const diagStatus = document.getElementById("diag-status");
    document.getElementById("diag-push").addEventListener("click", async () => {
      if (diagStatus) diagStatus.textContent = "Pushing diagnostics...";
      try {
        const res = await fetch("/api/diagnostics/push", { method: "POST" });
        const data = await res.json();
        if (data.ok) {
          diagStatus.textContent = "Pushed diagnostics" + (data.commit ? " (" + data.commit + ")" : "");
        } else {
          diagStatus.textContent = "Failed: " + (data.error || res.statusText);
        }
      } catch (e) {
        diagStatus.textContent = "Failed: " + e;
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

    document.getElementById("handbrake-form").addEventListener("input", () => { hbDirty = true; });
    document.getElementById("makemkv-form").addEventListener("input", () => { mkDirty = true; });
    document.getElementById("makemkv-form").addEventListener("change", () => { mkDirty = true; });
    document.getElementById("handbrake-form").addEventListener("change", () => { hbDirty = true; });
    const authDirtyFlag = () => { authDirty = true; };
    document.getElementById("auth-user").addEventListener("input", authDirtyFlag);
    document.getElementById("auth-pass").addEventListener("input", authDirtyFlag);

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

    loadPresets();
    refreshSettings();
  </script>
</body>
</html>
"""
