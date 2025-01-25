from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QWidget


class LoadingFileWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        self.setFixedHeight(40)
