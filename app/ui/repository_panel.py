"""Repository state presentation and visual-object interactions."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.repository_state import RepositoryState


BRANCH_MIME = "application/x-git-visual-branch"


class BranchList(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        if item is None:
            return
        mime = QMimeData()
        mime.setData(BRANCH_MIME, QByteArray(item.data(Qt.ItemDataRole.UserRole).encode("utf-8")))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class CurrentBranchTarget(QFrame):
    branch_dropped = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._branch = ""
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        caption = QLabel("CURRENT BRANCH · DROP ANOTHER BRANCH HERE TO PROPOSE A MERGE")
        caption.setStyleSheet("color: #667085; font-size: 10px;")
        self.name_label = QLabel("No repository open")
        self.name_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(caption)
        layout.addWidget(self.name_label)

    def set_branch(self, branch: str) -> None:
        self._branch = branch
        self.name_label.setText(branch)

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.mimeData().hasFormat(BRANCH_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        source = bytes(event.mimeData().data(BRANCH_MIME)).decode("utf-8", errors="replace")
        if source and source != self._branch:
            self.branch_dropped.emit(source)
            event.acceptProposedAction()


class RepositoryPanel(QWidget):
    merge_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.current_target = CurrentBranchTarget()
        self.current_target.branch_dropped.connect(self.merge_requested)
        layout.addWidget(self.current_target)

        top = QHBoxLayout()
        branch_group = QGroupBox("Local branches (drag onto current branch to merge)")
        branch_layout = QVBoxLayout(branch_group)
        self.branch_list = BranchList()
        branch_layout.addWidget(self.branch_list)
        top.addWidget(branch_group)

        remote_group = QGroupBox("Configured remotes")
        remote_layout = QVBoxLayout(remote_group)
        self.remote_list = QListWidget()
        remote_layout.addWidget(self.remote_list)
        top.addWidget(remote_group)
        layout.addLayout(top)

        files = QHBoxLayout()
        changed_group = QGroupBox("Changed / untracked files")
        changed_layout = QVBoxLayout(changed_group)
        self.changed_list = QListWidget()
        self.changed_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        changed_layout.addWidget(self.changed_list)
        files.addWidget(changed_group)

        staged_group = QGroupBox("Staged files")
        staged_layout = QVBoxLayout(staged_group)
        self.staged_list = QListWidget()
        self.staged_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        staged_layout.addWidget(self.staged_list)
        files.addWidget(staged_group)
        layout.addLayout(files)

        history_group = QGroupBox("Recent commits")
        history_layout = QVBoxLayout(history_group)
        self.commit_tree = QTreeWidget()
        self.commit_tree.setHeaderLabels(("Commit", "Message", "Branches / tags"))
        self.commit_tree.setRootIsDecorated(False)
        self.commit_tree.header().setStretchLastSection(True)
        history_layout.addWidget(self.commit_tree)
        layout.addWidget(history_group, 1)

    def set_state(self, state: RepositoryState) -> None:
        display_branch = "Detached HEAD" if state.detached_head else state.current_branch
        self.current_target.set_branch(display_branch)
        self.branch_list.clear()
        for branch in state.branches:
            item = QListWidgetItem(("● " if branch == state.current_branch else "○ ") + branch)
            item.setData(Qt.ItemDataRole.UserRole, branch)
            self.branch_list.addItem(item)

        self.changed_list.clear()
        for file in state.changed_files:
            item = QListWidgetItem(f"{file.worktree_label:>2}  {file.path}")
            item.setData(Qt.ItemDataRole.UserRole, file.path)
            item.setToolTip("? means untracked; M modified; D deleted. Select and choose Stage.")
            self.changed_list.addItem(item)

        self.staged_list.clear()
        for file in state.staged_files:
            item = QListWidgetItem(f"{file.staged_label:>2}  {file.path}")
            item.setData(Qt.ItemDataRole.UserRole, file.path)
            item.setToolTip("This version is prepared for the next commit. Select and choose Unstage to remove it from the staging area.")
            self.staged_list.addItem(item)

        self.remote_list.clear()
        for remote in state.remotes:
            urls = remote.fetch_urls or remote.push_urls
            item = QListWidgetItem(f"{remote.name}\n{urls[0] if urls else '(URL unavailable)'}")
            item.setToolTip("\n".join((*remote.fetch_urls, *remote.push_urls)))
            self.remote_list.addItem(item)

        self.commit_tree.clear()
        for commit in state.commits:
            self.commit_tree.addTopLevelItem(QTreeWidgetItem((commit.short_hash, commit.subject, commit.decorations)))
        for column in (0, 1):
            self.commit_tree.resizeColumnToContents(column)

    def selected_changed_paths(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.changed_list.selectedItems()]

    def selected_staged_paths(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.staged_list.selectedItems()]

    def selected_branch(self) -> str | None:
        item = self.branch_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

