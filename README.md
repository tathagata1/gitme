# GitMe

GitMe is an offline Windows desktop client for working with local Git repositories. It presents changes, staged files, branches, remotes, and recent commits in a compact visual workspace while showing the exact Git command before it runs.

```text
Action → 5-second command preview → Git execution → result → repository refresh
```

GitMe does not require an account, cloud service, database, hosting-provider API, or Python runtime. Git commands run locally as argument arrays without a command shell.

## Features

- Open a Git worktree from its root or any subfolder
- Restore the last successfully opened repository on launch
- Initialize a repository in an existing folder
- View changed and staged files, local branches, remotes, and recent commits
- Stage or unstage selected files
- Commit staged changes
- Create, switch, merge, and safely delete branches
- Add, remove, fetch, pull, push, and synchronize remotes
- Drag a branch onto the current branch to preview a merge
- Preview every command with a risk level and five-second cancellation window
- Run custom `git` commands without invoking a shell
- Inspect stdout, stderr, exit code, and duration in session history

The dashboard panels fit their content and become scrollable at a reasonable maximum height, keeping small repositories compact and large repositories manageable.

## Windows requirements

- Windows 10 or 11, 64-bit
- [Node.js](https://nodejs.org/) 22.12 or later, including npm
- [Git for Windows](https://git-scm.com/download/win), available on `PATH`
- PowerShell, Windows Terminal, or Command Prompt

Confirm the required tools in PowerShell:

```powershell
node --version
npm --version
git --version
```

If `git` is not recognized, rerun the Git for Windows installer and select the option that adds Git to the command line, then open a new terminal.

## Run from source on Windows

Clone the project, enter its directory, and install the locked dependencies:

```powershell
git clone <repository-url> gitme
Set-Location gitme
npm ci
```

Start the desktop app:

```powershell
npm start
```

`npm run dev` currently starts the same Electron development build. In GitMe, select **Open folder** and choose either a repository root or a folder inside a Git worktree.

## Package for Windows

Packaging is handled by `electron-builder`. Run packaging on Windows after `npm ci`.

### Create an unpacked app

```powershell
npm run pack:win
```

Run the result directly:

```powershell
& ".\dist\win-unpacked\GitMe.exe"
```

The unpacked directory is useful for local testing and does not install shortcuts or register an uninstaller. Keep all files in `dist\win-unpacked` together when copying it to another computer.

### Create an installer

```powershell
npm run dist:win
```

The generated x64 NSIS installer is written to:

```text
dist\GitMe-Setup-1.0.0-x64.exe
```

Open the installer and choose an installation directory. It creates Start menu and desktop shortcuts. The target computer still needs Git for Windows on `PATH`; Node.js and Python are not required by the packaged app.

The project does not currently configure Windows code signing. Windows SmartScreen may therefore warn when opening a locally built installer. For public distribution, configure a signing certificate before publishing the installer.

## Tests

Run the active Electron command and repository-service tests:

```powershell
npm test
```

The repository also retains a UI-independent Python Git-domain implementation and regression suite from the earlier architecture. It is not used by the Electron runtime. To run those tests:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm run test:python
```

If PowerShell blocks the activation script, either use `Set-ExecutionPolicy -Scope Process Bypass` for that terminal or call `.venv\Scripts\python.exe` directly.

## Project structure

```text
electron/
  main.cjs                 Electron lifecycle, native dialogs, and IPC handlers
  preload.cjs              Restricted renderer-to-main bridge
  git-service.cjs          Repository discovery, parsing, and Git execution
  renderer/
    index.html             Desktop interface structure
    styles.css             Responsive dark interface
    app.js                 UI state, rendering, and workflows
    commands.js            Command construction and risk classification
  *.test.cjs               Active Node test suite
app/                       Legacy UI-independent Python Git domain
tests/                     Python regression tests
package.json               Runtime scripts and Windows packaging configuration
```

Only `electron/**/*` and `package.json` are included in the packaged application. Source tests and the legacy Python implementation are excluded.

## Security model

- Git runs through Node's `execFile("git", args, { shell: false })`.
- Arguments are kept separate from the human-readable command preview.
- File operations use `--` to separate paths from Git options.
- The renderer has no direct Node.js access.
- Electron runs with context isolation and sandboxing enabled and Node integration disabled.
- A restrictive Content Security Policy limits renderer resources to the application itself.

Custom-command mode is intentionally advanced. Its risk detection catches common destructive forms such as `reset --hard`, forced pushes, `clean -f`, and `branch -D`, but it cannot recognize every alias or risky combination. Always review the command preview before the countdown completes.

## Keyboard shortcuts

- `Ctrl+O`: open a repository
- `Ctrl+R`: refresh the current repository
- `Esc`: cancel a command preview or close a cancelable dialog

## License

GitMe is licensed under the [GNU General Public License v3.0](LICENSE).
