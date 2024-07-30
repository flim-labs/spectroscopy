from PyQt6.QtWidgets import QWidget, QFrame, QSizePolicy, QVBoxLayout


def draw_layout_separator(line_width=1, color="#282828", vertical_space=10):
    spacer_widget = QWidget()
    spacer_widget.setFixedSize(1, vertical_space)

    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    separator.setLineWidth(line_width)
    separator.setStyleSheet(f"QFrame{{color: {color};}}")

    layout = QVBoxLayout()
    layout.setSpacing(0)
    layout.setContentsMargins(0,0,0,0)
    layout.addWidget(spacer_widget)
    layout.addWidget(separator)

    container_widget = QWidget()
    container_widget.setLayout(layout)

    return container_widget



def hide_layout(layout):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget():
            item.widget().hide()
        elif item.layout():
            hide_layout(item.layout())

def show_layout(layout):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget():
            item.widget().show()
        elif item.layout():
            show_layout(item.layout())
