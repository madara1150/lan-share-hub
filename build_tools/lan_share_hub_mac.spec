# PyInstaller spec for macOS -> dist/LAN Share Hub.app
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
VERSION = os.environ.get("APP_VERSION", "1.0.1")
EXCLUDES = ["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtPdf",
            "PySide6.QtBluetooth", "PySide6.QtSql"]

a = Analysis([os.path.join(ROOT, "main.py")], pathex=[ROOT],
             datas=[(os.path.join(ROOT, "assets"), "assets")], excludes=EXCLUDES)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LAN Share Hub", console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="LAN Share Hub", upx=False)
app = BUNDLE(
    coll,
    name="LAN Share Hub.app",
    icon=os.path.join(ROOT, "build", "icon.icns"),
    bundle_identifier="com.madara1150.lansharehub",
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "LAN Share Hub",
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSHumanReadableCopyright": "Copyright (c) 2026 Tanathip",
        "NSLocalNetworkUsageDescription": "LAN Share Hub serves your shared folders to devices on your local network.",
    },
)
