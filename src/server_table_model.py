from __future__ import annotations

from typing import Any, Optional

from PySide6 import QtCore

from controller import AppController
from models import LAUNCH_TYPE_JAVA


class ServerTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["#", "Name", "Status", "Memory", "Path", "Runtime"]

    def __init__(self, controller: AppController, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.controller.servers_changed.connect(self.refresh)
        self.controller.server_status_changed.connect(lambda *_: self.refresh())

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self.controller.list_servers())

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> Any:  # type: ignore[override]
        if not index.isValid():
            return None
        servers = self.controller.list_servers()
        if index.row() >= len(servers):
            return None
        server = servers[index.row()]
        column = index.column()

        if role == QtCore.Qt.DisplayRole:
            if column == 0:
                return index.row()
            if column == 1:
                return server.name
            if column == 2:
                return self.controller.server_status(server.id)
            if column == 3:
                return server.display_memory
            if column == 4:
                return server.primary_path
            if column == 5:
                if server.launch_type == LAUNCH_TYPE_JAVA:
                    return server.java_path or "java"
                return "External"
        if role == QtCore.Qt.ToolTipRole:
            if column == 4:
                return server.primary_path
            if column == 5 and server.launch_type == LAUNCH_TYPE_JAVA and server.java_path:
                return server.java_path
        if role == QtCore.Qt.TextAlignmentRole:
            if column in (0, 3):
                return int(QtCore.Qt.AlignCenter)
        return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole) -> Any:  # type: ignore[override]
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        else:
            return section + 1
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()


