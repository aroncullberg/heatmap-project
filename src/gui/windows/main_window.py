from PySide6.QtCore import QSize, QThreadPool
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow

from core.data_manager import DataManager
from core.workers import FileWorker

from ..widgets.clickable_widget import ClickableWidget
from ..widgets.file_widget import FileWidget
from ..widgets.map_view import MapView
from ..widgets.sidebar import SidebarWidget


class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool.globalInstance()
        self.loading_files = set()
        self.data_manager = DataManager()  # Initialize DataManager

        self.setWindowTitle("heatmap²")
        self.setGeometry(100, 100, 1200, 800)

        self.file_list = []

        central_widget = ClickableWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        self.map_view = MapView()
        self.map_view.set_aspect_ratio(16, 9)

        self.sidebar = SidebarWidget(self.map_view, self)
        self.sidebar.add_file_btn.clicked.connect(self.add_files)
        self.sidebar.generate_clicked.connect(self.generate_heatmap)
        self.sidebar.generate_button.setEnabled(False)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.map_view)

        self.generate_button = self.sidebar.generate_button

        central_widget.setFocus()

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def add_files(self):
        """Handle + button click to add files"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            "TCX Files (*.tcx);;GPX Files (*.gpx);;All Files (*)",
        )
        for file_path in files:
            if file_path not in self.file_list:
                self._start_file_processing(file_path=file_path)

    def _start_file_processing(self, file_path):
        """Begin async processing for a single file"""
        self.file_list.append(file_path)
        self.loading_files.add(file_path)

        # Add loading widget
        file_widget = FileWidget(file_path)
        file_widget.clicked.connect(self.remove_file)
        self.sidebar.file_layout.insertWidget(
            self.sidebar.file_layout.count() - 1, file_widget
        )

        # Configure worker
        worker = FileWorker(file_path)
        worker.finished.connect(self._on_file_loaded)
        worker.error.connect(self._on_file_error)

        # Start processing
        self.thread_pool.start(worker.process)

        # Update UI state
        self._update_ui_lock(True)

    def _on_file_loaded(self, file_path, points):
        """Handle successful file load"""
        self.data_manager.add_file(file_path, points)
        self._finalize_file_load(file_path)

    def _on_file_error(self, file_path, error_msg):
        """Handle file load error"""
        print(f"Error loading {file_path}: {error_msg}")
        self.file_list.remove(file_path)
        self._finalize_file_load(file_path, success=False)

    def _finalize_file_load(self, file_path, success=True):
        """Common cleanup for both success and error cases"""
        self.loading_files.discard(file_path)

        # Find and update widget
        for i in range(self.sidebar.file_layout.count()):
            widget = self.sidebar.file_layout.itemAt(i).widget()
            if isinstance(widget, FileWidget) and widget.file_path == file_path:
                if success:
                    widget.set_loaded()
                    widget.load_complete.emit(file_path)
                else:
                    widget.deleteLater()
                break

        # Update UI state when all files are processed
        if not self.loading_files:
            self._update_ui_lock(False)

    def _update_ui_lock(self, loading):
        """Enable/disable UI elements during loading"""
        self.sidebar.generate_button.setEnabled(not loading)
        self.sidebar.add_file_btn.setEnabled(not loading)

    def remove_file(self, file_path):
        """Remove a file from the list and its widget from the sidebar"""
        if file_path in self.loading_files:
            return
        self.data_manager.remove_file(file_path=file_path)

        if file_path in self.file_list:
            self.file_list.remove(file_path)
            if len(self.file_list) == 0:
                self.sidebar.generate_button.setEnabled(False)

        for i in range(self.sidebar.file_layout.count()):
            widget = self.sidebar.file_layout.itemAt(i).widget()
            if isinstance(widget, FileWidget) and widget.file_path == file_path:
                widget.deleteLater()
                break

    def calculate_aspect_ratio(
        self, width: int, height: int
    ) -> tuple[int, int]:
        """Calculate the simplified aspect ratio from dimensions."""
        if width <= 0 or height <= 0:
            return (16, 9)  # Default aspect ratio

        def gcd(a: int, b: int) -> int:
            """Calculate greatest common divisor using Euclidean algorithm."""
            while b:
                a, b = b, a % b
            return a

        divisor = gcd(width, height)
        return (width // divisor, height // divisor)

    def generate_heatmap(self):
        """Handle generate button click"""
        print("here")
        bounds = self.map_view.get_selection_bounds()
        if not bounds:
            return

        # Get resolution from sidebar inputs
        try:
            width = int(self.sidebar.res_width.text())
            height = int(self.sidebar.res_height.text())
        except ValueError:
            width, height = 1920, 1080  # Default if invalid

        # Get selected files
        selected_files = self.file_list

        if not selected_files:
            return  # No files selected

        # Here you would call your heatmap generation logic with:
        # - bounds (coordinate boundaries)
        # - width, height (output resolution)
        # - selected_files (list of TCX/GPX files to process)
        print(f"Generating heatmap with bounds: {bounds}")
        print(f"Resolution: {width}x{height}")
        print(f"Files: {selected_files}")

    def sizeHint(self) -> QSize:
        """Provide a reasonable default size"""
        return QSize(1200, 800)
