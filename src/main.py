import sys

from PySide6.QtWidgets import QApplication

from gui.windows.main_window import MapWindow
from utils.icon_utils import png_to_icon


def main():
    app = QApplication(sys.argv)

    window = MapWindow()
    window.setWindowIcon(png_to_icon())

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
