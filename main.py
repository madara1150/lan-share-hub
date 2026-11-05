import sys


def main():
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
