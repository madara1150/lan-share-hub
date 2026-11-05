"""Dialog listing the web apps running on this computer, so the user can pick which ones friends may test."""
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from .engine import LocalApp, find_local_apps
from .i18n import tr


class _Finder(QObject):
    done = Signal(object, int)  # list of LocalApp, scan id


def app_icon(app: LocalApp) -> str:
    p = (app.process + " " + app.server).lower()
    if "docker" in p:
        return "🐳"
    if "node" in p or "next" in p or "vite" in p or "express" in p:
        return "🟩"
    if "python" in p or "werkzeug" in p or "uvicorn" in p or "gunicorn" in p or "django" in p:
        return "🐍"
    if "php" in p or "java" in p or "ruby" in p or "dotnet" in p or "go" == p.strip():
        return "⚙️"
    return "🧪"


class AppPicker(QDialog):
    """`chosen(port, name)` is emitted when the user picks an app."""
    chosen = Signal(int, str)

    def __init__(self, parent, shared_ports, exclude_ports, pick_only=False):
        super().__init__(parent)
        self.shared_ports = dict(shared_ports)  # target port -> share name
        self.exclude = set(exclude_ports)
        self.pick_only = pick_only
        self._scan_id = 0
        self._finder = _Finder()
        self._finder.done.connect(self._show_apps)
        self.setWindowTitle(tr("picker_title"))
        self.setMinimumSize(620, 520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)
        head = QHBoxLayout()
        col = QVBoxLayout()
        title = QLabel(tr("picker_title"))
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        sub = QLabel(tr("picker_sub_pick") if pick_only else tr("picker_sub"))
        sub.setProperty("role", "mute")
        sub.setWordWrap(True)
        col.addWidget(title)
        col.addWidget(sub)
        head.addLayout(col, 1)
        self.refresh_btn = QPushButton("⟳ " + tr("picker_refresh"))
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.scan)
        head.addWidget(self.refresh_btn, 0, Qt.AlignTop)
        lay.addLayout(head)

        self.status = QLabel()
        self.status.setProperty("role", "mute")
        lay.addWidget(self.status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.rows = QWidget()
        self.rows_lay = QVBoxLayout(self.rows)
        self.rows_lay.setContentsMargins(0, 0, 0, 0)
        self.rows_lay.setSpacing(8)
        self.rows_lay.addStretch(1)
        self.scroll.setWidget(self.rows)
        lay.addWidget(self.scroll, 1)

        manual = QFrame()
        manual.setProperty("role", "card")
        ml = QHBoxLayout(manual)
        ml.setContentsMargins(14, 10, 14, 10)
        ml.addWidget(QLabel(tr("picker_manual")))
        ml.addWidget(QLabel("http://localhost :"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(3000)
        self.port_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.port_spin.setFixedWidth(90)
        ml.addWidget(self.port_spin)
        ml.addStretch(1)
        go = QPushButton(tr("picker_use") if pick_only else tr("picker_share"))
        go.setCursor(Qt.PointingHandCursor)
        go.clicked.connect(lambda: self._choose(self.port_spin.value(), ""))
        ml.addWidget(go)
        lay.addWidget(manual)
        self.scan()

    # ------------------------------------------------------------------
    def scan(self):
        self._scan_id += 1
        sid = self._scan_id
        self.refresh_btn.setEnabled(False)
        self.status.setText("🔎 " + tr("picker_scanning"))
        exclude = set(self.exclude)

        def work():
            try:
                apps = find_local_apps(exclude=exclude)
            except Exception:
                apps = []
            self._finder.done.emit(apps, sid)

        threading.Thread(target=work, daemon=True).start()

    def _clear(self):
        while self.rows_lay.count() > 1:
            w = self.rows_lay.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _show_apps(self, apps, sid):
        if sid != self._scan_id:
            return
        self.apps = apps
        self.refresh_btn.setEnabled(True)
        self._clear()
        self.status.setText(tr("picker_found", n=len(apps)) if apps else tr("picker_none"))
        for i, app in enumerate(apps):
            self.rows_lay.insertWidget(i, self._row(app))

    def _row(self, app: LocalApp):
        row = QFrame()
        row.setProperty("role", "card")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 10, 12, 10)
        rl.setSpacing(12)
        icon = QLabel(app_icon(app))
        icon.setStyleSheet("font-size: 22px;")
        rl.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(1)
        name = QLabel(app.title or f"localhost:{app.port}")
        name.setStyleSheet("font-weight: 700; font-size: 14px;")
        bits = [f"localhost:{app.port}"] if app.title else []
        bits += [b for b in (app.process, app.server) if b]
        if not (200 <= app.status < 400):
            bits.append(f"HTTP {app.status}")
        sub = QLabel(" · ".join(bits))
        sub.setProperty("role", "mute")
        col.addWidget(name)
        col.addWidget(sub)
        rl.addLayout(col, 1)
        shared = self.shared_ports.get(app.port)
        if shared and not self.pick_only:
            btn = QPushButton("✓ " + tr("picker_already"))
            btn.setToolTip(shared)
        else:
            btn = QPushButton(tr("picker_use") if self.pick_only else "▶ " + tr("picker_share"))
            btn.setProperty("kind", "primary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _=False, a=app: self._choose(a.port, a.title))
        rl.addWidget(btn)
        return row

    def _choose(self, port, name):
        self.chosen.emit(int(port), name or "")
        self.accept()
