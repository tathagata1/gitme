"""Extensible definitions for the POC's structured Git operations."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.command import RiskLevel


@dataclass(frozen=True, slots=True)
class CommandDefinition:
    id: str
    name: str
    category: str
    argument_template: tuple[str, ...]
    parameters: tuple[str, ...]
    risk_level: RiskLevel
    explanation_template: str


class CommandRegistry:
    """Lookup table intentionally small enough to evolve without becoming a DSL."""

    def __init__(self) -> None:
        definitions = (
            CommandDefinition("repo.init", "Initialize Repository", "Repository", ("init",), (), RiskLevel.NORMAL, "Initializes an empty Git repository in the selected folder."),
            CommandDefinition("changes.commit", "Commit", "Changes", ("commit", "-m", "{message}"), ("message",), RiskLevel.NORMAL, "Creates a commit from staged changes with the message “{message}”."),
            CommandDefinition("branch.create", "Create Branch", "Branches", ("switch", "-c", "{branch}"), ("branch",), RiskLevel.NORMAL, "Creates a new branch called “{branch}” and immediately switches to it."),
            CommandDefinition("branch.switch", "Switch Branch", "Branches", ("switch", "{branch}"), ("branch",), RiskLevel.NORMAL, "Switches the working directory to branch “{branch}”."),
            CommandDefinition("branch.delete", "Delete Branch", "Branches", ("branch", "-d", "{branch}"), ("branch",), RiskLevel.CAUTION, "Deletes the local branch “{branch}” only if Git considers it safely merged."),
            CommandDefinition("branch.merge", "Merge Branch", "Branches", ("merge", "{branch}"), ("branch",), RiskLevel.CAUTION, "Merges “{branch}” into the currently checked-out branch “{current_branch}”."),
            CommandDefinition("remote.fetch", "Fetch", "Remote", ("fetch",), (), RiskLevel.NORMAL, "Downloads remote references and objects without merging them."),
            CommandDefinition("remote.pull", "Pull", "Remote", ("pull",), (), RiskLevel.NORMAL, "Fetches from the configured upstream and integrates its changes into the current branch."),
            CommandDefinition("remote.push", "Push", "Remote", ("push",), (), RiskLevel.NORMAL, "Uploads current commits using the branch’s configured upstream."),
        )
        self._definitions = {definition.id: definition for definition in definitions}

    def get(self, operation_id: str) -> CommandDefinition:
        try:
            return self._definitions[operation_id]
        except KeyError as error:
            raise KeyError(f"Unknown Git operation: {operation_id}") from error

    def all(self) -> tuple[CommandDefinition, ...]:
        return tuple(self._definitions.values())

