"""LAN web servers without any UI: file sharing and static website hosting.

Everything here uses the Python standard library, so it can be tested and reused without Qt.
"""
import base64
import datetime as _dt
import hmac
import http.client
import html
import json
import mimetypes
import os
import posixpath
import re
import select
import socket
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, List, Optional
from urllib.parse import quote, unquote, urlsplit

MODE_FILES = "files"
MODE_SITE = "site"
MODE_PROXY = "proxy"  # forward to a dev server running on this computer (localhost:3000 etc.)
MODES = (MODE_FILES, MODE_SITE, MODE_PROXY)
DEV_PORTS = (3000, 3001, 5173, 5174, 4200, 8000, 8080, 8081, 5000, 4321, 8888, 9000, 1313, 4000)
CHUNK = 256 * 1024

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/markdown", ".md")


@dataclass
class Share:
    """One shared folder. The running server reads these fields on every request, so most
    changes apply right away; only a new port needs a restart."""
    name: str
    folder: str
    mode: str = MODE_FILES
    port: int = 8080
    allow_upload: bool = False
    password: str = ""
    auto_start: bool = False
    target_port: int = 3000
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        s = cls(**known)
        if s.mode not in MODES:
            s.mode = MODE_FILES
        return s


@dataclass
class Event:
    time: float
    client: str
    method: str
    path: str
    status: int
    kind: str  # view | download | upload | denied | auth
    size: int = 0


# ---------------------------------------------------------------- network helpers

def primary_ip() -> Optional[str]:
    """The address other devices on the LAN use to reach this computer (no packet is sent)."""
    for target in ("10.255.255.255", "192.168.255.255", "8.8.8.8"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((target, 1))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127.") and ip != "0.0.0.0":
                return ip
        except OSError:
            pass
        finally:
            s.close()
    return None


def lan_addresses() -> List[str]:
    """IPv4 addresses of this computer, the most likely LAN address first."""
    found = []
    first = primary_ip()
    if first:
        found.append(first)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in found and not ip.startswith("127.") and not ip.startswith("169.254."):
                found.append(ip)
    except OSError:
        pass
    return found


def port_available(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform != "win32":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port(start: int = 8080, taken=()) -> int:
    for p in range(start, start + 500):
        if p not in taken and port_available(p):
            return p
    raise OSError("no free port")


def target_alive(port: int, timeout: float = 0.3) -> bool:
    """Is something listening on localhost:port? Tries IPv6 and IPv4 (Node often binds only ::1)."""
    try:
        socket.create_connection(("localhost", int(port)), timeout=timeout).close()
        return True
    except OSError:
        return False


def detect_dev_servers(exclude=()) -> List[int]:
    """Common dev-server ports that have something running right now."""
    return [p for p in DEV_PORTS if p not in exclude and target_alive(p, 0.15)]


def share_url(ip: Optional[str], port: int) -> str:
    return f"http://{ip or 'localhost'}:{port}/"


# ---------------------------------------------------------------- file helpers

_BAD_CHARS = re.compile(r'[\x00-\x1f<>:"/\\|?*]')


def safe_filename(name: str) -> str:
    """A file name that can't escape the target folder or hide itself."""
    name = name.replace("\\", "/").split("/")[-1]
    name = _BAD_CHARS.sub("_", name).strip().strip(".").strip()
    if not name:
        name = "upload"
    stem, ext = os.path.splitext(name)
    if stem.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}:
        name = f"_{name}"
    return name[:200]


def unique_path(folder: str, name: str) -> str:
    """folder/name, or folder/name (2).ext etc. when that already exists — never overwrite."""
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(name)
    n = 2
    while True:
        path = os.path.join(folder, f"{stem} ({n}){ext}")
        if not os.path.exists(path):
            return path
        n += 1


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _hidden(name: str) -> bool:
    return name.startswith(".") or name in ("desktop.ini", "Thumbs.db", "$RECYCLE.BIN")


ICONS = [
    ({".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".svg"}, "🖼️"),
    ({".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}, "🎬"),
    ({".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}, "🎵"),
    ({".pdf"}, "📕"),
    ({".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".pages"}, "📝"),
    ({".xls", ".xlsx", ".csv", ".numbers", ".ods"}, "📊"),
    ({".ppt", ".pptx", ".key", ".odp"}, "📽️"),
    ({".zip", ".rar", ".7z", ".tar", ".gz", ".dmg", ".iso"}, "🗜️"),
    ({".exe", ".msi", ".apk", ".pkg", ".app"}, "📦"),
    ({".html", ".htm", ".css", ".js", ".py", ".json", ".xml"}, "💻"),
]


def file_icon(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    for exts, icon in ICONS:
        if ext in exts:
            return icon
    return "📄"


# ---------------------------------------------------------------- web page (what friends see)

WEB = {
    "files": ("ไฟล์", "Files"),
    "empty": ("โฟลเดอร์นี้ว่างเปล่า", "This folder is empty"),
    "up": ("ย้อนกลับ", "Back"),
    "upload": ("อัปโหลดไฟล์", "Upload files"),
    "drop": ("ลากไฟล์มาวางที่นี่ หรือแตะเพื่อเลือกไฟล์", "Drop files here or tap to choose"),
    "uploading": ("กำลังอัปโหลด", "Uploading"),
    "uploaded": ("อัปโหลดเสร็จแล้ว", "Upload complete"),
    "upload_fail": ("อัปโหลดไม่สำเร็จ", "Upload failed"),
    "download": ("ดาวน์โหลด", "Download"),
    "items": ("{n} รายการ", "{n} items"),
    "search": ("ค้นหาไฟล์…", "Search files…"),
    "shared_by": ("แชร์ผ่าน LAN Share Hub", "Shared with LAN Share Hub"),
    "no_index": ("ยังไม่มีหน้าเว็บ", "No web page yet"),
    "no_index_msg": ("โฟลเดอร์นี้ไม่มีไฟล์ index.html", "This folder has no index.html file"),
    "not_found": ("ไม่พบไฟล์นี้", "File not found"),
    "dev_down": ("แอปยังไม่ได้เปิด", "The app isn't running"),
    "dev_down_msg": ("เจ้าของเครื่องยังไม่ได้เปิดแอปที่ localhost:{port} — รอสักครู่แล้วกดรีเฟรช",
                     "Nothing is running at localhost:{port} on the host computer yet — wait a moment and refresh"),
}


def _web(key, lang, **kw):
    s = WEB[key][0 if lang == "th" else 1]
    return s.format(**kw) if kw else s


PAGE_CSS = """
:root{--bg:#f4f6fb;--card:#fff;--ink:#0f172a;--mute:#64748b;--line:#e5e9f2;--acc:#2563eb;--acc2:#0ea5a4;--hover:#f1f5ff}
@media (prefers-color-scheme:dark){:root{--bg:#0b1220;--card:#121a2b;--ink:#e5ecf8;--mute:#8b9ab3;--line:#1f2a40;--acc:#60a5fa;--acc2:#2dd4bf;--hover:#17223a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans Thai","Sukhumvit Set",Tahoma,sans-serif}
header{background:linear-gradient(120deg,var(--acc),var(--acc2));color:#fff;padding:22px 16px 56px}
.wrap{max-width:880px;margin:0 auto}
h1{margin:0;font-size:22px;font-weight:700;word-break:break-word}
.crumb{margin-top:6px;font-size:14px;opacity:.92}.crumb a{color:#fff;text-decoration:none}.crumb a:hover{text-decoration:underline}
main{padding:0 16px 40px;margin-top:-36px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 8px 30px rgba(15,23,42,.06);overflow:hidden}
.tools{display:flex;gap:10px;padding:12px;border-bottom:1px solid var(--line);align-items:center}
.tools input{flex:1;min-width:0;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:10px;padding:9px 12px;font:inherit}
.count{color:var(--mute);font-size:13px;white-space:nowrap}
.row{display:flex;align-items:center;gap:12px;padding:11px 14px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none}
.row:last-child{border-bottom:0}.row:hover{background:var(--hover)}
.ic{font-size:24px;width:32px;text-align:center;flex:none}
.nm{flex:1;min-width:0}.nm b{display:block;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nm small{color:var(--mute)}
.dl{flex:none;border:1px solid var(--line);border-radius:10px;padding:6px 12px;color:var(--acc);text-decoration:none;font-weight:600;font-size:13px}
.dl:hover{background:var(--acc);color:#fff;border-color:var(--acc)}
.empty{padding:40px;text-align:center;color:var(--mute)}
.drop{margin:14px;border:2px dashed var(--line);border-radius:14px;padding:22px;text-align:center;color:var(--mute);cursor:pointer;transition:.15s}
.drop.on,.drop:hover{border-color:var(--acc);color:var(--acc);background:var(--hover)}
.drop b{display:block;color:var(--ink);font-size:16px;margin-bottom:2px}
.bar{height:6px;background:var(--line);border-radius:3px;margin:10px 14px 0;overflow:hidden;display:none}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--acc),var(--acc2))}
.msg{margin:6px 14px 14px;font-size:13px;color:var(--mute);min-height:1em}
footer{text-align:center;color:var(--mute);font-size:12px;margin-top:18px}
"""

UPLOAD_JS = """
const drop=document.getElementById('drop'),pick=document.getElementById('pick'),bar=document.getElementById('bar'),
fill=bar.firstElementChild,msg=document.getElementById('msg');
drop.onclick=()=>pick.click();
pick.onchange=()=>send([...pick.files]);
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('on')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('on')}));
drop.addEventListener('drop',ev=>send([...ev.dataTransfer.files]));
async function send(files){
  if(!files.length)return;
  const total=files.reduce((a,f)=>a+f.size,0)||1;let done=0;bar.style.display='block';
  for(const f of files){
    msg.textContent=T.uploading+' '+f.name+'…';
    const ok=await new Promise(res=>{const x=new XMLHttpRequest();x.open('POST',location.pathname);
      x.setRequestHeader('X-File-Name',encodeURIComponent(f.name));
      x.upload.onprogress=e=>{fill.style.width=((done+e.loaded)/total*100)+'%'};
      x.onload=()=>res(x.status<300);x.onerror=()=>res(false);x.send(f)});
    if(!ok){msg.textContent=T.fail+': '+f.name;bar.style.display='none';return}
    done+=f.size;
  }
  fill.style.width='100%';msg.textContent=T.done+' ✓';setTimeout(()=>location.reload(),700);
}
"""

FILTER_JS = """
const q=document.getElementById('q');if(q)q.oninput=()=>{const v=q.value.toLowerCase();
document.querySelectorAll('.list .row').forEach(r=>{r.style.display=r.dataset.n.includes(v)?'':'none'})};
"""


def _page(title: str, lang: str, crumb_html: str, body: str, script: str = "") -> bytes:
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{PAGE_CSS}</style></head><body>
<header><div class="wrap"><h1>{html.escape(title)}</h1><div class="crumb">{crumb_html}</div></div></header>
<main><div class="wrap">{body}<footer>{_web('shared_by', lang)}</footer></div></main>
<script>{script}</script></body></html>""".encode("utf-8")


# ---------------------------------------------------------------- HTTP handler

class Handler(BaseHTTPRequestHandler):
    server_version = "LANShareHub/1.0"
    protocol_version = "HTTP/1.1"
    share: Share
    emit: Callable[[Event], None]

    # quiet: events go to the UI instead of stderr
    def log_message(self, fmt, *args):
        pass

    def _lang(self):
        al = (self.headers.get("Accept-Language") or "").lower()
        return "th" if al.startswith("th") or ",th" in al.replace(" ", "") else "en"

    def _event(self, status, kind, size=0):
        try:
            self.server.emit(Event(time.time(), self.client_address[0], self.command,
                                   unquote(urlsplit(self.path).path), int(status), kind, size))
        except Exception:
            pass

    # ---- auth
    def _authorized(self) -> bool:
        pw = self.server.share.password
        if not pw:
            return True
        h = self.headers.get("Authorization") or ""
        if h.startswith("Basic "):
            try:
                user_pw = base64.b64decode(h[6:]).decode("utf-8", "replace")
                given = user_pw.split(":", 1)[1] if ":" in user_pw else user_pw
                if hmac.compare_digest(given.encode(), pw.encode()):
                    return True
            except Exception:
                pass
        self._event(401, "auth")
        body = b"Password required"
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="LAN Share Hub", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    # ---- path mapping
    def _resolve(self):
        """Map the URL to a real path inside the shared folder, or None when it must not be served."""
        root = os.path.realpath(self.server.share.folder)
        raw = unquote(urlsplit(self.path).path)
        parts = [p for p in posixpath.normpath(raw).split("/") if p not in ("", ".", "..")]
        if any(_hidden(p) for p in parts):
            return None, raw
        real = os.path.realpath(os.path.join(root, *parts))
        if real != root and not real.startswith(root + os.sep):  # symlink pointing outside
            return None, raw
        return real, raw

    def _simple(self, status, text, lang=None):
        lang = lang or self._lang()
        title = _web("not_found", lang) if status == 404 else str(status)
        body = _page(title, lang, "", f'<div class="card"><div class="empty">{html.escape(text)}</div></div>')
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def _any(self):
        if self.server.share.mode == MODE_PROXY:
            if self._authorized():
                self._proxy()
        else:
            self._simple(405, "Method not allowed")

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _any

    def do_GET(self):
        if not self._authorized():
            return
        if self.server.share.mode == MODE_PROXY:
            return self._proxy()
        share = self.server.share
        path, raw = self._resolve()
        if raw == "/favicon.ico" and (path is None or not os.path.exists(path)):
            self.send_response(204)  # browsers ask for this on their own; not worth a log line
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path is None or not os.path.exists(path):
            self._event(404, "denied")
            return self._simple(404, _web("not_found", self._lang()))
        if os.path.isdir(path):
            if not raw.endswith("/"):
                self.send_response(301)
                self.send_header("Location", quote(raw + "/") + ("?" + urlsplit(self.path).query if urlsplit(self.path).query else ""))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if share.mode == MODE_SITE:
                for idx in ("index.html", "index.htm"):
                    if os.path.isfile(os.path.join(path, idx)):
                        return self._send_file(os.path.join(path, idx), view=True)
                lang = self._lang()
                self._event(404, "view")
                return self._simple(404, _web("no_index_msg", lang), lang)
            return self._listing(path, raw)
        query = urlsplit(self.path).query
        return self._send_file(path, view=share.mode == MODE_SITE or "dl=1" not in query)

    def _listing(self, path, raw):
        lang = self._lang()
        share = self.server.share
        try:
            names = os.listdir(path)
        except OSError:
            return self._simple(403, "Forbidden", lang)
        entries = []
        for n in names:
            if _hidden(n):
                continue
            full = os.path.join(path, n)
            try:
                st = os.stat(full)
            except OSError:
                continue
            entries.append((not os.path.isdir(full), n.lower(), n, st))
        entries.sort()

        # breadcrumb
        segs = [s for s in raw.split("/") if s]
        crumbs = [f'<a href="/">🏠 {html.escape(share.name)}</a>']
        acc = "/"
        for s in segs:
            acc += s + "/"
            crumbs.append(f'<a href="{quote(acc)}">{html.escape(s)}</a>')
        crumb_html = " / ".join(crumbs)

        rows = []
        if segs:
            rows.append(f'<a class="row" href="../" data-n=".."><span class="ic">↩️</span>'
                        f'<span class="nm"><b>{_web("up", lang)}</b></span></a>')
        for is_file, _, n, st in entries:
            href = quote(n) + ("" if is_file else "/")
            when = _dt.datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M")
            if is_file:
                rows.append(
                    f'<div class="row" data-n="{html.escape(n.lower())}"><span class="ic">{file_icon(n)}</span>'
                    f'<a class="nm" href="{href}" style="color:inherit;text-decoration:none">'
                    f'<b>{html.escape(n)}</b><small>{human_size(st.st_size)} · {when}</small></a>'
                    f'<a class="dl" href="{href}?dl=1" download>⬇ {_web("download", lang)}</a></div>')
            else:
                rows.append(
                    f'<a class="row" href="{href}" data-n="{html.escape(n.lower())}"><span class="ic">📁</span>'
                    f'<span class="nm"><b>{html.escape(n)}</b><small>{when}</small></span></a>')
        count = len(entries)
        listing = "".join(rows) if count or segs else ""
        if not count:
            listing += f'<div class="empty">📭 {_web("empty", lang)}</div>'
        upload = ""
        script = FILTER_JS
        if share.allow_upload:
            upload = (f'<div id="drop" class="drop"><b>⬆️ {_web("upload", lang)}</b>{_web("drop", lang)}</div>'
                      f'<input id="pick" type="file" multiple hidden><div id="bar" class="bar"><i></i></div>'
                      f'<div id="msg" class="msg"></div>')
            script += ("const T=" + json.dumps({"uploading": _web("uploading", lang), "done": _web("uploaded", lang),
                                             "fail": _web("upload_fail", lang)}, ensure_ascii=False) + ";" + UPLOAD_JS)
        body = (f'<div class="card"><div class="tools"><input id="q" placeholder="{_web("search", lang)}">'
                f'<span class="count">{_web("items", lang, n=count)}</span></div>'
                f'<div class="list">{listing}</div>{upload}</div>')
        title = share.name if not segs else unquote(segs[-1])
        data = _page(title, lang, crumb_html, body, script)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        self._event(200, "view")

    def _send_file(self, path, view):
        try:
            f = open(path, "rb")
        except OSError:
            return self._simple(403, "Forbidden")
        with f:
            size = os.fstat(f.fileno()).st_size
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/json", "image/svg+xml", "text/javascript"):
                ctype += "; charset=utf-8"
            start, end, status = 0, size - 1, 200
            rng = self.headers.get("Range")
            m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip()) if rng else None
            if m and size and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
                else:  # suffix: last N bytes
                    start = max(0, size - int(m.group(2)))
                if start >= size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status = 206
            length = max(0, end - start + 1)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            name = os.path.basename(path)
            disp = "inline" if view else "attachment"
            self.send_header("Content-Disposition", f"{disp}; filename*=UTF-8''{quote(name)}")
            self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(path)))
            if self.server.share.mode == MODE_SITE:
                self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if self.command == "HEAD":
                return
            f.seek(start)
            left = length
            try:
                while left > 0:
                    buf = f.read(min(CHUNK, left))
                    if not buf:
                        break
                    self.wfile.write(buf)
                    left -= len(buf)
            except (ConnectionError, OSError):
                return
        kind = "view" if self.server.share.mode == MODE_SITE else "download"
        if status == 200 or start == 0:  # count a video stream once, not every range request
            self._event(status, kind, length)

    def do_POST(self):
        """Upload: the page sends each file as the raw request body with its name in X-File-Name."""
        if not self._authorized():
            return
        share = self.server.share
        if share.mode == MODE_PROXY:
            return self._proxy()
        if share.mode != MODE_FILES or not share.allow_upload:
            self._event(403, "denied")
            return self._simple(403, "Uploads are turned off")
        folder, _ = self._resolve()
        if folder is None or not os.path.isdir(folder):
            self._event(404, "denied")
            return self._simple(404, "Folder not found")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._simple(411, "Content-Length required")
        name = safe_filename(unquote(self.headers.get("X-File-Name") or "upload"))
        target = unique_path(folder, name)
        tmp = target + ".uploading"
        ok = False
        try:
            with open(tmp, "wb") as out:
                left = length
                while left > 0:
                    buf = self.rfile.read(min(CHUNK, left))
                    if not buf:
                        break
                    out.write(buf)
                    left -= len(buf)
            if left == 0:
                target = unique_path(folder, name)  # another upload may have taken the name meanwhile
                os.replace(tmp, target)
                ok = True
        finally:
            if not ok and os.path.exists(tmp):
                os.remove(tmp)
        if not ok:
            self.close_connection = True
            return
        body = os.path.basename(target).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.server.emit(Event(time.time(), self.client_address[0], "POST",
                               unquote(urlsplit(self.path).path) + os.path.basename(target), 201, "upload", length))


    # ------------------------------------------------------------ proxy to localhost
    HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
           "transfer-encoding", "upgrade", "proxy-connection"}

    def _proxy_headers(self, port, upgrade=False):
        local = f"localhost:{port}"
        out = []
        for k, v in self.headers.items():
            lk = k.lower()
            if lk == "host":
                v = local
            elif lk in ("origin", "referer"):  # dev servers (Next.js, Vite) trust their own origin
                parts = urlsplit(v)
                if parts.netloc:
                    v = v.replace(f"{parts.scheme}://{parts.netloc}", f"http://{local}", 1)
            elif lk == "authorization" and self.server.share.password:
                continue  # our password, not the app's
            elif lk in self.HOP and not (upgrade and lk in ("connection", "upgrade")):
                continue
            out.append((k, v))
        out.append(("X-Forwarded-For", self.client_address[0]))
        out.append(("X-Forwarded-Host", self.headers.get("Host", "")))
        out.append(("X-Forwarded-Proto", "http"))
        return out

    def _read_body(self):
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            data = bytearray()
            while True:
                size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                        pass
                    return bytes(data)
                data += self.rfile.read(size)
                self.rfile.readline()
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else None

    def _proxy(self):
        share = self.server.share
        port = int(share.target_port)
        if "websocket" in (self.headers.get("Upgrade") or "").lower():
            return self._proxy_ws(port)
        is_page = (self.headers.get("Sec-Fetch-Dest") == "document"
                   or (self.command == "GET" and "text/html" in (self.headers.get("Accept") or "")))
        try:
            body = self._read_body()
            conn = http.client.HTTPConnection("localhost", port, timeout=120)
            conn.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            for k, v in self._proxy_headers(port):
                if k.lower() != "content-length":
                    conn.putheader(k, v)
            if body is not None:
                conn.putheader("Content-Length", str(len(body)))
            conn.endheaders(body)
            resp = conn.getresponse()
        except (ConnectionError, OSError, http.client.HTTPException):
            lang = self._lang()
            if is_page:
                self._event(502, "view")
            data = _page(_web("dev_down", lang), lang, "",
                         f'<div class="card"><div class="empty">⏳ {html.escape(_web("dev_down_msg", lang, port=port))}'
                         f'</div></div>', "setTimeout(()=>location.reload(),4000)")
            self.send_response(502)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            return
        try:
            self.send_response_only(resp.status, resp.reason)
            self.send_header("Date", self.date_time_string())
            length = resp.getheader("Content-Length")
            no_body = self.command == "HEAD" or resp.status in (204, 304) or 100 <= resp.status < 200
            for k, v in resp.getheaders():
                lk = k.lower()
                if lk in self.HOP or lk == "date":
                    continue
                if lk == "location":
                    for h in (f"http://localhost:{port}", f"http://127.0.0.1:{port}"):
                        if v.startswith(h):
                            v = v[len(h):] or "/"
                self.send_header(k, v)
            chunked = not no_body and length is None
            if chunked:  # streaming answer (server-sent events, React streaming): pass it on as it comes
                self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            sent = 0
            if not no_body:
                while True:
                    buf = resp.read1(CHUNK) if chunked else resp.read(CHUNK)
                    if not buf:
                        break
                    sent += len(buf)
                    if chunked:
                        self.wfile.write(b"%x\r\n%s\r\n" % (len(buf), buf))
                        self.wfile.flush()
                    else:
                        self.wfile.write(buf)
                if chunked:
                    self.wfile.write(b"0\r\n\r\n")
            if is_page:
                self._event(resp.status, "view", sent)
        except (ConnectionError, OSError):
            self.close_connection = True
        finally:
            conn.close()

    def _proxy_ws(self, port):
        """Hot reload (WebSocket): send the handshake on, then copy bytes both ways until one side closes."""
        try:
            up = socket.create_connection(("localhost", port), timeout=10)
        except OSError:
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.close_connection = True
        head = f"{self.command} {self.path} HTTP/1.1\r\n" + "".join(
            f"{k}: {v}\r\n" for k, v in self._proxy_headers(port, upgrade=True)) + "\r\n"
        client = self.connection
        try:
            up.settimeout(None)
            up.sendall(head.encode("latin-1", "replace"))
            while True:
                r, _, _ = select.select([client, up], [], [], 600)
                if not r:
                    break
                for src in r:
                    data = src.recv(CHUNK)
                    if not data:
                        return
                    (up if src is client else client).sendall(data)
        except (OSError, ValueError):
            pass
        finally:
            up.close()


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = sys.platform != "win32"  # on Windows it would let two servers share a port
    share: Share
    emit: Callable[[Event], None]

    def handle_error(self, request, client_address):  # broken connections are normal on phones
        pass


class ShareServer:
    """Runs one Share in a background thread."""

    def __init__(self, share: Share, on_event: Optional[Callable[[Event], None]] = None):
        self.share = share
        self.on_event = on_event
        self._httpd = None
        self._thread = None
        self.port = None

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self):
        if self.running:
            return
        if self.share.mode != MODE_PROXY and not os.path.isdir(self.share.folder):
            raise FileNotFoundError(self.share.folder)
        httpd = _Server(("0.0.0.0", int(self.share.port)), Handler)
        httpd.share = self.share
        httpd.emit = self._emit
        self._httpd = httpd
        self.port = httpd.server_address[1]
        self._thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.3},
                                        name=f"share-{self.share.id}", daemon=True)
        self._thread.start()

    def stop(self):
        httpd, self._httpd = self._httpd, None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        self.port = None

    def _emit(self, ev: Event):
        if self.on_event:
            self.on_event(ev)
