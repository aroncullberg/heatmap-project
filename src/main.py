from PyQt6.QtWidgets import *
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QRect

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Sidebar
        sidebar = QDockWidget("Controls", self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, sidebar)
        
        # Central Widget (Map + Overlay)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # WebEngine View for Folium
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Overlay (added as a child of central_widget)
        self.overlay = OverlayWidget(self.web_view)