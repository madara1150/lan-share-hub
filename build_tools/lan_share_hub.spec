# PyInstaller spec for Windows -> dist/LANShareHub/LANShareHub.exe
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
EXCLUDES = ["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtPdf",
            "PySide6.QtBluetooth", "PySide6.QtSql"]

a = Analysis([os.path.join(ROOT, "main.py")], pathex=[ROOT],
             datas=[(os.path.join(ROOT, "assets"), "assets")], excludes=EXCLUDES)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LANShareHub", console=False, upx=False,
          icon=os.path.join(ROOT, "assets", "icon.ico"),
          version=os.path.join(ROOT, "build_tools", "version_info.txt"))
coll = COLLECT(exe, a.binaries, a.datas, name="LANShareHub", upx=False)
