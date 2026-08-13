"""Centralized, shell-free Git process execution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import time

from app.models.command import GitCommand
from app.models.result import GitResult


class GitExecutor:
    """Execute GitCommand instances with predictable error reporting."""

    def __init__(self, timeout_seconds: float = 60.0) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, command: GitCommand, cwd: Path | str | None = None) -> GitResult:
        started = datetime.now()
        timer = time.monotonic()
        try:
            completed = subprocess.run(
                command.argv,
                cwd=str(cwd) if cwd is not None else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                shell=False,
                check=False,
            )
            return GitResult(
                command=command,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                success=completed.returncode == 0,
                started_at=started,
                duration_seconds=time.monotonic() - timer,
            )
        except FileNotFoundError:
            if cwd is not None and not Path(cwd).is_dir():
                message = f"The repository working folder was not found: {cwd}"
            else:
                message = "Git was not found. Install Git and ensure 'git' is available on PATH."
            return self._failure(command, started, timer, 127, message)
        except subprocess.TimeoutExpired as error:
            output = self._as_text(error.stdout)
            detail = self._as_text(error.stderr)
            message = f"Git timed out after {self.timeout_seconds:g} seconds."
            return self._failure(command, started, timer, 124, f"{detail}\n{message}".strip(), output)
        except (NotADirectoryError, OSError) as error:
            if cwd is not None and not Path(cwd).is_dir():
                return self._failure(command, started, timer, 1, f"The repository working folder was not found: {cwd}")
            return self._failure(command, started, timer, 1, f"Could not run Git: {error}")

    @staticmethod
    def _as_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value

    @staticmethod
    def _failure(
        command: GitCommand,
        started: datetime,
        timer: float,
        exit_code: int,
        stderr: str,
        stdout: str = "",
    ) -> GitResult:
        return GitResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            success=False,
            started_at=started,
            duration_seconds=time.monotonic() - timer,
        )
