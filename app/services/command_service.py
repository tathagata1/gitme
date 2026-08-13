"""Generate validated GitCommand objects from visual operations."""

from __future__ import annotations

import shlex
from typing import Iterable, Mapping

from app.git.command_registry import CommandRegistry
from app.models.command import GitCommand, RiskLevel


class CommandValidationError(ValueError):
    """Raised before an invalid command reaches preview or execution."""


class CommandService:
    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self.registry = registry or CommandRegistry()

    def build(self, operation_id: str, **parameters: str) -> GitCommand:
        definition = self.registry.get(operation_id)
        cleaned = {name: self._required(name, parameters.get(name, "")) for name in definition.parameters}
        context = {**parameters, **cleaned}
        args = tuple(part.format(**context) for part in definition.argument_template)
        explanation = definition.explanation_template.format(**context)
        return GitCommand(
            operation=operation_id,
            args=args,
            summary=definition.name,
            explanation=explanation,
            risk_level=definition.risk_level,
            argument_explanations=self._argument_explanations(operation_id, args),
        )

    def stage(self, paths: Iterable[str]) -> GitCommand:
        selected = self._paths(paths)
        return GitCommand(
            "changes.stage", ("add", "--", *selected), "Stage files",
            f"Stages {len(selected)} selected file(s), preparing their current changes for a commit.",
            RiskLevel.NORMAL,
            (("add", "Adds file content to Git’s staging area."), ("--", "Ends command options; following values are file paths."), (", ".join(selected), "Selected repository-relative file path(s).")),
        )

    def unstage(self, paths: Iterable[str], *, has_head: bool = True) -> GitCommand:
        selected = self._paths(paths)
        if not has_head:
            return GitCommand(
                "changes.unstage", ("rm", "--cached", "--", *selected), "Unstage files",
                f"Removes {len(selected)} selected file(s) from the first commit’s staging area while keeping the working files.",
                RiskLevel.NORMAL,
                (("rm", "Removes paths from Git’s index."), ("--cached", "Changes only the index and keeps working files."), ("--", "Ends command options; following values are file paths."), (", ".join(selected), "Selected repository-relative file path(s).")),
            )
        return GitCommand(
            "changes.unstage", ("restore", "--staged", "--", *selected), "Unstage files",
            f"Removes {len(selected)} selected file(s) from the next commit while keeping working files unchanged.",
            RiskLevel.NORMAL,
            (("restore", "Restores file content from another Git state."), ("--staged", "Updates only the staging area."), ("--", "Ends command options; following values are file paths."), (", ".join(selected), "Selected repository-relative file path(s).")),
        )

    def parse_raw(self, text: str) -> GitCommand:
        try:
            argv = shlex.split(text, posix=True)
        except ValueError as error:
            raise CommandValidationError(f"Could not parse the command: {error}") from error
        if not argv or argv[0].lower() not in ("git", "git.exe"):
            raise CommandValidationError("Custom commands must begin with 'git'.")
        if len(argv) == 1:
            raise CommandValidationError("Enter a Git subcommand after 'git'.")
        args = tuple(argv[1:])
        risk = self.classify_raw(args)
        return GitCommand(
            "raw", args, "Raw Git command",
            "Runs the entered Git arguments without a shell. Raw mode bypasses some structured safeguards; risk detection is intentionally not comprehensive.",
            risk,
            tuple((part, "Raw argument supplied by the user.") for part in args),
        )

    @staticmethod
    def classify_raw(args: tuple[str, ...]) -> RiskLevel:
        lowered = tuple(part.lower() for part in args)
        joined = " ".join(lowered)
        destructive = (
            lowered[:2] == ("reset", "--hard"),
            bool(lowered and lowered[0] == "clean" and any(part.startswith("-f") or "f" in part[1:] for part in lowered[1:] if part.startswith("-"))),
            bool(lowered and lowered[0] == "push" and any(part in ("--force", "-f", "--force-with-lease") for part in lowered[1:])),
            bool(lowered and lowered[0] == "branch" and any(part == "-D" for part in args)),
        )
        if any(destructive):
            return RiskLevel.DESTRUCTIVE
        if lowered[0] in ("merge", "rebase") or joined.startswith("branch -d "):
            return RiskLevel.CAUTION
        if lowered[0] in ("status", "log", "diff", "show", "fsck"):
            return RiskLevel.READ_ONLY
        return RiskLevel.NORMAL

    @staticmethod
    def _required(name: str, value: str) -> str:
        value = value.strip()
        if not value:
            raise CommandValidationError(f"{name.replace('_', ' ').title()} is required.")
        if "\0" in value or "\n" in value or "\r" in value:
            raise CommandValidationError(f"{name.replace('_', ' ').title()} cannot contain line breaks.")
        return value

    @staticmethod
    def _paths(paths: Iterable[str]) -> tuple[str, ...]:
        values = tuple(dict.fromkeys(str(path) for path in paths if str(path)))
        if not values:
            raise CommandValidationError("Select at least one file.")
        if any("\0" in path for path in values):
            raise CommandValidationError("A path contains an invalid null character.")
        return values

    @staticmethod
    def _argument_explanations(operation_id: str, args: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
        meanings: Mapping[str, str] = {
            "init": "Creates Git metadata in the selected folder.",
            "commit": "Records the staged snapshot in repository history.",
            "-m": "Uses the following value as the commit message.",
            "switch": "Changes which branch is checked out.",
            "-c": "Creates a new branch before switching to it.",
            "branch": "Manages local branches.",
            "-d": "Deletes a branch with Git’s merged-change safety check.",
            "merge": "Combines another branch into the current branch.",
            "fetch": "Downloads remote state without modifying working files.",
            "pull": "Fetches and integrates the current upstream branch.",
            "push": "Uploads commits to a configured remote/upstream.",
        }
        result: list[tuple[str, str]] = []
        for index, argument in enumerate(args):
            text = meanings.get(argument)
            if text is None:
                if operation_id == "changes.commit" and index == 2:
                    text = "The commit message, passed as one argument even when it contains spaces or quotes."
                elif "branch" in operation_id:
                    text = "The branch name selected or entered by the user."
                else:
                    text = "An argument for this Git operation."
            result.append((argument, text))
        return tuple(result)
