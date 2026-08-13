"""Repository discovery and state loading through the Git CLI."""

from __future__ import annotations

from pathlib import Path

from app.git.executor import GitExecutor
from app.git.parser import parse_log_records, parse_status_porcelain_v2
from app.models.command import GitCommand, RiskLevel
from app.models.repository_state import RemoteInfo, RepositoryState


class RepositoryError(RuntimeError):
    """A clear error suitable for presenting in the UI."""


class RepositoryService:
    def __init__(self, executor: GitExecutor | None = None) -> None:
        self.executor = executor or GitExecutor()

    def find_root(self, selected_path: Path | str) -> Path:
        path = Path(selected_path).expanduser()
        if not path.is_dir():
            raise RepositoryError(f"The selected folder does not exist: {path}")
        result = self._query(("rev-parse", "--show-toplevel"), path, "Validate repository")
        if not result.success:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RepositoryError(f"“{path}” is not a Git repository.\n\n{detail}".strip())
        root_text = result.stdout.strip()
        if not root_text:
            raise RepositoryError("Git did not return a repository root.")
        return Path(root_text).resolve()

    def load_state(self, repository_root: Path | str) -> RepositoryState:
        root = Path(repository_root).resolve()
        status_result = self._query(("status", "--porcelain=v2", "--branch", "-z"), root, "Read status")
        if not status_result.success:
            raise RepositoryError(status_result.stderr.strip() or "Git could not read repository status.")
        branch, detached, files = parse_status_porcelain_v2(status_result.stdout)

        branches_result = self._query(("for-each-ref", "--format=%(refname:short)", "refs/heads"), root, "Read branches")
        branches = tuple(line.strip() for line in branches_result.stdout.splitlines() if line.strip()) if branches_result.success else ()

        log_result = self._query(("log", "-20", "--format=%h%x1f%s%x1f%D%x1e"), root, "Read history")
        commits = parse_log_records(log_result.stdout) if log_result.success else ()

        remotes_result = self._query(("remote",), root, "Read remotes")
        remote_names = tuple(line.strip() for line in remotes_result.stdout.splitlines() if line.strip()) if remotes_result.success else ()
        remotes = tuple(self._load_remote(root, name) for name in remote_names)
        return RepositoryState(root, branch, detached, branches, files, commits, remotes)

    def _load_remote(self, root: Path, name: str) -> RemoteInfo:
        fetch = self._query(("remote", "get-url", "--all", name), root, "Read remote URL")
        push = self._query(("remote", "get-url", "--push", "--all", name), root, "Read remote push URL")
        return RemoteInfo(
            name,
            tuple(line for line in fetch.stdout.splitlines() if line) if fetch.success else (),
            tuple(line for line in push.stdout.splitlines() if line) if push.success else (),
        )

    def _query(self, args: tuple[str, ...], cwd: Path, summary: str):
        command = GitCommand(
            operation="repository.query",
            args=args,
            summary=summary,
            explanation="Reads repository information using Git.",
            risk_level=RiskLevel.READ_ONLY,
        )
        return self.executor.execute(command, cwd)

