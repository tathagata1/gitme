"""Main window coordinating UI intent with application and Git services."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.git.command_registry import CommandRegistry
from app.git.executor import GitExecutor
from app.git.repository import RepositoryError, RepositoryService
from app.models.command import GitCommand, RiskLevel
from app.models.repository_state import RepositoryState
from app.services.command_service import CommandService, CommandValidationError
from app.ui.action_palette import ActionPalette
from app.ui.command_preview import CommandPreview
from app.ui.history_panel import HistoryPanel
from app.ui.output_console import OutputConsole
from app.ui.raw_panel import RawCommandPanel
from app.ui.repository_panel import RepositoryPanel


class MainWindow(QMainWindow):
    """Presentation coordinator; subprocess and parsing logic live outside Qt."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Git Visual — Offline Visual Git Command Composer")
        self.resize(1180, 850)
        self.setMinimumSize(900, 650)

        self.executor = GitExecutor()
        self.repository_service = RepositoryService(self.executor)
        self.command_service = CommandService(CommandRegistry())
        self.repository_root: Path | None = None
        self.state: RepositoryState | None = None
        self.pending_command: GitCommand | None = None
        self.pending_cwd: Path | None = None
        self.open_after_execution = False

        self._create_toolbar()
        self._create_content()
        self._connect_signals()
        self._set_repository_enabled(False)
        self.statusBar().showMessage("Open or initialize a local Git repository to begin.")
        self.setStyleSheet(
            "QMainWindow { background: #f6f8fa; }"
            "QGroupBox { font-weight: 600; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
            "QPushButton { min-height: 25px; padding: 3px 10px; }"
            "QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit { background: white; }"
        )

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Repository")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        open_action = QAction("Open Repository", self)
        init_action = QAction("Initialize Repository", self)
        self.refresh_action = QAction("Refresh", self)
        open_action.triggered.connect(self.open_repository)
        init_action.triggered.connect(self.initialize_repository)
        self.refresh_action.triggered.connect(self.refresh_repository)
        toolbar.addAction(open_action)
        toolbar.addAction(init_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)
        toolbar.addSeparator()
        self.repository_label = QLabel("Repository: none")
        self.repository_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        toolbar.addWidget(self.repository_label)

    def _create_content(self) -> None:
        self.action_palette = ActionPalette()
        self.repository_panel = RepositoryPanel()
        self.history_panel = HistoryPanel()
        self.raw_panel = RawCommandPanel()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.repository_panel, "Repository")
        self.tabs.addTab(self.history_panel, "Command History")
        self.tabs.addTab(self.raw_panel, "Advanced / Raw Git Command")

        upper = QSplitter(Qt.Orientation.Horizontal)
        upper.addWidget(self.action_palette)
        upper.addWidget(self.tabs)
        upper.setStretchFactor(1, 1)
        upper.setSizes((190, 960))

        self.command_preview = CommandPreview()
        self.output_console = OutputConsole()
        lower = QSplitter(Qt.Orientation.Vertical)
        lower.addWidget(self.command_preview)
        lower.addWidget(self.output_console)
        lower.setSizes((260, 190))

        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.addWidget(upper)
        vertical.addWidget(lower)
        vertical.setStretchFactor(0, 1)
        vertical.setSizes((510, 320))

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(vertical)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self.action_palette.action_requested.connect(self._compose_operation)
        self.repository_panel.merge_requested.connect(self._compose_drop_merge)
        self.raw_panel.preview_requested.connect(self._compose_raw)
        self.command_preview.execute_requested.connect(self.execute_pending)
        self.command_preview.clear_requested.connect(self.clear_preview)

    def open_repository(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open Git Repository")
        if not folder:
            return
        try:
            root = self.repository_service.find_root(folder)
            self._open_root(root)
        except RepositoryError as error:
            QMessageBox.warning(self, "Not a Git repository", str(error))

    def initialize_repository(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Initialize Git Repository")
        if not folder:
            return
        command = self.command_service.build("repo.init")
        self._set_preview(command, cwd=Path(folder), open_after_execution=True)
        self.statusBar().showMessage("Initialization preview ready. Review git init, then click Execute.", 8000)

    def _open_root(self, root: Path) -> None:
        self.repository_root = root
        self.repository_label.setText(f"Repository: {root}")
        self.repository_label.setToolTip(str(root))
        self._set_repository_enabled(True)
        self.clear_preview()
        self.refresh_repository()

    def refresh_repository(self) -> None:
        if self.repository_root is None:
            return
        try:
            self.state = self.repository_service.load_state(self.repository_root)
            self.repository_panel.set_state(self.state)
            self.statusBar().showMessage(
                f"Refreshed {self.state.current_branch}: {len(self.state.changed_files)} changed, "
                f"{len(self.state.staged_files)} staged.", 5000
            )
        except RepositoryError as error:
            QMessageBox.critical(self, "Could not refresh repository", str(error))
            self.statusBar().showMessage("Repository refresh failed.")

    def _set_repository_enabled(self, enabled: bool) -> None:
        self.action_palette.setEnabled(enabled)
        self.repository_panel.setEnabled(enabled)
        self.raw_panel.setEnabled(enabled)
        self.refresh_action.setEnabled(enabled)

    def _compose_operation(self, operation_id: str) -> None:
        if self.state is None:
            return
        try:
            if operation_id == "changes.stage":
                command = self.command_service.stage(self.repository_panel.selected_changed_paths())
            elif operation_id == "changes.unstage":
                command = self.command_service.unstage(
                    self.repository_panel.selected_staged_paths(), has_head=bool(self.state.commits)
                )
            elif operation_id == "changes.commit":
                message, accepted = QInputDialog.getText(self, "Commit staged changes", "Commit message:")
                if not accepted:
                    return
                command = self.command_service.build(operation_id, message=message)
            elif operation_id == "branch.create":
                branch, accepted = QInputDialog.getText(self, "Create branch", "New branch name:")
                if not accepted:
                    return
                command = self.command_service.build(operation_id, branch=branch)
            elif operation_id in ("branch.switch", "branch.delete", "branch.merge"):
                branch = self.repository_panel.selected_branch()
                if not branch:
                    raise CommandValidationError("Select a branch in the repository panel first.")
                if operation_id == "branch.switch" and branch == self.state.current_branch:
                    raise CommandValidationError(f"“{branch}” is already checked out.")
                if operation_id in ("branch.delete", "branch.merge") and branch == self.state.current_branch:
                    raise CommandValidationError("Select a branch other than the current branch.")
                command = self.command_service.build(operation_id, branch=branch, current_branch=self.state.current_branch)
            else:
                command = self.command_service.build(operation_id)
            self._set_preview(command)
        except (CommandValidationError, KeyError) as error:
            QMessageBox.information(self, "Cannot create command", str(error))

    def _compose_drop_merge(self, branch: str) -> None:
        if self.state is None:
            return
        command = self.command_service.build("branch.merge", branch=branch, current_branch=self.state.current_branch)
        self._set_preview(command)
        self.statusBar().showMessage(f"Proposed: Merge {branch} into {self.state.current_branch}. Review and execute when ready.", 8000)

    def _compose_raw(self, text: str) -> None:
        try:
            self._set_preview(self.command_service.parse_raw(text))
        except CommandValidationError as error:
            QMessageBox.warning(self, "Invalid raw command", str(error))

    def _set_preview(
        self,
        command: GitCommand,
        *,
        cwd: Path | None = None,
        open_after_execution: bool = False,
    ) -> None:
        self.pending_command = command
        self.pending_cwd = cwd
        self.open_after_execution = open_after_execution
        self.command_preview.set_command(command)
        self.statusBar().showMessage(f"Preview ready: {command.summary}. No command has run yet.", 5000)

    def clear_preview(self) -> None:
        self.pending_command = None
        self.pending_cwd = None
        self.open_after_execution = False
        self.command_preview.set_command(None)

    def execute_pending(self) -> None:
        if self.pending_command is None:
            return
        command = self.pending_command
        execution_root = self.pending_cwd or self.repository_root
        open_after_execution = self.open_after_execution
        if execution_root is None:
            return
        if command.risk_level >= RiskLevel.CAUTION:
            heading = "Confirm destructive Git command" if command.risk_level == RiskLevel.DESTRUCTIVE else "Review caution command"
            detail = (
                "This raw command matches an obviously destructive pattern. Detection is not comprehensive."
                if command.risk_level == RiskLevel.DESTRUCTIVE
                else "This command can significantly change branch or repository state."
            )
            answer = QMessageBox.warning(
                self,
                heading,
                f"{detail}\n\n{command.display_command}\n\nExecute this exact command?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        result = self.executor.execute(command, execution_root)
        self.output_console.show_result(result)
        self.history_panel.add_result(result)
        self.clear_preview()
        if open_after_execution and result.success:
            try:
                self._open_root(self.repository_service.find_root(execution_root))
            except RepositoryError as error:
                QMessageBox.critical(self, "Repository error", str(error))
        elif self.repository_root is not None:
            self.refresh_repository()
        if result.success:
            self.statusBar().showMessage(f"Completed: {command.display_command}", 6000)
        else:
            self.statusBar().showMessage(f"Git failed with exit code {result.exit_code}. The raw error is shown below.", 8000)
