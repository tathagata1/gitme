from pathlib import Path
import subprocess

from app.git.executor import GitExecutor
from app.git.repository import RepositoryService
from app.models.command import GitCommand, RiskLevel
from app.services.command_service import CommandService


def test_executor_handles_repository_path_with_spaces(tmp_path: Path) -> None:
    repository = tmp_path / "repository with spaces"
    repository.mkdir()
    executor = GitExecutor(timeout_seconds=10)
    init = GitCommand("test.init", ("init",), "Init", "Test initialization", RiskLevel.NORMAL)
    result = executor.execute(init, repository)

    assert result.success, result.stderr
    status = GitCommand("test.status", ("status", "--short"), "Status", "Test status", RiskLevel.READ_ONLY)
    assert executor.execute(status, repository).success


def test_executor_reports_missing_working_folder(tmp_path: Path) -> None:
    missing = tmp_path / "no such repository"
    command = GitCommand("test.status", ("status",), "Status", "Test status", RiskLevel.READ_ONLY)
    result = GitExecutor().execute(command, missing)
    assert not result.success
    assert "working folder was not found" in result.stderr


def test_real_repository_state_and_quoted_commit_message(tmp_path: Path) -> None:
    repository = tmp_path / "integration repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repository, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "POC Tests"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "poc@example.invalid"], cwd=repository, check=True)
    changed = repository / "file with spaces.txt"
    changed.write_text("hello\n", encoding="utf-8")

    executor = GitExecutor(timeout_seconds=10)
    service = CommandService()
    assert executor.execute(service.stage([changed.name]), repository).success
    message = 'A message with spaces and "quotes"'
    result = executor.execute(service.build("changes.commit", message=message), repository)
    assert result.success, result.stderr

    state = RepositoryService(executor).load_state(repository)
    assert state.root == repository.resolve()
    assert state.current_branch == "main"
    assert state.commits[0].subject == message
    assert not state.files
