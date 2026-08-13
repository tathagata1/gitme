"""Structured subprocess result models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .command import GitCommand


@dataclass(frozen=True, slots=True)
class GitResult:
    command: GitCommand
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    started_at: datetime
    duration_seconds: float

    @property
    def combined_output(self) -> str:
        sections = [part.rstrip() for part in (self.stdout, self.stderr) if part.strip()]
        return "\n".join(sections)

