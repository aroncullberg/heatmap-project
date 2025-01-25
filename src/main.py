import math
import sys
from typing import Tuple

from PySide6.QtCore import (Property, QEasingCurve, QObject,
                            QPropertyAnimation, QRect, QRectF, QRunnable, Qt,
                            QThreadPool, QUrl, Signal)
from PySide6.QtGui import (QColor, QFont, QImage, QIntValidator, QPainter,
                           QPainterPath, QPen)
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QPushButton,
                               QScrollArea, QSizePolicy, QSlider, QSpacerItem,
                               QVBoxLayout, QWidget)

from map_filters import MapFilter


class FilterWorkerSignals(QObject):
    finished = Signal(str, QImage)  # key, filtered_image


class FilterWorker(QRunnable):
    def __init__(self, key: str, image: QImage, filter_name: str):
        super().__init__()
        self.key = key
        self.image = image
        self.filter_name = filter_name
        self.signals = FilterWorkerSignals()

    def run(self):
        filtered = MapFilter.apply_filter(self.image, self.filter_name)
        self.signals.finished.emit(self.key, filtered)


class ClickableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.ClickFocus)

    def mousePressEvent(self, event):
        # Clear focus from any focused widget
        focused_widget = QApplication.focusWidget()
        if focused_widget:
            focused_widget.clearFocus()
        super().mousePressEvent(event)


class TransparentOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.aspect_ratio = (16, 9)  # Default aspect ratio
        self._hole_rect = QRect()
        self._initialized = False

        self._zoom_factor = 0.8  # Default zoom factor (80% of max size)

        # Setup animation
        self._animation = QPropertyAnimation(self, b"hole_rect", self)
        self._animation.setDuration(250)  # 250ms duration
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

        # Internal target size for animation
        self._target_size = (0, 0)

    def set_zoom_factor(self, value):
        """Set zoom factor (0.1 to 1.0) and update hole size"""
        self._zoom_factor = max(
            0.1, min(0.9, value / 100.0)
        )  # Convert 1-10 scale to 0.1-1.0
        if self._initialized:
            self.update_hole_size(animate=True)

    def get_hole_rect(self):
        return self._hole_rect

    def set_hole_rect(self, rect):
        self._hole_rect = rect
        self.update()

    # Define the animated property
    hole_rect = Property(QRect, get_hole_rect, set_hole_rect)

    def set_aspect_ratio(self, width, height):
        """Update the aspect ratio and trigger animation to new size"""
        if (width, height) == self.aspect_ratio:
            return

        self.aspect_ratio = (width, height)
        if self._initialized:
            self.update_hole_size(animate=True)

    def get_hole_bounds(self):
        """Return the current hole rectangle"""
        return self._hole_rect

    def showEvent(self, event):
        """Initialize hole rectangle when widget is first shown"""
        super().showEvent(event)
        if not self._initialized:
            self.update_hole_size()
            self._initialized = True

    def resizeEvent(self, event):
        """Update hole size and position when widget is resized"""
        super().resizeEvent(event)
        self.update_hole_size(animate=False)

    def update_hole_size(self, animate=True):
        """Calculate and update hole dimensions"""
        widget_width = self.width()
        widget_height = self.height()

        # Calculate maximum possible hole size while maintaining aspect ratio
        if (
            widget_width * self.aspect_ratio[1]
            <= widget_height * self.aspect_ratio[0]
        ):
            max_hole_width = int(widget_width)
            max_hole_height = int(
                max_hole_width * self.aspect_ratio[1] / self.aspect_ratio[0]
            )
        else:
            max_hole_height = int(widget_height)
            max_hole_width = int(
                max_hole_height * self.aspect_ratio[0] / self.aspect_ratio[1]
            )

        # Apply zoom factor to get actual hole size
        new_hole_width = int(max_hole_width * self._zoom_factor)
        new_hole_height = int(max_hole_height * self._zoom_factor)

        # Center position
        x = (widget_width - new_hole_width) // 2
        y = (widget_height - new_hole_height) // 2

        target_rect = QRect(x, y, new_hole_width, new_hole_height)

        if animate:
            self._animation.stop()
            self._animation.setStartValue(self._hole_rect)
            self._animation.setEndValue(target_rect)
            self._animation.start()
        else:
            self._hole_rect = target_rect
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create a path for the entire widget
        full_path = QPainterPath()
        full_path.addRect(self.rect())

        # Create a path for the hole using current animated rect
        hole_path = QPainterPath()
        hole_path.addRect(self._hole_rect)

        # Subtract the hole from the full path
        final_path = full_path.subtracted(hole_path)

        # Draw the semi-transparent overlay
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 128))
        painter.drawPath(final_path)

        # Draw white border around the hole
        painter.setPen(QPen(QColor(255, 102, 0, 128), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self._hole_rect)


class MapView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.zoom_level = 12
        self.pan_x = 0
        self.pan_y = 0
        self.last_mouse_pos = None
        self.is_panning = False
        self.tile_cache = {}
        self.pending_requests = {}
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.handle_tile_response)
        self.setMouseTracking(True)
        self.tile_url_template = (
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        )
        self.current_painter = None
        self.initial_location = (59.4, 13.5)  # Initial coordinates
        self.threadpool = QThreadPool()
        self.current_filter = None
        self.filter_workers = {}  # Track active workers
        self.filtered_cache = {}

        self.setMinimumSize(1280, 720)

        self.overlay = TransparentOverlay(self)

    def process_filtered_tile(self, key: str, filtered_image: QImage):
        """Callback when filter processing completes"""
        self.filtered_cache[key] = filtered_image
        if key in self.filter_workers:
            del self.filter_workers[key]
        self.update()

    def get_tile(self, x: int, y: int, zoom: int) -> QImage:
        key = self.tile_key(x, y, zoom)
        filter_key = f"{key}_{self.current_filter}"

        # Return cached filtered tile if available
        if filter_key in self.filtered_cache:
            return self.filtered_cache[filter_key]

        # Get original tile
        if key not in self.tile_cache:
            self.request_tile(x, y, zoom)
            return None

        original_tile = self.tile_cache[key]

        # Return original if no filter
        if self.current_filter == "None":
            return original_tile

        # Start filter processing in background if not already processing
        if filter_key not in self.filter_workers:
            worker = FilterWorker(
                filter_key, original_tile, self.current_filter
            )
            worker.signals.finished.connect(self.process_filtered_tile)
            self.filter_workers[filter_key] = worker
            self.threadpool.start(worker)

        # Return original tile while filter processes
        return original_tile

    def zoom_to(
        self, new_zoom: int, center_x: float = None, center_y: float = None
    ):
        """
        Shared zoom logic that can be used by both wheel and button events

        Args:
            new_zoom: Target zoom level
            center_x: X coordinate to zoom around (defaults to center if None)
            center_y: Y coordinate to zoom around (defaults to center if None)
        """
        # Clamp zoom level
        new_zoom = max(0, min(19, new_zoom))

        if new_zoom == self.zoom_level:
            return

        # Use widget center if no center point specified
        if center_x is None:
            center_x = self.width() / 2
        if center_y is None:
            center_y = self.height() / 2

        # Convert center position to world coordinates before zoom
        world_x = center_x - self.pan_x
        world_y = center_y - self.pan_y

        # Calculate the scale factor between zoom levels
        scale_factor = 2 ** (new_zoom - self.zoom_level)

        # Calculate new world coordinates
        new_world_x = world_x * scale_factor
        new_world_y = world_y * scale_factor

        # Update pan to keep the center point fixed
        self.pan_x = center_x - new_world_x
        self.pan_y = center_y - new_world_y

        # Update zoom level
        self.zoom_level = new_zoom
        self.overlay.raise_()
        # Refresh the view
        self.clear_cache()
        self.update()

    def set_filter(self, filter_name: str):
        """Set the current filter and clear filtered cache"""
        if self.current_filter != filter_name:
            self.current_filter = filter_name
            self.filtered_cache.clear()
            self.filter_workers.clear()  # Cancel any pending filter operations
            self.update()

    def resizeEvent(self, event):
        """Ensure overlay resizes with the map"""
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def get_selection_bounds(self):
        """Convert the overlay hole bounds to map coordinates"""
        hole_rect = self.overlay.get_hole_bounds()
        if not hole_rect:
            return None

        # Convert screen coordinates to map coordinates
        def screen_to_map(x, y):
            # Adjust for pan offset
            map_x = x - self.pan_x
            map_y = y - self.pan_y

            # Calculate tile coordinates
            tile_x = map_x / 256
            tile_y = map_y / 256

            # Convert to lat/lon
            n = 2.0**self.zoom_level
            lon_deg = (tile_x / n * 360.0) - 180.0
            lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
            lat_deg = math.degrees(lat_rad)

            return (lat_deg, lon_deg)

        # Get bounds
        nw = screen_to_map(hole_rect.left(), hole_rect.top())
        ne = screen_to_map(hole_rect.right(), hole_rect.top())
        sw = screen_to_map(hole_rect.left(), hole_rect.bottom())
        se = screen_to_map(hole_rect.right(), hole_rect.bottom())

        return {"nw": nw, "ne": ne, "sw": sw, "se": se}

    def set_aspect_ratio(self, width, height):
        """Update the overlay's aspect ratio"""
        self.overlay.set_aspect_ratio(width, height)

    def zoom_in(self):
        """Zoom in one level, centered on viewport"""
        self.zoom_to(self.zoom_level + 1)

    def zoom_out(self):
        """Zoom out one level, centered on viewport"""
        self.zoom_to(self.zoom_level - 1)

    def showEvent(self, event):
        """Center on initial location when the widget is first shown."""
        super().showEvent(event)
        if self.initial_location:
            lat, lon = self.initial_location
            self.center_on_location(lat, lon)
            self.initial_location = None  # Prevent re-centering

    def tile_key(self, x: int, y: int, zoom: int) -> str:
        """Generate unique key for tile caching"""
        return f"{zoom}_{x}_{y}"

    def geo_to_pixel(
        self, lat: float, lon: float, zoom: int
    ) -> Tuple[float, float]:
        # Convert latitude/longitude to pixel coordinates at a given zoom level
        lat_rad = math.radians(lat)
        n = 2.0**zoom
        x = (lon + 180.0) / 360.0 * n * 256  # Pixel X coordinate
        y = (
            (
                1.0
                - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad))
                / math.pi
            )
            / 2.0
            * n
            * 256
        )  # Pixel Y
        return x, y

    def center_on_location(self, lat: float, lon: float):
        """Center the map view on a geographic coordinate."""
        # Get pixel coordinates for the location
        pixel_x, pixel_y = self.geo_to_pixel(lat, lon, self.zoom_level)

        # Adjust pan offsets to center the view
        self.pan_x = self.width() / 2 - pixel_x
        self.pan_y = self.height() / 2 - pixel_y

        # Clear cache and reload tiles
        self.clear_cache()
        self.update()

    def request_tile(self, x: int, y: int, zoom: int):
        """Request a map tile if not already cached or pending"""
        key = self.tile_key(x, y, zoom)
        if key in self.tile_cache or key in self.pending_requests:
            return

        url = (
            self.tile_url_template.replace("{z}", str(zoom))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
        )

        request = QNetworkRequest(QUrl(url))
        # Store the key in the request
        request.setAttribute(QNetworkRequest.User, key)  # Use User attribute

        # Set a valid User-Agent header
        user_agent = "HeatmapApp/1.0 (contact@example.com)"
        request.setHeader(QNetworkRequest.UserAgentHeader, user_agent)

        self.pending_requests[key] = None
        self.network_manager.get(request)

    def handle_tile_response(self, reply):
        """Handle network response for tile request"""
        key = reply.request().attribute(QNetworkRequest.Attribute.User)

        if reply.error() == QNetworkReply.NoError:
            image_data = reply.readAll()
            image = QImage()
            image.loadFromData(image_data)

            if not image.isNull():
                self.tile_cache[key] = image
                self.update()
        else:
            # Optional: Log the error for debugging
            print(f"Error loading tile: {reply.errorString()}")

        reply.deleteLater()
        if key in self.pending_requests:
            del self.pending_requests[key]

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self.is_panning and self.last_mouse_pos:
            delta = event.position() - self.last_mouse_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse_pos = event.position()
            self.update()

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming"""
        delta = event.angleDelta().y()
        zoom_change = 1 if delta > 0 else -1 if delta < 0 else 0
        new_zoom = self.zoom_level + zoom_change

        # Use mouse position as zoom center
        mouse_pos = event.position()
        self.zoom_to(new_zoom, mouse_pos.x(), mouse_pos.y())

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            self.current_painter = painter
            painter.setRenderHint(QPainter.Antialiasing)

            # Fill background
            painter.fillRect(self.rect(), QColor(240, 240, 240))

            # Calculate visible area
            tile_size = 256  # OSM tile size
            scale = 2**self.zoom_level

            # Calculate visible tile range
            viewport_left = -self.pan_x
            viewport_top = -self.pan_y
            viewport_right = viewport_left + self.width()
            viewport_bottom = viewport_top + self.height()

            # Convert to tile coordinates
            start_x = max(0, int(viewport_left / tile_size))
            start_y = max(0, int(viewport_top / tile_size))
            end_x = min(scale - 1, int(viewport_right / tile_size) + 1)
            end_y = min(scale - 1, int(viewport_bottom / tile_size) + 1)

            # Draw visible tiles
            for x in range(start_x, end_x + 1):
                for y in range(start_y, end_y + 1):
                    tile = self.get_tile(x, y, self.zoom_level)
                    if tile:
                        dest_rect = QRectF(
                            x * tile_size + self.pan_x,
                            y * tile_size + self.pan_y,
                            tile_size,
                            tile_size,
                        )
                        painter.drawImage(dest_rect, tile)
                    else:
                        # Draw placeholder for loading tiles
                        painter.fillRect(
                            QRectF(
                                x * tile_size + self.pan_x,
                                y * tile_size + self.pan_y,
                                tile_size,
                                tile_size,
                            ),
                            QColor(200, 200, 200),
                        )
        finally:
            if self.current_painter:
                self.current_painter.end()
                self.current_painter = None

    def clear_cache(self):
        self.tile_cache.clear()
        self.pending_requests.clear()
        self.filter_workers.clear()  # Cancel any pending workers
        self.update()


class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Selector")
        self.setGeometry(100, 100, 1200, 800)

        self.file_list = []

        # Create central widget
        central_widget = ClickableWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Create sidebar
        sidebar = self.create_sidebar()
        layout.addWidget(sidebar)

        # Create map view
        self.map_view = MapView()
        self.map_view.set_aspect_ratio(16, 9)
        layout.addWidget(self.map_view)
        central_widget.setFocus()

    def create_sidebar(self):
        """ababoboo"""
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)

        # Add title
        title = QLabel("heatmap²")
        title_font = QFont()
        title_font.setPointSize(24)  # Increased from 16 to 24
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)

        # Resolution inputs
        res_layout = QVBoxLayout()
        res_label = QLabel("Resolution:")
        res_layout.addWidget(res_label)

        res_input_layout = QHBoxLayout()
        self.res_width = QLineEdit("1920")
        self.res_height = QLineEdit("1080")
        self.res_width.setValidator(QIntValidator(1, 100000))
        self.res_height.setValidator(QIntValidator(1, 100000))
        res_input_layout.addWidget(self.res_width)
        res_input_layout.addWidget(QLabel("x"))
        res_input_layout.addWidget(self.res_height)

        res_layout.addLayout(res_input_layout)
        sidebar_layout.addLayout(res_layout)

        # Aspect ratio inputs
        aspect_layout = QVBoxLayout()
        aspect_label = QLabel("Aspect Ratio:")
        aspect_layout.addWidget(aspect_label)

        aspect_input_layout = QHBoxLayout()
        self.aspect_width = QLineEdit("16")
        self.aspect_height = QLineEdit("9")
        aspect_input_layout.addWidget(self.aspect_width)
        aspect_input_layout.addWidget(QLabel("x"))
        aspect_input_layout.addWidget(self.aspect_height)

        self.aspect_height.setEnabled(False)
        self.aspect_width.setEnabled(False)

        aspect_layout.addLayout(aspect_input_layout)
        sidebar_layout.addLayout(aspect_layout)

        # Add zoom controls
        zoom_layout = QVBoxLayout()
        zoom_label = QLabel("Zoom:")
        zoom_layout.addWidget(zoom_label)

        zoom_input_layout = QHBoxLayout()

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(0)
        self.zoom_slider.setMaximum(19)
        # self.zoom_slider.valueChanged.connect(set_zoom_value)
        sidebar_layout.addWidget(self.zoom_slider)

        zoom_in = QPushButton("+")
        zoom_out = QPushButton("-")
        zoom_in.clicked.connect(lambda: self.adjust_zoom(1))
        zoom_out.clicked.connect(lambda: self.adjust_zoom(-1))
        zoom_input_layout.addWidget(zoom_out)
        zoom_input_layout.addWidget(zoom_in)

        zoom_layout.addLayout(zoom_input_layout)
        sidebar_layout.addLayout(zoom_layout)

        # Boundry zoom
        selection_area_layout = QVBoxLayout()
        selection_area_label = QLabel("Selection area:")
        selection_area_layout.addWidget(selection_area_label)

        bz_layout = QHBoxLayout()
        bz = QSlider(Qt.Horizontal)
        bz.setMinimum(0)
        bz.setMaximum(100)
        bz.setSliderPosition(80)
        bz.valueChanged.connect(self.update_overlay_size)
        bz_layout.addWidget(bz)
        selection_area_layout.addLayout(bz_layout)
        sidebar_layout.addLayout(selection_area_layout)

        # File selector
        file_scroll = QScrollArea()
        file_scroll.setWidgetResizable(True)
        self.file_container = QWidget()
        self.file_layout = QVBoxLayout(self.file_container)
        self.file_layout.setAlignment(Qt.AlignTop)

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.add_files)
        self.file_layout.addWidget(add_btn)

        file_scroll.setWidget(self.file_container)
        sidebar_layout.addWidget(file_scroll, 1)

        # Add spacer
        sidebar_layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Add lock button to sidebar
        self.lock_button = QPushButton("Lock")
        self.lock_button.setCheckable(True)
        self.lock_button.setEnabled(False)
        # self.lock_button.clicked.connect(self.toggle_map_lock)
        sidebar_layout.addWidget(self.lock_button)

        # Generate button
        self.generate_button = QPushButton("Generate")
        sidebar_layout.addWidget(self.generate_button)
        self.generate_button.clicked.connect(self.generate_heatmap)

        return sidebar

    def add_files(self):
        """Handle + button click to add files"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", "All Files (*)"
        )
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.add_file_widget(file_path)

    def add_file_widget(self, file_path):
        """Create and add a new file widget"""
        file_widget = FileWidget(file_path)
        file_widget.clicked.connect(self.remove_file)
        self.file_layout.insertWidget(1, file_widget)

    def remove_file(self, file_path):
        """Remove a file from the list"""
        if file_path in self.file_list:
            self.file_list.remove(file_path)

        # Find and remove the widget
        for i in reversed(range(self.file_layout.count())):
            widget = self.file_layout.itemAt(i).widget()
            if (
                isinstance(widget, FileWidget)
                and widget.file_path == file_path
            ):
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

    def update_overlay_size(self, value):
        """Update the overlay hole size based on slider value"""
        self.map_view.overlay.set_zoom_factor(value)

    def generate_heatmap(self):
        """Handle generate button click"""
        bounds = self.map_view.get_selection_bounds()
        if bounds:
            print("Selection bounds in coordinates:")
            print(f"Northwest: {bounds['nw']}")
            print(f"Northeast: {bounds['ne']}")
            print(f"Southwest: {bounds['sw']}")
            print(f"Southeast: {bounds['se']}")

    def adjust_zoom(self, delta: int):
        """Adjust map zoom level using buttons"""
        if delta > 0:
            self.map_view.zoom_in()
        else:
            self.map_view.zoom_out()


class FileWidget(QWidget):
    clicked = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        self.label = QLabel(file_path)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # self.setStyleSheet("""
        #     QWidget {
        #         border: 1px solid transparent;
        #         padding: 2px;
        #     }
        #     QWidget:hover {
        #         background: palette(light);
        #         border: 1px solid palette(mid);
        #     }
        # """)

    def mousePressEvent(self, event):
        """Handle clicks anywhere on the widget"""
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


def main():
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
