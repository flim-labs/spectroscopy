from PyQt6.QtGui import QColor, QPalette, QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtWidgets import QStyleFactory


class GUIStyles:
    @staticmethod
    def set_default_theme(theme):
        QApplication.setStyle(QStyleFactory.create(theme))

    @staticmethod
    def customize_theme(window):
        palette = QPalette()
        background_color = QColor(28, 28, 28, 128)
        palette.setColor(QPalette.ColorRole.Window, background_color)
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        window.setPalette(palette)
        window.setStyleSheet("""
        QLabel {
            color: #f8f8f8;
            font-family: "Montserrat";
        }
        """)

    @staticmethod
    def set_fonts(font_name="Montserrat", font_size=10):
        general_font = QFont("Montserrat", 10)
        QApplication.setFont(general_font)


    @staticmethod
    def set_fonts_deep(root):
        if root is None:
            return
        for child in root.findChildren(QWidget):
            if child.objectName() == "font":
                child.setFont(QFont("Montserrat", 14, QFont.Weight.Thin))
            if child.metaObject().className() == "QPushButton":
                child.setFont(QFont("Montserrat", 14, QFont.Weight.Thin))
            GUIStyles.set_fonts_deep(child)
        for child in root.findChildren(QLabel):
            child.setFont(QFont("Montserrat", 14, QFont.Weight.Bold))
            GUIStyles.set_fonts_deep(child)

    @staticmethod
    def set_label_style(color="#f8f8f8"):
        return """
            QLabel{
                color: #f8f8f8;
                font-family: "Montserrat";
            }
        """

    @staticmethod
    def set_main_title_style():
        return """
            QLabel{
                color: #23F3AB;
                font-family: "Montserrat";
                font-size: 40px;
                font-weight: 100;
                font-style: italic;
            }
        """

    @staticmethod
    def button_style(color_base, color_border, color_hover, color_pressed, min_width, override=""):
        return f"""
            QPushButton {{
                background-color: {color_base};
                border: 1px solid {color_border};
                font-family: "Montserrat";
                color: white;
                letter-spacing: 0.1em;
                min-width: {min_width};
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: {color_hover};
                border: 2px solid {color_hover};
            }}

            QPushButton:pressed {{
                background-color: {color_pressed};
                border: 2px solid {color_pressed};
            }}
            
            QPushButton:disabled {{
                background-color: #cecece;
                border: 2px solid #cecece;
                color: #8c8b8b;
            }}
            
            {override}
        """

    @staticmethod
    def _set_button_style(button, color_dict, min_width):
        color_base, color_border, color_hover, color_pressed = (
            color_dict["base"],
            color_dict["border"],
            color_dict["hover"],
            color_dict["pressed"],
        )
        button.setStyleSheet(
            GUIStyles.button_style(
                color_base, color_border, color_hover, color_pressed, min_width
            )
        )

    @staticmethod
    def set_start_btn_style(button):
        color_dict = {
            "base": "#13B6B4",
            "border": "#13B6B4",
            "hover": "#1EC99F",
            "pressed": "#1AAE88",
        }
        GUIStyles._set_button_style(button, color_dict, min_width="200px")

    @staticmethod
    def set_stop_btn_style(button):
        color_dict = {
            "base": "#FFA726",
            "border": "#FFA726",
            "hover": "#FB8C00",
            "pressed": "#E65100",
        }
        GUIStyles._set_button_style(button, color_dict, min_width="200px")

    @staticmethod
    def set_reset_btn_style(button):
        color_dict = {
            "base": "#8d4ef2",
            "border": "#8d4ef2",
            "hover": "#a179ff",
            "pressed": "#6b3da5",
        }
        GUIStyles._set_button_style(button, color_dict, min_width="100px")

    @staticmethod
    def set_config_btn_style(button):
        color_dict = {
            "base": "black",
            "border": "#FFA726",
            "hover": "#FB8C00",
            "pressed": "#E65100",
        }
        GUIStyles._set_button_style(button, color_dict, min_width="100px")
        # set no rounded corners
        button.setStyleSheet(button.styleSheet() + "QPushButton {border-radius: 0px; padding-left: 10px; padding-right: 10px;}  QPushButton:checked {background-color: #FFA726;}")

    @staticmethod
    def set_checkbox_style():
        return """
            QCheckBox {
                spacing: 5px;
                color: #f8f8f8;
                font-family: "Montserrat";
                font-size: 14px;
                letter-spacing: 0.1em;
                border: 1px solid #252525;
                border-radius: 5px;
                padding: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;  
            }

            QCheckBox::indicator:unchecked {
                background-color: #6b6a6a;
            }

            QCheckBox::indicator:checked {
                background-color: #8d4ef2;
            }
        """

    @staticmethod
    def set_input_number_style():
        return """
            QDoubleSpinBox, QSpinBox {
                color: #f8f8f8;
                font-family: "Montserrat";
                font-size: 16px;
                padding: 8px;
                min-width: 100px;
                border: 1px solid #8d4ef2;
                border-radius: 5px;
                background-color: transparent;
            }
            QDoubleSpinBox:disabled, QSpinBox:disabled {
            color: #404040;  
            border-color: #404040;
            }        
        """

    @staticmethod
    def set_input_select_style():
        return """
            QComboBox {
                color: #f8f8f8;
                font-family: "Montserrat";
                font-size: 16px;
                padding: 8px;
                min-width: 100px;
                border: 1px solid #8d4ef2;
                border-radius: 5px;
                background-color: transparent;
            }
            QComboBox:disabled {
                color: darkgrey;  
                border-color: darkgrey;
            } 
            QComboBox:on { 
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }

           QComboBox QAbstractItemView {
            font-family: "Montserrat";
            border: 1px solid #8d4ef2;
            border-bottom-left-radius: 5px;
            border-bottom-right-radius: 5px;
            background-color: #181818;
            color: #f8f8f8;
            selection-background-color: #8d4ef2;
            }   
        """

    @staticmethod
    def set_msg_box_style():
        return """
            QMessageBox {
                background-color: #080808;   
            }
            QMessageBox QLabel {
                color: #f8f8f8;
                font-family: "Montserrat";
                font-weight: 300;
                font-size: 16px;
            }
            QMessageBox QIcon {
                width: 20px;
            }  
            QMessageBox QPushButton {
                background-color: #181818;
                color: white;
                width: 150px;
                padding: 12px;
                font-size: 14px;
                font-family: "Montserrat";
            }   
                 
        """

    @staticmethod
    def set_cps_label_style():
        return """
            QLabel{
                color: white;
                font-weight: 700;
                font-family: "Montserrat";
                font-size: 26px;
            }
        """
