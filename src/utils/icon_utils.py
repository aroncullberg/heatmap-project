from PySide6 import QtGui

from utils.config import ICON_PATH


def png_to_icon(png_path=None):
    """
    Convert a PNG image to a QIcon.

    Args:
        png_path (str, optional): The path to the PNG file. If not provided,
        uses the default path from config.py.

    Returns:
        QtGui.QIcon: The icon created from the PNG file.

    Raises:
        FileNotFoundError: If the PNG file does not exist.
    """
    if png_path is None:
        png_path = ICON_PATH  # Use the default path from config.py

    icon = QtGui.QIcon()
    icon.addPixmap(
        QtGui.QPixmap(png_path), QtGui.QIcon.Selected, QtGui.QIcon.On
    )
    return icon
