from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_FILE_NAME = "server_launcher_config.json"
DEFAULT_PLAYIT_PATH = r"C:\\Program Files\\playit_gg\\bin\\playit.exe"
LAUNCH_TYPE_JAVA = "java"
LAUNCH_TYPE_PLAYIT = "playit"


def get_config_path(base: Optional[Path] = None) -> Path:
    root = base if base is not None else Path.cwd()
    return root / CONFIG_FILE_NAME


@dataclass
class ServerConfig:
    id: str
    name: str
    jar_path: str
    min_ram: int = 512
    max_ram: int = 1024
    use_minecraft_gui: bool = False
    java_path: Optional[str] = None
    jvm_args: List[str] = field(default_factory=list)
    program_args: List[str] = field(default_factory=list)
    launch_type: str = LAUNCH_TYPE_JAVA
    custom_executable: Optional[str] = None
    hide_console: bool = False

    @property
    def primary_path(self) -> str:
        if self.launch_type == LAUNCH_TYPE_JAVA:
            return self.jar_path
        return self.custom_executable or self.jar_path

    @property
    def working_directory(self) -> str:
        path = self.primary_path
        if not path:
            return str(Path.cwd())
        return str(Path(path).resolve().parent)

    @property
    def display_memory(self) -> str:
        if self.launch_type != LAUNCH_TYPE_JAVA:
            return "--"
        return f"{self.min_ram}M / {self.max_ram}M"

    @property
    def supports_console(self) -> bool:
        return self.launch_type == LAUNCH_TYPE_JAVA

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ServerConfig":
        return ServerConfig(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Unnamed Server"),
            jar_path=data.get("jar_path", ""),
            min_ram=int(data.get("min_ram", 512)),
            max_ram=int(data.get("max_ram", 1024)),
            use_minecraft_gui=bool(data.get("use_minecraft_gui", False)),
            java_path=data.get("java_path"),
            jvm_args=list(data.get("jvm_args", [])),
            program_args=list(data.get("program_args", [])),
            launch_type=data.get("launch_type", LAUNCH_TYPE_JAVA),
            custom_executable=data.get("custom_executable"),
            hide_console=bool(data.get("hide_console", False)),
        )


@dataclass
class SavedCommand:
    id: str
    label: str
    command: str
    category: str = ""
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SavedCommand":
        return SavedCommand(
            id=data.get("id", str(uuid.uuid4())),
            label=data.get("label", "Command"),
            command=data.get("command", ""),
            category=data.get("category", ""),
            order=int(data.get("order", data.get("sequence", data.get("position", 0)))),
        )


@dataclass
class AppSettings:
    playit_path: str = DEFAULT_PLAYIT_PATH
    playit_args: List[str] = field(default_factory=list)
    auto_launch_playit: bool = False
    hide_console_windows: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppSettings":
        raw_args = data.get("playit_args", [])
        if isinstance(raw_args, str):
            args = raw_args.split()
        else:
            args = list(raw_args)
        if args == ["--silent"]:
            args = []
        return AppSettings(
            playit_path=data.get("playit_path", DEFAULT_PLAYIT_PATH),
            playit_args=args,
            auto_launch_playit=bool(data.get("auto_launch_playit", False)),
            hide_console_windows=bool(data.get("hide_console_windows", True)),
        )


@dataclass
class AppState:
    servers: List[ServerConfig] = field(default_factory=list)
    saved_commands: List[SavedCommand] = field(default_factory=list)
    settings: AppSettings = field(default_factory=AppSettings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": 4,
            "servers": [server.to_dict() for server in self.servers],
            "saved_commands": [cmd.to_dict() for cmd in self.saved_commands],
            "settings": self.settings.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppState":
        servers = [ServerConfig.from_dict(item) for item in data.get("servers", [])]
        saved = [SavedCommand.from_dict(item) for item in data.get("saved_commands", [])]
        settings = AppSettings.from_dict(data.get("settings", {}))
        return AppState(servers=servers, saved_commands=saved, settings=settings)


def load_app_state(config_path: Optional[Path] = None) -> AppState:
    path = get_config_path(config_path)
    if not path.exists():
        return AppState()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return AppState.from_dict(data)
    except Exception:
        return AppState()


def save_app_state(state: AppState, config_path: Optional[Path] = None) -> None:
    path = get_config_path(config_path)
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh, indent=2)
    except Exception as exc:
        raise RuntimeError(f"Failed to write configuration: {exc}")


