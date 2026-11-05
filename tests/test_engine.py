import base64
import http.client
import os

import pytest

from app.engine import (MODE_FILES, MODE_SITE, Share, ShareServer, free_port, safe_filename, unique_path)
from app.store import Store


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "hello.txt").write_text("สวัสดี hello", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a b.bin").write_bytes(bytes(range(256)) * 4)
    (tmp_path / ".secret").write_text("nope")
    return tmp_path


@pytest.fixture
def run(folder):
    servers = []

    def _run(**kw):
        events = []
        share = Share(name="Test", folder=str(folder), port=free_port(18080), **kw)
        srv = ShareServer(share, events.append)
        srv.start()
        servers.append(srv)
        return srv, events

    yield _run
    for s in servers:
        s.stop()


def req(srv, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    data = r.read()
    c.close()
    return r, data


def test_listing_and_download(run):
    srv, events = run()
    r, data = req(srv, "GET", "/", headers={"Accept-Language": "th-TH,th;q=0.9"})
    assert r.status == 200
    page = data.decode()
    assert "hello.txt" in page and "sub/" in page
    assert ".secret" not in page
    assert "ดาวน์โหลด" in page
    r, data = req(srv, "GET", "/hello.txt?dl=1")
    assert r.status == 200 and data.decode() == "สวัสดี hello"
    assert "attachment" in r.getheader("Content-Disposition")
    assert any(e.kind == "download" for e in events)


def test_english_page(run):
    srv, _ = run()
    _, data = req(srv, "GET", "/", headers={"Accept-Language": "en-US"})
    assert "Download" in data.decode()


def test_folder_redirect_and_quoted_names(run):
    srv, _ = run()
    r, _ = req(srv, "GET", "/sub")
    assert r.status == 301 and r.getheader("Location") == "/sub/"
    r, data = req(srv, "GET", "/sub/a%20b.bin")
    assert r.status == 200 and len(data) == 1024


def test_range_request(run):
    srv, _ = run()
    r, data = req(srv, "GET", "/sub/a%20b.bin", headers={"Range": "bytes=10-19"})
    assert r.status == 206
    assert data == bytes(range(10, 20))
    assert r.getheader("Content-Range") == "bytes 10-19/1024"
    r, data = req(srv, "GET", "/sub/a%20b.bin", headers={"Range": "bytes=-4"})
    assert r.status == 206 and data == bytes([252, 253, 254, 255])
    r, _ = req(srv, "GET", "/sub/a%20b.bin", headers={"Range": "bytes=5000-"})
    assert r.status == 416


def test_cannot_escape_or_read_hidden(run, folder):
    (folder.parent / "outside.txt").write_text("private")
    srv, _ = run()
    for path in ("/../outside.txt", "/%2e%2e/outside.txt", "/sub/../../outside.txt", "/.secret"):
        r, data = req(srv, "GET", path)
        assert r.status == 404, path
        assert b"private" not in data and b"nope" not in data


def test_symlink_outside_is_blocked(run, folder):
    outside = folder.parent / "elsewhere"
    outside.mkdir()
    (outside / "x.txt").write_text("private")
    os.symlink(outside, folder / "link")
    srv, _ = run()
    r, _ = req(srv, "GET", "/link/x.txt")
    assert r.status == 404


def test_password(run):
    srv, events = run(password="1234")
    r, _ = req(srv, "GET", "/")
    assert r.status == 401 and "Basic" in r.getheader("WWW-Authenticate")
    bad = base64.b64encode(b"friend:0000").decode()
    r, _ = req(srv, "GET", "/", headers={"Authorization": "Basic " + bad})
    assert r.status == 401
    good = base64.b64encode(b"anyone:1234").decode()
    r, _ = req(srv, "GET", "/", headers={"Authorization": "Basic " + good})
    assert r.status == 200
    assert any(e.kind == "auth" for e in events)


def test_password_change_applies_live(run):
    srv, _ = run()
    assert req(srv, "GET", "/")[0].status == 200
    srv.share.password = "secret"
    assert req(srv, "GET", "/")[0].status == 401


def test_upload_off_by_default(run, folder):
    srv, _ = run()
    r, _ = req(srv, "POST", "/", body=b"data", headers={"X-File-Name": "x.txt"})
    assert r.status == 403
    assert not (folder / "x.txt").exists()


def test_upload_never_overwrites(run, folder):
    srv, events = run(allow_upload=True)
    r, data = req(srv, "POST", "/", body="ใหม่".encode(), headers={"X-File-Name": "hello.txt"})
    assert r.status == 201 and data.decode() == "hello (2).txt"
    assert (folder / "hello.txt").read_text(encoding="utf-8") == "สวัสดี hello"
    assert (folder / "hello (2).txt").read_text(encoding="utf-8") == "ใหม่"
    r, _ = req(srv, "POST", "/sub/", body=b"x", headers={"X-File-Name": "..%2F..%2Fevil.txt"})
    assert r.status == 201
    assert (folder / "sub" / "evil.txt").exists()
    assert not (folder.parent / "evil.txt").exists()
    assert any(e.kind == "upload" for e in events)
    assert "ลากไฟล์" in req(srv, "GET", "/", headers={"Accept-Language": "th"})[1].decode()


def test_site_mode(run, folder):
    (folder / "index.html").write_text("<h1>My site</h1>")
    (folder / "app.js").write_text("console.log(1)")
    srv, _ = run(mode=MODE_SITE, allow_upload=True)
    r, data = req(srv, "GET", "/")
    assert r.status == 200 and data == b"<h1>My site</h1>"
    assert r.getheader("Content-Type").startswith("text/html")
    r, _ = req(srv, "GET", "/app.js")
    assert r.getheader("Content-Type").startswith("text/javascript")
    r, _ = req(srv, "GET", "/sub/")  # no index.html there, and no listing in site mode
    assert r.status == 404
    r, _ = req(srv, "POST", "/", body=b"x", headers={"X-File-Name": "x"})
    assert r.status == 403  # uploads only exist in file-sharing mode


def test_head(run):
    srv, _ = run()
    r, data = req(srv, "HEAD", "/hello.txt")
    assert r.status == 200 and data == b"" and int(r.getheader("Content-Length")) > 0


def test_stop_frees_port(run):
    srv, _ = run()
    port = srv.port
    srv.stop()
    assert not srv.running
    srv.share.port = port
    srv.start()
    assert req(srv, "GET", "/")[0].status == 200


def test_port_in_use(run, folder):
    srv, _ = run()
    other = ShareServer(Share(name="B", folder=str(folder), port=srv.port))
    with pytest.raises(OSError):
        other.start()


def test_missing_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        ShareServer(Share(name="x", folder=str(tmp_path / "nope"), port=free_port(18500))).start()


@pytest.mark.parametrize("raw,expected", [
    ("photo.jpg", "photo.jpg"),
    ("../../etc/passwd", "passwd"),
    ("C:\\Windows\\win.ini", "win.ini"),
    (".bashrc", "bashrc"),
    ("", "upload"),
    ("a<b>c?.txt", "a_b_c_.txt"),
    ("CON.txt", "_CON.txt"),
    ("รูปทริป.png", "รูปทริป.png"),
])
def test_safe_filename(raw, expected):
    assert safe_filename(raw) == expected


def test_unique_path(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "a (2).txt").write_text("2")
    assert unique_path(str(tmp_path), "a.txt").endswith("a (3).txt")


def test_store_roundtrip(tmp_path):
    p = tmp_path / "cfg" / "config.json"
    st = Store(str(p))
    st.lang = "en"
    st.shares.append(Share(name="ทริป", folder="/x", mode=MODE_FILES, port=9000, allow_upload=True, password="p"))
    st.save()
    again = Store(str(p))
    assert again.lang == "en"
    assert again.shares[0].name == "ทริป" and again.shares[0].allow_upload and again.shares[0].port == 9000
    p.write_text("{broken")
    assert Store(str(p)).shares == []


# ---------------------------------------------------------------- localhost proxy

import json  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

from app.engine import MODE_PROXY, detect_dev_servers, target_alive  # noqa: E402


class FakeDev(BaseHTTPRequestHandler):
    """Stands in for `npm run dev`: echoes what it received, streams, redirects, and speaks a tiny WebSocket."""
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _reply(self, body=b""):
        info = json.dumps({"method": self.command, "path": self.path, "host": self.headers.get("Host"),
                           "origin": self.headers.get("Origin"), "auth": self.headers.get("Authorization"),
                           "body": body.decode("utf-8", "replace")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(info)))
        self.end_headers()
        self.wfile.write(info)

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_address[1]}/login")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for part in (b"one,", b"two,", b"three"):
                self.wfile.write(b"%x\r\n%s\r\n" % (len(part), part))
            self.wfile.write(b"0\r\n\r\n")
        elif self.headers.get("Upgrade") == "websocket":
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.end_headers()
            self.wfile.flush()
            data = self.connection.recv(100)
            self.connection.sendall(b"echo:" + data)
            self.close_connection = True
        else:
            self._reply()

    def do_POST(self):
        self._reply(self.rfile.read(int(self.headers["Content-Length"])))


@pytest.fixture
def dev():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeDev)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def proxy(dev, tmp_path):
    srv = ShareServer(Share(name="dev", folder="", mode=MODE_PROXY, port=free_port(18700), target_port=dev))
    events = []
    srv.on_event = events.append
    srv.start()
    yield srv, events
    srv.stop()


def test_proxy_rewrites_host_and_origin(proxy, dev):
    srv, events = proxy
    r, data = req(srv, "GET", "/api/hello?x=1", headers={"Origin": f"http://10.0.0.5:{srv.port}",
                                                         "Accept": "text/html"})
    info = json.loads(data)
    assert r.status == 200
    assert info["path"] == "/api/hello?x=1"
    assert info["host"] == f"localhost:{dev}"
    assert info["origin"] == f"http://localhost:{dev}"
    assert any(e.kind == "view" for e in events)


def test_proxy_post_body(proxy):
    srv, _ = proxy
    r, data = req(srv, "POST", "/api/save", body="สวัสดี".encode(), headers={"Content-Type": "text/plain"})
    assert json.loads(data)["body"] == "สวัสดี"


def test_proxy_redirect_stays_on_lan_address(proxy):
    srv, _ = proxy
    r, _ = req(srv, "GET", "/redirect")
    assert r.status == 302 and r.getheader("Location") == "/login"


def test_proxy_streaming(proxy):
    srv, _ = proxy
    r, data = req(srv, "GET", "/stream")
    assert data == b"one,two,three"


def test_proxy_password_not_forwarded(proxy):
    srv, _ = proxy
    srv.share.password = "pw"
    assert req(srv, "GET", "/")[0].status == 401
    auth = base64.b64encode(b"x:pw").decode()
    r, data = req(srv, "GET", "/", headers={"Authorization": "Basic " + auth})
    assert r.status == 200 and json.loads(data)["auth"] is None


def test_proxy_websocket(proxy):
    srv, _ = proxy
    s = socket.create_connection(("127.0.0.1", srv.port), timeout=5)
    s.sendall(b"GET /_next/webpack-hmr HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
    head = b""
    while b"\r\n\r\n" not in head:
        head += s.recv(1024)
    assert head.startswith(b"HTTP/1.1 101")
    s.sendall(b"ping")
    got = head.split(b"\r\n\r\n", 1)[1]
    while not got.endswith(b"ping"):
        got += s.recv(1024)
    assert got == b"echo:ping"
    s.close()


def test_proxy_dev_server_down(tmp_path):
    port = free_port(18900)
    srv = ShareServer(Share(name="dev", folder="", mode=MODE_PROXY, port=free_port(18800), target_port=port))
    srv.start()
    try:
        r, data = req(srv, "GET", "/", headers={"Accept-Language": "th"})
        assert r.status == 502 and f"localhost:{port}".encode() in data
    finally:
        srv.stop()


def test_detect(dev):
    assert target_alive(dev)
    assert isinstance(detect_dev_servers(), list)
