"""Advanced shell-free raw Git command composer."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class RawCommandPanel(QWidget):
    preview_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        warning = QLabel(
            "Advanced mode accepts any command beginning with git. It never uses a shell, but it bypasses some structured safeguards. "
            "Destructive-pattern detection is helpful, not comprehensive."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("background: #fffaeb; color: #7a2e0e; padding: 10px;")
        layout.addWidget(warning)
        self.input = QLineEdit()
        self.input.setPlaceholderText('git fsck --full')
        self.input.returnPressed.connect(self._emit_preview)
        layout.addWidget(self.input)
        button = QPushButton("Create Command Preview")
        button.clicked.connect(self._emit_preview)
        layout.addWidget(button)
        layout.addStretch()

    def _emit_preview(self) -> None:
        self.preview_requested.emit(self.input.text())

