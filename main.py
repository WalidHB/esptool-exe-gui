from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QComboBox, QPushButton, QLineEdit, \
    QFileDialog, QSpacerItem, QSizePolicy, QGridLayout, QInputDialog, QMessageBox, QPlainTextEdit, QSplitter, \
    QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QProcess, Signal, Slot

import os
import json
from serial.tools.list_ports import comports

class CustomInputWidget(QWidget):
    optionSelected = Signal(str)
    selectClicked = Signal(str)
    deleteClicked = Signal(dict, str)
    cancelClicked = Signal()

    def __init__(self, items=None, parent=None):
        super(CustomInputWidget, self).__init__(parent)
  
        self.layout = QVBoxLayout()
        self.items = items
        # Create the combo box for input
        self.input_combobox = QComboBox(self)
        self.currenttext = ''
        if items:
            self.input_combobox.addItems(items)
            self.input_combobox.currentIndexChanged.connect(lambda _: setattr(self, 'currenttext', self.input_combobox.currentText()))
        self.layout.addWidget(self.input_combobox)

        # Create the custom buttons in a horizontal layout
        button_layout = QHBoxLayout()

        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.on_select_clicked)
        button_layout.addWidget(self.select_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        button_layout.addWidget(self.delete_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)
        self.show()

        self.currenttext = self.input_combobox.currentText()

    def on_select_clicked(self):

        self.selectClicked.emit(self.currenttext)
        self.close()

    def on_delete_clicked(self):

        self.deleteClicked.emit(self.items, self.currenttext)
        self.input_combobox.removeItem(self.input_combobox.currentIndex())

    def on_cancel_clicked(self):
        self.cancelClicked.emit()
        self.close()


class CustomComboBox(QComboBox):
    def __init__(self):
        super().__init__()

        # Initial setup
        self.com_ports = self.get_com_ports()
        self.addItems(self.com_ports)

    def get_com_ports(self):
        return [port.device for port in comports()]

    def update_com_ports(self):
        updated_com_ports = self.get_com_ports()

        # Check if the COM ports have changed
        if updated_com_ports != self.com_ports:
            self.com_ports = updated_com_ports
            self.clear()
            self.addItems(self.com_ports)

    def showPopup(self):
        # Update COM ports before showing the popup
        self.update_com_ports()
        super().showPopup()

class FlashToolApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Esptool GUI")
        self.setGeometry(100, 100, 800, 600)  # Set the window size

        self.current_directory = os.getcwd()

        self.directory_label = QLabel(self.current_directory)
        self.com_label = QLabel("COM port:")
        self.mode_label = QLabel("Flash Mode:")
        self.baud_label = QLabel("Baudrate:")
        self.size_label = QLabel("Flash Size:")
        self.freq_label = QLabel("Flash Frequency:")

        self.selected_com_port = None

        self.com_ports = [port.device for port in comports()]
        self.com_port_menu = CustomComboBox()
        self.com_port_menu.addItems(self.com_ports)

        self.baud_rates = ['115200', '230400', '460800', '921600', '1152000', '1500000']
        self.baud_menu = QComboBox()
        self.baud_menu.addItems(self.baud_rates)

        self.modes = ['default' , 'qio' , 'qout' , 'dio' , 'dout']
        self.modes_menu = QComboBox()
        self.modes_menu.addItems(self.modes)

        self.freq = ['default' , '80m ' , '40m' , '26m' , '20m']
        self.freq_menu = QComboBox()
        self.freq_menu.addItems(self.freq)

        self.sizes = ['default', 'detect', '1MB', '2MB', '4MB', '8MB', '16MB']
        self.sizes_menu = QComboBox()
        self.sizes_menu.addItems(self.sizes)

        self.erase_button = QPushButton("Erase Flash")
        self.erase_button.clicked.connect(self.erase_flash)

        self.file_label = QLabel("File Path:")
        self.file_entry = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse)

        self.address_label = QLabel("Address:")
        self.address_entry = QLineEdit()
        self.address_entry.setPlaceholderText("(optional)")
        
        self.custom_command_label = QLabel("Custom Command:")
        self.custom_command_entry = QLineEdit()
        self.custom_command_entry.setPlaceholderText("(optional)")
        self.add_button = QPushButton("Add File and Address")
        self.add_button.clicked.connect(lambda: self.add_to_flash_entries(file_path = self.file_entry.text(),
                                                                          address = self.address_entry.text(),
                                                                          command=self.custom_command_entry.text()))

        self.flash_button = QPushButton("Flash")
        self.flash_button.clicked.connect(self.flash_entries_action)

        self.save_profile_button = QPushButton("Save Profile")
        self.save_profile_button.clicked.connect(self.save_profile)

        self.load_profile_button = QPushButton("Load Profile")
        self.load_profile_button.clicked.connect(self.open_profile_window)

        self.clear_button = QPushButton("Clear Entries")
        self.clear_button.clicked.connect(self.clear_entries)

        # Terminal window
        self.terminal_window = QPlainTextEdit()
        self.terminal_window.setReadOnly(True)
        self.terminal_window_cursor = self.terminal_window.textCursor()


        # Set up a QProcess for handling subprocesses
        self.subprocess = QProcess(self)
        self.subprocess.setProcessChannelMode(QProcess.MergedChannels)
        self.subprocess.readyReadStandardOutput.connect(self.update_terminal)

        # Set up a QTimer to periodically check for updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(200)  # Update every 500 milliseconds


        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = QWidget(splitter)
        self.left_layout = QVBoxLayout(left_panel)

        self.left_layout.addWidget(self.directory_label)

        self.settings_label_layout = QHBoxLayout()

        self.settings_label_layout.addWidget(self.com_label)
        self.settings_label_layout.addWidget(self.baud_label)
        self.left_layout.addLayout(self.settings_label_layout)

        self.settings_layout = QHBoxLayout()

        self.settings_layout.addWidget(self.com_port_menu)
        self.settings_layout.addWidget(self.baud_menu)
        self.left_layout.addLayout(self.settings_layout)

        self.flash_settings_label_layout = QHBoxLayout()

        self.flash_settings_label_layout.addWidget(self.mode_label)
        self.flash_settings_label_layout.addWidget(self.freq_label)
        self.flash_settings_label_layout.addWidget(self.size_label)
        self.left_layout.addLayout(self.flash_settings_label_layout)

        self.flash_settings_layout = QHBoxLayout()

        self.flash_settings_layout.addWidget(self.modes_menu)
        self.flash_settings_layout.addWidget(self.freq_menu)
        self.flash_settings_layout.addWidget(self.sizes_menu)
        self.left_layout.addLayout(self.flash_settings_layout)




        self.left_layout.addWidget(self.erase_button)

        file_layout = QGridLayout()
        file_layout.addWidget(self.file_label, 0, 0)
        file_layout.addWidget(self.file_entry, 0, 1)
        file_layout.addWidget(self.browse_button, 0, 2)

        address_layout = QGridLayout()
        address_layout.addWidget(self.address_label, 0, 0)
        address_layout.addWidget(self.address_entry, 0, 1)

        custom_command_layout = QGridLayout()

        custom_command_layout.addWidget(self.custom_command_label, 0, 0)
        custom_command_layout.addWidget(self.custom_command_entry, 0, 1)

        self.left_layout.addLayout(file_layout)
        self.left_layout.addLayout(address_layout)
        self.left_layout.addLayout(custom_command_layout)

        self.left_layout.addWidget(self.add_button)
        self.left_layout.addWidget(self.flash_button)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.left_layout.addItem(spacer)

        self.left_layout.addWidget(self.save_profile_button)
        self.left_layout.addWidget(self.load_profile_button)

        self.left_layout.addWidget(self.clear_button)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.terminal_window)

    def erase_flash(self):
        com_port = self.com_port_menu.currentText()
        command = [f"{self.current_directory}/esptool.exe", "--port", com_port, "erase_flash"]
        self.run_subprocess(command)

    def browse(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", self.current_directory)
        if file_path:
            self.file_entry.setText(file_path)

    def add_to_flash_entries(self, file_path, address, command):

        print(f"Added file: {file_path}, Address: {address}")

        added_file_entry = QLineEdit(f"{file_path}")
        added_address_entry = QLineEdit(f"{address}")
        added_custom_command_entry = QLineEdit(f"{command}")

        # Clear the entry fields
        self.file_entry.clear()
        self.address_entry.clear()
        self.custom_command_entry.clear()

        # Find the index of the flash button in the layout
        flash_button_index = self.left_layout.indexOf(self.flash_button)

        # Add the added widgets after the "Flash" button
        self.left_layout.insertWidget(flash_button_index + 1, added_file_entry)
        self.left_layout.insertWidget(flash_button_index + 2, added_address_entry)
        self.left_layout.insertWidget(flash_button_index + 3, added_custom_command_entry)

        # Add space between entries
        spacer_label = QLabel()
        spacer_label.setFixedSize(20, 1)
        self.left_layout.insertWidget(flash_button_index + 4, spacer_label)

    def get_entries(self):
        flash_button_index = self.left_layout.indexOf(self.flash_button)

        widgets_to_use = []

        # Collect only QLineEdit widgets between "Flash" and "Profile" buttons
        i = flash_button_index + 1
        while i < self.left_layout.count() - 2:
            item = self.left_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLineEdit):
                widgets_to_use.append(item.widget())
            i += 1
        return widgets_to_use
    
    def clear_entries(self):

        widgets_to_remove = self.get_entries()

        # Remove collected widgets
        for widget in widgets_to_remove:
            widget.deleteLater()
    

    def flash_entries_action(self):
        com_port = self.com_port_menu.currentText()
        mode = self.modes_menu.currentText()
        baud = self.baud_menu.currentText()
        frequency = self.freq_menu.currentText()
        size = self.sizes_menu.currentText()

        if mode == "default":
            mode = "keep"

        if frequency == "default":
            frequency = "keep"

        if size == "default":
            size = "keep"
        
         

        files_to_flash = self.get_entries()
        files_to_flash = [entry.text() for entry in reversed(files_to_flash)]
        # files_to_flash = [(files_to_flash[j+2].text(), files_to_flash[j + 1].text(), files_to_flash[j].text()) for j in range(0, len(files_to_flash), 3)]

        if com_port:
            # for file_path, address, command in files_to_flash:
            #     print(f"Flashing: File Path: {file_path}, Address: {address}, COM Port: {com_port}")
            command = [f"{self.current_directory}/esptool.exe", "--port", com_port, "--baud", baud, "write_flash" , '--flash_mode', mode, "--flash_freq", frequency , '--flash_size', size]
            command.extend(files_to_flash)
            command = [k for k in command if k != '']
            print(command)
            self.run_subprocess(command)

    def save_profile(self):
        profile_name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if ok:
            chip_name = profile_name

            entries = self.get_entries()

            saved_data = [(entries[j].text(), entries[j + 1].text(), entries[j + 2].text()) for j in range(0, len(entries), 3)]
            files, addresses, commands = [k[0] for k in saved_data], [k[1] for k in saved_data], [k[2] for k in saved_data]

            print(files, addresses, commands)
            profile_data = {
                "chip_name": chip_name,
                "baudrate" : self.baud_menu.currentText(),
                "mode" : self.modes_menu.currentText(),
                "freq" : self.freq_menu.currentText(),
                "size" : self.sizes_menu.currentText(),
                "files": files,
                "addresses": addresses,
                "commands" : commands
            }

            existing_profiles = self.load_all_profiles()
            existing_profiles[profile_name] = profile_data

            with open('profiles.json', 'w') as file:
                json.dump(existing_profiles, file)

    def load_all_profiles(self):
        try:
            with open('profiles.json', 'r') as file:
                profile_list = json.load(file)
            return profile_list
        except FileNotFoundError:
            return {}
            
    def open_profile_window(self):
            profile_list = self.load_all_profiles()
            if not profile_list:
                QMessageBox.warning(self, "Load Profile", "No profiles available.")
                return

            self.custom_input_widget = CustomInputWidget(items=profile_list)

            self.custom_input_widget.selectClicked.connect(self.load_profile)
            self.custom_input_widget.deleteClicked.connect(self.delete_profile)


    def delete_profile(self, profile_list, profile_name):
        print(profile_list)
        del profile_list[profile_name]
        with open('profiles.json', 'w') as file:
            json.dump(profile_list, file)

    def load_profile(self, profile_name):
        profile_list = self.load_all_profiles()
        
        if profile_name in profile_list:
            selected_profile = profile_list[profile_name]
            
            for entry in selected_profile["files"]:
                self.add_to_flash_entries(entry, selected_profile["addresses"][
                    selected_profile["files"].index(entry)],selected_profile["commands"][selected_profile["files"].index(entry)])
            
            self.modes_menu.setCurrentText(selected_profile["mode"])
            self.baud_menu.setCurrentText(selected_profile["baudrate"])
            self.freq_menu.setCurrentText(selected_profile["freq"])
            self.sizes_menu.setCurrentText(selected_profile["size"])

            QMessageBox.information(self, "Load Profile",
                                    f"Profile Loaded Successfully:\n\nChip Name: {profile_name}")
            
            print("Loaded Profile:")
            print("Chip Name:", selected_profile["chip_name"])
            print("Mode:", selected_profile["mode"])
            print("Baudrate:", selected_profile["baudrate"])            
            print("Files:", selected_profile["files"])
            print("Addresses:", selected_profile["addresses"])
        else:
            QMessageBox.critical(self, "Load Profile", "Profile not found.")

    def run_subprocess(self, command):
        # Start the subprocess and run asynchronously
        self.subprocess.start(command[0], command[1:])

    def update_terminal(self):
        # Read available data from the subprocess
        output = self.subprocess.readAllStandardOutput().data().decode()
        self.terminal_window_cursor.movePosition(self.terminal_window_cursor.MoveOperation.End, self.terminal_window_cursor.MoveMode.MoveAnchor,1)
        self.terminal_window.insertPlainText(output)
        self.terminal_window.verticalScrollBar().setValue(self.terminal_window.verticalScrollBar().maximum())

    def update_ui(self):
        # Allow PySide6 to process events
        QApplication.processEvents()

if __name__ == "__main__":
    app = QApplication([])
    window = FlashToolApp()
    window.show()
    app.exec()
