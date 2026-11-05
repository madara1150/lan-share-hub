"""Run the real app on sample folders and save README screenshots to docs/screenshots.

    .venv/bin/python tools/screenshots.py

App windows are grabbed with Qt; the pages friends see are rendered by headless Google Chrome
from the app's own running servers.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.engine import MODE_FILES, MODE_PROXY, MODE_SITE  # noqa: E402
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
import functools  # noqa: E402
import threading  # noqa: E402
from app.i18n import set_lang  # noqa: E402
import app.main_window as mw  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from app.store import Store  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screenshots")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# README pictures must not show this computer's real address or folders: use example values on screen
SAMPLE_IP = "192.168.1.25"
SAMPLE_HOME = "~/Documents"
mw.lan_addresses = lambda: [SAMPLE_IP]

SITE_HTML = """<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Team Board</title>
<style>body{margin:0;font:16px/1.6 -apple-system,"Sukhumvit Set",sans-serif;background:#0f172a;color:#e2e8f0}
main{max-width:760px;margin:0 auto;padding:48px 20px}h1{font-size:34px;margin:0 0 6px}
.c{background:#1e293b;border-radius:14px;padding:18px 20px;margin:14px 0}b{color:#38bdf8}</style></head>
<body><main><h1>🚀 Team Board</h1><p>Sprint 12 · demo page served from a folder with index.html</p>
<div class="c"><b>Done</b> — Login page, upload form</div><div class="c"><b>Doing</b> — Dashboard charts</div>
<div class="c"><b>Next</b> — Mobile layout</div></main></body></html>"""


def make_samples(base):
    files = os.path.join(base, "Class Project")
    os.makedirs(os.path.join(files, "Trip photos"), exist_ok=True)
    os.makedirs(os.path.join(files, "Slides"), exist_ok=True)
    samples = {
        "Final report.pdf": 2_400_000, "Presentation.pptx": 8_700_000, "Budget.xlsx": 48_000,
        "Meeting notes.txt": 3_200, "Demo video.mp4": 46_000_000, "Source code.zip": 1_300_000,
        "Logo.png": 210_000,
    }
    for name, size in samples.items():
        with open(os.path.join(files, name), "wb") as f:
            f.truncate(size)
    site = os.path.join(base, "team-board")
    os.makedirs(site, exist_ok=True)
    with open(os.path.join(site, "index.html"), "w", encoding="utf-8") as f:
        f.write(SITE_HTML)
    return files, site


def pump(app, secs=0.4):
    end = time.time() + secs
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def grab(app, widget, name):
    pump(app)
    path = os.path.join(OUT, name)
    widget.grab().save(path)
    im = Image.open(path)
    if im.width > 2000:
        im = im.resize((2000, round(im.height * 2000 / im.width)), Image.LANCZOS)
    im.save(path, optimize=True)
    print("saved", name)


def chrome_shot(url, name, lang, size):
    if not os.path.exists(CHROME):
        print("Google Chrome not found, skipping", name)
        return
    prof = tempfile.mkdtemp()
    path = os.path.join(OUT, name)
    phone = size[0] < 500
    if phone:  # headless Chrome has a minimum window width, so show the page in a phone-sized frame
        frame = os.path.join(prof, "frame.html")
        with open(frame, "w") as f:
            f.write(f'<body style="margin:0"><iframe src="{url}" style="width:{size[0]}px;height:{size[1]}px;border:0">')
        url, size = "file://" + frame, (600, size[1])
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                    f"--lang={lang}", f"--accept-lang={lang}", "--force-device-scale-factor=2", "--blink-settings=preferredColorScheme=1",
                    f"--window-size={size[0]},{size[1]}", f"--screenshot={path}", url],
                   check=True, capture_output=True, timeout=60)
    shutil.rmtree(prof, ignore_errors=True)
    if phone:
        im = Image.open(path)
        im.crop((0, 0, 390 * 2, im.height)).save(path, optimize=True)
    print("saved", name)


def visit(port, ip, path, data=None, headers=None):
    req = urllib.request.Request(f"http://{ip}:{port}{path}", data=data, headers=headers or {},
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req) as r:
        r.read()


def run(lang, base):
    files, site = make_samples(base)
    store = Store(os.path.join(base, f"config-{lang}.json"))
    store.lang = lang
    set_lang(lang)
    win = MainWindow(store)
    real_show = win._show_current

    def show_with_sample_path():
        real_show()
        if win.current and win.current.folder:
            shown = os.path.join(SAMPLE_HOME, os.path.basename(win.current.folder))
            win.folder_edit.setText(shown)
            win.folder_edit.setToolTip(shown)
    win._show_current = show_with_sample_path
    win._force_close = True
    win.setAttribute(Qt.WA_DontShowOnScreen)  # so the window can be taller than this screen
    win.show()
    win.resize(1240, 1010)
    app = QApplication.instance()

    # empty state
    grab(app, win, f"empty-{lang}.png")

    # a real local "dev server" (python's http.server serving the sample app) for the localhost-testing mode
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    dev = ThreadingHTTPServer(("127.0.0.1", 5173), functools.partial(Quiet, directory=site))
    threading.Thread(target=dev.serve_forever, daemon=True).start()
    px = win.add_share(MODE_PROXY, target_port=5173)

    fs = win.add_share(MODE_FILES, files)
    fs.name = "Class Project" if lang == "en" else "งานกลุ่ม"
    fs.allow_upload = True
    st = win.add_share(MODE_SITE, site)
    st.name = "Team Board"
    win.start_share(px)
    win.start_share(fs)
    win.start_share(st)
    ip = "127.0.0.1"  # real requests go to this computer; the window shows SAMPLE_IP

    # real traffic so the activity list has something to show
    visit(fs.port, ip, "/")
    visit(fs.port, ip, "/Final%20report.pdf?dl=1")
    visit(fs.port, ip, "/Trip%20photos/")
    visit(fs.port, ip, "/Trip%20photos/", data=b"\x89PNG sample", headers={"X-File-Name": "beach.png"})
    visit(fs.port, ip, "/Budget.xlsx?dl=1")
    visit(st.port, ip, "/")
    for _ in range(2):
        visit(px.port, ip, "/", headers={"Accept": "text/html"})

    win.select_share(px)
    win._show_current()
    grab(app, win, f"proxy-{lang}.png")
    chrome_shot(f"http://127.0.0.1:{px.port}/", f"web-proxy-{lang}.png", lang, (390, 760))

    win.select_share(fs)
    win._show_current()
    grab(app, win, f"main-{lang}.png")

    # the page friends see
    chrome_shot(f"http://127.0.0.1:{fs.port}/", f"web-files-{lang}.png", lang, (1100, 940))
    chrome_shot(f"http://127.0.0.1:{fs.port}/", f"web-mobile-{lang}.png", lang, (390, 760))

    win.select_share(st)
    grab(app, win, f"site-{lang}.png")

    if lang == "th":
        win.select_share(fs)
        win.toggle_theme()
        grab(app, win, "dark-th.png")
        win.toggle_theme()

    win.close()
    dev.shutdown()
    dev.server_close()
    pump(app)


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    for lang in ("th", "en"):
        base = tempfile.mkdtemp(prefix="lsh-shots-")
        try:
            run(lang, base)
        finally:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
