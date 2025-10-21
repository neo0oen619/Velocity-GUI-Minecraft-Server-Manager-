from __future__ import annotations

import datetime
import os
import re
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

from controller import AppController
from dialogs import SavedCommandDialog, ServerEditDialog, SettingsDialog
from models import LAUNCH_TYPE_JAVA, LAUNCH_TYPE_PLAYIT, SavedCommand, ServerConfig
from server_table_model import ServerTableModel


def format_duration(delta: Optional[datetime.timedelta]) -> str:
    if not delta:
        return "--"
    total_seconds = max(0, int(delta.total_seconds()))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"



class ServersTab(QtWidgets.QWidget):
    def __init__(self, controller: AppController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.selected_server_id: Optional[str] = None

        layout = QtWidgets.QVBoxLayout(self)

        self.model = ServerTableModel(controller)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for column in range(2, self.model.columnCount()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)

        button_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add")
        self.edit_button = QtWidgets.QPushButton("Edit")
        self.duplicate_button = QtWidgets.QPushButton("Duplicate")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.move_up_button = QtWidgets.QPushButton("Move Up")
        self.move_down_button = QtWidgets.QPushButton("Move Down")
        for button in (
            self.add_button,
            self.edit_button,
            self.duplicate_button,
            self.remove_button,
            self.move_up_button,
            self.move_down_button,
        ):
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        actions_row = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.force_stop_button = QtWidgets.QPushButton("Force Stop")
        self.properties_button = QtWidgets.QPushButton("Open server.properties")
        self.whitelist_button = QtWidgets.QPushButton("Open whitelist.json")
        self.folder_button = QtWidgets.QPushButton("Open folder")
        for button in (
            self.start_button,
            self.stop_button,
            self.force_stop_button,
            self.properties_button,
            self.whitelist_button,
            self.folder_button,
        ):
            actions_row.addWidget(button)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        details_group = QtWidgets.QGroupBox("Selected server")
        details_layout = QtWidgets.QGridLayout(details_group)
        self.type_label = QtWidgets.QLabel("Type: --")
        self.status_label = QtWidgets.QLabel("Status: --")
        self.pid_label = QtWidgets.QLabel("PID: --")
        self.uptime_label = QtWidgets.QLabel("Uptime: --")
        self.memory_label = QtWidgets.QLabel("Memory: --")
        self.jar_label = QtWidgets.QLabel("Path: --")
        self.java_label = QtWidgets.QLabel("Runtime: --")
        details_layout.addWidget(self.type_label, 0, 0, 1, 3)
        details_layout.addWidget(self.status_label, 1, 0)
        details_layout.addWidget(self.pid_label, 1, 1)
        details_layout.addWidget(self.uptime_label, 1, 2)
        details_layout.addWidget(self.memory_label, 2, 0)
        details_layout.addWidget(self.jar_label, 3, 0, 1, 3)
        details_layout.addWidget(self.java_label, 4, 0, 1, 3)
        self.exit_label = QtWidgets.QLabel("Last exit: --")
        details_layout.addWidget(self.exit_label, 5, 0, 1, 3)
        layout.addWidget(details_group)

        self.uptime_timer = QtCore.QTimer(self)
        self.uptime_timer.setInterval(1000)
        self.uptime_timer.timeout.connect(self._refresh_uptime)
        self.uptime_timer.start()

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.add_button.clicked.connect(self._add_server)
        self.edit_button.clicked.connect(self._edit_server)
        self.duplicate_button.clicked.connect(self._duplicate_server)
        self.remove_button.clicked.connect(self._remove_server)
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))
        self.start_button.clicked.connect(self._start_selected)
        self.stop_button.clicked.connect(lambda: self._stop_selected(force=False))
        self.force_stop_button.clicked.connect(lambda: self._stop_selected(force=True))
        self.properties_button.clicked.connect(lambda: self._open_server_file("server.properties"))
        self.whitelist_button.clicked.connect(lambda: self._open_server_file("whitelist.json"))
        self.folder_button.clicked.connect(self._open_folder)

        self.controller.servers_changed.connect(self._refresh_selection)
        self.controller.server_status_changed.connect(self._handle_status_update)

        QtCore.QTimer.singleShot(0, self._refresh_selection)

    def select_server(self, server_id: str) -> None:
        self.selected_server_id = server_id
        model = self.table.model()
        selection_model = self.table.selectionModel()
        servers = self.controller.list_servers()
        for row, server in enumerate(servers):
            if server.id == server_id:
                index = model.index(row, 0)
                if selection_model:
                    selection_model.setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)
                self.table.scrollTo(index)
                break
        self._update_details()

    def _current_server(self) -> Optional[ServerConfig]:
        if self.selected_server_id:
            return self.controller.get_server(self.selected_server_id)
        return None

    def _current_row_index(self) -> Optional[int]:
        if not self.selected_server_id:
            return None
        for index, server in enumerate(self.controller.list_servers()):
            if server.id == self.selected_server_id:
                return index
        return None

    def _refresh_selection(self) -> None:
        selection_model = self.table.selectionModel()
        if not selection_model:
            return
        if not selection_model.hasSelection() and self.model.rowCount() > 0:
            index = self.model.index(0, 0)
            selection_model.select(index, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
            self.table.scrollTo(index)
            servers = self.controller.list_servers()
            if servers:
                self.selected_server_id = servers[0].id
        self._update_details()

    def _on_selection_changed(self, *_args) -> None:
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            servers = self.controller.list_servers()
            if row < len(servers):
                self.selected_server_id = servers[row].id
        else:
            self.selected_server_id = None
        self._update_details()

    def _update_details(self) -> None:
        server = self._current_server()
        if not server:
            self.type_label.setText("Type: --")
            self.status_label.setText("Status: --")
            self.pid_label.setText("PID: --")
            self.uptime_label.setText("Uptime: --")
            self.memory_label.setText("Memory: --")
            self.jar_label.setText("Path: --")
            self.java_label.setText("Runtime: --")
            self.exit_label.setText("Last exit: --")
            for button in (
                self.start_button,
                self.stop_button,
                self.force_stop_button,
                self.properties_button,
                self.whitelist_button,
                self.folder_button,
                self.duplicate_button,
                self.remove_button,
                self.move_up_button,
                self.move_down_button,
            ):
                button.setEnabled(False)
            return

        launch_type = server.launch_type
        type_text = "Minecraft / Velocity" if launch_type == LAUNCH_TYPE_JAVA else "External process"
        self.type_label.setText(f"Type: {type_text}")
        status = self.controller.server_status(server.id)
        details = self.controller.server_details(server.id)
        pid = details.get("pid") or "--"
        self.status_label.setText(f"Status: {status}")
        self.pid_label.setText(f"PID: {pid}")
        uptime = self.controller.server_uptime(server.id)
        self.uptime_label.setText(f"Uptime: {format_duration(uptime)}")
        self.memory_label.setText(f"Memory: {server.display_memory}")
        self.jar_label.setText(f"Path: {server.primary_path or '--'}")
        if launch_type == LAUNCH_TYPE_JAVA:
            runtime_label = server.java_path or "java"
        else:
            runtime_label = "Playit agent" if launch_type == LAUNCH_TYPE_PLAYIT else "External"
        self.java_label.setText(f"Runtime: {runtime_label}")

        exit_code = details.get("exit_code")
        exit_name = details.get("exit_status_name")
        error_name = details.get("process_error_name")
        error_code = details.get("process_error")
        exit_text = "--"
        if error_name:
            exit_text = f"Error: {error_name}"
            if error_code not in (None, 0):
                exit_text += f" ({error_code})"
        elif exit_name or exit_code is not None:
            if exit_code not in (None, 0):
                exit_text = f"{exit_name or 'Exit code'} ({exit_code})"
            elif exit_name:
                exit_text = str(exit_name)
            else:
                exit_text = str(exit_code)
        self.exit_label.setText(f"Last exit: {exit_text}")

        allow_files = launch_type == LAUNCH_TYPE_JAVA
        has_path = bool(server.primary_path)
        self.properties_button.setEnabled(allow_files)
        self.whitelist_button.setEnabled(allow_files)
        self.folder_button.setEnabled(has_path)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.force_stop_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        self.duplicate_button.setEnabled(launch_type == LAUNCH_TYPE_JAVA)
        row_index = self._current_row_index()
        total = len(self.controller.list_servers())
        self.move_up_button.setEnabled(row_index is not None and row_index > 0)
        self.move_down_button.setEnabled(row_index is not None and row_index < total - 1)

    def _refresh_uptime(self) -> None:
        server = self._current_server()
        if not server:
            self.uptime_label.setText("Uptime: --")
            return
        uptime = self.controller.server_uptime(server.id)
        self.uptime_label.setText(f"Uptime: {format_duration(uptime)}")

    def _add_server(self) -> None:
        dialog = ServerEditDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted and dialog.result_config:
            self.controller.add_server(dialog.result_config)
            self.select_server(dialog.result_config.id)

    def _edit_server(self) -> None:
        server = self._current_server()
        if not server:
            return
        if server.launch_type != LAUNCH_TYPE_JAVA:
            new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename entry", "Display name:", text=server.name)
            if ok and new_name.strip():
                updated = ServerConfig(
                    id=server.id,
                    name=new_name.strip(),
                    jar_path=server.jar_path,
                    min_ram=server.min_ram,
                    max_ram=server.max_ram,
                    use_minecraft_gui=server.use_minecraft_gui,
                    java_path=server.java_path,
                    jvm_args=list(server.jvm_args),
                    program_args=list(server.program_args),
                    launch_type=server.launch_type,
                    custom_executable=server.custom_executable,
                    hide_console=server.hide_console,
                )
                self.controller.update_server(updated)
            return
        dialog = ServerEditDialog(self, config=server)
        if dialog.exec() == QtWidgets.QDialog.Accepted and dialog.result_config:
            self.controller.update_server(dialog.result_config)
            self.select_server(dialog.result_config.id)

    def _duplicate_server(self) -> None:
        server = self._current_server()
        if not server or server.launch_type != LAUNCH_TYPE_JAVA:
            QtWidgets.QMessageBox.information(self, "Duplicate", "Only Java-based entries can be duplicated.")
            return
        clone = self.controller.duplicate_server(server.id)
        self.select_server(clone.id)

    def _remove_server(self) -> None:
        server = self._current_server()
        if not server:
            return
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Remove server",
            f"Are you sure you want to remove '{server.name}'? This will not delete any files.",
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            self.controller.remove_server(server.id)
            self.selected_server_id = None
            self._refresh_selection()

    def _move_selected(self, offset: int) -> None:
        server = self._current_server()
        if not server:
            return
        try:
            moved = self.controller.move_server(server.id, offset)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Reorder servers", str(exc))
            return
        if moved:
            QtCore.QTimer.singleShot(0, lambda: self.select_server(server.id))

    def _start_selected(self) -> None:
        server = self._current_server()
        if not server:
            return
        try:
            self.controller.start_server(server.id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Unable to start", str(exc))

    def _stop_selected(self, force: bool) -> None:
        server = self._current_server()
        if not server:
            return
        if force:
            self.controller.stop_server(server.id, force=True)
        else:
            self.controller.stop_server(server.id, force=False)

    def _open_server_file(self, filename: str) -> None:
        server = self._current_server()
        if not server or server.launch_type != LAUNCH_TYPE_JAVA:
            QtWidgets.QMessageBox.information(self, "Not available", "This entry does not expose Minecraft files.")
            return
        folder = Path(server.jar_path).resolve().parent
        path = folder / filename
        if not path.exists():
            try:
                path.touch(exist_ok=True)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Unable to create file", str(exc))
                return
        self._open_path(path)

    def _open_folder(self) -> None:
        server = self._current_server()
        if not server:
            return
        path = server.primary_path
        if not path:
            QtWidgets.QMessageBox.information(self, "Missing path", "No path is associated with this entry yet.")
            return
        folder = Path(path).resolve().parent
        self._open_path(folder)

    def _open_path(self, path: Path) -> None:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except AttributeError:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))

    def _handle_status_update(self, server_id: str, _status: str, _details: dict) -> None:
        if self.selected_server_id == server_id:
            self._update_details()
            self._refresh_uptime()



class SavedCommandsTreeWidget(QtWidgets.QTreeWidget):
    commandsReordered = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        super().dropEvent(event)
        self.commandsReordered.emit()


class ConsoleTab(QtWidgets.QWidget):
    def __init__(self, controller: AppController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.current_server_id: Optional[str] = None
        self._is_paused = False
        self._paused_buffer: List[str] = []
        self._paused_snapshot = ''
        self._current_console_supports = False
        self.auto_scroll_enabled = True
        self._log_filter_text = ''

        layout = QtWidgets.QVBoxLayout(self)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel('Server:'))
        self.server_combo = QtWidgets.QComboBox()
        top_row.addWidget(self.server_combo, 1)
        self.status_label = QtWidgets.QLabel('Status: --')
        self.pid_label = QtWidgets.QLabel('PID: --')
        top_row.addWidget(self.status_label)
        top_row.addWidget(self.pid_label)
        layout.addLayout(top_row)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)

        self.output_edit = QtWidgets.QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        left_layout.addWidget(self.output_edit, 1)

        log_controls = QtWidgets.QHBoxLayout()
        log_controls.addWidget(QtWidgets.QLabel('Filter:'))
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText('Type to filter log...')
        self.search_input.textChanged.connect(self._apply_log_filter)
        log_controls.addWidget(self.search_input, 1)
        self.search_clear_button = QtWidgets.QPushButton('Clear filter')
        self.search_clear_button.clicked.connect(self._reset_log_filter)
        log_controls.addWidget(self.search_clear_button)
        self.filter_status = QtWidgets.QLabel('')
        self.filter_status.setMinimumWidth(120)
        self.filter_status.setStyleSheet('color: #888;')
        log_controls.addWidget(self.filter_status)
        log_controls.addStretch(1)
        self.auto_scroll_check = QtWidgets.QCheckBox('Auto-scroll')
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._set_auto_scroll_enabled)
        log_controls.addWidget(self.auto_scroll_check)
        left_layout.addLayout(log_controls)

        command_row = QtWidgets.QHBoxLayout()
        self.command_input = QtWidgets.QLineEdit()
        self.command_input.setPlaceholderText('Type a command and press Enter')
        self.send_button = QtWidgets.QPushButton('Send')
        self.save_log_button = QtWidgets.QPushButton('Save Log')
        self.save_log_button.setToolTip('Save the current console output to a log file')
        self.pause_button = QtWidgets.QPushButton('Pause')
        self.pause_button.setToolTip('Temporarily stop console updates')
        self.clear_button = QtWidgets.QPushButton('Clear')
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.send_button)
        command_row.addWidget(self.save_log_button)
        command_row.addWidget(self.pause_button)
        command_row.addWidget(self.clear_button)
        left_layout.addLayout(command_row)
        self.save_log_button.setEnabled(False)
        self.pause_button.setEnabled(False)

        splitter.addWidget(left_panel)

        right_panel = QtWidgets.QGroupBox('Saved commands')
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        self.saved_tree = SavedCommandsTreeWidget()
        self.saved_tree.setColumnCount(1)
        self.saved_tree.setHeaderHidden(True)
        self.saved_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.saved_tree.setUniformRowHeights(True)
        self.saved_tree.setIndentation(18)
        right_layout.addWidget(self.saved_tree, 1)

        saved_buttons = QtWidgets.QHBoxLayout()
        self.saved_add = QtWidgets.QPushButton('Add')
        self.saved_edit = QtWidgets.QPushButton('Edit')
        self.saved_remove = QtWidgets.QPushButton('Remove')
        self.saved_copy = QtWidgets.QPushButton('Copy')
        self.saved_send = QtWidgets.QPushButton('Send')
        saved_buttons.addWidget(self.saved_add)
        saved_buttons.addWidget(self.saved_edit)
        saved_buttons.addWidget(self.saved_remove)
        saved_buttons.addWidget(self.saved_copy)
        saved_buttons.addWidget(self.saved_send)
        right_layout.addLayout(saved_buttons)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.server_combo.currentIndexChanged.connect(self._on_server_selected)
        self.send_button.clicked.connect(self._send_command)
        self.command_input.returnPressed.connect(self._send_command)
        self.clear_button.clicked.connect(self._clear_output)
        self.save_log_button.clicked.connect(self._save_log)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.saved_add.clicked.connect(self._add_saved_command)
        self.saved_edit.clicked.connect(self._edit_saved_command)
        self.saved_remove.clicked.connect(self._remove_saved_command)
        self.saved_copy.clicked.connect(self._copy_selected_saved_command)
        self.saved_send.clicked.connect(self._send_selected_saved_command)
        self.saved_tree.itemDoubleClicked.connect(self._handle_saved_item_activated)
        self.saved_tree.itemActivated.connect(self._handle_saved_item_activated)
        self.saved_tree.itemSelectionChanged.connect(self._update_saved_buttons)
        self.saved_tree.commandsReordered.connect(self._commit_saved_tree_changes)

        self.controller.servers_changed.connect(self._reload_servers)
        self.controller.server_status_changed.connect(self._handle_status_changed)
        self.controller.server_output.connect(self._handle_server_output)
        self.controller.saved_commands_changed.connect(self._reload_saved_commands)

        self._update_saved_buttons()
        QtCore.QTimer.singleShot(0, self._reload_servers)
        QtCore.QTimer.singleShot(0, self._reload_saved_commands)

    def _reload_servers(self) -> None:
        servers = self.controller.list_servers()
        current_id = self.current_server_id
        self.server_combo.blockSignals(True)
        self.server_combo.clear()
        for server in servers:
            self.server_combo.addItem(server.name, server.id)
        self.server_combo.blockSignals(False)
        target_index = 0
        if current_id:
            for idx in range(self.server_combo.count()):
                if self.server_combo.itemData(idx) == current_id:
                    target_index = idx
                    break
        if self.server_combo.count() > 0:
            self.server_combo.setCurrentIndex(target_index)
            self._refresh_console(force=True)
        else:
            self.current_server_id = None
            self._set_paused(False, refresh=False)
            self._paused_buffer.clear()
            self._paused_snapshot = ''
            self.output_edit.clear()
            self.status_label.setText('Status: --')
            self.pid_label.setText('PID: --')
            self._update_filter_status(0, 0)
            self._update_command_controls()

    def _on_server_selected(self, index: int) -> None:
        if index < 0:
            self.current_server_id = None
            self._set_paused(False, refresh=False)
            self._paused_buffer.clear()
            self._paused_snapshot = ''
            self.output_edit.clear()
            self.status_label.setText('Status: --')
            self.pid_label.setText('PID: --')
            self._update_filter_status(0, 0)
            self._update_command_controls()
            return
        server_id = self.server_combo.itemData(index)
        self.current_server_id = server_id
        self._paused_buffer.clear()
        self._paused_snapshot = ''
        self._set_paused(False, refresh=False)
        self._refresh_console(force=True)

    def _refresh_console(self, force: bool = False) -> None:
        if not self.current_server_id:
            self.output_edit.clear()
            self.status_label.setText('Status: --')
            self.pid_label.setText('PID: --')
            self._update_filter_status(0, 0)
            self._update_command_controls()
            return
        status = self.controller.server_status(self.current_server_id)
        details = self.controller.server_details(self.current_server_id)
        pid = details.get('pid') or '--'
        self.status_label.setText(f'Status: {status}')
        self.pid_label.setText(f'PID: {pid}')
        self._update_command_controls()
        if self._is_paused and not force:
            return
        log_text = self.controller.server_log_text(self.current_server_id)
        filtered_text, match_count, total_lines = self._filter_log_text(log_text)
        scrollbar = self.output_edit.verticalScrollBar()
        prev_value = scrollbar.value()
        prev_max = scrollbar.maximum()
        step = max(1, scrollbar.singleStep())
        was_at_bottom = prev_max - prev_value <= step
        self.output_edit.setPlainText(filtered_text)
        new_max = scrollbar.maximum()
        if self._is_paused:
            self._paused_snapshot = log_text
            scrollbar.setValue(min(prev_value, new_max))
        else:
            if self.auto_scroll_enabled and was_at_bottom:
                scrollbar.setValue(new_max)
            else:
                scrollbar.setValue(min(prev_value, new_max))
            self._paused_snapshot = ''
        self._update_filter_status(match_count, total_lines)

    def _update_command_controls(self) -> None:
        server = self.controller.get_server(self.current_server_id) if self.current_server_id else None
        supports_console = bool(server and server.supports_console)
        placeholder = 'Type a command and press Enter' if supports_console else 'Console commands not supported for this entry'
        self.command_input.setPlaceholderText(placeholder)
        self.command_input.setEnabled(supports_console)
        self.send_button.setEnabled(supports_console)
        self._current_console_supports = supports_console
        has_server = bool(self.current_server_id)
        self.save_log_button.setEnabled(has_server)
        self.pause_button.setEnabled(has_server)
        self.auto_scroll_check.setEnabled(has_server)
        if not has_server:
            self._set_paused(False, refresh=False)
        self._update_saved_buttons()

    def _send_command(self) -> None:
        if not self.current_server_id:
            return
        server = self.controller.get_server(self.current_server_id)
        if not server or not server.supports_console:
            QtWidgets.QMessageBox.information(self, 'Not supported', 'This entry does not accept console commands.')
            return
        command = self.command_input.text().strip()
        if not command:
            return
        try:
            self.controller.send_command(self.current_server_id, command)
            self.command_input.clear()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'Unable to send', str(exc))

    def _clear_output(self) -> None:
        if self.current_server_id:
            self.controller.clear_server_log(self.current_server_id)
        self._set_paused(False, refresh=False)
        self.output_edit.clear()
        self._update_filter_status(0, 0)

    def _handle_status_changed(self, server_id: str, _status: str, _details: dict) -> None:
        if server_id == self.current_server_id:
            self._refresh_console()

    def _handle_server_output(self, server_id: str, text: str) -> None:
        if server_id != self.current_server_id:
            return
        if self._is_paused:
            self._paused_buffer.append(text)
            return
        if self._log_filter_text:
            self._refresh_console(force=True)
            return
        scrollbar = self.output_edit.verticalScrollBar()
        prev_value = scrollbar.value()
        prev_max = scrollbar.maximum()
        step = max(1, scrollbar.singleStep())
        was_at_bottom = prev_max - prev_value <= step
        cursor = self.output_edit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        new_max = scrollbar.maximum()
        if self.auto_scroll_enabled and was_at_bottom:
            scrollbar.setValue(new_max)
        else:
            scrollbar.setValue(min(prev_value, new_max))
        self._update_filter_status(0, self.output_edit.blockCount())

    def _reload_saved_commands(self) -> None:
        commands = self.controller.list_saved_commands()
        self.saved_tree.blockSignals(True)
        self.saved_tree.clear()
        category_nodes: Dict[Tuple[str, ...], QtWidgets.QTreeWidgetItem] = {}
        match_counts: Dict[Tuple[str, ...], int] = {}
        root = self.saved_tree.invisibleRootItem()
        for command in commands:
            path_tuple = tuple(self._split_category(command.category))
            parent = root
            current_path: Tuple[str, ...] = tuple()
            for segment in path_tuple:
                current_path = current_path + (segment,)
                node = category_nodes.get(current_path)
                if node is None:
                    node = QtWidgets.QTreeWidgetItem([segment])
                    node.setData(0, QtCore.Qt.UserRole, None)
                    node.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)
                    parent.addChild(node)
                    category_nodes[current_path] = node
                    match_counts[current_path] = 0
                parent = node
            index = match_counts.get(path_tuple, 0)
            match_counts[path_tuple] = index + 1
            display = f"{index + 1}. {command.label}"
            item = QtWidgets.QTreeWidgetItem([display])
            item.setData(0, QtCore.Qt.UserRole, command.id)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)
            item.setToolTip(0, command.command)
            parent.addChild(item)
        self.saved_tree.expandToDepth(0)
        self.saved_tree.blockSignals(False)
        self._update_saved_buttons()

    def _add_saved_command(self) -> None:
        dialog = SavedCommandDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted and dialog.result_command:
            self.controller.add_saved_command(dialog.result_command)

    def _edit_saved_command(self) -> None:
        command = self._selected_saved_command()
        if not command:
            return
        dialog = SavedCommandDialog(self, command=command)
        if dialog.exec() == QtWidgets.QDialog.Accepted and dialog.result_command:
            self.controller.update_saved_command(dialog.result_command)

    def _remove_saved_command(self) -> None:
        command = self._selected_saved_command()
        if not command:
            return
        confirm = QtWidgets.QMessageBox.question(self, 'Remove command', f"Remove saved command '{command.label}'?")
        if confirm == QtWidgets.QMessageBox.Yes:
            self.controller.remove_saved_command(command.id)

    def _send_selected_saved_command(self) -> None:
        if not self.current_server_id:
            return
        server = self.controller.get_server(self.current_server_id)
        if not server or not server.supports_console:
            QtWidgets.QMessageBox.information(self, 'Not supported', 'This entry does not accept console commands.')
            return
        command = self._selected_saved_command()
        if not command:
            return
        try:
            self.controller.send_command(self.current_server_id, command.command)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'Unable to send', str(exc))

    def _selected_saved_command(self) -> Optional[SavedCommand]:
        items = self.saved_tree.selectedItems()
        if not items:
            return None
        command_id = items[0].data(0, QtCore.Qt.UserRole)
        if not command_id:
            return None
        for cmd in self.controller.list_saved_commands():
            if cmd.id == command_id:
                return cmd
        return None

    def _update_saved_buttons(self) -> None:
        has_command = self._selected_saved_command() is not None
        self.saved_edit.setEnabled(has_command)
        self.saved_remove.setEnabled(has_command)
        self.saved_copy.setEnabled(has_command)
        self.saved_send.setEnabled(has_command and self._current_console_supports)

    def _handle_saved_item_activated(self, item: QtWidgets.QTreeWidgetItem, _column: int) -> None:
        if item.data(0, QtCore.Qt.UserRole):
            self._send_selected_saved_command()

    def _copy_selected_saved_command(self) -> None:
        command = self._selected_saved_command()
        if not command:
            return
        QtWidgets.QApplication.clipboard().setText(command.command)

    def _toggle_pause(self) -> None:
        if not self.current_server_id:
            return
        self._set_paused(not self._is_paused)

    def _set_paused(self, paused: bool, refresh: bool = True) -> None:
        if self._is_paused == paused:
            self.pause_button.setText('Resume' if paused else 'Pause')
            self.pause_button.setToolTip('Resume updating the console' if paused else 'Temporarily stop console updates')
            return
        self._is_paused = paused
        if paused:
            self.pause_button.setText('Resume')
            self.pause_button.setToolTip('Resume updating the console')
            self._paused_snapshot = self.output_edit.toPlainText()
            self._paused_buffer.clear()
        else:
            self.pause_button.setText('Pause')
            self.pause_button.setToolTip('Temporarily stop console updates')
            buffered_text = ''.join(self._paused_buffer)
            self._paused_buffer.clear()
            self._paused_snapshot = ''
            if refresh and self.current_server_id:
                self._refresh_console(force=True)
            elif buffered_text:
                cursor = self.output_edit.textCursor()
                cursor.movePosition(QtGui.QTextCursor.End)
                cursor.insertText(buffered_text)
                if self.auto_scroll_enabled:
                    self.output_edit.verticalScrollBar().setValue(self.output_edit.verticalScrollBar().maximum())

    def _save_log(self) -> None:
        if not self.current_server_id:
            QtWidgets.QMessageBox.information(self, 'No server selected', 'Select a server before saving logs.')
            return
        server = self.controller.get_server(self.current_server_id)
        if not server:
            QtWidgets.QMessageBox.warning(self, 'Unknown server', 'Could not find server details.')
            return
        base_dir = Path.cwd() / 'logs'
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        safe_name = self._sanitize_filename(server.name)
        folder = base_dir / f'{safe_name}_{timestamp}'
        counter = 1
        while folder.exists():
            folder = base_dir / f'{safe_name}_{timestamp}_{counter}'
            counter += 1
        folder.mkdir(parents=True, exist_ok=True)
        log_path = folder / 'console.log'
        log_text = self.controller.server_log_text(self.current_server_id)
        try:
            log_path.write_text(log_text, encoding='utf-8')
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, 'Save failed', f'Unable to write log file\n{exc}')
            return
        QtWidgets.QMessageBox.information(self, 'Log saved', f'Saved log to\n{log_path}')

    @staticmethod
    def _sanitize_filename(value: str) -> str:
        cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', value.strip())
        return cleaned or 'server'

    def _set_auto_scroll_enabled(self, state: int) -> None:
        self.auto_scroll_enabled = state == QtCore.Qt.Checked
        if self.auto_scroll_enabled and not self._is_paused:
            scrollbar = self.output_edit.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _apply_log_filter(self, text: str) -> None:
        sanitized = text.strip()
        if sanitized == self._log_filter_text:
            return
        self._log_filter_text = sanitized
        self._refresh_console(force=True)

    def _reset_log_filter(self) -> None:
        if self.search_input.text():
            self.search_input.clear()
        else:
            self._apply_log_filter('')

    def _update_filter_status(self, matches: int, total: int) -> None:
        if not self._log_filter_text:
            self.filter_status.setText(f'{total} lines' if total else '')
        else:
            self.filter_status.setText(f'{matches} / {total} matches')

    def _filter_log_text(self, text: str) -> Tuple[str, int, int]:
        if not text:
            return text, 0, 0
        lines = text.splitlines()
        total = len(lines)
        if not self._log_filter_text:
            return text, total, total
        pattern = self._log_filter_text.lower()
        filtered_lines = [line for line in lines if pattern in line.lower()]
        filtered_text = '\n'.join(filtered_lines)
        if filtered_text and text.endswith('\n'):
            filtered_text += '\n'
        return filtered_text, len(filtered_lines), total

    def _split_category(self, category: str) -> List[str]:
        return [part.strip() for part in category.split('/') if part.strip()]

    def _commit_saved_tree_changes(self) -> None:
        updates: List[Tuple[str, str, int]] = []
        def visit(node: QtWidgets.QTreeWidgetItem, path: List[str]) -> None:
            for index in range(node.childCount()):
                child = node.child(index)
                command_id = child.data(0, QtCore.Qt.UserRole)
                if command_id:
                    updates.append((command_id, '/'.join(path), index))
                else:
                    visit(child, path + [child.text(0)])
        visit(self.saved_tree.invisibleRootItem(), [])
        if updates:
            self.controller.reorder_saved_commands(updates)


class MonitoringTab(QtWidgets.QWidget):
    def __init__(self, controller: AppController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._process_cache: Dict[int, psutil.Process] = {}
        self._server_items: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._root_path = Path.cwd().anchor or '/'

        layout = QtWidgets.QVBoxLayout(self)

        system_group = QtWidgets.QGroupBox('System overview')
        system_layout = QtWidgets.QGridLayout(system_group)
        self.cpu_label = QtWidgets.QLabel('CPU: --')
        self.memory_label = QtWidgets.QLabel('Memory: --')
        self.swap_label = QtWidgets.QLabel('Swap: --')
        self.disk_label = QtWidgets.QLabel('Disk: --')
        system_layout.addWidget(self.cpu_label, 0, 0)
        system_layout.addWidget(self.memory_label, 0, 1)
        system_layout.addWidget(self.swap_label, 1, 0)
        system_layout.addWidget(self.disk_label, 1, 1)
        layout.addWidget(system_group)

        self.server_tree = QtWidgets.QTreeWidget()
        self.server_tree.setColumnCount(6)
        self.server_tree.setHeaderLabels(['Server', 'Status', 'PID', 'Uptime', 'CPU %', 'Memory MB'])
        self.server_tree.setUniformRowHeights(True)
        self.server_tree.setAlternatingRowColors(True)
        layout.addWidget(self.server_tree, 1)

        self.metrics_note = QtWidgets.QLabel('Metrics update every 2 seconds.')
        self.metrics_note.setStyleSheet('color: #777; font-size: 11px;')
        layout.addWidget(self.metrics_note)

        self.controller.servers_changed.connect(self._rebuild_server_rows)
        self.controller.server_status_changed.connect(self._handle_status_changed)

        self._rebuild_server_rows()
        self._update_metrics()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self._update_metrics)
        self.timer.start()

    def _rebuild_server_rows(self) -> None:
        self.server_tree.clear()
        self._server_items.clear()
        for server in self.controller.list_servers():
            item = QtWidgets.QTreeWidgetItem([server.name, '--', '--', '--', '--', '--'])
            item.setData(0, QtCore.Qt.UserRole, server.id)
            self.server_tree.addTopLevelItem(item)
            self._server_items[server.id] = item
        self.server_tree.resizeColumnToContents(0)

    def _handle_status_changed(self, server_id: str, _status: str, _details: dict) -> None:
        self._update_server_row(server_id)

    def _update_metrics(self) -> None:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        self.cpu_label.setText(f'CPU: {cpu_percent:.1f}%')
        self.memory_label.setText(f"Memory: {mem.percent:.1f}% ({mem.used / (1024 ** 3):.2f}/{mem.total / (1024 ** 3):.2f} GB)")
        try:
            swap = psutil.swap_memory()
            self.swap_label.setText(f"Swap: {swap.percent:.1f}% ({swap.used / (1024 ** 3):.2f}/{swap.total / (1024 ** 3):.2f} GB)")
        except Exception:
            self.swap_label.setText('Swap: --')
        try:
            disk = psutil.disk_usage(self._root_path)
            self.disk_label.setText(f"Disk: {disk.percent:.1f}% ({disk.used / (1024 ** 3):.2f}/{disk.total / (1024 ** 3):.2f} GB)")
        except Exception:
            self.disk_label.setText('Disk: --')

        current_pids = set()
        for server_id, item in self._server_items.items():
            self._update_server_row(server_id)
            details = self.controller.server_details(server_id)
            pid = details.get('pid')
            cpu_text = '--'
            mem_text = '--'
            if pid:
                current_pids.add(pid)
                process = self._ensure_process(pid)
                if process:
                    try:
                        cpu_value = process.cpu_percent(interval=None)
                        mem_info = process.memory_info()
                        cpu_text = f"{cpu_value:.1f}"
                        mem_text = f"{mem_info.rss / (1024 * 1024):.1f}"
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        self._process_cache.pop(pid, None)
            item.setText(4, cpu_text)
            item.setText(5, mem_text)
        self._cleanup_process_cache(current_pids)

    def _update_server_row(self, server_id: str) -> None:
        item = self._server_items.get(server_id)
        if not item:
            return
        status = self.controller.server_status(server_id)
        item.setText(1, status)
        details = self.controller.server_details(server_id)
        pid = details.get('pid')
        item.setText(2, str(pid) if pid else '--')
        uptime = self.controller.server_uptime(server_id)
        item.setText(3, format_duration(uptime))

    def _ensure_process(self, pid: int) -> Optional[psutil.Process]:
        process = self._process_cache.get(pid)
        if process and process.is_running() and process.pid == pid:
            return process
        try:
            process = psutil.Process(pid)
            process.cpu_percent(interval=None)
            self._process_cache[pid] = process
            return process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self._process_cache.pop(pid, None)
            return None

    def _cleanup_process_cache(self, active_pids: set[int]) -> None:
        stale = [pid for pid in self._process_cache if pid not in active_pids]
        for pid in stale:
            self._process_cache.pop(pid, None)
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Velocity GUI Minecraft Server Manger")
        icon_path = Path(__file__).resolve().parent / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        self.resize(1000, 640)

        self.tab_widget = QtWidgets.QTabWidget()
        self.servers_tab = ServersTab(controller, self)
        self.console_tab = ConsoleTab(controller, self)
        self.monitoring_tab = MonitoringTab(controller, self)
        self.tab_widget.addTab(self.servers_tab, "Servers")
        self.tab_widget.addTab(self.console_tab, "Console")
        self.tab_widget.addTab(self.monitoring_tab, "Monitoring")
        self.setCentralWidget(self.tab_widget)

        self._create_actions()
        self._create_menus()
        self._create_status_bar()

    def _create_actions(self) -> None:
        self.action_settings = QtGui.QAction("Settings", self)
        self.action_settings.triggered.connect(self._open_settings)
        self.action_reload = QtGui.QAction("Reload configuration", self)
        self.action_reload.triggered.connect(self._reload_state)
        self.action_exit = QtGui.QAction("Exit", self)
        self.action_exit.triggered.connect(self.close)

        self.action_playit_add = QtGui.QAction("Add Playit agent to Servers", self)
        self.action_playit_add.triggered.connect(self._ensure_playit_entry)
        self.action_playit_start = QtGui.QAction("Launch Playit agent", self)
        self.action_playit_start.triggered.connect(self._start_playit_agent)
        self.action_playit_stop = QtGui.QAction("Stop Playit agent", self)
        self.action_playit_stop.triggered.connect(self._stop_playit_agent)

        self.action_about = QtGui.QAction("About", self)
        self.action_about.triggered.connect(self._show_about)

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.action_settings)
        file_menu.addAction(self.action_reload)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        tools_menu = menu_bar.addMenu("Tools")
        tools_menu.addAction(self.action_playit_add)
        tools_menu.addAction(self.action_playit_start)
        tools_menu.addAction(self.action_playit_stop)

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self.action_about)

    def _create_status_bar(self) -> None:
        bar = self.statusBar()
        bar.showMessage("Ready")
        credit = QtWidgets.QLabel("made with <3 by neo0oen")
        credit.setStyleSheet("color: #8000ff; font-size: 125%;")
        credit.setContentsMargins(0, 0, 12, 0)
        bar.addPermanentWidget(credit)
        self.credit_label = credit

    def _ensure_playit_entry(self) -> None:
        try:
            server = self.controller.ensure_playit_server()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Playit agent", str(exc))
            return
        self.servers_tab.select_server(server.id)
        self.statusBar().showMessage("Playit agent entry ready", 4000)

    def _start_playit_agent(self) -> None:
        try:
            server = self.controller.ensure_playit_server_started()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Playit agent", str(exc))
            return
        self.servers_tab.select_server(server.id)
        self.statusBar().showMessage("Playit agent launched", 4000)

    def _stop_playit_agent(self) -> None:
        server = self.controller.find_playit_server()
        if not server:
            QtWidgets.QMessageBox.information(self, "Playit agent", "No Playit agent entry found.")
            return
        self.controller.stop_server(server.id, force=False)
        self.servers_tab.select_server(server.id)
        self.statusBar().showMessage("Playit agent stop requested", 4000)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self, settings=self.controller.state.settings)
        if dialog.exec() == QtWidgets.QDialog.Accepted and dialog.result_settings:
            self.controller.update_settings(dialog.result_settings)
            self.statusBar().showMessage("Settings saved", 3000)

    def _reload_state(self) -> None:
        self.controller.reload_state()
        self.statusBar().showMessage("Configuration reloaded", 3000)

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "About",
            "Minecraft Server Launcher\nManage multiple Minecraft and Velocity instances, send commands, and manage the Playit agent.",
        )


def run_app() -> None:
    import sys

    app = QtWidgets.QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "logo.ico"
    if icon_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))
    controller = AppController()
    window = MainWindow(controller)
    window.show()
    sys.exit(app.exec())


