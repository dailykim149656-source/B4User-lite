# @b4user/cli

npm launcher for the B4User Python CLI.

## Install

```cmd
npm install -g @b4user/cli
b4user --help
```

The installer creates a private Python virtual environment under:

- Windows: `%LOCALAPPDATA%\b4user\runtime`
- macOS/Linux: `~/.b4user/runtime`

Python 3.11+ is required. If Python is not installed, install it first and rerun the npm command.

On Windows PowerShell, if `b4user` is not found after install, the global npm directory is not on PATH yet. Verify it with:

```powershell
npm prefix -g
```

On Windows this prefix is usually the directory that should be on PATH for global npm commands. Close and reopen PowerShell after installing Node/npm, or add that directory to the user PATH. For Python-only installs from PyPI, prefer this PATH-safe check:

```powershell
py -m pip install --user --upgrade b4user
py -m b4user
```

Running with no arguments opens the first-run menu. To print the full command list directly:

```powershell
py -m b4user --help
```

## Development overrides

Use a local checkout directly:

```cmd
cd F:\korean_simulator
npm install -g .\npm\b4user-cli
b4user --help
```

Use an explicit Python package spec instead of the published package:

```cmd
set B4USER_PYTHON_PACKAGE_SPEC=git+https://github.com/ORG/b4user.git
npm install -g @b4user/cli
```

Use an already-installed CLI executable:

```cmd
set B4USER_PYTHON_CLI=C:\path\to\b4user.exe
b4user --help
```
