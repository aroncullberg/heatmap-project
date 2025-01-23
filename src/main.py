import sys
import folium
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                              QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QLineEdit, QSpacerItem, QSizePolicy,
                              QSplitter)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QMenu, QComboBox, QSlider


class ResponsiveWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._page = self.page()
        self._is_locked = False
        
        # Inject CSS to make the map fill the container
        self._style = """
            <style>
                html, body {
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }
                #map {
                    position: absolute;
                    top: 0;
                    bottom: 0;
                    right: 0;
                    left: 0;
                }
                .leaflet-container {
                    width: 100%;
                    height: 100%;
                }
            </style>
        """
        
    def set_locked(self, locked):
        """Enable or disable map interactions"""
        self._is_locked = locked
        if locked:
            # Disable map interactions with CSS
            self.page().runJavaScript("""
                document.querySelector('.leaflet-control-zoom').style.display = 'none';
                document.querySelector('.leaflet-container').style.pointerEvents = 'none';
            """)
        else:
            # Enable map interactions
            self.page().runJavaScript("""
                document.querySelector('.leaflet-control-zoom').style.display = 'block';
                document.querySelector('.leaflet-container').style.pointerEvents = 'auto';
            """)
            
            
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        # Add custom actions
        center_action = menu.addAction("Center Map Here")
        menu.addSeparator()
        zoom_in = menu.addAction("Zoom In")
        zoom_out = menu.addAction("Zoom Out")
        menu.addSeparator()
        copy_coords = menu.addAction("Copy Coordinates")
        
        
        # Style the menu
        menu.setStyleSheet("""
            QMenu {
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 30px 5px 30px;
                color: white;
            }
            QMenu::item:selected {
                background-color: #404040;
            }
        """)
       
        def handle_center():
            js = """
            var map = document.querySelector('#map').map;
            var point = L.point(%d, %d);
            var latLng = map.containerPointToLatLng(point);
            map.setView(latLng, map.getZoom());
            """ % (event.pos().x(), event.pos().y())
            self.page().runJavaScript(js)

        def handle_copy():
            js = """
            var map = document.querySelector('#map').map;
            var point = L.point(%d, %d);
            var latLng = map.containerPointToLatLng(point);
            [latLng.lat.toFixed(6), latLng.lng.toFixed(6)];
            """ % (event.pos().x(), event.pos().y())
            self.page().runJavaScript(js, lambda coords: 
                QApplication.clipboard().setText(f"{coords[0]}, {coords[1]}"))
            
        
        # Connect actions with fixed handlers
        center_action.triggered.connect(handle_center)
        zoom_in.triggered.connect(lambda: self.page().runJavaScript(
            "document.querySelector('#map').map.zoomIn()"))
        zoom_out.triggered.connect(lambda: self.page().runJavaScript(
            "document.querySelector('#map').map.zoomOut()"))
        copy_coords.triggered.connect(handle_copy)
        
        menu.exec_(event.globalPos())
        
        
    def _center_map_at_point(self, pos):
        # Convert screen coordinates to map coordinates and center
        js = """
        function getLatLngFromPoint(x, y) {
            var point = L.point(x, y);
            var latLng = map.containerPointToLatLng(point);
            return [latLng.lat, latLng.lng];
        }
        getLatLngFromPoint(%d, %d);
        """ % (pos.x(), pos.y())
        
        self.page().runJavaScript(js, lambda coords: 
            self.page().runJavaScript(f"map.setView({coords}, map.getZoom())"))

    def _copy_coordinates(self, pos):
        js = """
        function getLatLngFromPoint(x, y) {
            var point = L.point(x, y);
            var latLng = map.containerPointToLatLng(point);
            return [latLng.lat.toFixed(6), latLng.lng.toFixed(6)];
        }
        getLatLngFromPoint(%d, %d);
        """ % (pos.x(), pos.y())
        
        def copy_to_clipboard(coords):
            QApplication.clipboard().setText(f"{coords[0]}, {coords[1]}")
        
        self.page().runJavaScript(js, copy_to_clipboard)
    

    def show_map(self, folium_map):
        """Display a folium map with responsive sizing"""
        # Get the HTML from the Folium map
        html = folium_map.get_root().render()
        
        # Insert our responsive CSS
        html = html.replace('</head>', f'{self._style}</head>')
        
        # Set the modified HTML
        self.setHtml(html)
        
class TransparentOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.aspect_ratio = (16, 9)  # Default aspect ratio
        self._hole_rect = None  # Store the hole rectangle

    
    def set_aspect_ratio(self, width, height):
        self.aspect_ratio = (width, height)
        self.update()  # Trigger repaint
        
    def get_hole_bounds(self):
        return self._hole_rect if self._hole_rect else None
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate hole dimensions maintaining aspect ratio
        width = self.width()
        height = self.height()
        
        
        if width * self.aspect_ratio[1] <= height * self.aspect_ratio[0]:
            hole_width = int(width * 0.8)
            hole_height = int(hole_width * self.aspect_ratio[1] / self.aspect_ratio[0])
        else:
            hole_height = int(height * 0.8)
            hole_width = int(hole_height * self.aspect_ratio[0] / self.aspect_ratio[1])
        
        x = (width - hole_width) // 2
        y = (height - hole_height) // 2
                
        # Store the hole rectangle
        self._hole_rect = QRect(x, y, hole_width, hole_height)
        
        # Create a path for the entire widget
        full_path = QPainterPath()
        full_path.addRect(self.rect())
        
        # Create a path for the hole
        hole_path = QPainterPath()
        hole_path.addRect(self._hole_rect)
        
        # Subtract the hole from the full path
        final_path = full_path.subtracted(hole_path)
        
        # Draw the semi-transparent overlay
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 128))
        painter.drawPath(final_path)
        
        # Draw white border around the hole
        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self._hole_rect)

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Map with Overlay")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setMinimumSize(1280, 720)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(300)
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
        res_input_layout.addWidget(self.res_width)
        res_input_layout.addWidget(QLabel("x"))
        self.res_height = QLineEdit("1080")
        res_input_layout.addWidget(self.res_height)
        
        res_layout.addLayout(res_input_layout)
        sidebar_layout.addLayout(res_layout)
        
        # Aspect ratio inputs
        aspect_layout = QVBoxLayout()
        aspect_label = QLabel("Aspect Ratio:")
        aspect_layout.addWidget(aspect_label)
        
        aspect_input_layout = QHBoxLayout()
        self.aspect_width = QLineEdit("16")
        aspect_input_layout.addWidget(self.aspect_width)
        aspect_input_layout.addWidget(QLabel("x"))
        self.aspect_height = QLineEdit("9")
        aspect_input_layout.addWidget(self.aspect_height)
        
        aspect_layout.addLayout(aspect_input_layout)
        sidebar_layout.addLayout(aspect_layout)
        
        filter_layout = QVBoxLayout()
        filter_label = QLabel("Map Filter:")
        filter_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                font-size: 14px;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                padding: 5px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                padding: 5px;
                selection-background-color: #e0e0e0;
            }
        """)

        # Add filter options
        self.filters = {
            "None": "",
            "Night Mode": "invert(100%) hue-rotate(180deg)",
            "Sepia": "sepia(100%)",
            "Cool Tone": "hue-rotate(180deg)",
            "Warm Tone": "hue-rotate(-30deg) saturate(120%)",
            "High Contrast": "contrast(150%) saturate(150%)",
            "Muted": "saturate(50%) brightness(95%)"
        }
        
        self.filter_combo.addItems(list(self.filters.keys()))
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        
        # Add to sidebar layout
        sidebar_layout.addLayout(filter_layout)
        
        rotation_layout = QVBoxLayout()
        rotation_label = QLabel("Rotation:")
        rotation_layout.addWidget(rotation_label)

        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setRange(0, 359)
        self.rotation_slider.setValue(0)
        self.rotation_slider.setTickPosition(QSlider.TicksBelow)
        self.rotation_slider.setTickInterval(45)
        rotation_layout.addWidget(self.rotation_slider)

        sidebar_layout.addLayout(rotation_layout)



        
        # Add spacer
        sidebar_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Add lock button to sidebar
        self.lock_button = QPushButton("Lock")
        self.lock_button.setCheckable(True)
        self.lock_button.clicked.connect(self.toggle_map_lock)
        sidebar_layout.addWidget(self.lock_button)

        
        # Generate button
        self.generate_button = QPushButton("Generate")
        
        sidebar_layout.addWidget(self.generate_button)
        self.generate_button.clicked.connect(self.generate_heatmap)

        
        # Create map container
        map_container = QWidget()
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create and add the responsive map view
        self.web_view = ResponsiveWebView()
        map_layout.addWidget(self.web_view)
        
        # Create and add the overlay
        self.overlay = TransparentOverlay(map_container)
        self.overlay.setGeometry(map_container.rect())
        
        
        # Make sure overlay resizes with container
        map_container.resizeEvent = lambda event: self.overlay.setGeometry(
            map_container.rect()
        )
        
        
        # Add widgets to main layout
        layout.addWidget(sidebar)
        layout.addWidget(map_container)
        
        # Set fixed width for sidebar
        sidebar.setFixedWidth(300)
        
        self.aspect_width.textChanged.connect(self.validate_and_update_aspect)
        self.aspect_height.textChanged.connect(self.validate_and_update_aspect)

        input_style = """
            QLineEdit {
                padding: 8px;
                font-size: 18px;
                min-height: 24px;
            }
        """
        # Style for buttons
        button_style = """
            QPushButton {
                padding: 10px;
                font-size: 14px;
                min-height: 40px;
            }
        """

        # Style for labels
        label_style = """
            QLabel {
                font-size: 14px;
                padding: 5px;
            }
        """
        
        # Apply styles
        self.res_width.setStyleSheet(input_style)
        self.res_height.setStyleSheet(input_style)
        self.aspect_width.setStyleSheet(input_style)
        self.aspect_height.setStyleSheet(input_style)
        
        # Apply to all labels
        for label in self.findChildren(QLabel):
            label.setStyleSheet(label_style)



        # Initialize the map
        self.show_map()
    
    
    def get_map_bounds(self, rect, callback):
        """Convert screen coordinates to map coordinates"""
        js = """
        function getLatLngFromPoint(x, y) {
            // Use the globally stored map instance
            if (!window.leafletMap) {
                console.log('Map not initialized yet');
                return null;
            }
            
            var point = L.point(x, y);
            var latLng = window.leafletMap.containerPointToLatLng(point);
            return [latLng.lat, latLng.lng];
        }
        
        var bounds = {
            'nw': getLatLngFromPoint(%d, %d),
            'ne': getLatLngFromPoint(%d, %d),
            'sw': getLatLngFromPoint(%d, %d),
            'se': getLatLngFromPoint(%d, %d)
        };
        bounds;
        """ % (
            rect.left(), rect.top(),  # Northwest
            rect.right(), rect.top(),  # Northeast
            rect.left(), rect.bottom(),  # Southwest
            rect.right(), rect.bottom()  # Southeast
        )
        
        self.web_view.page().runJavaScript(js, callback)
    
    
    def apply_filter(self, filter_name):
        filter_style = self.filters[filter_name]
        js = f"""
            document.querySelector('.leaflet-container').style.filter = '{filter_style}';
        """
        self.web_view.page().runJavaScript(js)
        
        # Force update the combo box text
        self.filter_combo.setCurrentText(filter_name)
        self.filter_combo.update()


    def update_aspect_ratio(self):
        try:
            width = int(self.aspect_width.text())
            height = int(self.aspect_height.text())
            print(f"Aspect ratio changed to: {width}x{height}")
            self.overlay.set_aspect_ratio(width, height)
        except ValueError:
            pass  # Handle invalid input gracefully
    
    def update_resolution(self):
        try:
            width = int(self.res_width.text())
            height = int(self.res_height.text())
            print(f"Resolution changed to: {width}x{height}")
        except ValueError:
            pass  # Handle invalid input gracefully
    
    
    
    def generate_heatmap(self):
        """Handle generate button click"""
        hole_rect = self.overlay.get_hole_bounds()
        if hole_rect:
            def handle_bounds(bounds):
                if bounds and any(bounds.values()):  # Check if we got valid coordinates
                    print("Selection bounds in coordinates:")
                    print(f"Northwest: {bounds['nw']}")
                    print(f"Northeast: {bounds['ne']}")
                    print(f"Southwest: {bounds['sw']}")
                    print(f"Southeast: {bounds['se']}")
                else:
                    print("Could not get map coordinates. Please wait a moment for the map to fully load and try again.")

        
        
    def toggle_map_lock(self):
        """Toggle map interaction lock"""
        is_locked = self.lock_button.isChecked()
        self.lock_button.setText("Unlock" if is_locked else "Lock")
        self.web_view.set_locked(is_locked)
    
    def show_map(self):
        """Initialize and display a responsive folium map"""
        m = folium.Map(
            location=[59.4, 13.5],
            zoom_start=12,
            attributionControl=False,
            tiles='OpenStreetMap'
        )
        
        # Add a script to expose the map instance globally
        m.get_root().script.add_child(folium.Element("""
            // Store map instance globally after it's initialized
            document.addEventListener('DOMContentLoaded', function() {
                setTimeout(function() {
                    var maps = document.getElementsByClassName('folium-map');
                    if (maps.length > 0) {
                        window.leafletMap = maps[0]._leaflet;
                    }
                }, 1000);  // Give map time to initialize
            });
        """))
        
        self.web_view.show_map(m)

    def validate_and_update_aspect(self):
        """Validate aspect ratio inputs and update overlay if valid"""
        try:
            width = self.aspect_width.text()
            height = self.aspect_height.text()
            
            # TODO: Add your validation logic here
            # For example: check if numbers are positive, within certain range, etc.
            
            width_val = int(width)
            height_val = int(height)
            
            if width_val > 0 and height_val > 0:  # Basic validation
                self.overlay.set_aspect_ratio(width_val, height_val)
        except ValueError:
            pass  # Handle invalid input
    
def main():
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()