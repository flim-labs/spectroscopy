import json
import os
import queue
import sys
import time

import flim_labs
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QTimer, QSettings, QSize, Qt, QEvent
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QLayout, QLabel, \
    QSizePolicy, QPushButton, QDialog, QMessageBox, QFileDialog

from components.fancy_checkbox import FancyButton
from components.gradient_text import GradientText
from components.gui_styles import GUIStyles
from components.helpers import format_size
from components.input_number_control import InputNumberControl, InputFloatControl
from components.link_widget import LinkWidget
from components.logo_utilities import OverlayWidget, TitlebarIcon
from components.resource_path import resource_path
from components.select_control import SelectControl
from components.switch_control import SwitchControl

VERSION = "1.2"
APP_DEFAULT_WIDTH = 1000
APP_DEFAULT_HEIGHT = 800
TOP_BAR_HEIGHT = 250
MAX_CHANNELS = 8
current_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_path))

SETTINGS_BIN_WIDTH = "bin_width"
DEFAULT_BIN_WIDTH = 1000
SETTINGS_TIME_SPAN = "time_span"
DEFAULT_TIME_SPAN = 10
SETTINGS_CONNECTION_TYPE = "connection_type"
DEFAULT_CONNECTION_TYPE = "SMA"
SETTINGS_FREE_RUNNING = "free_running"
DEFAULT_FREE_RUNNING = "false"
SETTINGS_ACQUISITION_TIME = "acquisition_time"
SETTINGS_TAU_NS = "tau_ns"
DEFAULT_ACQUISITION_TIME = 10
SETTINGS_SYNC = "sync"
DEFAULT_SYNC = "sync_in"
SETTINGS_SYNC_IN_FREQUENCY_MHZ = "sync_in_frequency_mhz"
DEFAULT_SYNC_IN_FREQUENCY_MHZ = 0.0
SETTINGS_WRITE_DATA = "write_data"
DEFAULT_WRITE_DATA = True

MODE_STOPPED = "stopped"
MODE_RUNNING = "running"


class SpectroscopyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.update_plots_enabled = False
        self.settings = self.init_settings()

        self.channel_checkboxes = []
        self.sync_buttons = []
        self.control_inputs = {}

        self.mode = MODE_STOPPED
        self.tab_selected = "tab_spectroscopy"
        self.reference_file = None

        self.intensity_lines = []
        self.phasors_charts = []
        self.decay_curves = []
        self.decay_curves_queue = queue.Queue()

        self.selected_channels = []
        self.selected_sync = self.settings.value(SETTINGS_SYNC, DEFAULT_SYNC)
        self.sync_in_frequency_mhz = float(
            self.settings.value(SETTINGS_SYNC_IN_FREQUENCY_MHZ, DEFAULT_SYNC_IN_FREQUENCY_MHZ))

        self.write_data = True
        self.show_bin_file_size_helper = self.settings.value(SETTINGS_WRITE_DATA, DEFAULT_WRITE_DATA) == 'true'

        self.bin_file_size = ''
        self.bin_file_size_label = QLabel("")

        self.get_selected_channels_from_settings()

        (self.top_bar, self.grid_layout) = self.init_ui()

        self.on_tab_selected("tab_spectroscopy")

        # self.update_sync_in_button()

        self.generate_plots()

        self.overlay = OverlayWidget(self)
        self.overlay.resize(QSize(100, 100))
        self.installEventFilter(self)
        self.overlay.raise_()

        GUIStyles.set_fonts(self)

        self.timer_update = QTimer()
        self.timer_update.timeout.connect(self.update_plots)

        self.pull_from_queue_timer = QTimer()
        self.pull_from_queue_timer.timeout.connect(self.pull_from_queue)
        # self.timer_update.start(25)

        self.calc_exported_file_size()

    def eventFilter(self, source, event):
        try:
            if event.type() in (
                    QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                self.overlay.raise_()
                self.overlay.resize(self.size())
            return super().eventFilter(source, event)
        except:
            pass

    def init_ui(self):
        self.setWindowTitle("FlimLabs - SPECTROSCOPY v" + VERSION)
        TitlebarIcon.setup(self)
        GUIStyles.customize_theme(self)
        main_layout = QVBoxLayout()
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        grid_layout = QGridLayout()
        main_layout.addLayout(grid_layout)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(main_layout)

        self.resize(self.settings.value("size", QSize(APP_DEFAULT_WIDTH, APP_DEFAULT_HEIGHT)))
        self.move(
            self.settings.value("pos", QApplication.primaryScreen().geometry().center() - self.frameGeometry().center())
        )

        return top_bar, grid_layout

    @staticmethod
    def init_settings():
        settings = QSettings('settings.ini', QSettings.Format.IniFormat)
        return settings

    def closeEvent(self, event):
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        event.accept()

    def create_top_bar(self):
        top_bar = QVBoxLayout()
        top_bar.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_bar_header = QHBoxLayout()

        top_bar_header.addLayout(self.create_logo_and_title())

        # add hlayout
        tabs_layout = QHBoxLayout()
        # set height of parent
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        # no spacing
        tabs_layout.setSpacing(0)

        self.control_inputs["tab_spectroscopy"] = QPushButton("Spectroscopy")
        self.control_inputs["tab_spectroscopy"].setFlat(True)
        self.control_inputs["tab_spectroscopy"].setSizePolicy(QSizePolicy.Policy.Preferred,
                                                              QSizePolicy.Policy.Preferred)
        self.control_inputs["tab_spectroscopy"].setCursor(Qt.CursorShape.PointingHandCursor)
        self.control_inputs["tab_spectroscopy"].setCheckable(True)
        GUIStyles.set_config_btn_style(self.control_inputs["tab_spectroscopy"])
        self.control_inputs["tab_spectroscopy"].setChecked(True)
        self.control_inputs["tab_spectroscopy"].clicked.connect(lambda: self.on_tab_selected("tab_spectroscopy"))
        tabs_layout.addWidget(self.control_inputs["tab_spectroscopy"])

        self.control_inputs["tab_reference"] = QPushButton("Reference (Phasors)")
        self.control_inputs["tab_reference"].setFlat(True)
        self.control_inputs["tab_reference"].setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.control_inputs["tab_reference"].setCursor(Qt.CursorShape.PointingHandCursor)
        self.control_inputs["tab_reference"].setCheckable(True)
        GUIStyles.set_config_btn_style(self.control_inputs["tab_reference"])
        self.control_inputs["tab_reference"].clicked.connect(lambda: self.on_tab_selected("tab_reference"))
        tabs_layout.addWidget(self.control_inputs["tab_reference"])

        self.control_inputs["tab_data"] = QPushButton("Data (Phasors)")
        self.control_inputs["tab_data"].setFlat(True)
        self.control_inputs["tab_data"].setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.control_inputs["tab_data"].setCursor(Qt.CursorShape.PointingHandCursor)
        self.control_inputs["tab_data"].setCheckable(True)
        GUIStyles.set_config_btn_style(self.control_inputs["tab_data"])
        self.control_inputs["tab_data"].clicked.connect(lambda: self.on_tab_selected("tab_data"))
        tabs_layout.addWidget(self.control_inputs["tab_data"])

        top_bar_header.addLayout(tabs_layout)

        top_bar_header.addStretch(1)
        info_link_widget, export_data_control = self.create_export_data_input()
        file_size_info_layout = self.create_file_size_info_row()

        top_bar_header.addWidget(info_link_widget)
        top_bar_header.addLayout(export_data_control)
        export_data_control.addSpacing(10)

        top_bar_header.addLayout(file_size_info_layout)

        top_bar.addLayout(top_bar_header)
        top_bar.addSpacing(10)
        top_bar.addLayout(self.create_channel_selector())
        top_bar.addLayout(self.create_sync_buttons())
        top_bar.addSpacing(5)
        top_bar.addLayout(self.create_control_inputs())

        # # add a label to use as status
        # self.control_inputs["status"] = QLabel("Status: Ready")
        # self.control_inputs["status"].setStyleSheet("QLabel { color : #FFA726; }")
        # top_bar.addWidget(self.control_inputs["status"])

        container = QWidget()
        container.setLayout(top_bar)
        container.setFixedHeight(TOP_BAR_HEIGHT)
        return container

    def create_logo_and_title(self):
        row = QHBoxLayout()

        pixmap = QPixmap(
            resource_path("assets/spectroscopy-logo-white.png")
        ).scaledToWidth(38)
        ctl = QLabel(pixmap=pixmap)
        row.addWidget(ctl)

        row.addSpacing(10)

        ctl = GradientText(self,
                           text="SPECTROSCOPY",
                           colors=[(0.5, "#23F3AB"), (1.0, "#8d4ef2")],
                           stylesheet=GUIStyles.set_main_title_style())
        ctl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(ctl)

        ctl = QWidget()
        ctl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(ctl)
        return row

    def create_export_data_input(self):
        # Link to export data documentation
        info_link_widget = LinkWidget(

            icon_filename=resource_path("assets/info-icon.png"),
            link="https://flim-labs.github.io/spectroscopy-py/v1.0/#gui-usage",
        )
        info_link_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        info_link_widget.show()

        # Export data switch control
        export_data_control = QHBoxLayout()
        export_data_label = QLabel("Export data:")
        inp = SwitchControl(
            active_color="#FB8C00", width=70, height=30, checked=self.write_data
        )
        inp.toggled.connect(self.on_export_data_changed)
        export_data_control.addWidget(export_data_label)
        export_data_control.addSpacing(8)
        export_data_control.addWidget(inp)

        return info_link_widget, export_data_control

    def create_file_size_info_row(self):
        file_size_info_layout = QHBoxLayout()
        self.bin_file_size_label.setText("File size: " + str(self.bin_file_size))
        self.bin_file_size_label.setStyleSheet("QLabel { color : #FFA726; }")

        file_size_info_layout.addWidget(self.bin_file_size_label)
        self.bin_file_size_label.show() if self.write_data is True else self.bin_file_size_label.hide()

        return file_size_info_layout

    def create_control_inputs(self):
        controls_row = QHBoxLayout()
        _, inp = SelectControl.setup(
            "Channel type:",
            self.settings.value(SETTINGS_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE),
            controls_row,
            ["USB", "SMA"],
            self.on_connection_type_value_change
        )
        inp.setStyleSheet(GUIStyles.set_input_select_style())
        self.control_inputs["channel_type"] = inp

        _, inp = InputNumberControl.setup(
            "Bin width (µs):",
            100,
            1000000,
            int(self.settings.value(SETTINGS_BIN_WIDTH, DEFAULT_BIN_WIDTH)),
            controls_row,
            self.on_bin_width_change
        )
        inp.setStyleSheet(GUIStyles.set_input_number_style())
        self.control_inputs[SETTINGS_BIN_WIDTH] = inp

        _, inp = InputNumberControl.setup(
            "Time span (s):",
            1,
            300,
            int(self.settings.value(SETTINGS_TIME_SPAN, DEFAULT_TIME_SPAN)),
            controls_row,
            self.on_time_span_change
        )
        inp.setStyleSheet(GUIStyles.set_input_number_style())
        self.control_inputs[SETTINGS_TIME_SPAN] = inp

        switch_control = QVBoxLayout()
        inp = SwitchControl(
            active_color="#8d4ef2",
            checked=self.settings.value(SETTINGS_FREE_RUNNING, DEFAULT_FREE_RUNNING) == "true"
        )
        inp.toggled.connect(self.on_free_running_changed)
        switch_control.addWidget(QLabel("Free running:"))
        switch_control.addSpacing(8)
        switch_control.addWidget(inp)
        controls_row.addLayout(switch_control)
        controls_row.addSpacing(20)
        self.control_inputs[SETTINGS_FREE_RUNNING] = inp

        _, inp = InputNumberControl.setup(
            "Acquisition time (s):",
            1,
            1800,
            int(self.settings.value(SETTINGS_ACQUISITION_TIME, DEFAULT_ACQUISITION_TIME)),
            controls_row,
            self.on_acquisition_time_change
        )
        inp.setStyleSheet(GUIStyles.set_input_number_style())
        self.control_inputs[SETTINGS_ACQUISITION_TIME] = inp
        self.on_free_running_changed(self.settings.value(SETTINGS_FREE_RUNNING, DEFAULT_FREE_RUNNING) == "true")

        label, inp = InputFloatControl.setup(
            "TAU (ns):",
            0,
            1000,
            float(self.settings.value(SETTINGS_TAU_NS, "0")),
            controls_row,
            self.on_tau_change
        )
        inp.setStyleSheet(GUIStyles.set_input_number_style())
        self.control_inputs["tau"] = inp
        self.control_inputs["tau_label"] = label

        spacer = QWidget()
        spacer.setMaximumWidth(300)
        controls_row.addWidget(spacer)

        save_button = QPushButton("SAVE")
        save_button.setFlat(True)
        save_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setHidden(True)
        save_button.clicked.connect(self.on_save_reference)
        save_button.setStyleSheet("""
        QPushButton {
            background-color: #8d4ef2;
            color: white;
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 16px;
        }
        """)
        self.control_inputs["save"] = save_button
        controls_row.addWidget(save_button)

        start_button = QPushButton("START")
        start_button.setFlat(True)
        start_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        start_button.clicked.connect(self.on_start_button_click)
        self.control_inputs["start_button"] = start_button
        self.style_start_button()
        controls_row.addWidget(start_button)

        return controls_row

    def style_start_button(self):
        if self.mode == MODE_STOPPED:
            self.control_inputs["start_button"].setText("START")
            GUIStyles.set_start_btn_style(self.control_inputs["start_button"])
        else:
            self.control_inputs["start_button"].setText("STOP")
            GUIStyles.set_stop_btn_style(self.control_inputs["start_button"])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(event.size())

    def on_tab_selected(self, tab_name):
        self.control_inputs[self.tab_selected].setChecked(False)
        self.tab_selected = tab_name
        self.control_inputs[self.tab_selected].setChecked(True)
        if tab_name == "tab_spectroscopy":
            # hide tau input
            self.control_inputs["tau_label"].hide()
            self.control_inputs["tau"].hide()
        elif tab_name == "tab_reference":
            # show tau input
            self.control_inputs["tau_label"].show()
            self.control_inputs["tau"].show()
        elif tab_name == "tab_data":
            self.control_inputs["tau_label"].hide()
            self.control_inputs["tau"].hide()
        self.control_inputs["save"].setHidden(True)

        self.clear_plots()
        self.generate_plots()

    def on_start_button_click(self):
        if self.mode == MODE_STOPPED:
            self.begin_spectroscopy_experiment()
        elif self.mode == MODE_RUNNING:
            self.stop_spectroscopy_experiment()

    def on_tau_change(self, value):
        self.settings.setValue(SETTINGS_TAU_NS, value)

    def on_save_reference(self):
        if self.tab_selected == "tab_reference":
            # read all lines from .pid file
            with open(".pid", "r") as f:
                lines = f.readlines()
                reference_file = lines[0].split("=")[1]

            dialog = QFileDialog()
            dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            # extension supported: .reference.json
            dialog.setNameFilter("Reference files (*.reference.json)")
            dialog.setDefaultSuffix("reference.json")
            file_name, _ = dialog.getSaveFileName(
                self,
                "Save reference file",
                "",
                "Reference files (*.reference.json)",
                options=QFileDialog.Option.DontUseNativeDialog
            )
            if file_name:
                if not file_name.endswith('.reference.json'):
                    file_name += '.reference.json'
                try:
                    with open(reference_file, "r") as f:
                        with open(file_name, "w") as f2:
                            f2.write(f.read())
                except:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Error saving reference file",
                                QMessageBox.StandardButton.Ok).exec()

    def get_free_running_state(self):
        return self.control_inputs[SETTINGS_FREE_RUNNING].isChecked()

    def on_acquisition_time_change(self, value):
        self.settings.setValue(SETTINGS_ACQUISITION_TIME, value)
        self.calc_exported_file_size()

    def on_time_span_change(self, value):
        self.settings.setValue(SETTINGS_TIME_SPAN, value)

    def on_free_running_changed(self, state):
        self.control_inputs[SETTINGS_ACQUISITION_TIME].setEnabled(not state)
        self.settings.setValue(SETTINGS_FREE_RUNNING, state)
        self.calc_exported_file_size()

    def on_bin_width_change(self, value):
        self.settings.setValue(SETTINGS_BIN_WIDTH, value)
        self.calc_exported_file_size()

    def on_connection_type_value_change(self, value):
        self.settings.setValue(SETTINGS_CONNECTION_TYPE, value)

    def on_export_data_changed(self, state):
        self.settings.setValue(SETTINGS_WRITE_DATA, state)
        self.bin_file_size_label.show() if state else self.bin_file_size_label.hide()
        self.calc_exported_file_size() if state else None

    def create_channel_selector(self):
        grid = QHBoxLayout()
        grid.addSpacing(20)
        for i in range(MAX_CHANNELS):
            from components.fancy_checkbox import FancyCheckbox
            fancy_checkbox = FancyCheckbox(text=f"Channel {i + 1}")
            if self.selected_channels:
                fancy_checkbox.set_checked(i in self.selected_channels)
            fancy_checkbox.toggled.connect(lambda checked, channel=i: self.on_channel_selected(checked, channel))
            grid.addWidget(fancy_checkbox)
            self.channel_checkboxes.append(fancy_checkbox)
        grid.addSpacing(20)
        return grid

    def controls_set_enabled(self, enabled: bool):
        for key in self.control_inputs:
            if key != "start_button":
                self.control_inputs[key].setEnabled(enabled)
        if enabled:
            self.control_inputs[SETTINGS_ACQUISITION_TIME].setEnabled(not self.get_free_running_state())

    def top_bar_set_enabled(self, enabled: bool):
        self.sync_buttons_set_enabled(enabled)
        self.channel_selector_set_enabled(enabled)
        self.controls_set_enabled(enabled)

    def sync_buttons_set_enabled(self, enabled: bool):
        for i in range(len(self.sync_buttons)):
            self.sync_buttons[i][0].setEnabled(enabled)

    def channel_selector_set_enabled(self, enabled: bool):
        for i in range(len(self.channel_checkboxes)):
            self.channel_checkboxes[i].setEnabled(enabled)

    def on_channel_selected(self, checked: bool, channel: int):
        if checked:
            if channel not in self.selected_channels:
                self.selected_channels.append(channel)
        else:
            if channel in self.selected_channels:
                self.selected_channels.remove(channel)
        self.selected_channels.sort()
        self.set_selected_channels_to_settings()
        self.clear_plots()
        self.generate_plots()
        self.calc_exported_file_size()

    def on_sync_selected(self, sync: str):
        if self.selected_sync == sync and sync == 'sync_in':
            self.start_sync_in_dialog()
            return
        self.selected_sync = sync
        self.settings.setValue(SETTINGS_SYNC, sync)

    def start_sync_in_dialog(self):
        dialog = SyncInDialog()
        dialog.exec()
        if dialog.frequency_mhz != 0.0:
            self.sync_in_frequency_mhz = dialog.frequency_mhz
            self.settings.setValue(SETTINGS_SYNC_IN_FREQUENCY_MHZ, self.sync_in_frequency_mhz)
            self.update_sync_in_button()

    def update_sync_in_button(self):
        if self.sync_in_frequency_mhz == 0.0:
            self.sync_buttons[0][0].setText("Sync In (not detected)")
        else:
            self.sync_buttons[0][0].setText(f"Sync In ({self.sync_in_frequency_mhz} MHz)")

    def create_sync_buttons(self):
        buttons_layout = QHBoxLayout()

        sync_in_button = FancyButton("Sync In")
        buttons_layout.addWidget(sync_in_button)
        self.sync_buttons.append((sync_in_button, 'sync_in'))
        self.update_sync_in_button()

        sync_out_80_button = FancyButton("Sync Out (80MHz)")
        buttons_layout.addWidget(sync_out_80_button)
        self.sync_buttons.append((sync_out_80_button, 'sync_out_80'))

        sync_out_40_button = FancyButton("Sync Out (40MHz)")
        buttons_layout.addWidget(sync_out_40_button)
        self.sync_buttons.append((sync_out_40_button, 'sync_out_40'))

        sync_out_20_button = FancyButton("Sync Out (20MHz)")
        buttons_layout.addWidget(sync_out_20_button)
        self.sync_buttons.append((sync_out_20_button, 'sync_out_20'))

        sync_out_10_button = FancyButton("Sync Out (10MHz)")
        buttons_layout.addWidget(sync_out_10_button)
        self.sync_buttons.append((sync_out_10_button, 'sync_out_10'))

        for button, name in self.sync_buttons:
            def on_toggle(toggled_name):
                for b, n in self.sync_buttons:
                    b.set_selected(n == toggled_name)
                self.on_sync_selected(toggled_name)

            button.clicked.connect(lambda _, n=name: on_toggle(n))
            button.set_selected(self.selected_sync == name)

        return buttons_layout

    def generate_plots(self, frequency_mhz=0.0):
        if len(self.selected_channels) == 0:
            self.grid_layout.addWidget(QWidget(), 0, 0)
            return

        for i in range(len(self.selected_channels)):
            v_layout = QVBoxLayout()

            if self.tab_selected != "tab_data":

                intensity_widget = pg.PlotWidget()
                intensity_widget.setLabel('left', 'AVG. Photon counts', units='')
                intensity_widget.setLabel('bottom', 'Time', units='s')
                intensity_widget.setTitle(f'Channel {self.selected_channels[i] + 1} intensity')

                # remove margins
                intensity_widget.plotItem.setContentsMargins(0, 0, 0, 0)

                x = np.arange(1)
                y = x * 0
                intensity_plot = intensity_widget.plot(x, y, pen='#23F3AB')
                self.intensity_lines.append(intensity_plot)

                v_layout.addWidget(intensity_widget, 1)

                curve_widget = pg.PlotWidget()
                curve_widget.setLabel('left', 'Photon counts', units='')
                curve_widget.setLabel('bottom', 'Time', units='ns')
                curve_widget.setTitle(f'Channel {self.selected_channels[i] + 1} decay')

                if frequency_mhz != 0.0:
                    period = 1_000 / frequency_mhz
                    x = np.linspace(0, period, 256)
                else:
                    x = np.arange(1)

                y = x * 0
                static_curve = curve_widget.plot(x, y, pen='r')
                self.decay_curves.append(static_curve)
                v_layout.addWidget(curve_widget, 4)
            else:
                # add h layout, with a label 10K CPS, and a curve_widget
                h_layout = QHBoxLayout()
                label = QLabel("10K CPS")
                label.setStyleSheet(
                    "QLabel { color : #FFA726; font-size: 20px; weight: bold; background-color: #000000; padding: 8px; }")

                curve_widget = pg.PlotWidget()
                curve_widget.setLabel('left', 'Photon counts', units='')
                curve_widget.setLabel('bottom', 'Time', units='ns')
                curve_widget.setTitle(f'Channel {self.selected_channels[i] + 1} decay')

                if frequency_mhz != 0.0:
                    period = 1_000 / frequency_mhz
                    x = np.linspace(0, period, 256)
                else:
                    x = np.arange(1)

                y = x * 0
                static_curve = curve_widget.plot(x, y, pen='r')
                self.decay_curves.append(static_curve)
                h_layout.addWidget(label)
                h_layout.addWidget(curve_widget)
                v_layout.addLayout(h_layout, 1)

                # add a phasors chart
                phasors_widget = pg.PlotWidget()

                # mantain aspect ratio
                phasors_widget.setAspectLocked(True)
                phasors_widget.setLabel('left', '', units='')
                phasors_widget.setTitle(f'Channel {self.selected_channels[i] + 1} phasors')
                # draw semi-circle
                x = np.linspace(-1, 1, 1000)
                y = np.sqrt(1 - x ** 2)
                phasors_widget.plot(x, y, pen='#23F3AB')

                self.phasors_charts.append(phasors_widget.plot([], [], pen=None, symbol='o', symbolPen=None, symbolSize=5, symbolBrush='#23F3AB'))

                v_layout.addWidget(phasors_widget, 4)

            col_length = 1
            if len(self.selected_channels) == 2:
                col_length = 2
            elif len(self.selected_channels) == 3:
                col_length = 3
            if len(self.selected_channels) > 3:
                col_length = 2
            self.grid_layout.addLayout(v_layout, i // col_length, i % col_length)

    def get_selected_channels_from_settings(self):
        self.selected_channels = []
        for i in range(MAX_CHANNELS):
            if self.settings.value(f"channel_{i}", 'false') == 'true':
                self.selected_channels.append(i)

    def set_selected_channels_to_settings(self):
        for i in range(MAX_CHANNELS):
            self.settings.setValue(f"channel_{i}", 'false')
            if i in self.selected_channels:
                self.settings.setValue(f"channel_{i}", 'true')

    def stop_plots(self):
        self.timer_update.stop()

    def clear_plots(self):
        for curve in self.intensity_lines:
            curve.clear()
        for curve in self.decay_curves:
            curve.clear()
        for phasor in self.phasors_charts:
            phasor.clear()
        self.phasors_charts.clear()
        self.intensity_lines.clear()
        self.decay_curves.clear()
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
            layout = self.grid_layout.itemAt(i).layout()
            if layout is not None:
                self.clear_layout_tree(layout)

    def clear_layout_tree(self, layout: QLayout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout_tree(item.layout())
            del layout

    def calc_exported_file_size(self):
        free_running = self.settings.value(SETTINGS_FREE_RUNNING, DEFAULT_FREE_RUNNING)
        acquisition_time = self.settings.value(SETTINGS_ACQUISITION_TIME, DEFAULT_ACQUISITION_TIME)
        bin_width = self.settings.value(SETTINGS_BIN_WIDTH, DEFAULT_BIN_WIDTH)

        if free_running is True or acquisition_time is None:
            file_size_MB = len(self.selected_channels) * (1000 / int(bin_width))
            self.bin_file_size = format_size(file_size_MB * 1024 * 1024)
            self.bin_file_size_label.setText("File size: " + str(self.bin_file_size) + "/s")
        else:
            file_size_MB = int(acquisition_time) * len(self.selected_channels) * (1000 / int(bin_width))
            self.bin_file_size = format_size(file_size_MB * 1024 * 1024)
            self.bin_file_size_label.setText("File size: " + str(self.bin_file_size))

    def begin_spectroscopy_experiment(self):
        if self.selected_sync == "sync_in":
            frequency_mhz = self.sync_in_frequency_mhz
        else:
            frequency_mhz = int(self.selected_sync.split("_")[-1])
        if frequency_mhz == 0.0:
            QMessageBox(QMessageBox.Icon.Warning, "Error", "Frequency not detected",
                        QMessageBox.StandardButton.Ok).exec()
            return

        self.clear_plots()
        self.generate_plots(frequency_mhz)

        if len(self.selected_channels) == 0:
            QMessageBox(QMessageBox.Icon.Warning, "Error", "No channels selected",
                        QMessageBox.StandardButton.Ok).exec()
            return

        acquisition_time_millis = None if self.get_free_running_state() else int(
            self.settings.value(SETTINGS_ACQUISITION_TIME, DEFAULT_ACQUISITION_TIME)) * 1000
        bin_width_micros = int(self.settings.value(SETTINGS_BIN_WIDTH, DEFAULT_BIN_WIDTH))

        connection_type = self.settings.value(SETTINGS_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE)

        if str(connection_type) == "0":
            connection_type = "USB"
        else:
            connection_type = "SMA"

        firmware_selected = flim_labs.get_spectroscopy_firmware(
            sync="in" if self.selected_sync == "sync_in" else "out",
            frequency_mhz=frequency_mhz,
            channel=connection_type.lower(),
            sync_connection="sma"
        )

        print(f"Firmware selected: {firmware_selected}")
        print(f"Connection type: {connection_type}")
        print(f"Frequency: {frequency_mhz} Mhz")
        print(f"Selected channels: {self.selected_channels}")
        print(f"Acquisition time: {acquisition_time_millis} ms")
        print(f"Bin width: {bin_width_micros} µs")
        print(f"Free running: {self.get_free_running_state()}")
        print(f"Tau: {self.settings.value(SETTINGS_TAU_NS, '0')} ns")
        print(f"Reference file: {self.reference_file}")

        if self.tab_selected == "tab_data":
            if not self.reference_file:
                QMessageBox(QMessageBox.Icon.Warning, "Error", "No reference file selected",
                            QMessageBox.StandardButton.Ok).exec()
                return

            # load reference file (is a json)
            # example: {
            #   "bin_width_micros": 1000,
            #   "calibrations": [
            #     [
            #       -1.652415386892391,
            #       1.0223231306721805
            #     ],
            #     [
            #       -1.9086511584591719,
            #       1.0557978525373855
            #     ]
            #   ],
            #   "channels": [1,3],
            #   "curves": [
            #     [ ... 256 intensities ... ],
            #     [ ... 256 intensities ... ]
            #   ],
            #   "laser_period_ns": 25.0,
            #   "tau_ns": 2.0
            # }
            with open(self.reference_file, "r") as f:
                reference_data = json.load(f)
                if "bin_width_micros" not in reference_data:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (missing bin width)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                elif reference_data["bin_width_micros"] != bin_width_micros:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (bin width mismatch)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                if "channels" not in reference_data:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (missing channels)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                elif len(reference_data["channels"]) != len(self.selected_channels):
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (channels mismatch)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                if "curves" not in reference_data:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (missing curves)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                elif len(reference_data["curves"]) != len(self.selected_channels):
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (curves mismatch)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                if "laser_period_ns" not in reference_data:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (missing laser period)",
                                QMessageBox.StandardButton.Ok).exec()
                    return
                if "tau_ns" not in reference_data:
                    QMessageBox(QMessageBox.Icon.Warning, "Error", "Invalid reference file (missing tau)",
                                QMessageBox.StandardButton.Ok).exec()
                    return

        try:
            # set tau_ns if selected tab is reference
            tau_ns = float(self.settings.value(SETTINGS_TAU_NS, "0")) if self.tab_selected == "tab_reference" else None

            reference_file = None if self.tab_selected != "tab_data" else self.reference_file

            flim_labs.start_spectroscopy(
                enabled_channels=self.selected_channels,
                bin_width_micros=bin_width_micros,
                frequency_mhz=frequency_mhz,
                firmware_file=firmware_selected,
                acquisition_time_millis=acquisition_time_millis,
                tau_ns=tau_ns,
                reference_file=reference_file
            )
        except Exception as e:
            QMessageBox(QMessageBox.Icon.Warning, "Error", "Error starting spectroscopy: " + str(e),
                        QMessageBox.StandardButton.Ok).exec()
            return
        self.mode = MODE_RUNNING
        self.style_start_button()
        QApplication.processEvents()
        self.update_plots_enabled = True
        self.top_bar_set_enabled(False)
        # self.timer_update.start(18)
        self.pull_from_queue_timer.start(25)
        # self.pull_from_queue()

    def pull_from_queue(self):
        val = flim_labs.pull_from_queue()
        if len(val) > 0:
            for v in val:
                if v == ('end',):  # End of acquisition
                    print("Got end of acquisition, stopping")
                    self.on_start_button_click()
                    self.mode = MODE_STOPPED
                    self.style_start_button()
                    self.control_inputs["save"].setHidden(False)
                    QApplication.processEvents()

                    if self.tab_selected == "tab_reference":
                        # read reference file from .pid file
                        with open(".pid", "r") as f:
                            lines = f.readlines()
                            reference_file = lines[0].split("=")[1]
                        self.reference_file = reference_file
                        print(f"Last reference file: {reference_file}")

                    break
                if 'sp_phasors' in v[0]:
                    channel = v[1][0]
                    harmonic = v[1][0]
                    phasors = v[3]
                    self.draw_points_in_phasors(channel, harmonic, phasors)
                    continue


                ((channel,), (time_ns,), intensities) = v
                channel_index = self.selected_channels.index(channel)
                # self.decay_curves_queue.put((channel_index, time_ns, intensities))
                self.update_plots2(channel_index, time_ns, intensities)
                QApplication.processEvents()
        # QTimer.singleShot(1, self.pull_from_queue)

    def draw_points_in_phasors(self, channel, harmonic, phasors):
        channel_index = self.selected_channels.index(channel)
        x, y = self.phasors_charts[channel_index].getData()
        if x is None:
            x = np.array([])
            y = np.array([])

        # phasors is a list of 2 points: (g,s), (g,s), (g,s), ... I need to append them to x and y
        new_x = [p[0] for p in phasors]
        new_y = [p[1] for p in phasors]

        x = np.concatenate((x, new_x))
        y = np.concatenate((y, new_y))  

        self.phasors_charts[channel_index].setData(x, y)
        pass

    def update_plots2(self, channel_index, time_ns, curve):
        intensity_line = self.intensity_lines[channel_index] if channel_index < len(self.intensity_lines) else None
        if intensity_line is not None:
            x, y = intensity_line.getData()
            if x is None or (len(x) == 1 and x[0] == 0):
                x = np.array([time_ns / 1_000_000_000])
                y = np.array([np.sum(curve)])
            else:
                x = np.append(x, time_ns / 1_000_000_000)
                y = np.append(y, np.sum(curve))
            # if len(x) > 100:
            #     x = x[1:]
            #     y = y[1:]
            intensity_line.setData(x, y)

        decay_curve = self.decay_curves[channel_index] if channel_index < len(self.decay_curves) else None
        if decay_curve is not None:
            x, y = decay_curve.getData()
            decay_curve.setData(x, curve + y)
        QApplication.processEvents()
        time.sleep(0.01)

    def update_plots(self):
        try:
            (channel_index, time_ns, curve) = self.decay_curves_queue.get(block=True, timeout=0.1)
        except queue.Empty:
            QApplication.processEvents()
            return
        except Exception as e:
            print("Error: " + str(e))
            return
        x, y = self.intensity_lines[channel_index].getData()
        if x is None or (len(x) == 1 and x[0] == 0):
            x = np.array([time_ns / 1_000_000_000])
            y = np.array([np.sum(curve)])
        else:
            x = np.append(x, time_ns / 1_000_000_000)
            y = np.append(y, np.sum(curve))
        # if len(x) > 100:
        #     x = x[1:]
        #     y = y[1:]
        self.intensity_lines[channel_index].setData(x, y)
        x, y = self.decay_curves[channel_index].getData()
        self.decay_curves[channel_index].setData(x, curve + y)
        QApplication.processEvents()
        time.sleep(0.01)

    def stop_spectroscopy_experiment(self):
        print("Stopping spectroscopy")
        try:
            flim_labs.request_stop()
        except:
            pass
        self.mode = MODE_STOPPED
        self.style_start_button()
        QApplication.processEvents()
        # time.sleep(0.5)
        # self.pull_from_queue_timer.stop()
        # time.sleep(0.5)
        # self.timer_update.stop()
        # self.update_plots_enabled = False
        self.top_bar_set_enabled(True)


class SyncInDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sync In Measure Frequency")
        self.setFixedSize(300, 200)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Do you want to start to measure frequency?")
        self.layout.addWidget(self.label)
        self.label.setWordWrap(True)

        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        self.no_button = QPushButton("No")
        self.no_button.clicked.connect(self.on_no_button_click)
        self.button_layout.addWidget(self.no_button)

        self.yes_button = QPushButton("Do it")
        self.yes_button.clicked.connect(self.on_yes_button_click)
        self.button_layout.addWidget(self.yes_button)

        self.frequency_mhz = 0.0

        GUIStyles.customize_theme(self)
        GUIStyles.set_fonts()

    def on_yes_button_click(self):
        self.label.setText(
            "Measuring frequency... The process can take a few seconds. Please wait. After 30 seconds, the process "
            "will be interrupted automatically.")
        self.yes_button.setEnabled(False)
        self.no_button.setEnabled(False)
        QApplication.processEvents()
        try:
            res = flim_labs.detect_laser_frequency()
            if res is None or res == 0.0:
                self.frequency_mhz = 0.0
                self.label.setText("Frequency not detected. Please check the connection and try again.")
                self.no_button.setText("Cancel")
            else:
                self.frequency_mhz = round(res, 3)
                self.label.setText(f"Frequency detected: {self.frequency_mhz} MHz")
                self.no_button.setText("Done")
        except Exception as e:
            self.frequency_mhz = 0.0
            self.label.setText("Error: " + str(e))
            self.no_button.setText("Cancel")
        self.yes_button.setEnabled(True)
        self.yes_button.setText("Retry again")
        self.no_button.setEnabled(True)

    def on_no_button_click(self):
        self.close()


if __name__ == "__main__":
    # remove .pid file if exists
    if os.path.exists(".pid"):
        os.remove(".pid")
    app = QApplication(sys.argv)
    window = SpectroscopyWindow()
    window.show()
    app.exec()
    window.pull_from_queue_timer.stop()
    sys.exit()
