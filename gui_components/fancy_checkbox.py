from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent, QFont, QCursor, QPalette, QIcon
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QButtonGroup, QRadioButton, QMenu, QPushButton

SELECTED_COLOR = "#0078D7"
SELECTED_HOVER_COLOR = "#0053a4"
DISABLED_SELECTED_COLOR = "#2E2E2E"
UNSELECTED_COLOR = "#00000"
DISABLED_COLOR = "lightgrey"
TEXT_COLOR = "#FFFFFF"


CHECKED_COLOR = "#0078D7"
UNCHECKED_COLOR = "lightgrey"


class FancyCheckbox(QWidget):
    toggled = pyqtSignal(bool)  # Signal to emit when the checkbox state changes

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # Remove margins around the checkbox and label
        self.layout.setSpacing(5)  # Set spacing between checkbox and label

        self.checkbox = Checkbox(self)
        self.label = QLabel(text, self)

        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.label)

        self.label.mousePressEvent = self.checkbox.mousePressEvent  # Forward mousePressEvent from label to checkbox
        self.checkbox.toggled.connect(self.emit_toggled_signal)

    def emit_toggled_signal(self, checked):
        self.toggled.emit(checked)  # Emit toggled signal when the checkbox state changes

    def is_checked(self):
        return self.checkbox.is_checked()

    def set_checked(self, checked):
        self.checkbox.set_checked(checked)

    def set_text(self, text):
        self.label.setText(text)

    def setEnabled(self, enabled):
        self.checkbox.setEnabled(enabled)
        self.label.setEnabled(enabled)


class Checkbox(QWidget):
    toggled = pyqtSignal(bool)  # Signal to emit when the checkbox state changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)  # Set the size of the checkbox
        self.checked = False
        self.enabled = True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.checked:
            outer_color = QColor(CHECKED_COLOR if self.enabled else DISABLED_COLOR)
        else:
            outer_color = QColor(CHECKED_COLOR if self.enabled else DISABLED_COLOR)
        painter.setPen(QPen(outer_color, 2))
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawEllipse(1, 1, 18, 18)
        if self.checked:
            inner_color = QColor(CHECKED_COLOR if self.enabled else DISABLED_COLOR)
            painter.setBrush(QBrush(inner_color))
            painter.drawEllipse(4, 4, 12, 12)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.enabled:
            self.checked = not self.checked
            self.update()  # Trigger a repaint
            self.toggled.emit(self.checked)  # Emit the toggled signal

    def is_checked(self):
        return self.checked

    def set_checked(self, checked):
        if self.checked != checked:
            self.checked = checked
            self.update()  # Trigger a repaint

    def setEnabled(self, enabled):
        if self.enabled != enabled:
            self.enabled = enabled
            self.update()  # Trigger a repaint


class FancyButton(QPushButton):
    def __init__(self, text="", icon_path=None, parent=None):
        super().__init__(text, parent)
        self.selected = False  # Track the selected state
        self.initUI(icon_path)

    def initUI(self, icon_path):
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))  # Adjust icon size as needed
        self.setFlat(True)  # Set the button to flat style
        self.updateStyleSheet()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, selected):
        self.selected = selected
        self.updateStyleSheet()

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.updateStyleSheet()

    def updateStyleSheet(self):
        bg_color = SELECTED_COLOR if self.selected else UNSELECTED_COLOR
        color = SELECTED_COLOR
        if not self.isEnabled():
            bg_color = "#3c3c3c" if self.selected else "#000000"
            color = "white"
        hover_color = SELECTED_HOVER_COLOR
        pressed_color = "#003d7a"

        self.setStyleSheet(f"""
            QPushButton {{
                border: 2px solid {color};
                border-radius: 0px;
                color: white;
                padding: 5px;
                background-color: {bg_color};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)
