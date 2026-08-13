"""Command models used between the UI, services, and Git executor."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import re


class RiskLevel(IntEnum):
    """Safety classification shown before a command runs."""

    READ_ONLY = 0
    NORMAL = 1
    CAUTION = 2
    DESTRUCTIVE = 3


_SIMPLE_ARGUMENT = re.compile(r"^[A-Za-z0-9_./:@%+=,-]+$")


def display_argument(argument: str) -> str:
    """Quote one argument for display only; execution always uses argument arrays."""

    if argument and _SIMPLE_ARGUMENT.fullmatch(argument):
        return argument
    return '"' + argument.replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass(frozen=True, slots=True)
class GitCommand:
    """A validated, previewable Git operation."""

    operation: str
    args: tuple[str, ...]
    summary: str
    explanation: str
    risk_level: RiskLevel = RiskLevel.NORMAL
    argument_explanations: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def argv(self) -> list[str]:
        return ["git", *self.args]

    @property
    def display_command(self) -> str:
        return " ".join(display_argument(part) for part in self.argv)

    @property
    def detailed_explanation(self) -> str:
        details = [self.explanation, "", "git\nRuns the Git command-line application."]
        details.extend(f"{token}\n{text}" for token, text in self.argument_explanations)
        return "\n\n".join(details)

