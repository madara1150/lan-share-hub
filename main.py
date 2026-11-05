import sys


def main():
    if "--selftest" in sys.argv:  # used by CI on the built app: no window, exit code says pass/fail
        from app.selftest import run as selftest
        i = sys.argv.index("--selftest")
        sys.exit(selftest(sys.argv[i + 1] if len(sys.argv) > i + 1 else ""))
    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("LAN Share Hub")
    app.setOrganizationName("Tanathip")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
