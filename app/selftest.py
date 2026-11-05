"""`<app> --selftest [log]`: checks a built app without opening a window (used by CI). Exit code 0 = pass."""
import http.client
import os
import sys
import tempfile
import threading
import traceback
from http.server import BaseHTTPRequestHandler


def _get(port, path="/"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    return r.status, r.read()


def _checks(log):
    from PySide6.QtWidgets import QApplication  # noqa: F401  (bundled Qt loads)
    import segno

    from .engine import MODE_PROXY, FastHTTPServer, Share, ShareServer, free_port

    segno.make("http://192.168.1.25:8080/").save(os.path.join(tempfile.gettempdir(), "lsh-qr.png"), scale=4)
    log("qr ok")

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "ไฟล์.txt"), "w", encoding="utf-8") as f:
            f.write("hello")
        srv = ShareServer(Share(name="t", folder=d, port=free_port(18080)))
        srv.start()
        try:
            assert _get(srv.port, "/%E0%B9%84%E0%B8%9F%E0%B8%A5%E0%B9%8C.txt") == (200, b"hello")
        finally:
            srv.stop()
    log("file sharing ok")

    class Dev(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            body = self.headers.get("Host", "").encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    dev = FastHTTPServer(("127.0.0.1", 0), Dev)
    threading.Thread(target=dev.serve_forever, daemon=True).start()
    srv = ShareServer(Share(name="p", folder="", mode=MODE_PROXY, port=free_port(18200),
                            target_port=dev.server_address[1]))
    srv.start()
    try:
        status, body = _get(srv.port)
        assert status == 200 and body == f"localhost:{dev.server_address[1]}".encode(), (status, body)
    finally:
        srv.stop()
        dev.shutdown()
    log("localhost proxy ok")


def run(log_path=""):
    lines = []

    def log(msg):
        lines.append(msg)

    code = 0
    try:
        _checks(log)
        log("PASS")
    except Exception:
        log(traceback.format_exc())
        log("FAIL")
        code = 1
    text = "\n".join(lines) + "\n"
    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return code
