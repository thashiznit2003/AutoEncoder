from flask import Flask, jsonify, Response, request

HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Linux Video Encoder</title>
  <style>
    :root { color-scheme: dark; font-family: "Segoe UI", Arial, sans-serif; }
    body { margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 12px 16px; background: #111827; border-bottom: 1px solid #1f2937; display: flex; justify-content: space-between; align-items: center; }
    h1 { font-size: 18px; margin: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); grid-auto-rows: minmax(240px, auto); gap: 12px; padding: 12px; }
    .panel { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    .panel h2 { margin: 0 0 8px 0; font-size: 15px; color: #93c5fd; }
    form { display: grid; gap: 8px; margin-top: 8px; }
    label { font-size: 12px; color: #cbd5e1; display: grid; gap: 4px; }
    input, select { padding: 6px 8px; border-radius: 6px; border: 1px solid #1f2937; background: #0b1220; color: #e2e8f0; }
    button { padding: 8px 12px; border: 0; border-radius: 8px; background: #2563eb; color: #fff; font-weight: 600; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .log { font-family: "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; background: #0b1220; border-radius: 8px; padding: 10px; overflow: auto; height: 320px; border: 1px solid #1f2937; white-space: pre-wrap; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; color: #0f172a; font-weight: 600; }
    .badge.running { background: #fde047; }
    .badge.success { background: #34d399; }
    .badge.error { background: #f87171; }
    .progress { background: #1f2937; border-radius: 6px; height: 8px; overflow: hidden; margin-top: 6px; }
    .progress-bar { background: #22c55e; height: 100%; transition: width 0.2s ease; }
    .item { padding: 8px; border-bottom: 1px solid #1f2937; }
    .item:last-child { border-bottom: 0; }
    .muted { color: #94a3b8; }
    .flex-between { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .path { word-break: break-all; }
  </style>
</head>
<body>
  <header>
    <h1>Linux Video Encoder - Live Status</h1>
    <div id="clock" class="muted"></div>
  </header>
  <div class="grid">
    <div class="panel">
      <h2>Active Encodes</h2>
      <div id="active"></div>
    </div>
    <div class="panel">
      <h2>Recent Jobs</h2>
      <div id="recent" style="max-height: 260px; overflow-y: auto;"></div>
      <div style="margin-top:8px; display:flex; gap:6px; flex-wrap: wrap;">
        <button data-clear="success" class="clear-btn">Clear Success</button>
        <button data-clear="error" class="clear-btn">Clear Error</button>
        <button data-clear="running" class="clear-btn">Clear Running</button>
        <button data-clear="all" class="clear-btn">Clear All</button>
      </div>
    </div>
    <div class="panel">
      <h2>Status Messages</h2>
      <div id="events" class="log"></div>
    </div>
    <div class="panel">
      <h2>HandBrake Settings</h2>
      <form id="handbrake-form">
        <label>Default encoder <input id="hb-encoder" name="encoder" /></label>
        <label>Default quality (RF) <input id="hb-quality" name="quality" type="number" step="1" /></label>
        <label>DVD quality (RF) <input id="hb-dvd-quality" name="quality_dvd" type="number" step="1" /></label>
        <label>Blu-ray quality (RF) <input id="hb-br-quality" name="quality_br" type="number" step="1" /></label>
        <label>Output extension <input id="hb-ext" name="extension" /></label>
        <button type="submit">Save HandBrake</button>
      </form>
    </div>
    <div class="panel">
      <h2>MakeMKV Settings</h2>
      <form id="makemkv-form">
        <label>Rip directory <input id="mk-ripdir" name="rip_dir" /></label>
        <label>Min title length (seconds) <input id="mk-minlen" name="min_length" type="number" step="60" /></label>
        <button type="submit">Save MakeMKV</button>
      </form>
    </div>
    <div class="panel" style="grid-column: 1 / -1;">
      <h2>Logs</h2>
      <div id="logs" class="log"></div>
    </div>
  </div>
  <script>
    async function fetchJSON(url) {
      const res = await fetch(url);
      return res.json();
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
        container.innerHTML = `<div class="muted">${empty}</div>`;
        return;
      }
      container.innerHTML = items.map(item => {
        const badge = `<span class="badge ${item.state}">${item.state.toUpperCase()}</span>`;
        const duration = item.duration_sec ? fmtDuration(item.duration_sec) : (item.finished_at && item.started_at ? fmtDuration(item.finished_at - (item.started_at || item.finished_at)) : "");
        const progress = (item.progress || item.progress === 0) ? Math.min(100, Math.max(0, item.progress)).toFixed(0) : null;
        const progBar = progress !== null ? `<div class="progress"><div class="progress-bar" style="width:${progress}%"></div></div>` : "";
        const stopBtn = item.state === "running" ? `<button class="stop-btn" data-src="${encodeURIComponent(item.source || "")}">Stop</button>` : "";
        return `<div class="item">
          <div class="flex-between">
            <div class="path">${item.source || ""}</div>
            <div>${badge} ${stopBtn}</div>
          </div>
          <div class="muted">-> ${item.destination || ""}</div>
          <div class="muted">${item.message || ""}</div>
          <div class="muted">${duration ? "Encode elapsed: " + duration : ""}</div>
          ${progBar}
        </div>`;
      }).join("");
    }

    async function refresh() {
      try {
        const status = await fetchJSON("/api/status");
        renderList(document.getElementById("active"), status.active, "No active encodes.");
        renderList(document.getElementById("recent"), status.recent, "No recent jobs.");
      } catch (e) {
        document.getElementById("active").innerHTML = "<div class='muted'>Status unavailable.</div>";
        document.getElementById("recent").innerHTML = "<div class='muted'>Status unavailable.</div>";
      }
      try {
        const logs = await fetchJSON("/api/logs");
        document.getElementById("logs").textContent = logs.lines.join("\\n");
      } catch (e) {
        document.getElementById("logs").textContent = "Logs unavailable.";
      }
      try {
        const events = await fetchJSON("/api/events");
        const lines = events.map(ev => `[${new Date(ev.ts * 1000).toLocaleTimeString()}] ${ev.message}`);
        document.getElementById("events").textContent = lines.join("\\n") || "No recent events.";
      } catch (e) {
        document.getElementById("events").textContent = "Events unavailable.";
      }
      try {
        const cfg = await fetchJSON("/api/config");
        document.getElementById("hb-encoder").value = cfg.handbrake.encoder || "";
        document.getElementById("hb-quality").value = cfg.handbrake.quality ?? "";
        document.getElementById("hb-dvd-quality").value = cfg.handbrake_dvd.quality ?? "";
        document.getElementById("hb-br-quality").value = cfg.handbrake_br.quality ?? "";
        document.getElementById("hb-ext").value = cfg.handbrake.extension || ".mp4";
        document.getElementById("mk-ripdir").value = cfg.rip_dir || "";
        document.getElementById("mk-minlen").value = cfg.makemkv_minlength ?? 1200;
      } catch (e) {
        // ignore populate errors
      }
    }

    function tickClock() {
      const now = new Date();
      document.getElementById("clock").textContent = now.toLocaleString();
    }

    document.getElementById("handbrake-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        handbrake: {
          encoder: document.getElementById("hb-encoder").value,
          quality: Number(document.getElementById("hb-quality").value),
          extension: document.getElementById("hb-ext").value
        },
        handbrake_dvd: { quality: Number(document.getElementById("hb-dvd-quality").value) },
        handbrake_br: { quality: Number(document.getElementById("hb-br-quality").value) }
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    });

    document.addEventListener("click", async (e) => {
      if (e.target.classList.contains("clear-btn")) {
        const status = e.target.getAttribute("data-clear");
        await fetch(`/api/clear`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
        refresh();
      }
      if (e.target.classList.contains("stop-btn")) {
        const src = decodeURIComponent(e.target.getAttribute("data-src"));
        const ok = confirm("Stop this encode?\nAre you sure?");
        if (!ok) return;
        await fetch("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: src }) });
        refresh();
      }
    });

    document.getElementById("makemkv-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        rip_dir: document.getElementById("mk-ripdir").value,
        makemkv_minlength: Number(document.getElementById("mk-minlen").value)
      };
      await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    });

    setInterval(refresh, 2000);
    setInterval(tickClock, 1000);
    refresh();
    tickClock();
  </script>
</body>
</html>
"""


def create_app(tracker, config_manager=None):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return Response(HTML_PAGE, mimetype="text/html")

    @app.route("/api/status")
    def status():
        return jsonify(tracker.snapshot())

    @app.route("/api/logs")
    def logs():
        return jsonify({"lines": tracker.tail_logs()})

    @app.route("/api/events")
    def events():
        return jsonify(tracker.events())

    if config_manager:
        @app.route("/api/config", methods=["GET", "POST"])
        def config():
            if request.method == "GET":
                return jsonify(config_manager.read())
            payload = request.get_json(force=True) or {}
            updated = config_manager.update(payload)
            return jsonify(updated)

    @app.route("/api/stop", methods=["POST"])
    def stop():
        payload = request.get_json(force=True) or {}
        src = payload.get("source")
        if src:
            tracker.stop_proc(src)
            tracker.add_event(f"Stopped encode: {src}")
        return jsonify({"stopped": bool(src)})

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
