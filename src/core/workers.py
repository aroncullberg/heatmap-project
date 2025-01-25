from PySide6.QtCore import QObject, Signal
from tcxparser import TCXParser


class FileWorker(QObject):
    finished = Signal(str, list)
    error = Signal(str, str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def process(self):
        try:
            trackpoints = TCXParser(self.file_path).position_values()
            points = [
                (float(pt[0]), float(pt[1]))
                for pt in trackpoints
                if pt[0] and pt[1]
            ]
            self.finished.emit(self.file_path, points)

            self.finished.emit(self.file_path, points)
        except Exception as e:
            self.error.emit(self.file_path, str(e))
