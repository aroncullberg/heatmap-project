from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget, QProgressBar


class FileWidget(QWidget):
    clicked = Signal(str)
    load_complete = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.is_loaded = False

        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.label = QLabel(file_path)
        self.label.setWordWrap(True)
        self.label.hide()
        
        layout.addWidget(self.label)

    def set_loaded(self):
        """Switch from loading to loaded state"""
        self.is_loaded = True
        self.progress.hide()
        self.label.show()
        
    def mousePressEvent(self, event):
        if self.is_loaded:  # Only allow removal when loaded
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Mouse hover in"""
        self.label.setStyleSheet(
            "text-decoration: line-through; color: #fb9e4b;"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse hover out"""
        self.label.setStyleSheet("")
        super().leaveEvent(event)
