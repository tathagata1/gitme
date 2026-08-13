"""Categorized visual operation launcher."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QPushButton, QScrollArea, QVBoxLayout, QWidget


class ActionPalette(QScrollArea):
    action_requested = Signal(str)

    ACTIONS = {
        "Changes": (("Stage", "changes.stage"), ("Unstage", "changes.unstage"), ("Commit…", "changes.commit")),
        "Branches": (("Create…", "branch.create"), ("Switch", "branch.switch"), ("Delete", "branch.delete"), ("Merge", "branch.merge")),
        "Remote": (("Fetch", "remote.fetch"), ("Pull", "remote.pull"), ("Push", "remote.push")),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(175)
        body = QWidget()
        layout = QVBoxLayout(body)
        for category, actions in self.ACTIONS.items():
            group = QGroupBox(category)
            group_layout = QVBoxLayout(group)
            for label, operation in actions:
                button = QPushButton(label)
                button.clicked.connect(lambda _checked=False, value=operation: self.action_requested.emit(value))
                group_layout.addWidget(button)
            layout.addWidget(group)
        layout.addStretch()
        self.setWidget(body)

