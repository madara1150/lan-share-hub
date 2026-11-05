import os
import urllib.request

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.engine import MODE_FILES, MODE_SITE  # noqa: E402
from app.i18n import S  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from app.store import Store  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(qapp, tmp_path):
    w = MainWindow(Store(str(tmp_path / "config.json")))
    w._force_close = True
    yield w
    w.close()


def pump(qapp, until, tries=200):
    import time
    for _ in range(tries):
        qapp.processEvents()
        if until():
            return True
        time.sleep(0.01)
    return False


def test_strings_have_both_languages():
    for key, pair in S.items():
        assert len(pair) == 2 and all(pair), key


def test_empty_state(win):
    assert win.stack.currentIndex() == 0


def test_add_start_visit_stop(win, qapp, tmp_path):
    folder = tmp_path / "share"
    folder.mkdir()
    (folder / "a.txt").write_text("hi")
    share = win.add_share(MODE_FILES, str(folder))
    assert win.current is share and win.stack.currentIndex() == 1
    assert win.title.text() == "share"
    assert win.start_share(share)
    assert win.is_running(share)
    assert win.url.text().endswith(f":{share.port}/")
    with urllib.request.urlopen(f"http://127.0.0.1:{share.port}/a.txt") as r:
        assert r.read() == b"hi"
    assert pump(qapp, lambda: win.table.rowCount() > 0)
    win.stop_share(share)
    assert not win.is_running(share)
    win.store.save()
    assert Store(win.store.path).shares[0].folder == str(folder)


def test_site_mode_disables_upload(win, tmp_path):
    folder = tmp_path / "site"
    folder.mkdir()
    share = win.add_share(MODE_FILES, str(folder))
    win.upload_chk.setChecked(True)
    assert share.allow_upload
    win.type_combo.setCurrentIndex(win.type_combo.findData(MODE_SITE))
    assert share.mode == MODE_SITE and not share.allow_upload
    assert not win.upload_chk.isEnabled()
    assert not win.index_warn.isHidden()


def test_password_and_language(win, tmp_path):
    folder = tmp_path / "pw"
    folder.mkdir()
    share = win.add_share(MODE_FILES, str(folder))
    win.pw_chk.setChecked(True)
    win.pw_edit.setText("1234")
    win._pw_changed("1234")
    assert share.password == "1234"
    win.pw_chk.setChecked(False)
    assert share.password == ""
    th = win.toggle_btn.text()
    win.toggle_lang()
    assert win.toggle_btn.text() != th
    assert win.store.lang == "en"


def test_two_shares_get_different_ports(win, tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    s1 = win.add_share(MODE_FILES, str(a))
    s2 = win.add_share(MODE_FILES, str(b))
    assert s1.port != s2.port
    assert win.list.count() == 2


def test_proxy_share(win, qapp):
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    from app.engine import MODE_PROXY

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    dev = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=dev.serve_forever, daemon=True).start()
    try:
        share = win.add_share(MODE_PROXY, target_port=dev.server_address[1])
        assert share.name == f"localhost:{dev.server_address[1]}"
        assert win.folder_edit.isHidden() and not win.target_box.isHidden()
        assert not win.upload_chk.isVisibleTo(win)
        win._refresh_target()
        assert "●" in win.target_status.text()
        assert win.start_share(share)
        with urllib.request.urlopen(f"http://127.0.0.1:{share.port}/") as r:
            assert r.status == 200
        win.stop_share(share)
        assert win.type_combo.currentData() == MODE_PROXY
    finally:
        dev.shutdown()
        dev.server_close()
