"""Always-visible preview and offline explanation panel."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from app.models.command import GitCommand, RiskLevel


class CommandPreview(QFrame):
    execute_requested = Signal()
    clear_requested = Signal()

    RISK_STYLES = {
        RiskLevel.READ_ONLY: ("READ ONLY", "#027a48", "#ecfdf3"),
        RiskLevel.NORMAL: ("NORMAL", "#175cd3", "#eff8ff"),
        RiskLevel.CAUTION: ("CAUTION", "#b54708", "#fffaeb"),
        RiskLevel.DESTRUCTIVE: ("DESTRUCTIVE", "#b42318", "#fef3f2"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("COMMAND PREVIEW")
        title.setStyleSheet("font-weight: 700;")
        self.risk_label = QLabel("NO COMMAND")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.risk_label)
        layout.addLayout(header)
        self.command_text = QPlainTextEdit()
        self.command_text.setReadOnly(True)
        self.command_text.setMaximumHeight(58)
        self.command_text.setPlaceholderText("Choose a visual action to generate a Git command. Nothing executes immediately.")
        self.command_text.setStyleSheet("font-family: Consolas, monospace; font-size: 14px;")
        layout.addWidget(self.command_text)
        self.summary_label = QLabel("Visual actions generate a command here. Review it, then click Execute.")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.explanation_text = QPlainTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setMaximumHeight(160)
        self.explanation_text.hide()
        layout.addWidget(self.explanation_text)
        buttons = QHBoxLayout()
        self.explain_button = QPushButton("Explain")
        self.explain_button.clicked.connect(self._toggle_explanation)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_requested)
        self.execute_button = QPushButton("Execute")
        self.execute_button.setDefault(True)
        self.execute_button.clicked.connect(self.execute_requested)
        buttons.addWidget(self.explain_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch()
        buttons.addWidget(self.execute_button)
        layout.addLayout(buttons)
        self.set_command(None)

    def set_command(self, command: GitCommand | None) -> None:
        enabled = command is not None
        self.execute_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.explain_button.setEnabled(enabled)
        if command is None:
            self.command_text.clear()
            self.summary_label.setText("Visual actions generate a command here. Review it, then click Execute.")
            self.explanation_text.clear()
            self.explanation_text.hide()
            self.risk_label.setText("NO COMMAND")
            self.risk_label.setStyleSheet("color: #667085;")
            return
        self.command_text.setPlainText(command.display_command)
        self.summary_label.setText(command.explanation)
        self.explanation_text.setPlainText(command.detailed_explanation)
        self.explanation_text.hide()
        label, foreground, background = self.RISK_STYLES[command.risk_level]
        self.risk_label.setText(label)
        self.risk_label.setStyleSheet(f"color: {foreground}; background: {background}; padding: 4px 8px; font-weight: 700;")

    def _toggle_explanation(self) -> None:
        self.explanation_text.setVisible(not self.explanation_text.isVisible())

