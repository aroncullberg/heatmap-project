import math
from pathlib import Path
from typing import Tuple

import numpy as np
from PySide6.QtCore import (
    QObject,
    QRectF,
    QRunnable,
    Qt,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .overlay import TransparentOverlay


class FilterWorkerSignals(QObject):
    """Signals for the filter worker"""

    finished = Signal(str, QImage)  # key, filtered_image
    error = Signal(str)  # error message


class TileFilterWorker(QRunnable):
    """Worker thread for filtering map tiles."""

    def __init__(self, image: QImage, tile_key: str):
        super().__init__()
        self.image = image.copy()  # Make a copy to ensure thread safety
        self.tile_key = tile_key
        self.signals = FilterWorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """Filter the image in the background thread."""
        try:
            # Convert image to ARGB32 format if needed
            if self.image.format() != QImage.Format_ARGB32:
                self.image = self.image.convertToFormat(QImage.Format_ARGB32)

            width = self.image.width()
            height = self.image.height()

            # Convert QImage data to numpy array
            buffer = self.image.constBits()
            arr = np.frombuffer(buffer, np.uint8).reshape(height, width, 4)

            # Calculate grayscale and inversion in one step
            gray = 255 - np.dot(arr[:, :, :3], [0.1, 0.7, 0.2])

            # Create output image
            result = QImage(width, height, QImage.Format_ARGB32)
            result_buffer = result.bits()
            result_arr = np.frombuffer(result_buffer, np.uint8).reshape(
                height, width, 4
            )

            # Set channels (BGR for ARGB32)
            result_arr[:, :, 0] = gray  # Blue
            result_arr[:, :, 1] = gray  # Green
            result_arr[:, :, 2] = gray  # Red
            result_arr[:, :, 3] = arr[:, :, 3]  # Original alpha

            self.signals.finished.emit(self.tile_key, result)

        except Exception as e:
            self.signals.error.emit(
                f"Error filtering tile {self.tile_key}: {str(e)}"
            )


class TileCache:
    def __init__(self, cache_dir="tile_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}  # Memory cache for original tiles
        self.filtered_cache = {}  # Memory cache for filtered tiles
        self.max_cache_size = 1000  # Maximum number of tiles to keep in memory

    def __contains__(self, key):
        """Enable 'in' operator for memory cache"""
        return key in self.memory_cache

    def __getitem__(self, key):
        """Enable dictionary-like access"""
        return self.memory_cache[key]

    def __setitem__(self, key, value):
        """Enable dictionary-like setting with cache size management"""
        # Implement LRU-style cache eviction if needed
        if len(self.memory_cache) >= self.max_cache_size:
            # Remove oldest items from both caches
            self.memory_cache.pop(next(iter(self.memory_cache)))
            self.filtered_cache.pop(next(iter(self.filtered_cache)))

        self.memory_cache[key] = value

    def get_tile_path(self, x: int, y: int, zoom: int) -> Path:
        """Generate filesystem path for a tile"""
        return self.cache_dir / f"tile_{zoom}_{x}_{y}.png"

    def get_tile(self, x: int, y: int, zoom: int) -> QImage:
        """Read tile from disk cache"""
        path = self.get_tile_path(x, y, zoom)
        if path.exists():
            image = QImage()
            if image.load(str(path)):
                return image
        return None

    def save_tile(self, x: int, y: int, zoom: int, image: QImage) -> bool:
        """Save tile to disk cache"""
        try:
            return image.save(str(self.get_tile_path(x, y, zoom)))
        except Exception as e:
            print(f"Error saving tile to cache: {e}")
            return False

    def clear_memory(self):
        """Clear only memory caches, preserve disk cache"""
        self.memory_cache.clear()
        self.filtered_cache.clear()


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
        self.initial_location = (59.4, 13.5)

        # Tiels management
        self.tile_cache = TileCache()
        self.pending_requests = {}
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.handle_tile_response)
        self.tile_url_template = (
            # "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            "https://{s}.basemaps.cartocdn.com/{style}/{z}/{x}/{y}{scale}.png"
        )

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)
        self.pending_filters = set()

        # Widget setup
        self.setMouseTracking(True)
        self.setMinimumSize(1280, 720)

        # Create and setup overlay
        self.overlay = TransparentOverlay(self)
        self.current_painter = None

    def get_tile(self, x: int, y: int, zoom: int) -> QImage:
        """Get a tile from cache or network, with asynchronous filtering"""
        key = self._cache_key(x, y, zoom)

        # Check filtered cache first
        if key in self.tile_cache.filtered_cache:
            return self.tile_cache.filtered_cache[key]

        # Get original tile
        original_tile = None

        # Check memory cache
        if key in self.tile_cache:
            original_tile = self.tile_cache[key]
        else:
            # Check disk cache
            original_tile = self.tile_cache.get_tile(x, y, zoom)
            if original_tile:
                self.tile_cache[key] = original_tile

        if original_tile:
            return original_tile

        # Request from network if not found
        self.request_tile(x, y, zoom)
        return None

    def _cache_key(self, x: int, y: int, zoom: int) -> str:
        """Generate cache key for both original and filtered tiles"""
        return f"{zoom}_{x}_{y}"

    def zoom_to(
        self, new_zoom: int, center_x: float = None, center_y: float = None
    ):
        """Zoom the map to a specific level, optionally around a center point"""
        new_zoom = max(0, min(19, new_zoom))
        if new_zoom == self.zoom_level:
            return

        if center_x is None:
            center_x = self.width() / 2
        if center_y is None:
            center_y = self.height() / 2

        world_x = center_x - self.pan_x
        world_y = center_y - self.pan_y

        scale_factor = 2 ** (new_zoom - self.zoom_level)
        new_world_x = world_x * scale_factor
        new_world_y = world_y * scale_factor

        self.pan_x = center_x - new_world_x
        self.pan_y = center_y - new_world_y
        self.zoom_level = new_zoom
        self.overlay.raise_()

        self.clear_cache()
        self.update()

    def get_selection_bounds(self):
        """Convert the overlay hole bounds to map coordinates"""
        hole_rect = self.overlay.get_hole_bounds()
        if not hole_rect:
            return None

        def screen_to_map(x, y):
            map_x = x - self.pan_x
            map_y = y - self.pan_y
            tile_x = map_x / 256
            tile_y = map_y / 256
            n = 2.0**self.zoom_level
            lon_deg = (tile_x / n * 360.0) - 180.0
            lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
            lat_deg = math.degrees(lat_rad)
            return (lat_deg, lon_deg)

        nw = screen_to_map(hole_rect.left(), hole_rect.top())
        ne = screen_to_map(hole_rect.right(), hole_rect.top())
        sw = screen_to_map(hole_rect.left(), hole_rect.bottom())
        se = screen_to_map(hole_rect.right(), hole_rect.bottom())

        return {"nw": nw, "ne": ne, "sw": sw, "se": se}

    def _on_filter_completed(self, key: str, filtered_image: QImage):
        """Handle completed filter operation"""
        self.tile_cache.filtered_cache[key] = filtered_image
        self.pending_filters.discard(key)
        self.update()  # Trigger repaint with new filtered tile

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
        """Center on initial location when first shown"""
        super().showEvent(event)
        if self.initial_location:
            lat, lon = self.initial_location
            self.center_on_location(lat, lon)
            self.initial_location = None

    def tile_key(self, x: int, y: int, zoom: int) -> str:
        """Generate unique key for tile caching"""
        return f"{zoom}_{x}_{y}"

    def geo_to_pixel(
        self, lat: float, lon: float, zoom: int
    ) -> Tuple[float, float]:
        """Convert latitude/longitude to pixel coordinates"""
        lat_rad = math.radians(lat)
        n = 2.0**zoom
        x = (lon + 180.0) / 360.0 * n * 256
        y = (
            (
                1.0
                - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad))
                / math.pi
            )
            / 2.0
            * n
            * 256
        )
        return x, y

    def center_on_location(self, lat: float, lon: float):
        """Center the map on given coordinates"""
        pixel_x, pixel_y = self.geo_to_pixel(lat, lon, self.zoom_level)
        self.pan_x = self.width() / 2 - pixel_x
        self.pan_y = self.height() / 2 - pixel_y
        self.clear_cache()
        self.update()

    def request_tile(self, x: int, y: int, zoom: int):
        """Request a map tile if not already cached"""
        print
        key = self.tile_key(x, y, zoom)
        if key in self.tile_cache or key in self.pending_requests:
            return

        url = (
            self.tile_url_template.replace("{s}", str("a"))
            .replace("{style}", str("rastertiles/voyager"))
            .replace("{z}", str(zoom))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
            .replace("{scale}", str(""))
        )
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.User, key)
        request.setHeader(
            QNetworkRequest.UserAgentHeader,
            "HeatmapApp/1.1 (contact@example.com)",
        )

        self.pending_requests[key] = None
        self.network_manager.get(request)

    def handle_tile_response(self, reply):
        """Handle network response for tile request"""
        key = reply.request().attribute(QNetworkRequest.Attribute.User)
        if reply.error() == QNetworkReply.NoError:
            image = QImage()
            image.loadFromData(reply.readAll())
            if not image.isNull():
                # Cache in memory
                self.tile_cache[key] = image

                # Save to disk cache
                zoom, x, y = map(int, key.split("_"))
                self.tile_cache.save_tile(x, y, zoom, image)

                self.update()

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
        mouse_pos = event.position()
        self.zoom_to(new_zoom, mouse_pos.x(), mouse_pos.y())

    def resizeEvent(self, event):
        """Ensure overlay resizes with the map"""
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            self.current_painter = painter
            painter.setRenderHint(QPainter.Antialiasing)

            painter.fillRect(self.rect(), QColor(240, 240, 240))

            tile_size = 256
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
                        # placehgolder ofr tile
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
        """Clear tile cache and pending requests"""
        self.pending_filters.clear()
        self.pending_requests.clear()
        self.tile_cache.clear_memory()
        self.update()
