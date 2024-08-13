import json
import numpy as np
from functools import partial
from PyQt6.QtWidgets import QHBoxLayout, QSlider, QWidget
from PyQt6.QtCore import Qt
from components.gui_styles import GUIStyles
from components.input_number_control import InputNumberControl
from components.lin_log_control import LinLogControl
from settings import *


class SpectroscopyTimeShift(QWidget):
    def __init__(self, window, channel, parent=None):
        super().__init__(parent)
        self.app = window
        self.channel = channel
        self.init_control_inputs()
        self.setLayout(self.create_controls())

    def init_control_inputs(self):
        if "time_shift_sliders" not in self.app.control_inputs:
            self.app.control_inputs["time_shift_sliders"] = {}
        if "time_shift_inputs" not in self.app.control_inputs:
            self.app.control_inputs["time_shift_inputs"] = {}

    def create_controls(self):
        time_shift = self.app.time_shifts.get(self.channel, 0)
        h_layout = QHBoxLayout()
        slider = self.setup_slider(time_shift)
        h_layout.addWidget(slider)
        _, inp = InputNumberControl.setup(
            "Time shift (bin):",
            0,
            255,
            int(time_shift),
            h_layout,
            partial(self.on_value_change, inp_type="input", channel=self.channel),
            control_layout="horizontal",
            spacing=0
        )
        inp.setStyleSheet(GUIStyles.set_input_number_style()) 
        self.app.control_inputs["time_shift_sliders"][self.channel] = slider
        self.app.control_inputs["time_shift_inputs"][self.channel] = inp
        return h_layout

    def setup_slider(self, time_shift):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(time_shift)
        slider.valueChanged.connect(partial(self.on_value_change, inp_type="slider", channel=self.channel))
        return slider

    def on_value_change(self, value, inp_type, channel):
        self.app.time_shifts[self.channel] = value
        lin_log_mode = self.app.lin_log_mode[self.channel] if self.channel in self.app.lin_log_mode else 'LIN'
        if inp_type == "slider":
            self.app.control_inputs["time_shift_inputs"][self.channel].setValue(value)
        else:
            self.app.control_inputs["time_shift_sliders"][self.channel].setValue(value)
        if self.app.tab_selected in self.app.decay_curves: 
            if self.channel in self.app.decay_curves[self.app.tab_selected]:
                decay_curve = self.app.decay_curves[self.app.tab_selected][self.channel]
                x, y = decay_curve.getData()
                if x is not None and y is not None:
                    cached_decay_curve = self.app.cached_decay_values[self.app.tab_selected][channel]
                    decay_widget = self.app.decay_widgets[channel]
                    if lin_log_mode == 'LIN':
                        ticks, y_data = LinLogControl.calculate_lin_mode(cached_decay_curve)
                        decay_widget.showGrid(x=False, y=False)
                    else:
                        ticks, y_data, _ = LinLogControl.calculate_log_mode(cached_decay_curve)
                        decay_widget.showGrid(x=False, y=True, alpha=0.3)     
                    decay_widget.getAxis("left").setTicks([ticks])    
                    y = np.roll(y_data, value)
                    decay_curve.setData(x, y)
                    self.app.set_plot_y_range(decay_widget, lin_log_mode)
        self.app.settings.setValue(SETTINGS_TIME_SHIFTS, json.dumps(self.app.time_shifts))
        
    
    @staticmethod
    def get_channel_time_shift(app, channel):
        return app.time_shifts[channel] if channel in app.time_shifts else 0    
