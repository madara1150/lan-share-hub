"""Light / dark Qt style sheets built from one set of colour tokens."""
import os

THEMES = {
    "light": {
        "bg": "#f4f6fb", "panel": "#ffffff", "card": "#ffffff", "ink": "#0f172a", "mute": "#64748b",
        "line": "#e3e8f1", "acc": "#2563eb", "acc_hover": "#1d4ed8", "acc_soft": "#e8efff", "acc2": "#0ea5a4",
        "ok": "#16a34a", "ok_soft": "#dcfce7", "off": "#94a3b8", "off_soft": "#eef2f7", "danger": "#dc2626",
        "danger_soft": "#fee2e2", "input": "#f8fafc", "sel": "#e8efff", "warn": "#b45309", "warn_soft": "#fef3c7",
    },
    "dark": {
        "bg": "#0b1220", "panel": "#0f1729", "card": "#121b2e", "ink": "#e6edf8", "mute": "#8a99b2",
        "line": "#1f2b42", "acc": "#3b82f6", "acc_hover": "#60a5fa", "acc_soft": "#16264a", "acc2": "#2dd4bf",
        "ok": "#22c55e", "ok_soft": "#0f2e1f", "off": "#64748b", "off_soft": "#1a2438", "danger": "#f87171",
        "danger_soft": "#3a1418", "input": "#0d1526", "sel": "#16264a", "warn": "#fbbf24", "warn_soft": "#3a2a0c",
    },
}

QSS = """
* {{ font-size: 13px; color: {ink}; }}
QMainWindow, QDialog, #root {{ background: {bg}; }}
QToolTip {{ background: {card}; color: {ink}; border: 1px solid {line}; padding: 4px 8px; }}
#topbar {{ background: {panel}; border-bottom: 1px solid {line}; }}
#brand {{ font-size: 17px; font-weight: 700; }}
#brandSub, .mute, QLabel[role="mute"] {{ color: {mute}; }}
#ipChip {{ background: {acc_soft}; color: {acc}; border-radius: 13px; padding: 5px 12px; font-weight: 600; }}
#sidebar {{ background: {panel}; border-right: 1px solid {line}; }}
QLabel[role="section"] {{ color: {mute}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; }}
QListWidget#shareList {{ background: transparent; border: none; outline: none; }}
QListWidget#shareList::item {{ border-radius: 10px; margin: 2px 0; }}
QListWidget#shareList::item:selected {{ background: {sel}; }}
QListWidget#shareList::item:hover:!selected {{ background: {off_soft}; }}
QLabel[role="itemName"] {{ font-weight: 600; font-size: 14px; }}
QLabel[role="itemSub"] {{ color: {mute}; font-size: 12px; }}
QFrame[role="card"] {{ background: {card}; border: 1px solid {line}; border-radius: 14px; }}
QLabel[role="cardTitle"] {{ font-size: 14px; font-weight: 700; }}
QLabel#shareTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#url {{ font-size: 21px; font-weight: 700; color: {acc}; }}
QLabel#url[off="true"] {{ color: {off}; }}
QLabel[role="pill"] {{ border-radius: 11px; padding: 3px 10px; font-weight: 600; font-size: 12px; }}
QLabel[role="pill"][state="on"] {{ background: {ok_soft}; color: {ok}; }}
QLabel[role="pill"][state="off"] {{ background: {off_soft}; color: {mute}; }}
QLabel[role="pill"][state="mode"] {{ background: {acc_soft}; color: {acc}; }}
QLabel[role="warn"] {{ background: {warn_soft}; color: {warn}; border-radius: 8px; padding: 6px 10px; }}
QLabel#emptyTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#qr {{ background: #ffffff; border-radius: 12px; border: 1px solid {line}; }}

QPushButton {{ background: {card}; border: 1px solid {line}; border-radius: 9px; padding: 7px 14px; font-weight: 600; min-height: 18px; }}
QPushButton:hover {{ background: {off_soft}; }}
QPushButton:disabled {{ color: {off}; }}
QPushButton[kind="primary"] {{ background: {acc}; color: #ffffff; border: none; }}
QPushButton[kind="primary"]:hover {{ background: {acc_hover}; }}
QPushButton[kind="go"] {{ background: {ok}; color: #ffffff; border: none; font-size: 14px; padding: 10px 22px; border-radius: 11px; }}
QPushButton[kind="go"]:hover {{ background: {acc2}; }}
QPushButton[kind="stop"] {{ background: {danger_soft}; color: {danger}; border: none; font-size: 14px; padding: 10px 22px; border-radius: 11px; }}
QPushButton[kind="danger"] {{ color: {danger}; }}
QPushButton[kind="big"] {{ padding: 12px 22px; font-size: 14px; border-radius: 12px; }}
QPushButton[kind="ghost"] {{ background: transparent; border: none; color: {mute}; padding: 6px 10px; }}
QPushButton[kind="ghost"]:hover {{ background: {off_soft}; color: {ink}; }}

QLineEdit, QSpinBox, QComboBox {{ background: {input}; border: 1px solid {line}; border-radius: 8px; padding: 6px 9px; min-height: 20px;
    selection-background-color: {acc}; selection-color: #ffffff; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {acc}; }}
QLineEdit:disabled {{ color: {off}; }}
QComboBox QAbstractItemView {{ background: {card}; border: 1px solid {line}; selection-background-color: {sel}; selection-color: {ink}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1.5px solid {off}; border-radius: 5px; background: {input}; }}
QCheckBox::indicator:hover {{ border-color: {acc}; }}
QCheckBox::indicator:checked {{ background: {acc}; border-color: {acc}; image: url({check}); }}
QCheckBox::indicator:disabled {{ background: {off_soft}; border-color: {line}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({chevron}); width: 12px; height: 12px; }}
QCheckBox:disabled {{ color: {off}; }}

QTableWidget {{ background: transparent; border: none; gridline-color: transparent; selection-background-color: {sel}; selection-color: {ink}; }}
QTableWidget::item {{ padding: 4px 6px; border-bottom: 1px solid {line}; }}
QHeaderView, QTableCornerButton::section {{ background: transparent; border: none; }}
QHeaderView::section {{ background: transparent; color: {mute}; border: none; border-bottom: 1px solid {line};
    padding: 6px; font-weight: 700; font-size: 12px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {line}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QMessageBox {{ background: {card}; }}
"""


def stylesheet(theme: str, assets_dir: str = "") -> str:
    def url(name):
        return os.path.join(assets_dir, name).replace("\\", "/")
    return QSS.format(check=url("check.svg"), chevron=url("chevron.svg"), **THEMES.get(theme, THEMES["light"]))


def color(theme: str, key: str) -> str:
    return THEMES.get(theme, THEMES["light"])[key]
