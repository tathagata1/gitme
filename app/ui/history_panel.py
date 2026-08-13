"""In-memory, inspect-only command history."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPlainTextEdit, QWidget

from app.models.result import GitResult


class HistoryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[GitResult] = []
        layout = QHBoxLayout(self)
        self.list = QListWidget()
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Select a command to inspect its explanation and exact result. History never re-executes commands.")
        self.detail.setStyleSheet("font-family: Consolas, monospace;")
        self.list.currentItemChanged.connect(self._show_item)
        layout.addWidget(self.list, 2)
        layout.addWidget(self.detail, 3)

    def add_result(self, result: GitResult) -> None:
        self._results.append(result)
        symbol = "✓" if result.success else "✗"
        item = QListWidgetItem(f"{symbol} {result.command.display_command}")
        item.setData(Qt.ItemDataRole.UserRole, len(self._results) - 1)
        item.setForeground(Qt.GlobalColor.darkGreen if result.success else Qt.GlobalColor.darkRed)
        self.list.insertItem(0, item)

    def _show_item(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.detail.clear()
            return
        result = self._results[current.data(Qt.ItemDataRole.UserRole)]
        self.detail.setPlainText(
            f"{result.command.display_command}\n\n{result.command.detailed_explanation}\n\n"
            f"stdout:\n{result.stdout or '(empty)'}\n\nstderr:\n{result.stderr or '(empty)'}\n\nExit code: {result.exit_code}"
        )

