from PySide6.QtGui import QImage, qRgb, QColor
from typing import Callable
import colorsys
class MapFilter:
    """Handles various filter effects for map tiles"""
    
    @staticmethod
    def no_filter(image: QImage) -> QImage:
        """Returns original image without modifications"""
        return image

    @staticmethod
    def night_mode(image: QImage) -> QImage:
        """Creates a dark theme version of the map"""
        # Convert to ARGB32 format if needed
        if image.format() != QImage.Format_ARGB32:
            result = image.convertToFormat(QImage.Format_ARGB32)
        else:
            result = image.copy()

        # Get direct access to pixel data
        for y in range(result.height()):
            line = result.scanLine(y)
            for x in range(result.width()):
                pixel = QColor(result.pixel(x, y))
                # Invert colors and adjust brightness
                pixel.setHsv(
                    pixel.hue(),
                    pixel.saturation(),
                    255 - pixel.value()
                )
                result.setPixelColor(x, y, pixel)
        return result

    @staticmethod
    def sepia(image: QImage) -> QImage:
        """Applies sepia tone effect"""
        if image.format() != QImage.Format_ARGB32:
            result = image.convertToFormat(QImage.Format_ARGB32)
        else:
            result = image.copy()

        for y in range(result.height()):
            for x in range(result.width()):
                color = QColor(result.pixel(x, y))
                r, g, b = color.red(), color.green(), color.blue()
                tr = min(int(0.393 * r + 0.769 * g + 0.189 * b), 255)
                tg = min(int(0.349 * r + 0.686 * g + 0.168 * b), 255)
                tb = min(int(0.272 * r + 0.534 * g + 0.131 * b), 255)
                result.setPixelColor(x, y, QColor(tr, tg, tb, color.alpha()))
        return result

    @staticmethod
    def cool_tone(image: QImage) -> QImage:
        """Shifts colors towards cool tones (blue/cyan)"""
        if image.format() != QImage.Format_ARGB32:
            result = image.convertToFormat(QImage.Format_ARGB32)
        else:
            result = image.copy()

        for y in range(result.height()):
            for x in range(result.width()):
                color = QColor(result.pixel(x, y))
                h, s, v = color.hueF(), color.saturationF(), color.valueF()
                # Shift hue towards blue
                h = (h + 0.5) % 1.0
                new_color = QColor()
                new_color.setHsvF(h, s, v, color.alphaF())
                result.setPixelColor(x, y, new_color)
        return result

    @staticmethod
    def warm_tone(image: QImage) -> QImage:
        """Shifts colors towards warm tones (red/orange)"""
        if image.format() != QImage.Format_ARGB32:
            result = image.convertToFormat(QImage.Format_ARGB32)
        else:
            result = image.copy()

        for y in range(result.height()):
            for x in range(result.width()):
                color = QColor(result.pixel(x, y))
                h, s, v = color.hueF(), color.saturationF(), color.valueF()
                # Shift hue towards red/orange
                h = (h - 0.1) % 1.0
                s = min(s * 1.2, 1.0)  # Increase saturation
                new_color = QColor()
                new_color.setHsvF(h, s, v, color.alphaF())
                result.setPixelColor(x, y, new_color)
        return result

    @staticmethod
    def high_contrast(image: QImage) -> QImage:
        """Increases contrast and saturation"""
        if image.format() != QImage.Format_ARGB32:
            result = image.convertToFormat(QImage.Format_ARGB32)
        else:
            result = image.copy()

        for y in range(result.height()):
            for x in range(result.width()):
                color = QColor(result.pixel(x, y))
                h, s, v = color.hueF(), color.saturationF(), color.valueF()
                # Increase saturation and adjust value for contrast
                s = min(s * 1.5, 1.0)
                v = 0.5 + (v - 0.5) * 1.5
                v = max(0.0, min(1.0, v))
                new_color = QColor()
                new_color.setHsvF(h, s, v, color.alphaF())
                result.setPixelColor(x, y, new_color)
        return result

    @staticmethod
    def muted(image: QImage) -> QImage:
        """Creates a muted, subtle color palette"""
        if image.format() != QImage.Format_ARGB32:
            result = image.convertToFormat(QImage.Format_ARGB32)
        else:
            result = image.copy()

        for y in range(result.height()):
            for x in range(result.width()):
                color = QColor(result.pixel(x, y))
                h, s, v = color.hueF(), color.saturationF(), color.valueF()
                # Reduce saturation and slightly adjust brightness
                s *= 0.5
                v = v * 0.95 + 0.05
                new_color = QColor()
                new_color.setHsvF(h, s, v, color.alphaF())
                result.setPixelColor(x, y, new_color)
        return result

    # Dictionary mapping filter names to their functions
    FILTERS = {
        "None": no_filter,
        "Night Mode": night_mode,
        "Sepia": sepia,
        "Cool Tone": cool_tone,
        "Warm Tone": warm_tone,
        "High Contrast": high_contrast,
        "Muted": muted
    }

    @classmethod
    def apply_filter(cls, image: QImage, filter_name: str) -> QImage:
        """Apply the specified filter to the image"""
        if filter_name not in cls.FILTERS:
            return image
        try:
            return cls.FILTERS[filter_name](image)
        except Exception as e:
            print(f"Error applying filter {filter_name}: {e}")
            return image

    @classmethod
    def get_filter_names(cls) -> list[str]:
        """Get list of available filter names"""
        return list(cls.FILTERS.keys())

    @classmethod
    def add_custom_filter(cls, name: str, filter_func: Callable[[QImage], QImage]):
        """Add a custom filter to the available filters"""
        cls.FILTERS[name] = filter_func