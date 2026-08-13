from app.git.command_registry import CommandRegistry
from app.models.command import RiskLevel
from app.services.command_service import CommandService, CommandValidationError


def test_commit_message_is_one_unmodified_argument() -> None:
    service = CommandService()
    message = 'Fix login for "quoted users"'
    command = service.build("changes.commit", message=message)

    assert command.argv == ["git", "commit", "-m", message]
    assert command.args[-1] == message
    assert '\\"quoted users\\"' in command.display_command


def test_stage_supports_multiple_paths_and_option_like_names() -> None:
    command = CommandService().stage(["folder with spaces/app.py", "-unusual.txt"])

    assert command.args == ("add", "--", "folder with spaces/app.py", "-unusual.txt")
    assert '"folder with spaces/app.py"' in command.display_command


def test_registry_lookup_and_unknown_operation() -> None:
    registry = CommandRegistry()
    assert registry.get("branch.create").argument_template == ("switch", "-c", "{branch}")
    assert len(registry.all()) >= 9

    try:
        registry.get("does.not.exist")
    except KeyError as error:
        assert "Unknown Git operation" in str(error)
    else:
        raise AssertionError("Unknown registry entry should fail")


def test_required_parameter_validation() -> None:
    try:
        CommandService().build("branch.create", branch="  ")
    except CommandValidationError:
        pass
    else:
        raise AssertionError("Blank branch should fail validation")


def test_risk_levels_for_structured_commands() -> None:
    service = CommandService()
    assert service.build("remote.fetch").risk_level is RiskLevel.NORMAL
    assert service.build("branch.delete", branch="old").risk_level is RiskLevel.CAUTION
    assert service.build("branch.merge", branch="topic", current_branch="main").risk_level is RiskLevel.CAUTION


def test_unstage_uses_index_removal_before_first_commit() -> None:
    command = CommandService().unstage(["new file.txt"], has_head=False)
    assert command.args == ("rm", "--cached", "--", "new file.txt")
