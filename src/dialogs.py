from __future__ import annotations

import shlex
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore, QtWidgets

from models import (
    LAUNCH_TYPE_JAVA,
    LAUNCH_TYPE_PLAYIT,
    AppSettings,
    SavedCommand,
    ServerConfig,
)



class ServerEditDialog(QtWidgets.QDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, config: Optional[ServerConfig] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Server" if config else "Add Server")
        self.resize(520, 370)
        self._config = config
        self._launch_type = config.launch_type if config else LAUNCH_TYPE_JAVA
        self.result_config: Optional[ServerConfig] = None

        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.type_notice = QtWidgets.QLabel()
        self._update_type_notice()
        form.addRow("Type", self.type_notice)

        self.name_edit = QtWidgets.QLineEdit()
        form.addRow("Display name", self.name_edit)

        self.jar_edit = QtWidgets.QLineEdit()
        self.browse_jar = QtWidgets.QPushButton("Browse...")
        self.browse_jar.clicked.connect(self._browse_jar)
        self.jar_label = QtWidgets.QLabel("Server jar")
        self.jar_row_widget = QtWidgets.QWidget()
        jar_row = QtWidgets.QHBoxLayout(self.jar_row_widget)
        jar_row.setContentsMargins(0, 0, 0, 0)
        jar_row.addWidget(self.jar_edit)
        jar_row.addWidget(self.browse_jar)
        form.addRow(self.jar_label, self.jar_row_widget)

        self.min_spin = QtWidgets.QSpinBox()
        self.min_spin.setRange(128, 65536)
        self.min_spin.setSingleStep(128)
        self.max_spin = QtWidgets.QSpinBox()
        self.max_spin.setRange(128, 65536)
        self.max_spin.setSingleStep(128)
        self.memory_label = QtWidgets.QLabel("Memory")
        self.memory_row_widget = QtWidgets.QWidget()
        mem_row = QtWidgets.QHBoxLayout(self.memory_row_widget)
        mem_row.setContentsMargins(0, 0, 0, 0)
        mem_row.addWidget(QtWidgets.QLabel("Min (MB)"))
        mem_row.addWidget(self.min_spin)
        mem_row.addSpacing(12)
        mem_row.addWidget(QtWidgets.QLabel("Max (MB)"))
        mem_row.addWidget(self.max_spin)
        form.addRow(self.memory_label, self.memory_row_widget)

        self.gui_check = QtWidgets.QCheckBox("Keep Minecraft GUI window (disable nogui)")
        self.gui_label = QtWidgets.QLabel("Minecraft GUI")
        form.addRow(self.gui_label, self.gui_check)

        self.jvm_args_edit = QtWidgets.QLineEdit()
        self.jvm_label = QtWidgets.QLabel("JVM arguments")
        form.addRow(self.jvm_label, self.jvm_args_edit)

        self.java_path_edit = QtWidgets.QLineEdit()
        self.browse_java = QtWidgets.QPushButton("Browse...")
        self.browse_java.clicked.connect(self._browse_java)
        self.java_label = QtWidgets.QLabel("Java executable")
        self.java_row_widget = QtWidgets.QWidget()
        java_row = QtWidgets.QHBoxLayout(self.java_row_widget)
        java_row.setContentsMargins(0, 0, 0, 0)
        java_row.addWidget(self.java_path_edit)
        java_row.addWidget(self.browse_java)
        form.addRow(self.java_label, self.java_row_widget)

        self.program_args_edit = QtWidgets.QLineEdit()
        self.program_label = QtWidgets.QLabel("Server arguments")
        form.addRow(self.program_label, self.program_args_edit)

        self.playit_hide_check = QtWidgets.QCheckBox("Hide console window when launching")
        self.playit_hide_label = QtWidgets.QLabel("Hide console window")
        form.addRow(self.playit_hide_label, self.playit_hide_check)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(button_box)

        if config:
            self._load_config(config)
        else:
            self.min_spin.setValue(512)
            self.max_spin.setValue(1024)
            self.playit_hide_check.setChecked(True)
        self._update_field_states()

    def _set_row_visible(self, label: QtWidgets.QWidget, widget: QtWidgets.QWidget, visible: bool) -> None:
        label.setVisible(visible)
        widget.setVisible(visible)

    def _update_type_notice(self) -> None:
        if self._launch_type == LAUNCH_TYPE_JAVA:
            self.type_notice.setText("Minecraft / Velocity (Java)")
        elif self._launch_type == LAUNCH_TYPE_PLAYIT:
            self.type_notice.setText("Playit agent")
        else:
            self.type_notice.setText(self._launch_type.title())

    def _update_field_states(self) -> None:
        is_java = self._launch_type == LAUNCH_TYPE_JAVA
        self.jar_label.setText("Server jar" if is_java else "Executable")
        if is_java:
            self.jar_edit.setPlaceholderText("")
        else:
            self.jar_edit.setPlaceholderText("C:/Program Files/playit_gg/bin/playit.exe")

        self._set_row_visible(self.memory_label, self.memory_row_widget, is_java)
        self._set_row_visible(self.gui_label, self.gui_check, is_java)
        self._set_row_visible(self.jvm_label, self.jvm_args_edit, is_java)
        self._set_row_visible(self.java_label, self.java_row_widget, is_java)

        self.program_label.setText("Server arguments" if is_java else "Agent arguments")
        self.program_args_edit.setPlaceholderText("" if is_java else "Optional parameters to pass to playit.exe")

        self._set_row_visible(self.playit_hide_label, self.playit_hide_check, not is_java)
        self.playit_hide_check.setEnabled(not is_java)

        self.min_spin.setEnabled(is_java)
        self.max_spin.setEnabled(is_java)
        self.gui_check.setEnabled(is_java)
        self.jvm_args_edit.setEnabled(is_java)
        self.java_path_edit.setEnabled(is_java)
        self.browse_java.setEnabled(is_java)

    def _load_config(self, config: ServerConfig) -> None:
        self.name_edit.setText(config.name)
        if config.launch_type == LAUNCH_TYPE_JAVA:
            self.jar_edit.setText(config.jar_path)
            self.min_spin.setValue(max(config.min_ram, self.min_spin.minimum()))
            self.max_spin.setValue(max(config.max_ram, self.max_spin.minimum()))
            self.gui_check.setChecked(config.use_minecraft_gui)
            self.jvm_args_edit.setText(" ".join(config.jvm_args))
            self.program_args_edit.setText(" ".join(config.program_args))
            if config.java_path:
                self.java_path_edit.setText(config.java_path)
        else:
            self.jar_edit.setText(config.custom_executable or config.jar_path)
            self.program_args_edit.setText(" ".join(config.program_args))
            self.playit_hide_check.setChecked(config.hide_console)
        self._update_type_notice()

    def _browse_jar(self) -> None:
        if self._launch_type == LAUNCH_TYPE_JAVA:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select server jar", str(Path.home()), "Java Archives (*.jar);;All files (*)")
        else:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select playit executable", str(Path.home()), "Executables (*.exe);;All files (*)")
        if filename:
            self.jar_edit.setText(filename)

    def _browse_java(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Java executable", str(Path.home()))
        if filename:
            self.java_path_edit.setText(filename)

    def _accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Missing name", "Please provide a display name.")
            return

        launch_type = self._launch_type
        if launch_type == LAUNCH_TYPE_JAVA:
            jar_path = self.jar_edit.text().strip()
            if not jar_path:
                QtWidgets.QMessageBox.warning(self, "Missing jar", "Please provide the server jar path.")
                return
            if self.min_spin.value() > self.max_spin.value():
                QtWidgets.QMessageBox.warning(self, "Memory range", "Minimum memory cannot exceed maximum memory.")
                return
            min_ram = self.min_spin.value()
            max_ram = self.max_spin.value()
            use_gui = self.gui_check.isChecked()
            java_path = self.java_path_edit.text().strip() or None
            jvm_args = self._split_args(self.jvm_args_edit.text())
            program_args = self._split_args(self.program_args_edit.text())
            custom_executable = self._config.custom_executable if self._config else None
            hide_console = self._config.hide_console if self._config else False
        else:
            executable = self.jar_edit.text().strip()
            if not executable:
                QtWidgets.QMessageBox.warning(self, "Missing executable", "Please provide the playit executable path.")
                return
            jar_path = ""
            min_ram = 0
            max_ram = 0
            use_gui = False
            java_path = None
            jvm_args: List[str] = []
            program_args = self._split_args(self.program_args_edit.text())
            custom_executable = executable
            hide_console = self.playit_hide_check.isChecked()

        base = self._config or ServerConfig(
            id=QtCore.QUuid.createUuid().toString().strip("{}"),
            name=name,
            jar_path=jar_path,
        )
        config = ServerConfig(
            id=base.id,
            name=name,
            jar_path=jar_path,
            min_ram=min_ram,
            max_ram=max_ram,
            use_minecraft_gui=use_gui,
            java_path=java_path,
            jvm_args=jvm_args,
            program_args=program_args,
            launch_type=launch_type,
            custom_executable=custom_executable,
            hide_console=hide_console,
        )
        self.result_config = config
        self.accept()

    @staticmethod
    def _split_args(text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except ValueError:
            return text.split()
class SavedCommandDialog(QtWidgets.QDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, command: Optional[SavedCommand] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Command" if command else "Add Command")
        self.result_command: Optional[SavedCommand] = None
        self._command = command

        form = QtWidgets.QFormLayout()
        self.label_edit = QtWidgets.QLineEdit()
        self.command_edit = QtWidgets.QLineEdit()
        self.category_edit = QtWidgets.QLineEdit()
        self.category_edit.setPlaceholderText("Optional, use / to create sub-categories")
        form.addRow("Label", self.label_edit)
        form.addRow("Command", self.command_edit)
        form.addRow("Category", self.category_edit)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if command:
            self.label_edit.setText(command.label)
            self.command_edit.setText(command.command)
            self.category_edit.setText(command.category)

    def _accept(self) -> None:
        label = self.label_edit.text().strip()
        command_text = self.command_edit.text().strip()
        category = self.category_edit.text().strip()
        if not label or not command_text:
            QtWidgets.QMessageBox.warning(self, "Missing data", "Label and command are required.")
            return
        if self._command:
            command_id = self._command.id
            order = self._command.order
        else:
            command_id = QtCore.QUuid.createUuid().toString().strip("{}")
            order = 0
        self.result_command = SavedCommand(id=command_id, label=label, command=command_text, category=category, order=order)
        self.accept()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, settings: Optional[AppSettings] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.result_settings: Optional[AppSettings] = None
        self._settings = settings or AppSettings()

        form = QtWidgets.QFormLayout()

        self.playit_path_edit = QtWidgets.QLineEdit(self._settings.playit_path)
        browse_playit = QtWidgets.QPushButton("Browse...")
        browse_playit.clicked.connect(self._browse_playit)
        playit_row = QtWidgets.QHBoxLayout()
        playit_row.addWidget(self.playit_path_edit)
        playit_row.addWidget(browse_playit)

        self.playit_args_edit = QtWidgets.QLineEdit(" ".join(self._settings.playit_args))
        self.auto_launch_check = QtWidgets.QCheckBox("Launch Playit agent automatically on startup")
        self.auto_launch_check.setChecked(self._settings.auto_launch_playit)
        self.hide_console_check = QtWidgets.QCheckBox("Hide Windows console windows when possible")
        self.hide_console_check.setChecked(self._settings.hide_console_windows)

        form.addRow("Playit agent", playit_row)
        form.addRow("Playit arguments", self.playit_args_edit)
        form.addRow(self.auto_launch_check)
        form.addRow(self.hide_console_check)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse_playit(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select playit.exe", str(Path.home()), "Executables (*.exe);;All files (*)")
        if filename:
            self.playit_path_edit.setText(filename)

    def _accept(self) -> None:
        playit_path = self.playit_path_edit.text().strip()
        if not playit_path:
            QtWidgets.QMessageBox.warning(self, "Playit path", "Please provide the Playit agent path.")
            return
        args = self._split_args(self.playit_args_edit.text())
        settings = AppSettings(
            playit_path=playit_path,
            playit_args=args,
            auto_launch_playit=self.auto_launch_check.isChecked(),
            hide_console_windows=self.hide_console_check.isChecked(),
        )
        self.result_settings = settings
        self.accept()

    @staticmethod
    def _split_args(text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except ValueError:
            return text.split()


