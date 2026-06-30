import io
import json
import socket
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


STREAM_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Karaoke Stream</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; overflow: hidden; }
body {
    background-color: #0a0a0a;
    color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 20px;
    transition: opacity 0.15s ease;
}
.song-info {
    font-size: clamp(14px, 3vw, 22px);
    color: #888;
    text-align: center;
    margin-bottom: 8px;
    min-height: 1.4em;
}
.section-label {
    font-size: clamp(18px, 5vw, 24px);
    font-weight: bold;
    letter-spacing: 3px;
    color: #aaa;
    text-align: center;
    margin-bottom: 16px;
    min-height: 1.2em;
    transition: opacity 0.2s;
}
.content {
    flex: 1;
    /*display: flex;*/
    align-items: center;
    justify-content: center;
    width: 100%;
    max-width: 900px;
    overflow-y: auto;
}
.content-inner {
    text-align: center;
    width: 100%;
    transition: opacity 0.15s;
}
.content-inner.fade { opacity: 0; }
.next-section { font-size: 1.1em !important; }
.next-section * { font-size: 1.1em !important; opacity: 0.4; }
.progress-row {
    width: 100%;
    max-width: 900px;
    margin-top: 16px;
}
.progress-bar {
    position: relative;
    width: 100%;
    height: 8px;
    background-color: #2a2a2a;
    border-radius: 4px;
    overflow: visible;
}
.progress-fill {
    height: 100%;
    background-color: #2196F3;
    border-radius: 4px;
    transition: width 0.3s ease;
    position: relative;
    z-index: 1;
}
.marker {
    position: absolute;
    top: -2px;
    width: 2px;
    height: 12px;
    background-color: #FF9800;
    border-radius: 1px;
    z-index: 2;
}
.countdown-label {
    width: 100%;
    max-width: 900px;
    margin-top: 10px;
    font-size: clamp(13px, 2.5vw, 18px);
    font-weight: bold;
    text-align: center;
    color: #e65100;
    min-height: 1.4em;
}
.time-row {
    display: flex;
    justify-content: space-between;
    width: 100%;
    max-width: 900px;
    margin-top: 6px;
    font-size: clamp(11px, 2vw, 16px);
    font-family: 'Courier New', monospace;
    color: #888;
}
.qr-section {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 100;
}
.qr-toggle {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    color: #ccc;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
}
.qr-toggle:hover { background: rgba(255,255,255,0.15); }
.qr-overlay {
    display: none;
    position: fixed;
    top: 48px;
    right: 12px;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.qr-overlay.show { display: block; }
.qr-overlay img { width: 180px; height: 180px; display: block; margin: 0 auto; }
.qr-overlay .url { margin-top: 8px; font-size: 12px; color: #888; word-break: break-all; }
@media (max-width: 600px) {
    body { padding: 10px; }
    .qr-section { top: 6px; right: 6px; }
    .qr-overlay { right: 6px; left: 6px; }
}
</style>
</head>
<body>
<div class="qr-section">
    <button class="qr-toggle" onclick="toggleQR()">📱 QR</button>
    <div class="qr-overlay" id="qrOverlay">
        <img src="/api/qr" alt="QR Code">
        <div class="url" id="qrUrl"></div>
    </div>
</div>
<div class="song-info" id="songInfo"></div>
<div class="section-label" id="sectionLabel">Esperando reproducción...</div>
<div class="content">
    <div class="content-inner" id="contentInner"></div>
</div>
<div class="countdown-label" id="countdownLabel"></div>
<div class="time-row">
    <span id="timeElapsed">00:00.00</span>
    <span id="timeTotal">00:00.00</span>
</div>
<div class="progress-row">
    <div class="progress-bar" id="progressBar">
        <div class="progress-fill" id="progressFill"></div>
    </div>
</div>

<script>
let lastHtml = '';
const contentEl = document.getElementById('contentInner');
const progressFill = document.getElementById('progressFill');
const progressBar = document.getElementById('progressBar');
const timeElapsed = document.getElementById('timeElapsed');
const timeTotal = document.getElementById('timeTotal');
const sectionLabel = document.getElementById('sectionLabel');
const songInfo = document.getElementById('songInfo');
const countdownLabel = document.getElementById('countdownLabel');

function toggleQR() {
    const ov = document.getElementById('qrOverlay');
    ov.classList.toggle('show');
    if (ov.classList.contains('show')) {
        document.getElementById('qrUrl').textContent = window.location.href;
    }
}

function fadeTransition(newHtml) {
    if (newHtml === lastHtml) return;
    if (!lastHtml) {
        contentEl.innerHTML = newHtml;
        lastHtml = newHtml;
        return;
    }
    contentEl.classList.add('fade');
    setTimeout(() => {
        contentEl.innerHTML = newHtml;
        lastHtml = newHtml;
        contentEl.classList.remove('fade');
    }, 150);
}

function updateBar(progress, markers) {
    const pct = Math.min(progress * 100, 100);
    progressFill.style.width = pct + '%';
    const existing = progressBar.querySelectorAll('.marker:not(.progress-fill)');
    existing.forEach(m => m.remove());
    if (markers && markers.length) {
        markers.forEach(r => {
            const m = document.createElement('div');
            m.className = 'marker';
            m.style.left = (r * 100) + '%';
            progressBar.appendChild(m);
        });
    }
}

function fmtTime(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return String(m).padStart(2,'0') + ':' + String(s.toFixed(2)).padStart(5,'0');
}

async function poll() {
    try {
        const resp = await fetch('/api/state');
        if (!resp.ok) return;
        const st = await resp.json();
        songInfo.textContent = st.song_name ? (st.song_name + (st.song_artist ? ' — '+st.song_artist : '')) : '';
        if (st.section_name) {
            sectionLabel.textContent = '▶ ' + st.section_name;
        } else {
            sectionLabel.textContent = st.song_name ? '▶ REPRODUCIENDO' : 'Esperando reproducción...';
        }
        let html = '';
        if (st.section_html) {
            html = st.section_html;
            if (st.next_section_html) {
                html += '<hr style="border:none;border-top:1px solid #2a2a2a;margin:30px 0 10px 0"><div class="next-section">'+st.next_section_html+'</div>';
            }
        }
        fadeTransition(html);
        updateBar(st.progress || 0, st.markers || []);
        timeElapsed.textContent = fmtTime(st.elapsed || 0);
        timeTotal.textContent = fmtTime(st.total || 0);
        if (st.countdown_remaining > 0) {
            let cd = 'Próxima sección en ' + st.countdown_remaining.toFixed(1) + 's';
            if (st.next_section_name) cd += ' → ' + st.next_section_name;
            countdownLabel.textContent = cd;
        } else {
            countdownLabel.textContent = '';
        }
    } catch(e) {}
    requestAnimationFrame(() => setTimeout(poll, 200));
}
poll();
</script>
</body>
</html>"""


class _StateHandler(BaseHTTPRequestHandler):
    _get_state = None

    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_png(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send_html(STREAM_HTML)
        elif path == "/api/state":
            state = self._get_state() if self._get_state else {}
            self._send_json(state)
        elif path == "/api/qr":
            if HAS_QR:
                host = self.headers.get("Host", "localhost")
                url = f"http://{host}"
                qr = qrcode.make(url)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")
                self._send_png(buf.getvalue())
            else:
                self.send_error(404, "QR not available")
        else:
            self.send_error(404)


class KaraokeStreamer:
    def __init__(self, get_state=None):
        self._get_state = get_state
        self._server = None
        self._thread = None
        self._port = 8080
        self._url = ""

    @property
    def running(self):
        return self._server is not None

    @property
    def url(self):
        return self._url

    @property
    def port(self):
        return self._port

    def _find_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self, port=8080):
        if self._server:
            return
        self._port = port
        _StateHandler._get_state = self._get_state
        self._server = HTTPServer(("0.0.0.0", port), _StateHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        ip = self._find_local_ip()
        self._url = f"http://{ip}:{port}"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            self._thread = None
            self._url = ""
