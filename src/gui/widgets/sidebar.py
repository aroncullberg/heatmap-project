from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIntValidator
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


def style_button(button: QPushButton, height: int = 40, padding: int = 8):
    """Apply consistent styling to a button"""
    button.setMinimumHeight(height)
    button.setStyleSheet(
        f"""
        QPushButton {{
            padding: {padding}px;
        }}
        QPushButton:hover {{
            background-color: #fc8d1c;
        }}
        QPushButton:pressed {{
            background-color: #e87d0d;
        }}
        QPushButton:disabled {{
        }}
    """
    )


class SidebarWidget(QWidget):
    # Signals
    resolution_changed = Signal(int, int)  # width, height
    generate_clicked = Signal()

    def __init__(self, map_view, parent=None):
        super().__init__(parent)
        self.map_view = map_view
        self.setFixedWidth(300)

        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        """Setup all UI components"""
        self._add_title()
        self._add_resolution_controls()
        self._add_aspect_ratio_controls()
        self._add_zoom_controls()
        self._add_selection_area_controls()
        self._add_filter_selector()
        self._add_file_controls()
        self._add_spacer()
        self._add_action_buttons()

    def _add_title(self):
        """Add title section"""
        title = QLabel("heatmap²")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title)

    def _add_resolution_controls(self):
        """Add resolution input section"""
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))

        input_layout = QHBoxLayout()
        self.res_width = QLineEdit("1920")
        self.res_height = QLineEdit("1080")
        self.res_width.setValidator(QIntValidator(1, 100000))
        self.res_height.setValidator(QIntValidator(1, 100000))

        # Connect signals
        self.res_width.textChanged.connect(self._on_resolution_changed)
        self.res_height.textChanged.connect(self._on_resolution_changed)

        input_layout.addWidget(self.res_width)
        input_layout.addWidget(QLabel("x"))
        input_layout.addWidget(self.res_height)

        res_layout.addLayout(input_layout)
        self.main_layout.addLayout(res_layout)

    def _add_aspect_ratio_controls(self):
        """Add aspect ratio section"""
        aspect_layout = QVBoxLayout()
        aspect_layout.addWidget(QLabel("Aspect Ratio:"))

        input_layout = QHBoxLayout()
        self.aspect_width = QLineEdit("16")
        self.aspect_height = QLineEdit("9")

        # These are display-only
        self.aspect_width.setEnabled(False)
        self.aspect_height.setEnabled(False)

        input_layout.addWidget(self.aspect_width)
        input_layout.addWidget(QLabel("x"))
        input_layout.addWidget(self.aspect_height)

        aspect_layout.addLayout(input_layout)
        self.main_layout.addLayout(aspect_layout)

    def _add_zoom_controls(self):
        """Add zoom control section"""
        zoom_layout = QVBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(0)
        self.zoom_slider.setMaximum(19)
        self.zoom_slider.setValue(self.map_view.zoom_level)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)

        button_layout = QHBoxLayout()
        zoom_out = QPushButton("-")
        zoom_in = QPushButton("+")
        style_button(zoom_in)
        style_button(zoom_out)
        zoom_in.clicked.connect(self.map_view.zoom_in)
        zoom_out.clicked.connect(self.map_view.zoom_out)
        button_layout.addWidget(zoom_out)
        button_layout.addWidget(zoom_in)

        zoom_layout.addLayout(button_layout)
        self.main_layout.addLayout(zoom_layout)

    def _add_selection_area_controls(self):
        """Add selection area control section"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Selection area:"))

        self.selection_slider = QSlider(Qt.Horizontal)
        self.selection_slider.setMinimum(10)
        self.selection_slider.setMaximum(90)
        self.selection_slider.setValue(80)
        self.selection_slider.valueChanged.connect(
            self.map_view.overlay.set_zoom_factor
        )
        layout.addWidget(self.selection_slider)

        self.main_layout.addLayout(layout)

    def _add_file_controls(self):
        """Add file management section"""
        self.file_scroll = QScrollArea()
        self.file_scroll.setWidgetResizable(True)

        self.file_container = QWidget()
        self.file_layout = QVBoxLayout(self.file_container)
        self.file_layout.setAlignment(Qt.AlignTop)

        self.add_file_btn = QPushButton("+")
        style_button(self.add_file_btn, 30, 8)
        self.file_layout.addWidget(self.add_file_btn)

        self.file_scroll.setWidget(self.file_container)
        self.main_layout.addWidget(self.file_scroll, 1)  # 1 = stretch factor

    def _add_filter_selector(self):
        layout1 = QVBoxLayout(self)

        self.combo_box = QComboBox()

        self.combo_box.addItem("light_all,")
        self.combo_box.addItem("dark_all,")
        self.combo_box.addItem("light_nolabels,")
        self.combo_box.addItem("light_only_labels,")
        self.combo_box.addItem("dark_nolabels,")
        self.combo_box.addItem("dark_only_labels,")
        self.combo_box.addItem("rastertiles/voyager,")
        self.combo_box.addItem("rastertiles/voyager_nolabels,")
        self.combo_box.addItem("rastertiles/voyager_only_labels,")
        self.combo_box.addItem("rastertiles/voyager_labels_under")

        self.combo_box.currentIndexChanged.connect(self._on_filter_change)

        layout1.addWidget(self.combo_box)
        self.selected_value = None

        self.main_layout.addLayout(layout1)

    def _add_spacer(self):
        """Add flexible space"""
        self.main_layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

    def _add_action_buttons(self):
        """Add action buttons"""
        self.lock_button = QPushButton("Lock")
        self.lock_button.setCheckable(True)
        self.lock_button.setEnabled(False)
        style_button(self.lock_button)
        self.main_layout.addWidget(self.lock_button)

        self.generate_button = QPushButton("Generate")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self.generate_clicked)
        style_button(self.generate_button)
        self.main_layout.addWidget(self.generate_button)

    def _on_resolution_changed(self):
        """Handle resolution input changes"""
        try:
            width = int(self.res_width.text())
            height = int(self.res_height.text())
            self.resolution_changed.emit(width, height)

            # Update aspect ratio display
            gcd = self._calculate_gcd(width, height)
            if gcd > 0:
                self.aspect_width.setText(str(width // gcd))
                self.aspect_height.setText(str(height // gcd))

                # Update map overlay aspect ratio
                self.map_view.set_aspect_ratio(width // gcd, height // gcd)
        except ValueError:
            pass

    def _on_zoom_changed(self, value):
        """Handle zoom slider changes"""
        if value != self.map_view.zoom_level:
            self.map_view.zoom_to(value)

    def _calculate_gcd(self, a: int, b: int) -> int:
        """Calculate greatest common divisor"""
        while b:
            a, b = b, a % b
        return a

    def _on_filter_change(self, index):
        self.selected_value = self.combo_box.itemText(index)
        print(f"Selected value: {self.selected_value}")

    def get_resolution(self) -> tuple[int, int]:
        """Get current resolution values"""
        try:
            width = int(self.res_width.text())
            height = int(self.res_height.text())
            return width, height
        except ValueError:
            return 1920, 1080  # Default resolution

    def clear_file_list(self):
        """Clear all files from the list"""
        while self.file_layout.count() > 1:  # Keep the add button
            item = self.file_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
