from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtCore

from models import LAUNCH_TYPE_JAVA, LAUNCH_TYPE_PLAYIT, ServerConfig


class ServerStatus(Enum):
    STOPPED = "Stopped"
    STARTING = "Starting"
    RUNNING = "Running"
    STOPPING = "Stopping"
    FAILED = "Failed"


class ServerRuntime(QtCore.QObject):
    output = QtCore.Signal(str, str)
    status_changed = QtCore.Signal(str, str, dict)

    def __init__(self, config: ServerConfig, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.config = config
        self.process: Optional[QtCore.QProcess] = None
        self.status = ServerStatus.STOPPED
        self._graceful_timer = QtCore.QTimer(self)
        self._graceful_timer.setInterval(10000)
        self._graceful_timer.setSingleShot(True)
        self._graceful_timer.timeout.connect(self._handle_force_kill)
        self._last_details: Dict[str, object] = {"pid": None, "exit_code": None}

    def start(self) -> None:
        if self.process and self.process.state() != QtCore.QProcess.NotRunning:
            return

        if self.config.launch_type == LAUNCH_TYPE_JAVA:
            self._start_java_server()
        else:
            self._start_custom_process()

    def _start_java_server(self) -> None:
        jar_path = Path(self.config.jar_path)
        if not jar_path.exists():
            raise FileNotFoundError(f"Server jar not found: {jar_path}")
        program = self.config.java_path or "java"
        args: List[str] = [
            f"-Xms{self.config.min_ram}M",
            f"-Xmx{self.config.max_ram}M",
        ]
        args.extend(self.config.jvm_args)
        args.append("-jar")
        args.append(str(jar_path))
        args.extend(self.config.program_args)
        if not self.config.use_minecraft_gui and "nogui" not in args:
            args.append("nogui")

        process = QtCore.QProcess(self)
        process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        process.setProgram(program)
        process.setArguments(args)
        process.setWorkingDirectory(str(jar_path.parent))
        env = QtCore.QProcessEnvironment.systemEnvironment()
        process.setProcessEnvironment(env)
        self._wire_process(process)
        self.status = ServerStatus.STARTING
        self.status_changed.emit(self.config.id, self.status.value, {})
        process.start()

    def _start_custom_process(self) -> None:
        executable = self.config.custom_executable or self.config.jar_path
        if not executable:
            raise FileNotFoundError("Executable path not configured")
        exe_path = Path(executable)
        if not exe_path.exists():
            raise FileNotFoundError(f"Executable not found: {exe_path}")

        process = QtCore.QProcess(self)
        process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        process.setProgram(str(exe_path))
        process.setArguments(list(self.config.program_args))
        process.setWorkingDirectory(str(exe_path.parent))
        env = QtCore.QProcessEnvironment.systemEnvironment()
        process.setProcessEnvironment(env)

        if os.name == "nt" and self.config.hide_console:
            try:
                process.setCreateProcessArgumentsModifier(self._apply_no_window_flag)
            except AttributeError:
                pass

        self._wire_process(process)
        self.status = ServerStatus.STARTING
        self.status_changed.emit(self.config.id, self.status.value, {})
        process.start()

    def stop(self) -> None:
        if not self.process or self.process.state() == QtCore.QProcess.NotRunning:
            return
        self.status = ServerStatus.STOPPING
        self.status_changed.emit(self.config.id, self.status.value, {})
        if self.config.launch_type == LAUNCH_TYPE_JAVA:
            try:
                self.send_command("stop")
            except Exception:
                pass
            self._graceful_timer.start()
        else:
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()

    def force_stop(self) -> None:
        if not self.process:
            return
        self._graceful_timer.stop()
        self.process.kill()

    def send_command(self, command: str) -> None:
        if self.config.launch_type != LAUNCH_TYPE_JAVA:
            raise RuntimeError("This process does not accept console commands")
        if not self.process or self.process.state() == QtCore.QProcess.NotRunning:
            raise RuntimeError("Server is not running")
        payload = (command.rstrip("\n") + "\n").encode("utf-8", errors="ignore")
        self.process.write(payload)
        self.process.waitForBytesWritten(1000)

    def update_config(self, config: ServerConfig) -> None:
        self.config = config

    def current_status(self) -> ServerStatus:
        if self.process and self.process.state() != QtCore.QProcess.NotRunning:
            return self.status
        return ServerStatus.STOPPED

    def last_details(self) -> Dict[str, object]:
        return dict(self._last_details)

    def _wire_process(self, process: QtCore.QProcess) -> None:
        self.process = process
        process.readyReadStandardOutput.connect(self._handle_output)
        process.started.connect(self._handle_started)
        process.finished.connect(self._handle_finished)
        process.errorOccurred.connect(self._handle_error)

    @staticmethod
    def _enum_to_int(value) -> Optional[int]:
        if hasattr(value, "value"):
            try:
                return int(value.value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    def _handle_started(self) -> None:
        if not self.process:
            return
        self._graceful_timer.stop()
        self.status = ServerStatus.RUNNING
        self._last_details["pid"] = self.process.processId()
        self._last_details["exit_code"] = None
        self._last_details.pop("exit_status", None)
        self._last_details.pop("exit_status_name", None)
        self._last_details.pop("process_error", None)
        self._last_details.pop("process_error_name", None)
        self.status_changed.emit(self.config.id, self.status.value, dict(self._last_details))

    def _handle_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        self._graceful_timer.stop()
        self.status = ServerStatus.STOPPED
        self._last_details["exit_code"] = exit_code
        exit_value = self._enum_to_int(exit_status)
        if exit_value is not None:
            self._last_details["exit_status"] = exit_value
        else:
            self._last_details.pop("exit_status", None)
        name = getattr(exit_status, "name", None)
        self._last_details["exit_status_name"] = name if name is not None else str(exit_status)
        self.status_changed.emit(self.config.id, self.status.value, dict(self._last_details))
        if self.process:
            self.process.deleteLater()
            self.process = None

    def _handle_error(self, process_error: QtCore.QProcess.ProcessError) -> None:
        self._graceful_timer.stop()
        self.status = ServerStatus.FAILED
        error_value = self._enum_to_int(process_error)
        if error_value is not None:
            self._last_details["process_error"] = error_value
        else:
            self._last_details.pop("process_error", None)
        name = getattr(process_error, "name", None)
        if name is not None:
            self._last_details["process_error_name"] = name
        self.status_changed.emit(self.config.id, self.status.value, dict(self._last_details))

    def _handle_output(self) -> None:
        if not self.process:
            return
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.output.emit(self.config.id, data)

    def _handle_force_kill(self) -> None:
        if not self.process:
            return
        if self.process.state() != QtCore.QProcess.NotRunning:
            self.process.kill()

    @staticmethod
    def _apply_no_window_flag(args: QtCore.QProcess.CreateProcessArguments) -> None:
        try:
            CREATE_NO_WINDOW = 0x08000000
            args.creationFlags |= CREATE_NO_WINDOW
        except AttributeError:
            if isinstance(args, dict):
                CREATE_NO_WINDOW = 0x08000000
                args["creationFlags"] = args.get("creationFlags", 0) | CREATE_NO_WINDOW
