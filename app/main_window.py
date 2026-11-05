"""Main window: list of shares on the left, link / QR / settings / activity of the selected share on the right."""
import datetime as _dt
import io
import os
import sys

import segno
from PySide6.QtCore import QObject, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QMenu,
                               QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import __version__
from .engine import (MODE_FILES, MODE_PROXY, MODE_SITE, Event, Share, ShareServer, detect_dev_servers, free_port,
                     lan_addresses, share_url, target_alive)
from .i18n import lang, set_lang, tr
from .store import Store
from .styles import color, stylesheet

MAX_EVENTS = 500


def asset(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", name)


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


def card():
    f = QFrame()
    f.setProperty("role", "card")
    return f


def label(text="", role=None, wrap=False):
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def button(text="", kind=None):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    b.setCursor(Qt.PointingHandCursor)
    return b


def qr_pixmap(text, size):
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="png", scale=10, border=2)
    pm = QPixmap()
    pm.loadFromData(buf.getvalue(), "PNG")
    return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


MODE_ICON = {MODE_FILES: "📁", MODE_SITE: "🌐", MODE_PROXY: "🧪"}
MODE_ORDER = (MODE_PROXY, MODE_FILES, MODE_SITE)


def mode_name(mode):
    return tr({MODE_FILES: "mode_files", MODE_SITE: "mode_site", MODE_PROXY: "mode_proxy"}[mode])


class Bridge(QObject):
    """Carries server events from the server threads to the UI thread."""
    event = Signal(str, object)


class ShareItem(QWidget):
    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(10)
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.icon = QLabel()
        self.icon.setStyleSheet("font-size: 20px;")
        col = QVBoxLayout()
        col.setSpacing(1)
        self.name = label(role="itemName")
        self.sub = label(role="itemSub")
        col.addWidget(self.name)
        col.addWidget(self.sub)
        lay.addWidget(self.icon)
        lay.addLayout(col, 1)
        lay.addWidget(self.dot)

    def update_from(self, share, running, theme):
        self.icon.setText(MODE_ICON[share.mode])
        self.name.setText(share.name)
        state = tr("status_on") if running else tr("status_off")
        if share.mode == MODE_PROXY:
            self.sub.setText(f"localhost:{share.target_port} → :{share.port} · {state}")
        else:
            self.sub.setText(f"{mode_name(share.mode)} · :{share.port} · {state}")
        c = color(theme, "ok" if running else "off")
        self.dot.setStyleSheet(f"background:{c}; border-radius:5px;")


class MainWindow(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store()
        set_lang(self.store.lang)
        self.servers = {}  # share id -> ShareServer
        self.events = {}  # share id -> [Event]
        self.visitors = {}  # share id -> set of client IPs
        self.bridge = Bridge()
        self.bridge.event.connect(self._on_event)
        self.current = None  # selected Share
        self._loading = False
        self._save_timer = QTimer(self, singleShot=True, interval=400, timeout=self.store.save)
        self.ips = lan_addresses()

        self.setWindowTitle("LAN Share Hub")
        if os.path.exists(asset("icon.png")):
            self.setWindowIcon(QIcon(asset("icon.png")))
        self.resize(1160, 760)
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)
        self._build()
        self.apply_theme()
        self.retranslate()
        self._reload_list()
        for s in self.store.shares:
            if s.auto_start and (s.mode == MODE_PROXY or os.path.isdir(s.folder)):
                self.start_share(s, quiet=True)
        if self.store.shares:
            self.list.setCurrentRow(0)
        # the LAN address can change (laptop moves to another Wi-Fi)
        self._ip_timer = QTimer(self, interval=3000, timeout=self._refresh_ip)
        self._ip_timer.start()

    # ------------------------------------------------------------------ layout
    def _build(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # top bar
        top = QFrame(objectName="topbar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(18, 10, 14, 10)
        logo = QLabel()
        if os.path.exists(asset("icon.png")):
            logo.setPixmap(QPixmap(asset("icon.png")).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        tl.addWidget(logo)
        bcol = QVBoxLayout()
        bcol.setSpacing(0)
        self.brand = QLabel("LAN Share Hub", objectName="brand")
        self.brand_sub = QLabel(objectName="brandSub")
        bcol.addWidget(self.brand)
        bcol.addWidget(self.brand_sub)
        tl.addLayout(bcol)
        tl.addStretch(1)
        self.ip_chip = QLabel(objectName="ipChip")
        tl.addWidget(self.ip_chip)
        self.theme_btn = button(kind="ghost")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.lang_btn = button(kind="ghost")
        self.lang_btn.clicked.connect(self.toggle_lang)
        self.about_btn = button(kind="ghost")
        self.about_btn.clicked.connect(self.show_about)
        for b in (self.theme_btn, self.lang_btn, self.about_btn):
            tl.addWidget(b)
        outer.addWidget(top)

        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # sidebar
        side = QFrame(objectName="sidebar")
        side.setFixedWidth(300)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 16, 14, 14)
        sl.setSpacing(8)
        self.list_title = label(role="section")
        sl.addWidget(self.list_title)
        self.list = QListWidget(objectName="shareList")
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.currentRowChanged.connect(self._select_row)
        sl.addWidget(self.list, 1)
        self.add_proxy_btn = button(kind="primary")
        self.add_proxy_btn.clicked.connect(lambda: self.add_share(MODE_PROXY))
        sl.addWidget(self.add_proxy_btn)
        self.add_files_btn = button()
        self.add_files_btn.clicked.connect(lambda: self.add_share(MODE_FILES))
        self.add_site_btn = button()
        self.add_site_btn.clicked.connect(lambda: self.add_share(MODE_SITE))
        sl.addWidget(self.add_files_btn)
        sl.addWidget(self.add_site_btn)
        self.drop_hint = label(role="mute")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        sl.addWidget(self.drop_hint)
        row = QHBoxLayout()
        self.start_all_btn = button(kind="ghost")
        self.start_all_btn.clicked.connect(self.start_all)
        self.stop_all_btn = button(kind="ghost")
        self.stop_all_btn.clicked.connect(self.stop_all)
        row.addWidget(self.start_all_btn)
        row.addWidget(self.stop_all_btn)
        sl.addLayout(row)
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_empty())
        self.stack.addWidget(self._build_detail())

    def _build_empty(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addStretch(1)
        art = QLabel()
        if os.path.exists(asset("icon.png")):
            art.setPixmap(QPixmap(asset("icon.png")).scaled(112, 112, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        art.setAlignment(Qt.AlignCenter)
        lay.addWidget(art)
        self.empty_title = QLabel(objectName="emptyTitle")
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_body = label(role="mute", wrap=True)
        self.empty_body.setAlignment(Qt.AlignCenter)
        lay.addSpacing(10)
        lay.addWidget(self.empty_title)
        lay.addWidget(self.empty_body)
        lay.addSpacing(16)
        row = QHBoxLayout()
        row.addStretch(1)
        self.empty_proxy_btn = button(kind="primary")
        self.empty_proxy_btn.clicked.connect(lambda: self.add_share(MODE_PROXY))
        self.empty_files_btn = button()
        self.empty_files_btn.clicked.connect(lambda: self.add_share(MODE_FILES))
        self.empty_site_btn = button()
        self.empty_site_btn.clicked.connect(lambda: self.add_share(MODE_SITE))
        for b in (self.empty_proxy_btn, self.empty_files_btn, self.empty_site_btn):
            b.setMinimumHeight(44)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(2)
        return w

    def _build_detail(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        scroll.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(26, 22, 26, 26)
        lay.setSpacing(16)

        # title row
        head = QHBoxLayout()
        self.title = QLabel(objectName="shareTitle")
        self.state_pill = label(role="pill")
        self.mode_pill = label(role="pill")
        self.mode_pill.setProperty("state", "mode")
        head.addWidget(self.title)
        head.addSpacing(6)
        head.addWidget(self.state_pill)
        head.addWidget(self.mode_pill)
        head.addStretch(1)
        self.toggle_btn = button()
        self.toggle_btn.setMinimumWidth(150)
        self.toggle_btn.clicked.connect(self.toggle_current)
        head.addWidget(self.toggle_btn)
        lay.addLayout(head)

        # link card
        link = card()
        ll = QHBoxLayout(link)
        ll.setContentsMargins(20, 18, 18, 18)
        ll.setSpacing(18)
        lc = QVBoxLayout()
        lc.setSpacing(6)
        self.link_title = label(role="cardTitle")
        self.url = QLabel(objectName="url")
        self.url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.other_urls = label(role="mute")
        self.other_urls.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.link_hint = label(role="mute", wrap=True)
        lc.addWidget(self.link_title)
        lc.addWidget(self.url)
        lc.addWidget(self.other_urls)
        lc.addWidget(self.link_hint)
        br = QHBoxLayout()
        self.copy_btn = button(kind="primary")
        self.copy_btn.clicked.connect(self.copy_url)
        self.open_btn = button()
        self.open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.current_url(local=True))))
        br.addWidget(self.copy_btn)
        br.addWidget(self.open_btn)
        br.addStretch(1)
        lc.addSpacing(4)
        lc.addLayout(br)
        self.firewall_tip = label(role="mute", wrap=True)
        self.firewall_tip.setStyleSheet("font-size: 12px;")
        lc.addWidget(self.firewall_tip)
        lc.addStretch(1)
        ll.addLayout(lc, 1)
        self.qr = QLabel(objectName="qr")
        self.qr.setFixedSize(176, 176)
        self.qr.setAlignment(Qt.AlignCenter)
        ll.addWidget(self.qr, 0, Qt.AlignTop)
        lay.addWidget(link)

        # settings card
        sc = card()
        sg = QGridLayout(sc)
        sg.setContentsMargins(20, 16, 20, 18)
        sg.setHorizontalSpacing(14)
        sg.setVerticalSpacing(10)
        self.settings_title = label(role="cardTitle")
        sg.addWidget(self.settings_title, 0, 0, 1, 4)
        self.lb_name, self.lb_folder, self.lb_type, self.lb_port, self.lb_pw = (label() for _ in range(5))
        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._name_changed)
        sg.addWidget(self.lb_name, 1, 0)
        sg.addWidget(self.name_edit, 1, 1, 1, 3)

        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.choose_btn = button()
        self.choose_btn.clicked.connect(self.choose_folder)
        self.reveal_btn = button()
        self.reveal_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.current.folder)))
        sg.addWidget(self.lb_folder, 2, 0)
        sg.addWidget(self.folder_edit, 2, 1)
        sg.addWidget(self.choose_btn, 2, 2)
        sg.addWidget(self.reveal_btn, 2, 3)
        self.folder_widgets = (self.lb_folder, self.folder_edit, self.choose_btn, self.reveal_btn)

        self.lb_target = label()
        self.target_box = QWidget()
        tb = QHBoxLayout(self.target_box)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.addWidget(label("http://localhost :"))
        self.target_spin = QSpinBox()
        self.target_spin.setRange(1, 65535)
        self.target_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.target_spin.setFixedWidth(100)
        self.target_spin.editingFinished.connect(self._target_changed)
        tb.addWidget(self.target_spin)
        self.target_status = label()
        tb.addWidget(self.target_status, 1)
        self.detect_btn = button()
        self.detect_btn.clicked.connect(self.detect_menu)
        tb.addWidget(self.detect_btn)
        sg.addWidget(self.lb_target, 10, 0)
        sg.addWidget(self.target_box, 10, 1, 1, 3)
        self.proxy_note = label(role="mute", wrap=True)
        sg.addWidget(self.proxy_note, 11, 1, 1, 3)
        self.target_widgets = (self.lb_target, self.target_box, self.proxy_note)
        # keep the "your app" row right under the name: move rows 10-11 above the folder row
        for w in self.target_widgets:
            sg.removeWidget(w)
        sg.addWidget(self.lb_target, 2, 0)
        sg.addWidget(self.target_box, 2, 1, 1, 3)
        sg.addWidget(self.proxy_note, 4, 1, 1, 3)

        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.port_spin.setFixedWidth(110)
        self.port_spin.editingFinished.connect(self._port_changed)
        trow = QHBoxLayout()
        trow.addWidget(self.type_combo, 1)
        trow.addSpacing(16)
        trow.addWidget(self.lb_port)
        trow.addWidget(self.port_spin)
        sg.addWidget(self.lb_type, 3, 0)
        sg.addLayout(trow, 3, 1, 1, 3)
        self.index_warn = label(role="warn", wrap=True)
        sg.addWidget(self.index_warn, 4, 1, 1, 3)

        self.upload_chk = QCheckBox()
        self.upload_chk.toggled.connect(self._upload_changed)
        self.upload_note = label(role="mute", wrap=True)
        sg.addWidget(self.upload_chk, 5, 1, 1, 3)
        sg.addWidget(self.upload_note, 6, 1, 1, 3)

        self.pw_chk = QCheckBox()
        self.pw_chk.toggled.connect(self._pw_toggled)
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.pw_edit.textEdited.connect(self._pw_changed)
        self.pw_show = QCheckBox()
        self.pw_show.toggled.connect(lambda on: self.pw_edit.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        prow = QHBoxLayout()
        prow.addWidget(self.pw_chk)
        prow.addWidget(self.pw_edit, 1)
        prow.addWidget(self.pw_show)
        sg.addWidget(self.lb_pw, 7, 0)
        sg.addLayout(prow, 7, 1, 1, 3)
        self.pw_hint = label(role="mute", wrap=True)
        sg.addWidget(self.pw_hint, 8, 1, 1, 3)

        self.auto_chk = QCheckBox()
        self.auto_chk.toggled.connect(self._auto_changed)
        sg.addWidget(self.auto_chk, 9, 1, 1, 2)
        self.delete_btn = button(kind="danger")
        self.delete_btn.clicked.connect(self.delete_current)
        sg.addWidget(self.delete_btn, 9, 3, Qt.AlignRight)
        sg.setColumnStretch(1, 1)
        lay.addWidget(sc)

        # activity card
        ac = card()
        al = QVBoxLayout(ac)
        al.setContentsMargins(20, 16, 20, 16)
        ah = QHBoxLayout()
        self.activity_title = label(role="cardTitle")
        self.visitors_lb = label(role="pill")
        self.visitors_lb.setProperty("state", "mode")
        self.clear_btn = button(kind="ghost")
        self.clear_btn.clicked.connect(self.clear_activity)
        ah.addWidget(self.activity_title)
        ah.addWidget(self.visitors_lb)
        ah.addStretch(1)
        ah.addWidget(self.clear_btn)
        al.addLayout(ah)
        self.table = QTableWidget(0, 4)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setMinimumHeight(220)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.no_activity = label(role="mute")
        self.no_activity.setAlignment(Qt.AlignCenter)
        al.addWidget(self.table)
        al.addWidget(self.no_activity)
        lay.addWidget(ac)
        lay.addStretch(1)
        lay.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        return scroll

    # ------------------------------------------------------------------ text & theme
    def retranslate(self):
        self.brand_sub.setText(tr("brand_sub"))
        self.lang_btn.setText("🌐 " + tr("lang_switch"))
        self.theme_btn.setText(("🌙 " + tr("dark")) if self.store.theme == "light" else ("☀️ " + tr("light")))
        self.about_btn.setText("ⓘ " + tr("about"))
        self.list_title.setText(tr("shares").upper() if lang() == "en" else tr("shares"))
        self.add_proxy_btn.setText("🧪  " + tr("new_proxy"))
        self.empty_proxy_btn.setText("🧪  " + tr("new_proxy"))
        self.lb_target.setText(tr("target"))
        self.detect_btn.setText("🔎 " + tr("detect"))
        self.add_files_btn.setText("📁  " + tr("new_files"))
        self.add_site_btn.setText("🌐  " + tr("new_site"))
        self.empty_files_btn.setText("📁  " + tr("new_files"))
        self.empty_site_btn.setText("🌐  " + tr("new_site"))
        self.drop_hint.setText(tr("drop_hint"))
        self.start_all_btn.setText("▶ " + tr("start_all"))
        self.stop_all_btn.setText("■ " + tr("stop_all"))
        self.empty_title.setText(tr("empty_title"))
        self.empty_body.setText(tr("empty_body"))
        self.link_title.setText(tr("link_title"))
        self.copy_btn.setText("📋 " + tr("copy"))
        self.open_btn.setText("↗ " + tr("open_browser"))
        self.firewall_tip.setText("💡 " + tr("firewall_tip"))
        self.settings_title.setText(tr("settings"))
        self.lb_name.setText(tr("name"))
        self.lb_folder.setText(tr("folder"))
        self.lb_type.setText(tr("type"))
        self.lb_port.setText(tr("port"))
        self.lb_pw.setText(tr("password"))
        self.choose_btn.setText(tr("choose"))
        self.reveal_btn.setText(tr("show_folder"))
        self._loading = True
        idx = self.type_combo.currentIndex()
        self.type_combo.clear()
        for m in MODE_ORDER:
            self.type_combo.addItem(MODE_ICON[m] + "  " + mode_name(m), m)
        self.type_combo.setCurrentIndex(max(0, idx))
        self._loading = False
        self.upload_chk.setText(tr("allow_upload"))
        self.pw_chk.setText(tr("use_password"))
        self.pw_show.setText(tr("show"))
        self.pw_hint.setText(tr("password_hint"))
        self.auto_chk.setText(tr("auto_start"))
        self.delete_btn.setText("🗑  " + tr("delete"))
        self.activity_title.setText(tr("activity"))
        self.clear_btn.setText(tr("clear"))
        self.no_activity.setText(tr("no_activity"))
        self.table.setHorizontalHeaderLabels([tr("col_time"), tr("col_device"), tr("col_action"), tr("col_file")])
        self._refresh_ip()
        self._refresh_items()
        self._show_current()
        self._fill_table()

    def apply_theme(self):
        QApplication.instance().setStyleSheet(stylesheet(self.store.theme, os.path.dirname(asset("check.svg"))))
        self._refresh_items()

    def toggle_theme(self):
        self.store.theme = "dark" if self.store.theme == "light" else "light"
        self.apply_theme()
        self.retranslate()
        self._save()

    def toggle_lang(self):
        self.store.lang = "en" if lang() == "th" else "th"
        set_lang(self.store.lang)
        self.retranslate()
        self._save()

    def show_about(self):
        QMessageBox.about(self, "LAN Share Hub", tr("about_msg", v=__version__))

    # ------------------------------------------------------------------ list
    def _reload_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for s in self.store.shares:
            it = QListWidgetItem()
            it.setData(Qt.UserRole, s.id)
            it.setSizeHint(QSize(260, 58))
            self.list.addItem(it)
            self.list.setItemWidget(it, ShareItem())
        self.list.blockSignals(False)
        self._refresh_items()
        if not self.store.shares:
            self.current = None
            self.stack.setCurrentIndex(0)

    def _refresh_items(self):
        if not hasattr(self, "list"):
            return
        for i in range(self.list.count()):
            it = self.list.item(i)
            s = self._share(it.data(Qt.UserRole))
            w = self.list.itemWidget(it)
            if s and w:
                w.update_from(s, self.is_running(s), self.store.theme)

    def _share(self, sid):
        return next((s for s in self.store.shares if s.id == sid), None)

    def _select_row(self, row):
        if row < 0 or row >= len(self.store.shares):
            self.current = None
            self.stack.setCurrentIndex(0)
            return
        self.current = self._share(self.list.item(row).data(Qt.UserRole))
        self.stack.setCurrentIndex(1)
        self._show_current()
        self._fill_table()

    def select_share(self, share):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == share.id:
                self.list.setCurrentRow(i)
                return

    # ------------------------------------------------------------------ detail
    def is_running(self, share):
        srv = self.servers.get(share.id)
        return bool(srv and srv.running)

    def current_url(self, local=False):
        if not self.current:
            return ""
        ip = "localhost" if local or not self.ips else self.ips[0]
        return share_url(ip, self.current.port)

    def _show_current(self):
        s = self.current
        if not s:
            return
        self._loading = True
        running = self.is_running(s)
        self.title.setText(s.name)
        self.state_pill.setText(("● " + tr("status_on")) if running else tr("status_off"))
        self.state_pill.setProperty("state", "on" if running else "off")
        self.mode_pill.setText(mode_name(s.mode))
        self.toggle_btn.setText(("■  " + tr("stop")) if running else ("▶  " + tr("start")))
        self.toggle_btn.setProperty("kind", "stop" if running else "go")
        url = share_url(self.ips[0] if self.ips else None, s.port)
        self.url.setText(url)
        self.url.setProperty("off", "false" if running else "true")
        others = [share_url(ip, s.port) for ip in self.ips[1:3]]
        self.other_urls.setText("  ·  ".join(others))
        self.other_urls.setVisible(bool(others))
        self.link_hint.setText(tr("link_hint") if running else tr("link_off"))
        self.qr.setPixmap(qr_pixmap(url, 164))
        self.qr.setEnabled(running)
        self.qr.setGraphicsEffect(None)
        if not running:
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            eff = QGraphicsOpacityEffect(self.qr)
            eff.setOpacity(0.35)
            self.qr.setGraphicsEffect(eff)
        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(running)
        for w in (self.state_pill, self.toggle_btn, self.url):
            repolish(w)

        if self.name_edit.text() != s.name:
            self.name_edit.setText(s.name)
        self.folder_edit.setText(s.folder)
        self.folder_edit.setCursorPosition(0)
        self.folder_edit.setToolTip(s.folder)
        self.type_combo.setCurrentIndex(MODE_ORDER.index(s.mode))
        self.port_spin.setValue(int(s.port))
        site = s.mode == MODE_SITE
        proxy = s.mode == MODE_PROXY
        for w in self.folder_widgets:
            w.setVisible(not proxy)
        for w in self.target_widgets:
            w.setVisible(proxy)
        self.target_spin.setValue(int(s.target_port))
        self.proxy_note.setText(tr("proxy_note", port=s.target_port))
        self._refresh_target()
        self.upload_chk.setVisible(not proxy)
        self.upload_note.setVisible(not proxy)
        self.upload_chk.setChecked(s.allow_upload and not site)
        self.upload_chk.setEnabled(not site)
        self.upload_note.setText(tr("upload_site_note") if site else tr("upload_note"))
        has_index = any(os.path.isfile(os.path.join(s.folder, n)) for n in ("index.html", "index.htm"))
        self.index_warn.setText("⚠️ " + tr("no_index_warn"))
        self.index_warn.setVisible(site and not has_index)
        self.pw_chk.setChecked(bool(s.password))
        self.pw_edit.setText(s.password)
        self.pw_edit.setEnabled(bool(s.password) or self.pw_chk.isChecked())
        self.pw_edit.setPlaceholderText(tr("password"))
        self.auto_chk.setChecked(s.auto_start)
        self._loading = False
        self._refresh_visitors()

    def _changed(self, refresh=True):
        self._save()
        self._refresh_items()
        if refresh:
            self._show_current()

    def _save(self):
        self._save_timer.start()

    def _name_changed(self, text):
        if self._loading or not self.current:
            return
        self.current.name = text.strip() or os.path.basename(self.current.folder) or "Share"
        self.title.setText(self.current.name)
        self._changed(refresh=False)

    def _type_changed(self, idx):
        if self._loading or not self.current or idx < 0:
            return
        self.current.mode = self.type_combo.itemData(idx)
        if self.current.mode != MODE_FILES:
            self.current.allow_upload = False
        self._changed()

    def _upload_changed(self, on):
        if self._loading or not self.current:
            return
        self.current.allow_upload = on
        self._changed(refresh=False)

    def _pw_toggled(self, on):
        if self._loading or not self.current:
            return
        self.pw_edit.setEnabled(on)
        if on:
            self.pw_edit.setFocus()
            self.current.password = self.pw_edit.text()
        else:
            self.current.password = ""
        self._changed(refresh=False)

    def _pw_changed(self, text):
        if self._loading or not self.current:
            return
        self.current.password = text
        self._changed(refresh=False)

    def _auto_changed(self, on):
        if self._loading or not self.current:
            return
        self.current.auto_start = on
        self._changed(refresh=False)

    def _port_changed(self):
        if self._loading or not self.current:
            return
        new = self.port_spin.value()
        s = self.current
        if new == s.port:
            return
        running = self.is_running(s)
        old = s.port
        if running:
            self.stop_share(s)
        s.port = new
        if running and not self.start_share(s):
            s.port = old
            self.start_share(s, quiet=True)
        self._changed()

    def _target_changed(self):
        if self._loading or not self.current:
            return
        self.current.target_port = self.target_spin.value()
        self._changed()

    def _refresh_target(self):
        s = self.current
        if not s or s.mode != MODE_PROXY:
            return
        alive = target_alive(s.target_port)
        self.target_status.setText(tr("target_on") if alive else tr("target_off"))
        self.target_status.setStyleSheet(f"color: {color(self.store.theme, 'ok' if alive else 'warn')};")

    def detect_menu(self):
        if not self.current:
            return
        ports = detect_dev_servers(exclude={x.port for x in self.store.shares})
        menu = QMenu(self)
        if not ports:
            menu.addAction(tr("detect_none")).setEnabled(False)
        for p in ports:
            menu.addAction(f"localhost:{p}", lambda p=p: self.set_target(p))
        menu.exec(self.detect_btn.mapToGlobal(self.detect_btn.rect().bottomLeft()))

    def set_target(self, port):
        if not self.current:
            return
        old_name = f"localhost:{self.current.target_port}"
        self.current.target_port = port
        if self.current.name == old_name:
            self.current.name = f"localhost:{port}"
        self._changed()

    def choose_folder(self):
        if not self.current:
            return
        d = QFileDialog.getExistingDirectory(self, tr("choose_folder"), self.current.folder)
        if not d:
            return
        self.current.folder = os.path.normpath(d)  # a running server picks it up on the next request
        self._changed()

    # ------------------------------------------------------------------ add / delete
    def add_share(self, mode, folder=None, target_port=None):
        taken = {s.port for s in self.store.shares}
        if mode == MODE_PROXY:
            if target_port is None:
                found = detect_dev_servers(exclude=taken)
                target_port = found[0] if found else 3000
            share = Share(name=f"localhost:{target_port}", folder="", mode=MODE_PROXY,
                          port=free_port(8090, taken | {target_port}), target_port=target_port)
            self.store.shares.append(share)
            self._reload_list()
            self.select_share(share)
            self._save()
            return share
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, tr("choose_folder"), os.path.expanduser("~"))
            if not folder:
                return None
        folder = os.path.normpath(folder)
        taken = {s.port for s in self.store.shares}
        share = Share(name=os.path.basename(folder) or folder, folder=folder, mode=mode,
                      port=free_port(8080 if mode == MODE_FILES else 8000, taken))
        self.store.shares.append(share)
        self._reload_list()
        self.select_share(share)
        self._save()
        return share

    def delete_current(self):
        s = self.current
        if not s:
            return
        if QMessageBox.question(self, "LAN Share Hub", tr("delete_confirm", name=s.name)) != QMessageBox.Yes:
            return
        self.stop_share(s)
        self.servers.pop(s.id, None)
        self.events.pop(s.id, None)
        self.visitors.pop(s.id, None)
        row = self.store.shares.index(s)
        self.store.shares.remove(s)
        self._reload_list()
        if self.store.shares:
            self.list.setCurrentRow(min(row, len(self.store.shares) - 1))
        self._save()

    # ------------------------------------------------------------------ start / stop
    def start_share(self, share, quiet=False):
        srv = self.servers.get(share.id)
        if srv is None:
            srv = ShareServer(share, lambda ev, sid=share.id: self.bridge.event.emit(sid, ev))
            self.servers[share.id] = srv
        try:
            srv.start()
        except FileNotFoundError:
            if not quiet:
                QMessageBox.warning(self, tr("err_start"), tr("err_folder", folder=share.folder))
            return False
        except OSError:
            if not quiet:
                taken = {s.port for s in self.store.shares}
                free = free_port(share.port + 1, taken)
                box = QMessageBox(QMessageBox.Warning, tr("err_start"), tr("err_port", port=share.port, free=free),
                                  parent=self)
                use = box.addButton(tr("use_port", port=free), QMessageBox.AcceptRole)
                box.addButton(tr("cancel"), QMessageBox.RejectRole)
                box.exec()
                if box.clickedButton() is use:
                    share.port = free
                    self._save()
                    return self.start_share(share)
            return False
        finally:
            self._refresh_items()
            if share is self.current:
                self._show_current()
        return True

    def stop_share(self, share):
        srv = self.servers.get(share.id)
        if srv:
            srv.stop()
        self._refresh_items()
        if share is self.current:
            self._show_current()

    def toggle_current(self):
        if not self.current:
            return
        if self.is_running(self.current):
            self.stop_share(self.current)
        else:
            self.start_share(self.current)

    def start_all(self):
        for s in self.store.shares:
            if not self.is_running(s):
                self.start_share(s, quiet=True)

    def stop_all(self):
        for s in self.store.shares:
            self.stop_share(s)

    def copy_url(self):
        QApplication.clipboard().setText(self.current_url())
        self.copy_btn.setText("✓ " + tr("copied"))
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 " + tr("copy")))

    def _refresh_ip(self):
        ips = lan_addresses()
        changed = ips != self.ips
        self.ips = ips
        self.ip_chip.setText(f"📶 {tr('your_ip')}: {ips[0]}" if ips else "⚠️ " + tr("no_network"))
        self._refresh_target()
        if changed and self.current:
            self._show_current()

    # ------------------------------------------------------------------ activity
    def _on_event(self, sid, ev: Event):
        lst = self.events.setdefault(sid, [])
        lst.append(ev)
        del lst[:-MAX_EVENTS]
        if ev.kind != "auth":
            local = ev.client.startswith("127.") or ev.client in self.ips
            self.visitors.setdefault(sid, set()).add("local" if local else ev.client)
        if self.current and self.current.id == sid:
            self._add_row(ev, top=True)
            self._refresh_visitors()

    def _add_row(self, ev, top=False):
        names = {"view": tr("act_view"), "download": "⬇ " + tr("act_download"), "upload": "⬆ " + tr("act_upload"),
                 "denied": "⛔ " + tr("act_denied"), "auth": "🔒 " + tr("act_auth")}
        row = 0 if top else self.table.rowCount()
        self.table.insertRow(row)
        when = _dt.datetime.fromtimestamp(ev.time).strftime("%H:%M:%S")
        device = "💻 " + ("เครื่องนี้" if lang() == "th" else "This computer") if ev.client in (
            "127.0.0.1", *self.ips) else "📱 " + ev.client
        for col, text in enumerate((when, device, names.get(ev.kind, ev.kind), ev.path)):
            it = QTableWidgetItem(text)
            it.setToolTip(text)
            self.table.setItem(row, col, it)
        while self.table.rowCount() > MAX_EVENTS:
            self.table.removeRow(self.table.rowCount() - 1)
        self.table.setVisible(True)
        self.no_activity.setVisible(False)

    def _fill_table(self):
        self.table.setRowCount(0)
        if not self.current:
            return
        evs = self.events.get(self.current.id, [])
        for ev in reversed(evs):
            self._add_row(ev)
        self.table.setVisible(bool(evs))
        self.no_activity.setVisible(not evs)
        self._refresh_visitors()

    def _refresh_visitors(self):
        n = len(self.visitors.get(self.current.id, ())) if self.current else 0
        self.visitors_lb.setText(tr("visitors", n=n))
        self.visitors_lb.setVisible(n > 0)

    def clear_activity(self):
        if not self.current:
            return
        self.events.pop(self.current.id, None)
        self.visitors.pop(self.current.id, None)
        self._fill_table()

    # ------------------------------------------------------------------ drag & drop, close
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(os.path.isdir(u.toLocalFile()) for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if os.path.isdir(p):
                mode = MODE_SITE if os.path.isfile(os.path.join(p, "index.html")) else MODE_FILES
                self.add_share(mode, p)

    def closeEvent(self, e):
        running = [s for s in self.store.shares if self.is_running(s)]
        if running and not getattr(self, "_force_close", False):
            box = QMessageBox(QMessageBox.Question, "LAN Share Hub", tr("quit_running", n=len(running)), parent=self)
            q = box.addButton(tr("quit"), QMessageBox.AcceptRole)
            box.addButton(tr("cancel"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is not q:
                e.ignore()
                return
        self.shutdown()
        e.accept()

    def shutdown(self):
        self._save_timer.stop()
        try:
            self.store.save()
        except OSError:
            pass
        for srv in self.servers.values():
            srv.stop()
