from app.git.parser import parse_log_records, parse_status_porcelain_v2


def test_parse_porcelain_v2_status() -> None:
    output = (
        "# branch.oid abcdef\0"
        "# branch.head main\0"
        "1 M. N... 100644 100644 100644 aaaaaaa bbbbbbb staged.py\0"
        "1 .M N... 100644 100644 100644 aaaaaaa bbbbbbb changed file.py\0"
        "2 R. N... 100644 100644 100644 aaaaaaa bbbbbbb R100 new.py\0old.py\0"
        "? new file.txt\0"
    )
    branch, detached, files = parse_status_porcelain_v2(output)

    assert branch == "main"
    assert not detached
    assert [file.path for file in files] == ["staged.py", "changed file.py", "new.py", "new file.txt"]
    assert files[0].is_staged
    assert files[1].has_worktree_change
    assert files[2].original_path == "old.py"
    assert files[3].is_untracked


def test_parse_log_delimiters_allow_spaces_and_decorations() -> None:
    output = "abc123\x1fFix login flow\x1fHEAD -> main, tag: v1\x1edef456\x1fInitial commit\x1f\x1e"
    commits = parse_log_records(output)
    assert commits[0].short_hash == "abc123"
    assert commits[0].subject == "Fix login flow"
    assert commits[0].decorations == "HEAD -> main, tag: v1"
    assert commits[1].decorations == ""

