import os
import shutil

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from components.box_message import BoxMessage
from components.gui_styles import GUIStyles
from components.messages_utilities import MessagesUtilities

current_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_path, ".."))


class ScriptFileUtils:
    @classmethod
    def export_script_file(
        cls, bin_file_path, file_extension, content_modifier
    ):
        file_name, _ = QFileDialog.getSaveFileName(
            None, "Save File", "", f"All Files (*.{file_extension})"
        )
        if not file_name:
            return
        try:
            bin_file_name = os.path.join(
                os.path.dirname(file_name),
                f"{os.path.splitext(os.path.basename(file_name))[0]}.bin",
            ).replace("\\", "/")

            shutil.copy(bin_file_path, bin_file_name) if bin_file_path else None

            # write script file
            content = content_modifier["source_file"]
            new_content = cls.manipulate_file_content(content, bin_file_name)
            cls.write_file(file_name, new_content)

            # write requirements file only for python export
            if len(content_modifier["requirements"]) > 0:
                requirement_path, requirements_content = cls.create_requirements_file(
                    file_name, content_modifier["requirements"]
                )
                cls.write_file(requirement_path, requirements_content)

            cls.show_success_message(file_name)
        except Exception as e:
            cls.show_error_message(str(e))

    @classmethod
    def write_file(cls, file_name, content):
        with open(file_name, "w") as file:
            file.writelines(content)

    @classmethod
    def create_requirements_file(cls, script_file_name, requirements):
        directory = os.path.dirname(script_file_name)
        requirements_path = os.path.join(directory, "requirements.txt")
        requirements_content = []

        for requirement in requirements:
            requirements_content.append(f"{requirement}\n")
        return [requirements_path, requirements_content]

    @classmethod
    def read_file_content(cls, file_path):
        with open(file_path, "r") as file:
            return file.readlines()

    @classmethod
    def manipulate_file_content(cls, content, file_name):
        return content.replace("<FILE-PATH>", file_name.replace("\\", "/"))

    @classmethod
    def show_success_message(cls, file_name):
        info_title, info_msg = MessagesUtilities.info_handler(
            "SavedScriptFile", file_name
        )
        BoxMessage.setup(
            info_title,
            info_msg,
            QMessageBox.Icon.Information,
            GUIStyles.set_msg_box_style(),
        )

    @classmethod
    def show_error_message(cls, error_message):
        error_title, error_msg = MessagesUtilities.error_handler(
            "ErrorSavingScriptFile", error_message
        )
        BoxMessage.setup(
            error_title,
            error_msg,
            QMessageBox.Icon.Critical,
            GUIStyles.set_msg_box_style(),
        )


class PythonScriptUtils(ScriptFileUtils):

        
    @staticmethod
    def download_spectroscopy(window, bin_file_path):
        content_modifier = {
            "source_file": """import os
import struct
import matplotlib.pyplot as plt
import numpy as np
file_path = "<FILE-PATH>"
with open(file_path, 'rb') as f:
    # first 4 bytes must be SP01
    # 'SP01' is an identifier for spectroscopy bin files
    if f.read(4) != b"SP01":
        print("Invalid data file")
        exit(0)

    # read metadata from file
    (json_length,) = struct.unpack("I", f.read(4))
    null = None
    metadata = eval(f.read(json_length).decode("utf-8"))

    
    # ENABLED CHANNELS
    if "channels" in metadata and metadata["channels"] is not None:
        print(
            "Enabled channels: "
            + (
                ", ".join(
                    ["Channel " + str(ch + 1) for ch in metadata["channels"]]
                )
            )
        )   
    # BIN WIDTH (us)    
    if "bin_width_micros" in metadata and metadata["bin_width_micros"] is not None:
        print("Bin width: " + str(metadata["bin_width_micros"]) + "us")    
    # ACQUISITION TIME (duration of the acquisition)
    if "acquisition_time_millis" in metadata and metadata["acquisition_time_millis"] is not None:
        print("Acquisition time: " + str(metadata["acquisition_time_millis"] / 1000) + "s")
    # LASER PERIOD (ns)
    if "laser_period_ns" in metadata and metadata["laser_period_ns"] is not None:
        print("Laser period: " + str(metadata["laser_period_ns"]) + "ns") 
    # TAU (ns)
    if "tau_ns" in metadata and metadata["tau_ns"] is not None:
        print("Tau: " + str(metadata["tau_ns"]) + "ns")   
        
              
    channel_curves = [[] for _ in range(len(metadata["channels"]))]
    times = []
    number_of_channels = len(metadata["channels"])
    channel_values_unpack_string = 'I' * 256 
    
    while True:        
        data = f.read(8)
        if not data:
            break
        (time,) = struct.unpack('d', data)    
        for i in range(number_of_channels):
            data = f.read(4 * 256)  
            if len(data) < 4 * 256:
                break
            curve = struct.unpack(channel_values_unpack_string, data)    
            channel_curves[i].append(np.array(curve))
        times.append(time / 1_000_000_000)    
    
    # PLOTTING
    plt.xlabel("Bin")
    plt.ylabel("Intensity")
    plt.yscale('log')
    plt.title("Spectroscopy (time: " + str(round(times[-1])) + "s, curves stored: " + str(len(times)) + ")")
    # plot all channels summed up    
    total_max = 0
    total_min = 9999999999999
    for i in range(len(channel_curves)):
        sum_curve = np.sum(channel_curves[i], axis=0)
        max = np.max(sum_curve)
        min = np.min(sum_curve)
        if max > total_max:
            total_max = max
        if min < total_min:    
            total_min = min
        plt.plot(sum_curve, label=f"Channel {metadata['channels'][i] + 1}")  
        plt.legend()  
    plt.ylim(min * 0.99, max * 1.01) 
    plt.tight_layout()   
    plt.show()                   
            """,
            "skip_pattern": "get_recent_spectroscopy_file():",
            "end_pattern": "with open(file_path, 'rb') as f:",
            "replace_pattern": "with open(file_path, 'rb') as f:",
            "requirements": ["matplotlib", "numpy"],
        }
        ScriptFileUtils.export_script_file(
            bin_file_path, "py", content_modifier
        )
        
        
        
    @staticmethod    
    def download_phasors(window, bin_file_path):
        content_modifier = {
            "source_file": """import struct
from matplotlib.gridspec import GridSpec            
import matplotlib.pyplot as plt

file_path = "<FILE-PATH>"
                     
                              
            """,
            "skip_pattern": "def get_recent_fcs_file():",
            "end_pattern": "def calc_g2_correlations_mean(g2):",
            "replace_pattern": "def calc_g2_correlations_mean(g2):",
            "requirements": ["matplotlib"],
        }
        ScriptFileUtils.export_script_file(
            bin_file_path, "py", content_modifier
        )    