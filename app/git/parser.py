"""Parsers for Git's delimiter-based, machine-readable output."""

from __future__ import annotations

from app.models.repository_state import CommitInfo, FileState


def parse_status_porcelain_v2(output: str) -> tuple[str, bool, tuple[FileState, ...]]:
    """Parse `git status --porcelain=v2 --branch -z` output."""

    branch = "(unknown)"
    detached = False
    files: list[FileState] = []
    records = output.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if record.startswith("# branch.head "):
            branch = record.removeprefix("# branch.head ")
            detached = branch == "(detached)"
            continue
        if record.startswith("1 "):
            fields = record.split(" ", 8)
            if len(fields) == 9:
                files.append(FileState(fields[8], fields[1][0], fields[1][1]))
            continue
        if record.startswith("2 "):
            fields = record.split(" ", 9)
            original_path = records[index] if index < len(records) else None
            index += 1
            if len(fields) == 10:
                files.append(FileState(fields[9], fields[1][0], fields[1][1], original_path))
            continue
        if record.startswith("? "):
            files.append(FileState(record[2:], "?", "?"))
    return branch, detached, tuple(files)


def parse_log_records(output: str) -> tuple[CommitInfo, ...]:
    """Parse records emitted with %x1f fields and %x1e records."""

    commits: list[CommitInfo] = []
    for record in output.split("\x1e"):
        record = record.strip("\r\n\0 ")
        if not record:
            continue
        fields = record.split("\x1f", 2)
        if len(fields) >= 2:
            commits.append(CommitInfo(fields[0], fields[1], fields[2] if len(fields) > 2 else ""))
    return tuple(commits)

