# GitGod

GitGod is a polished, offline Electron desktop client for operating real local Git repositories visually while always showing the exact Git CLI command. It is designed to make Git understandable during normal use rather than hide it.

Every modifying workflow follows the same path:

```text
Visual action → command preview → explicit Execute → Git CLI → raw result → refreshed repository
```

There is no cloud service, account, database, LLM, or Git hosting API. Git commands are executed as argument arrays without a shell.

## Requirements

- Node.js 22 or later
- A local Git installation available as `git` on `PATH`
- Windows, macOS, or Linux (Windows is the primary tested target)

## Run the desktop app

```powershell
npm install
npm start
```

The repository picker uses Electron's native folder dialog. You can select the repository root or any subfolder inside a Git worktree; GitGod resolves and opens the worktree root. The last successfully opened repository is restored on the next launch.

## Tests

Electron and Git parsing tests:

```powershell
npm test
```

The original Python Git-domain tests remain available during the migration:

```powershell
pip install -r requirements.txt
python -m pytest
```

## Features

- Native folder picker for switching between any local Git worktrees
- Initialize a repository in a selected folder
- Repository dashboard with current branch, working changes, staged files, local branches, remotes, and recent commits
- Multi-select staging and unstaging with safe `--` path separation
- Commit, create/switch/delete/merge branch, fetch, pull, and push workflows
- Drag a branch onto the current branch to propose a merge
- Always-visible command preview with risk classification before execution
- Raw Git mode parsed into arguments and executed without a shell
- Extra confirmation for caution and destructive patterns
- Raw stdout, stderr, exit code, duration, and inspect-only session history
- Responsive dark desktop UI with keyboard shortcuts (`Ctrl/Cmd+O` to open, `Ctrl/Cmd+R` to refresh, `Esc` to close previews)

## Architecture

- `electron/main.cjs`: Electron lifecycle, native dialogs, and narrow IPC handlers
- `electron/preload.cjs`: context-isolated renderer bridge
- `electron/git-service.cjs`: shell-free Git execution, repository discovery, and state loading
- `electron/renderer`: HTML/CSS workspace and command composition
- `electron/*.test.cjs`: Node unit tests for porcelain/log parsing and command safety
- `app`, `tests`: UI-independent Python Git domain implementation and regression tests

The renderer has no direct Node.js access. `contextIsolation`, sandboxing, disabled Node integration, and a restrictive Content Security Policy keep filesystem and process access in the Electron main process.

## Safety

Git always runs through Node's `execFile("git", args, { shell: false })`. Arguments remain separate from the display string, so spaces and quote characters in paths or commit messages do not become shell syntax. `--` separates file paths from Git options when staging and unstaging.

Raw mode is intentionally advanced. Its destructive-pattern detection is conservative and cannot identify every risky combination or alias, so the exact command remains visible and still requires an explicit Execute step.
