"""Raw Git output display."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout, QWidget

from app.models.result import GitResult


class OutputConsole(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("OUTPUT", parent)
        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(5000)
        self.text.setStyleSheet("font-family: Consolas, monospace;")
        self.text.setPlaceholderText("Git stdout and stderr will appear here without being hidden or rewritten.")
        layout.addWidget(self.text)

    def show_result(self, result: GitResult) -> None:
        sections = [f"> {result.command.display_command}", ""]
        if result.stdout:
            sections.extend((result.stdout.rstrip(), ""))
        if result.stderr:
            sections.extend(("stderr:", result.stderr.rstrip(), ""))
        sections.append(f"Exit code: {result.exit_code}    Duration: {result.duration_seconds:.2f}s")
        self.text.setPlainText("\n".join(sections))
        color = "#067647" if result.success else "#b42318"
        self.text.setStyleSheet(f"font-family: Consolas, monospace; border: 2px solid {color};")

