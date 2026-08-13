import pytest

from app.models.command import RiskLevel
from app.services.command_service import CommandService, CommandValidationError


@pytest.mark.parametrize(
    ("text", "risk"),
    [
        ("git status --short", RiskLevel.READ_ONLY),
        ("git fsck --full", RiskLevel.READ_ONLY),
        ("git reset --hard HEAD~1", RiskLevel.DESTRUCTIVE),
        ("git clean -fd", RiskLevel.DESTRUCTIVE),
        ("git push --force", RiskLevel.DESTRUCTIVE),
        ("git branch -D experiment", RiskLevel.DESTRUCTIVE),
        ("git merge topic", RiskLevel.CAUTION),
    ],
)
def test_raw_risk_detection(text: str, risk: RiskLevel) -> None:
    assert CommandService().parse_raw(text).risk_level is risk


def test_raw_parsing_preserves_quoted_argument() -> None:
    command = CommandService().parse_raw('git log --grep "fix login"')
    assert command.argv == ["git", "log", "--grep", "fix login"]


@pytest.mark.parametrize("text", ["", "echo hello", "git", 'git commit -m "unfinished'])
def test_invalid_raw_commands_are_rejected(text: str) -> None:
    with pytest.raises(CommandValidationError):
        CommandService().parse_raw(text)

