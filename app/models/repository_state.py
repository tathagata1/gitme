"""Dataclasses describing the current state of a Git repository."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileState:
    path: str
    index_status: str = "."
    worktree_status: str = "."
    original_path: str | None = None

    @property
    def is_untracked(self) -> bool:
        return self.index_status == "?" and self.worktree_status == "?"

    @property
    def is_staged(self) -> bool:
        return self.index_status not in (".", " ", "?")

    @property
    def has_worktree_change(self) -> bool:
        return self.is_untracked or self.worktree_status not in (".", " ")

    @property
    def staged_label(self) -> str:
        return "?" if self.is_untracked else self.index_status

    @property
    def worktree_label(self) -> str:
        return "?" if self.is_untracked else self.worktree_status


@dataclass(frozen=True, slots=True)
class CommitInfo:
    short_hash: str
    subject: str
    decorations: str = ""


@dataclass(frozen=True, slots=True)
class RemoteInfo:
    name: str
    fetch_urls: tuple[str, ...] = ()
    push_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RepositoryState:
    root: Path
    current_branch: str
    detached_head: bool
    branches: tuple[str, ...] = field(default_factory=tuple)
    files: tuple[FileState, ...] = field(default_factory=tuple)
    commits: tuple[CommitInfo, ...] = field(default_factory=tuple)
    remotes: tuple[RemoteInfo, ...] = field(default_factory=tuple)

    @property
    def staged_files(self) -> tuple[FileState, ...]:
        return tuple(file for file in self.files if file.is_staged)

    @property
    def changed_files(self) -> tuple[FileState, ...]:
        return tuple(file for file in self.files if file.has_worktree_change)

