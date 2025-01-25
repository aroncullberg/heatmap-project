from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class TransparentOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.aspect_ratio = (16, 9)

        self._hole_rect = QRect()
        self._initialized = False
        self._zoom_factor = 0.8  # (80% of max size)

        self._animation = QPropertyAnimation(self, b"hole_rect", self)
        self._animation.setDuration(250)  # ms
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def set_zoom_factor(self, value):
        """Set zoom factor (0.1 to 1.0) and update hole size"""
        self._zoom_factor = max(0.1, min(0.9, value / 100.0))
        if self._initialized:
            self.update_hole_size(animate=True)

    def get_hole_rect(self):
        return self._hole_rect

    def set_hole_rect(self, rect):
        self._hole_rect = rect
        self.update()

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

        # Draw orange border around the hole
        painter.setPen(QPen(QColor(255, 102, 0, 128), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self._hole_rect)
