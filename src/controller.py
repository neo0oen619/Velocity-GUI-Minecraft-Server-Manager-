from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional, Tuple

from PySide6 import QtCore

from models import (
    LAUNCH_TYPE_JAVA,
    LAUNCH_TYPE_PLAYIT,
    AppSettings,
    AppState,
    SavedCommand,
    ServerConfig,
    load_app_state,
    save_app_state,
)
from process_manager import ServerRuntime, ServerStatus

MAX_LOG_LINES = 5000
DEFAULT_PLAYIT_NAME = "Playit Agent"


class AppController(QtCore.QObject):
    servers_changed = QtCore.Signal()
    saved_commands_changed = QtCore.Signal()
    server_status_changed = QtCore.Signal(str, str, dict)
    server_output = QtCore.Signal(str, str)

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.state: AppState = load_app_state()
        self._normalize_saved_command_order(save=False)
        self.server_runtimes: Dict[str, ServerRuntime] = {}
        self.server_logs: Dict[str, Deque[str]] = {}
        self.server_start_times: Dict[str, datetime] = {}
        for server in self.state.servers:
            self.ensure_log_buffer(server.id)
        if self.state.settings.auto_launch_playit:
            QtCore.QTimer.singleShot(1000, self._auto_launch_playit)

    def list_servers(self) -> List[ServerConfig]:
        return list(self.state.servers)

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        for server in self.state.servers:
            if server.id == server_id:
                return server
        return None

    def add_server(self, config: ServerConfig) -> None:
        self.state.servers.append(config)
        self.ensure_log_buffer(config.id)
        self.save_state()
        self.servers_changed.emit()

    def update_server(self, updated: ServerConfig) -> None:
        for index, server in enumerate(self.state.servers):
            if server.id == updated.id:
                self.state.servers[index] = updated
                runtime = self.server_runtimes.get(updated.id)
                if runtime:
                    runtime.update_config(updated)
                self.save_state()
                self.servers_changed.emit()
                return
        raise KeyError(f"Server not found: {updated.id}")

    def remove_server(self, server_id: str) -> None:
        self.stop_server(server_id, force=True)
        self.state.servers = [srv for srv in self.state.servers if srv.id != server_id]
        self.server_runtimes.pop(server_id, None)
        self.server_logs.pop(server_id, None)
        self.server_start_times.pop(server_id, None)
        self.save_state()
        self.servers_changed.emit()


    def move_server(self, server_id: str, offset: int) -> bool:
        if not self.state.servers:
            return False
        current_index = None
        for index, server in enumerate(self.state.servers):
            if server.id == server_id:
                current_index = index
                break
        if current_index is None:
            raise KeyError(f"Server not found: {server_id}")
        new_index = max(0, min(len(self.state.servers) - 1, current_index + offset))
        if new_index == current_index:
            return False
        entry = self.state.servers.pop(current_index)
        self.state.servers.insert(new_index, entry)
        self.save_state()
        self.servers_changed.emit()
        return True

    def duplicate_server(self, server_id: str) -> ServerConfig:
        server = self.get_server(server_id)
        if not server:
            raise KeyError(f"Server not found: {server_id}")
        clone = ServerConfig(
            id=QtCore.QUuid.createUuid().toString().strip("{}"),
            name=f"{server.name} Copy",
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
        self.add_server(clone)
        return clone

    def list_saved_commands(self) -> List[SavedCommand]:
        return list(self.state.saved_commands)

    def add_saved_command(self, command: SavedCommand) -> None:
        command.order = self._next_order_value(command.category)
        self.state.saved_commands.append(command)
        self._normalize_saved_command_order(save=False)
        self.save_state()
        self.saved_commands_changed.emit()

    def update_saved_command(self, command: SavedCommand) -> None:
        for index, existing in enumerate(self.state.saved_commands):
            if existing.id == command.id:
                if existing.category != command.category:
                    command.order = self._next_order_value(command.category)
                else:
                    command.order = existing.order
                self.state.saved_commands[index] = command
                self._normalize_saved_command_order(save=False)
                self.save_state()
                self.saved_commands_changed.emit()
                return
        raise KeyError(f"Command not found: {command.id}")

    def remove_saved_command(self, command_id: str) -> None:
        self.state.saved_commands = [cmd for cmd in self.state.saved_commands if cmd.id != command_id]
        self._normalize_saved_command_order(save=False)
        self.save_state()
        self.saved_commands_changed.emit()

    def reorder_saved_commands(self, ordering: List[Tuple[str, str, int]]) -> None:
        if not ordering:
            return
        updates = {cmd_id: (category, order) for cmd_id, category, order in ordering}
        for cmd in self.state.saved_commands:
            info = updates.get(cmd.id)
            if info:
                category, order = info
                cmd.category = category
                cmd.order = order
        self._normalize_saved_command_order(save=False)
        self.save_state()
        self.saved_commands_changed.emit()

    def server_uptime(self, server_id: str) -> Optional[timedelta]:
        start_time = self.server_start_times.get(server_id)
        if not start_time:
            return None
        return datetime.now() - start_time

    def _next_order_value(self, category: str) -> int:
        return max((cmd.order for cmd in self.state.saved_commands if cmd.category == category), default=-1) + 1

    def _normalize_saved_command_order(self, save: bool = True) -> None:
        buckets: Dict[str, List[SavedCommand]] = {}
        for cmd in self.state.saved_commands:
            buckets.setdefault(cmd.category, []).append(cmd)
        changed = False
        for commands in buckets.values():
            commands.sort(key=lambda c: (c.order, c.label.lower()))
            for index, cmd in enumerate(commands):
                if cmd.order != index:
                    cmd.order = index
                    changed = True
        sorted_commands = sorted(self.state.saved_commands, key=self._saved_command_sort_key)
        if sorted_commands != self.state.saved_commands:
            self.state.saved_commands = sorted_commands
            changed = True
        if changed and save:
            self.save_state()

    @staticmethod
    def _category_key(category: str) -> Tuple[str, ...]:
        return tuple(part.strip().lower() for part in category.split('/') if part.strip())

    def _saved_command_sort_key(self, command: SavedCommand) -> Tuple[Tuple[str, ...], int, str]:
        return (self._category_key(command.category), command.order, command.label.lower())

    def start_server(self, server_id: str) -> None:
        server = self.get_server(server_id)
        if not server:
            raise KeyError(f"Server not found: {server_id}")
        runtime = self.server_runtimes.get(server_id)
        if not runtime:
            runtime = ServerRuntime(server, self)
            runtime.output.connect(self._handle_server_output)
            runtime.status_changed.connect(self._handle_status_changed)
            self.server_runtimes[server_id] = runtime
        try:
            runtime.start()
        except Exception as exc:
            raise RuntimeError(str(exc))

    def stop_server(self, server_id: str, force: bool = False) -> None:
        runtime = self.server_runtimes.get(server_id)
        if not runtime:
            return
        if force:
            runtime.force_stop()
        else:
            runtime.stop()

    def send_command(self, server_id: str, command: str) -> None:
        runtime = self.server_runtimes.get(server_id)
        if not runtime:
            raise RuntimeError("Server is not running")
        runtime.send_command(command)

    def server_status(self, server_id: str) -> str:
        runtime = self.server_runtimes.get(server_id)
        if runtime:
            return runtime.current_status().value
        return ServerStatus.STOPPED.value

    def server_details(self, server_id: str) -> Dict[str, object]:
        runtime = self.server_runtimes.get(server_id)
        if runtime:
            return runtime.last_details()
        return {"pid": None, "exit_code": None, "exit_status": None, "exit_status_name": "Unknown"}

    def server_log_text(self, server_id: str) -> str:
        lines = self.server_logs.get(server_id)
        if not lines:
            return ""
        return "".join(lines)

    def clear_server_log(self, server_id: str) -> None:
        if server_id in self.server_logs:
            self.server_logs[server_id].clear()

    def ensure_log_buffer(self, server_id: str) -> None:
        self.server_logs.setdefault(server_id, deque(maxlen=MAX_LOG_LINES))

    def find_playit_server(self) -> Optional[ServerConfig]:
        for server in self.state.servers:
            if server.launch_type == LAUNCH_TYPE_PLAYIT:
                return server
        return None


    def ensure_playit_server(self) -> ServerConfig:
        settings = self.state.settings
        existing = self.find_playit_server()
        if existing:
            executable = existing.custom_executable or settings.playit_path
            args = list(existing.program_args) if existing.program_args else list(settings.playit_args)
            if args == ["--silent"]:
                args = []
            hide_console = existing.hide_console
            name = existing.name
            identifier = existing.id
        else:
            executable = settings.playit_path
            args = list(settings.playit_args)
            hide_console = settings.hide_console_windows
            name = DEFAULT_PLAYIT_NAME
            identifier = QtCore.QUuid.createUuid().toString().strip("{}")
        updated = ServerConfig(
            id=identifier,
            name=name,
            jar_path="",
            min_ram=0,
            max_ram=0,
            use_minecraft_gui=False,
            java_path=None,
            jvm_args=[],
            program_args=args,
            launch_type=LAUNCH_TYPE_PLAYIT,
            custom_executable=executable,
            hide_console=hide_console,
        )
        if existing:
            self.update_server(updated)
        else:
            self.add_server(updated)
        return updated

    def ensure_playit_server_started(self) -> ServerConfig:
        server = self.ensure_playit_server()
        self.start_server(server.id)
        return server

    def update_settings(self, settings: AppSettings) -> None:
        self.state.settings = settings
        self.save_state()
        existing_playit = self.find_playit_server()
        if existing_playit:
            # Refresh the stored executable/args without duplicating entries
            playit_config = ServerConfig(
                id=existing_playit.id,
                name=existing_playit.name,
                jar_path="",
                min_ram=0,
                max_ram=0,
                use_minecraft_gui=False,
                java_path=None,
                jvm_args=[],
                program_args=list(settings.playit_args),
                launch_type=LAUNCH_TYPE_PLAYIT,
                custom_executable=settings.playit_path,
                hide_console=settings.hide_console_windows,
            )
            self.update_server(playit_config)

    def save_state(self) -> None:
        save_app_state(self.state)

    def reload_state(self) -> None:
        self.state = load_app_state()
        self._normalize_saved_command_order(save=False)
        self.server_logs.clear()
        self.server_start_times.clear()
        for server in self.state.servers:
            self.ensure_log_buffer(server.id)
        self.servers_changed.emit()
        self.saved_commands_changed.emit()


    def _handle_server_output(self, server_id: str, text: str) -> None:
        self.ensure_log_buffer(server_id)
        buffer = self.server_logs[server_id]
        buffer.extend(text.splitlines(keepends=True))
        self.server_output.emit(server_id, text)

    def _handle_status_changed(self, server_id: str, status: str, details: Dict[str, Optional[int]]) -> None:
        self.server_status_changed.emit(server_id, status, details)

    def _auto_launch_playit(self) -> None:
        try:
            self.ensure_playit_server_started()
        except Exception:
            # Intentionally swallow errors to avoid blocking startup
            pass


