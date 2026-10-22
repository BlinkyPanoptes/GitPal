# GitPal

A pal for your daily Git needs. Run `gitpal` inside a repository and a desktop window opens, ready to check your setup, stage, commit and push.

## Requirements

- Python 3.10 or later, with tkinter (included with the standard Python installer on Windows and macOS; on Debian/Ubuntu install it with `sudo apt install python3-tk`)
- [Git](https://git-scm.com/downloads)
- [GitHub CLI (`gh`)](https://cli.github.com/), used for GitHub authentication and remote repository verification
- [pipx](https://pipx.pypa.io/) (recommended) for installing GitPal as a standalone command

## Installation

GitPal is installed once and run from anywhere — not activated inside a project's virtual environment.

### Option 1: pipx (recommended)

[pipx](https://pipx.pypa.io/) installs GitPal into its own isolated environment and puts the `gitpal` command on your `PATH`, so it works in any directory without you ever needing to create or activate a venv.

```bash
# Install pipx if you don't already have it
python -m pip install --user pipx
python -m pipx ensurepath

# Clone and install GitPal
git clone https://github.com/BlinkyPanoptes/GitPal.git
cd GitPal
pipx install .
```

After installation, restart your terminal (so the updated `PATH` takes effect) and run `gitpal`.

### Option 2: pip (in a virtual environment)

If you'd rather manage the environment yourself:

```bash
git clone https://github.com/BlinkyPanoptes/GitPal.git
cd GitPal
python -m venv .venv
.venv\Scripts\activate   # on Windows
source .venv/bin/activate # on macOS/Linux

pip install .
gitpal
```

### Updating

```bash
cd GitPal
git pull
pipx install . --force   # or: pip install --upgrade . (Option 2)
```

## Usage

Go to the local Git repository you want to work with and run `gitpal`. The window opens and your terminal is free again right away:

```bash
cd path/to/your/project
gitpal
```

GitPal works on the folder you start it from, and shows that folder at the top of its terminal panel.

The window has four areas:

- **Git Authentication Checker** — runs the startup checks (Git installed, `gh` installed, GitHub authenticated, Git repository, remote repository) and marks each one **Done** (green) or **Failed** (red). If something is missing it asks whether to fix it: log in to GitHub, run `git init`, or connect a remote repository.
- **Current Remote** — shows the repository you are connected to, with a **Change Remote** button.
- **Terminal** — shows the folder you are working in and prints the output of every action: green for success, yellow for instructions and warnings, red for errors.
- **Buttons**
  - **Repository Status** — view untracked, modified, and staged files at a glance
  - **Stage Changes** — stage everything (`git add .`) or pick specific files
  - **Commit Changes** — review what's staged, confirm, and enter a commit message
  - **Push Changes** — push to the configured remote, with plain-language explanations if it fails
  - **Exit** — quit GitPal

Choices and text input (staging options, file selection, commit message, remote URL) appear as pop-up windows. Git commands run in the background, so the window never freezes during a push, and the buttons are disabled while an action is running. When you log in to GitHub from GitPal, `gh auth login` opens in its own console window.

To run GitPal straight from a clone without installing it:

```bash
python src/gui.py
```

## Current Version

**v0.4.0 — Desktop GUI Release**

GitPal is a Git and GitHub assistant built with Python. It is currently in early development.

Version 0.4.0 turns GitPal into a desktop application built with tkinter. Running `gitpal` now opens a window that brings the startup checks, repository status, staging, committing, pushing and remote management together, with a built-in terminal output panel, rounded buttons that respond to hover and click, pop-up dialogs for input, and background execution of Git commands.

Version 0.3.0 expanded GitPal from a startup and repository configuration tool into a functional Git workflow assistant and packaged it as an installable `gitpal` command.

## Current Features

### GitHub Authentication

- Detect whether the user is authenticated with GitHub
- Authenticate through GitHub CLI when necessary
- Reuse an existing GitHub authentication session
- Support first-time GitHub authentication

### Local Git Repository

- Detect whether the current directory is a Git repository
- Ask the user whether to initialize Git when necessary
- Initialize a repository using `git init`
- Verify that the repository was successfully initialized

### Git Remote

- Detect whether the local repository has a configured remote
- Inform the user when no remote is configured
- Connect the local repository to an existing remote repository
- Verify that the remote GitHub repository exists and is accessible
- Configure the remote as `origin`
- View the current remote repository
- Change the configured remote repository
- Prevent invalid or inaccessible repositories from being configured as the remote

### Repository Status

- Retrieve the current Git repository status
- Parse Git status codes
- Identify untracked files
- Identify modified files
- Identify staged modifications
- Identify staged additions
- Identify staged deletions
- Detect when the working tree is clean
- Display status information as a color-coded table

### Directory Inspection

- Exclude the `.git` directory from the project files
- Warn the user when a repository contains no project files

### Git Operations

- Stage all changes, or only the files you select
- Display files successfully staged
- Validate that changes exist before staging
- Validate that staged changes exist before committing
- Commit changes using a user-provided commit message
- Push changes to the configured remote repository
- Automatically establish upstream tracking during the first push

### Git Error Handling

- Capture errors returned by Git operations
- Display the original Git error
- Provide a human-readable explanation for recognized Git errors
- Provide recommended actions when a recognized error occurs
- Provide a generic explanation for unrecognized Git errors

### Desktop Interface

- Startup checks with live Done / Failed status
- Offers to fix a failed check (GitHub login, `git init`, connect a remote)
- Shows the connected remote repository and lets you change it
- Repository status, staging, committing and pushing from one window
- Terminal-style output panel with color coding: green for success, yellow for instructions, red for errors, white for neutral messages
- Rounded interface with hover and click feedback on buttons
- Pop-up dialogs for choices, file selection and text input
- Git commands run in the background so the window stays responsive
- Opens without leaving a terminal or console windows behind (Windows)
