"""Saved shares and settings (a small JSON file in the user's config folder)."""
import json
import os
import sys
import tempfile

from .engine import Share

APP_DIR_NAME = "LAN Share Hub"


def default_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_DIR_NAME, "config.json")


class Store:
    def __init__(self, path=None):
        self.path = path or default_path()
        self.shares = []
        self.lang = "th"
        self.theme = "light"
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        self.lang = data.get("lang", "th") if data.get("lang") in ("th", "en") else "th"
        self.theme = data.get("theme", "light") if data.get("theme") in ("light", "dark") else "light"
        self.shares = []
        for d in data.get("shares", []):
            try:
                self.shares.append(Share.from_dict(d))
            except TypeError:
                continue

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        data = {"lang": self.lang, "theme": self.theme, "shares": [s.to_dict() for s in self.shares]}
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
