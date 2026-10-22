import os
import queue
import subprocess
import sys
import threading
import tkinter as tk

from git_auth import is_git_installed, is_gh_installed, is_github_authenticated
from git_remote import has_git_remote, git_remote_origin, verify_git_remote, change_git_remote
from git_operations import (
    is_git_repository,
    get_repository_status,
    has_staged_changes,
    collect_staged_files,
    stages_changes,
    git_push_changes,
)
from git_staging import git_add_stages, git_add_specific

# ---------- Palette (matches the terminal version) ----------
BG = "#0C0C0C"
ACCENT = "#61D6D6"   # bold cyan  - headings, borders, prompts
YELLOW = "#F9F1A5"   # bold yellow - warnings, instructions
GREEN = "#16C60C"    # bold green - success
RED = "#E74856"      # bold red - errors
WHITE = "#CCCCCC"    # normal text
HOVER = "#173A3A"    # button fill when the mouse is over it
MUTED = "#555555"    # disabled buttons
INPUT_BG = "#1A1A1A"

COLORS = {"white": WHITE, "accent": ACCENT, "yellow": YELLOW, "green": GREEN, "red": RED}

TITLE_FONT = ("Arial", 16, "bold")
CHECK_FONT = ("Arial", 9, "bold")

# These widgets are created in main(); the functions below look them up when they run
window = None
terminal_text = None
remote_label = None
check_status = []      # the "Done" / "Failed" label of each startup check
action_buttons = []    # buttons that get disabled while a job runs

# busy = how many background jobs are running, locked = a startup check failed for good
app_state = {"busy": 0, "locked": False}


# =====================================================================
# Drawing helpers: rounded boxes and rounded buttons
# =====================================================================

# Draws a rectangle with rounded corners (tkinter has no built-in one)
def round_rect(canvas, x1, y1, x2, y2, radius, **options):
    points = [
        x1 + radius, y1, x1 + radius, y1, x2 - radius, y1, x2 - radius, y1,
        x2, y1, x2, y1 + radius, x2, y1 + radius, x2, y2 - radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x2 - radius, y2,
        x1 + radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius,
        x1, y2 - radius, x1, y1 + radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **options)


# A rounded box. Returns (box, body): grid/pack the box, put your widgets in the body.
def make_box(parent, title="", height=1):
    canvas = tk.Canvas(parent, width=1, height=height, bg=BG, highlightthickness=0)
    body = tk.Frame(canvas, bg=BG)
    body_id = canvas.create_window(0, 0, window=body, anchor="nw")

    def redraw(event):
        canvas.delete("border")

        top = 16 if title else 2
        round_rect(canvas, 2, top, event.width - 2, event.height - 2, 22,
                   outline=ACCENT, width=2, fill="", tags="border")

        if title:
            text_id = canvas.create_text(28, top, text=title, anchor="w",
                                         font=TITLE_FONT, fill=ACCENT, tags="border")
            x1, y1, x2, y2 = canvas.bbox(text_id)
            gap_id = canvas.create_rectangle(x1 - 8, y1, x2 + 8, y2,
                                             fill=BG, outline="", tags="border")
            canvas.tag_raise(text_id, gap_id)

        body_y = top + (22 if title else 8)
        canvas.coords(body_id, 14, body_y)
        canvas.itemconfigure(body_id,
                             width=max(1, event.width - 28),
                             height=max(1, event.height - body_y - 10))

    canvas.bind("<Configure>", redraw)
    return canvas, body


# A rounded button. It lights up on hover, fills in while pressed, and calls command()
# when you release the mouse on it. button.set_enabled(False) greys it out.
def make_button(parent, text, command=None, font=("Arial", 14, "bold"), width=1, height=44):
    canvas = tk.Canvas(parent, width=width, height=height, bg=BG,
                       highlightthickness=0, cursor="hand2")
    state = {"hover": False, "pressed": False, "enabled": True}

    def draw():
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()

        if not state["enabled"]:
            border, fill, label = MUTED, "", MUTED
        elif state["pressed"]:
            border, fill, label = ACCENT, ACCENT, BG
        elif state["hover"]:
            border, fill, label = ACCENT, HOVER, WHITE
        else:
            border, fill, label = ACCENT, "", WHITE

        round_rect(canvas, 2, 2, w - 2, h - 2, 14, outline=border, width=2, fill=fill)
        canvas.create_text(w / 2, h / 2, text=text, font=font, fill=label)

    def on_enter(_event):
        state["hover"] = True
        draw()

    def on_leave(_event):
        state["hover"] = False
        state["pressed"] = False
        draw()

    def on_press(_event):
        if state["enabled"]:
            state["pressed"] = True
            draw()

    def on_release(_event):
        was_pressed = state["pressed"]
        state["pressed"] = False
        draw()
        if was_pressed and state["hover"] and command:
            command()

    def set_enabled(enabled):
        state["enabled"] = enabled
        state["hover"] = False
        state["pressed"] = False
        canvas.config(cursor="hand2" if enabled else "arrow")
        draw()

    canvas.bind("<Configure>", lambda _event: draw())
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.set_enabled = set_enabled

    return canvas


# =====================================================================
# Pop-up dialogs (they replace console.input from the terminal version)
# =====================================================================

def open_dialog(title, width, height):
    dialog = tk.Toplevel(window)
    dialog.title(title)
    dialog.configure(bg=BG)
    dialog.transient(window)
    dialog.resizable(False, False)

    x = window.winfo_rootx() + (window.winfo_width() - width) // 2
    y = window.winfo_rooty() + (window.winfo_height() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.bind("<Escape>", lambda _event: dialog.destroy())

    box, body = make_box(dialog, title)
    box.pack(fill="both", expand=True, padx=15, pady=15)
    return dialog, body


# Blocks (while keeping the window alive) until the dialog is closed
def run_dialog(dialog):
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_force()
    dialog.wait_window()


def dialog_message(body, message, width):
    label = tk.Label(body, text=message, font=("Arial", 11, "bold"), fg=WHITE, bg=BG,
                     wraplength=width - 90, justify="left")
    label.pack(anchor="w", padx=10, pady=(0, 10))


# Shows a message and one button per choice. Returns the chosen text, or None if closed.
def ask_choice(title, message, choices):
    answer = []
    width = 480
    dialog, body = open_dialog(title, width, 170 + 56 * len(choices))
    dialog_message(body, message, width)

    def choose(choice):
        answer.append(choice)
        dialog.destroy()

    for choice in choices:
        button = make_button(body, choice, lambda choice=choice: choose(choice), height=40)
        button.pack(fill="x", padx=10, pady=5)

    run_dialog(dialog)
    return answer[0] if answer else None


def ask_yes_no(title, message):
    return ask_choice(title, message, ["Yes", "No"]) == "Yes"


# Asks for one line of text. Returns the text, or None if cancelled.
def ask_text(title, message):
    answer = []
    width = 520
    dialog, body = open_dialog(title, width, 310)
    dialog_message(body, message, width)

    entry = tk.Entry(body, font=("Consolas", 11), bg=INPUT_BG, fg=WHITE,
                     insertbackground=WHITE, relief="flat", highlightthickness=2,
                     highlightbackground=ACCENT, highlightcolor=ACCENT)
    entry.pack(fill="x", padx=10, ipady=6)
    entry.focus_set()

    def submit():
        answer.append(entry.get().strip())
        dialog.destroy()

    entry.bind("<Return>", lambda _event: submit())
    make_button(body, "OK", submit, height=40).pack(fill="x", padx=10, pady=(14, 5))
    make_button(body, "Cancel", dialog.destroy, height=40).pack(fill="x", padx=10, pady=5)

    run_dialog(dialog)
    return answer[0] if answer else None


# Shows a list of files to tick. Returns the chosen file names, or None if cancelled.
def ask_files(title, files):
    answer = []
    width = 520
    rows = min(len(files), 10)
    dialog, body = open_dialog(title, width, 290 + rows * 24)
    dialog_message(body, "Select the file(s) to stage (click to select, click again to unselect):", width)

    listbox = tk.Listbox(body, selectmode="multiple", height=rows, exportselection=False,
                         font=("Consolas", 11), bg=BG, fg=WHITE, bd=0, highlightthickness=2,
                         highlightbackground=ACCENT, highlightcolor=ACCENT,
                         selectbackground=ACCENT, selectforeground=BG, activestyle="none")
    for file in files:
        listbox.insert("end", file)
    listbox.pack(fill="both", expand=True, padx=10)

    def submit():
        answer.append([files[index] for index in listbox.curselection()])
        dialog.destroy()

    make_button(body, "Stage Selected", submit, height=40).pack(fill="x", padx=10, pady=(14, 5))
    make_button(body, "Cancel", dialog.destroy, height=40).pack(fill="x", padx=10, pady=5)

    run_dialog(dialog)
    return answer[0] if answer else None


# =====================================================================
# Terminal output
# =====================================================================

def terminal_write(text="", color="white", end="\n"):
    terminal_text.config(state="normal")
    terminal_text.insert("end", text + end, color)
    terminal_text.config(state="disabled")
    terminal_text.see("end")


# Prints a table like the terminal version: #, File, Status (status in its own color)
def terminal_table(title, rows):
    file_width = max([len("File")] + [len(row["file"]) for row in rows]) + 4

    terminal_write(f"\n{title}", "accent")
    terminal_write(f"{'#':<5}{'File':<{file_width}}Status", "accent")

    for index, row in enumerate(rows, start=1):
        terminal_write(f"{index:<5}{row['file']:<{file_width}}", "white", end="")
        terminal_write(row["status"], row["color"])


# =====================================================================
# Background jobs: run slow Git commands off the window's thread
# =====================================================================

jobs = queue.Queue()


def refresh_buttons():
    enabled = app_state["busy"] == 0 and not app_state["locked"]
    for button in action_buttons:
        button.set_enabled(enabled)


# Runs work() in a thread. When it finishes, when_done(result) runs on the window's thread.
def run_in_background(work, when_done):
    app_state["busy"] += 1
    refresh_buttons()

    def worker():
        try:
            jobs.put((when_done, work()))
        except Exception as error:
            jobs.put((report_crash, error))

    threading.Thread(target=worker, daemon=True).start()


def check_jobs():
    window.after(50, check_jobs)

    while not jobs.empty():
        when_done, result = jobs.get()
        try:
            when_done(result)
        except Exception as error:
            report_crash(error)
        finally:
            app_state["busy"] -= 1
            refresh_buttons()


def report_crash(error):
    terminal_write(f"\nUnexpected error: {error}", "red")


# Stops the app from running Git actions (used when a startup check fails for good)
def lock_app(*lines):
    app_state["locked"] = True
    for index, line in enumerate(lines):
        terminal_write(line, "red" if index == 0 else "yellow")


# =====================================================================
# Helpers that wrap git/gh commands the src modules don't cover
# =====================================================================

def has_project_files():
    return any(item != ".git" for item in os.listdir("."))


def get_remote_name():
    result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)

    if result.returncode != 0:
        return None

    url = result.stdout.strip().removesuffix(".git").rstrip("/")
    return "/".join(url.replace(":", "/").split("/")[-2:])


def initialize_repository():
    result = subprocess.run(["git", "init"], capture_output=True, text=True)
    return result.returncode == 0 and is_git_repository(), result.stderr


# gh auth login is interactive, so on Windows it gets its own visible console window
# ("start /wait" opens that window and waits until the login there is finished)
def run_github_login():
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "start", "GitHub Login", "/wait", "gh", "auth", "login"])
    else:
        subprocess.run(["gh", "auth", "login"])

    return is_github_authenticated()


# GitPal runs without a console, so every git/gh command would flash a black window on
# Windows. This makes every command run hidden, including the ones in the other modules.
def hide_console_windows():
    if sys.platform != "win32":
        return

    original_init = subprocess.Popen.__init__

    def quiet_init(self, *args, **kwargs):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        original_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = quiet_init


def apply_remote(action, url):
    if not verify_git_remote(url):
        return "unverified"
    return "ok" if action(url) else "failed"


def refresh_remote_label():
    def show(name):
        remote_label.config(text=f"Current Remote: {name or 'None'}")

    run_in_background(get_remote_name, show)


# =====================================================================
# Startup checks (same order as main.py)
# =====================================================================

def set_check(index, ok):
    if ok:
        check_status[index].config(text=" Done", fg=GREEN)
    else:
        check_status[index].config(text=" Failed", fg=RED)


def start_checks():
    terminal_write("Running startup checks...", "accent")
    run_in_background(is_git_installed, after_git_check)


def after_git_check(installed):
    set_check(0, installed)

    if installed:
        terminal_write("Git is installed.", "green")
        run_in_background(is_gh_installed, after_gh_check)
    else:
        lock_app("Git is not installed.",
                 "Please install Git to use this tool.",
                 "Visit: https://git-scm.com/downloads for installation instructions.")


def after_gh_check(installed):
    set_check(1, installed)

    if installed:
        terminal_write("GitHub CLI is installed.", "green")
        run_in_background(is_github_authenticated, after_auth_check)
    else:
        lock_app("GitHub CLI is not installed.",
                 "Please install the GitHub CLI to use this tool.",
                 "Visit: https://cli.github.com/ for installation instructions.")


def after_auth_check(authenticated):
    if authenticated:
        set_check(2, True)
        terminal_write("GitHub account is already authenticated.", "green")
        check_repository()
        return

    terminal_write("GitHub authentication failed.", "yellow")

    if ask_yes_no("GitHub Authentication", "Do you want to authenticate with GitHub?"):
        terminal_write("Finish logging in inside the window that just opened.", "yellow")
        run_in_background(run_github_login, after_login)
    else:
        set_check(2, False)
        lock_app("GitHub authentication canceled.")


def after_login(authenticated):
    set_check(2, authenticated)

    if authenticated:
        terminal_write("Successfully authenticated with GitHub.", "green")
        check_repository()
    else:
        lock_app("GitHub authentication canceled.")


def check_repository():
    run_in_background(is_git_repository, after_repository_check)


def after_repository_check(is_repository):
    if is_repository:
        set_check(3, True)
        terminal_write("This is a Git repository.", "green")
        check_remote()
        return

    terminal_write("This is not a Git repository.", "red")

    if ask_yes_no("Git Repository Initialization",
                  "Do you want to initialize a new Git repository here?"):
        run_in_background(initialize_repository, after_initialize)
    else:
        set_check(3, False)
        lock_app("Git repository initialization canceled.")


def after_initialize(result):
    ok, error = result
    set_check(3, ok)

    if ok:
        terminal_write("Successfully initialized a new Git repository.", "green")
        check_remote()
    else:
        lock_app("Failed to initialize a Git repository.")
        terminal_write(error)


def check_remote():
    run_in_background(has_git_remote, after_remote_check)


def after_remote_check(has_remote):
    if has_remote:
        set_check(4, True)
        terminal_write("This Git repository is connected to a remote repository.", "green")
        finish_startup()
        return

    terminal_write("This Git repository is not connected to any remote repository.", "red")

    if ask_yes_no("Remote Repository Connection",
                  "Do you want to connect this to an existing remote repository?"):
        url = ask_text("Remote Repository Connection",
                       "Paste your remote origin repository link here:")

        if url:
            terminal_write("Verifying the remote repository...", "white")
            run_in_background(lambda: apply_remote(git_remote_origin, url),
                              remote_result_handler("Successfully connected to the remote repository.",
                                                    during_startup=True))
            return

    set_check(4, False)
    terminal_write("Remote repository connection canceled.", "yellow")
    finish_startup()


def finish_startup():
    terminal_write("Startup checks complete.\n", "accent")
    refresh_remote_label()


# =====================================================================
# Main actions (the five buttons + Change Remote)
# =====================================================================

def show_status():
    terminal_write("\n> Repository Status", "accent")

    if not has_project_files():
        terminal_write("Warning: This repository contains no project files.", "red")
        terminal_write("Please add at least one file before attempting to stage, commit, or push.", "yellow")
        return

    run_in_background(get_repository_status, after_status)


def after_status(status):
    if status is None:
        terminal_write("Failed to retrieve repository status.", "red")
    elif not status:
        terminal_write("Working tree is clean.", "green")
    else:
        terminal_table("Repository Changes", status)


def stage_changes():
    terminal_write("\n> Stage Changes", "accent")
    run_in_background(get_repository_status, after_stage_status)


def after_stage_status(status):
    if status is None:
        terminal_write("Failed to retrieve repository status.", "red")
        return

    if not status:
        terminal_write("There are no changes to stage.", "yellow")
        terminal_write("Please add a file or make a change before staging.", "yellow")
        return

    choice = ask_choice("Stage Changes", "What would you like to stage?",
                        ["Stage All Changes", "Stage Specific Changes"])

    if choice == "Stage All Changes":
        run_in_background(git_add_stages, after_staged)

    elif choice == "Stage Specific Changes":
        files = ask_files("Stage Specific Changes", [item["file"] for item in status])

        if not files:
            terminal_write("No files selected.", "yellow")
            return

        lookup = {item["file"]: item for item in status}
        terminal_write("Attention: You are about to stage the following files:", "yellow")
        terminal_table("Files to be staged", [lookup[file] for file in files])

        if ask_yes_no("Stage Changes", "Are you sure you want to continue?"):
            run_in_background(lambda: git_add_specific(files), after_staged)
        else:
            terminal_write("Staging canceled.", "yellow")

    else:
        terminal_write("Staging canceled.", "yellow")


def after_staged(staged):
    if staged is None:
        terminal_write("Failed to stage changes.", "red")
    else:
        terminal_table("Successfully staged files:", staged)


def commit_changes():
    terminal_write("\n> Commit Changes", "accent")
    run_in_background(has_staged_changes, after_commit_check)


def after_commit_check(has_staged):
    if has_staged is None:
        terminal_write("Failed to retrieve repository status.", "red")
    elif not has_staged:
        terminal_write("There are no staged changes to commit.", "yellow")
        terminal_write("Please stage changes before committing.", "yellow")
    else:
        run_in_background(collect_staged_files, after_collect_staged)


def after_collect_staged(files):
    terminal_table("Files to be committed", files)

    if not ask_yes_no("Commit Changes", "Are you sure you want to continue?"):
        terminal_write("Commit canceled.", "yellow")
        return

    message = ask_text("Commit Changes", "Type your commit message:")

    if message is None:
        terminal_write("Commit canceled.", "yellow")
        return

    run_in_background(lambda: stages_changes(message), after_commit)


def after_commit(committed):
    if committed:
        terminal_write("Successfully committed changes.", "green")
    else:
        terminal_write("Failed to commit changes.", "red")


def push_changes():
    terminal_write("\n> Push Changes", "accent")
    terminal_write("Pushing...", "white")
    run_in_background(git_push_changes, after_push)


def after_push(result):
    if result is True:
        terminal_write("Successfully pushed changes.", "green")
        return

    terminal_write("Attention: Push failed.", "red")
    terminal_write("\nGit Error:", "red")
    terminal_write(result["error"])
    terminal_write("\nWhy this happened:", "white")
    terminal_write(result["explanation"])
    terminal_write("\nRecommended action:", "yellow")
    terminal_write(result["recommended"])


def change_remote():
    terminal_write("\n> Change Remote", "accent")
    run_in_background(has_git_remote, after_remote_exists)


def after_remote_exists(has_remote):
    if has_remote:
        if not ask_yes_no("Change Remote", "Are you sure you would like to change remote origin?"):
            return
        action, prompt = change_git_remote, "Please paste your new remote link here:"
        success = "Successfully changed the remote repository."
    else:
        action, prompt = git_remote_origin, "Paste your remote origin repository link here:"
        success = "Successfully connected to the remote repository."

    url = ask_text("Change Remote", prompt)

    if not url:
        terminal_write("Remote change canceled.", "yellow")
        return

    terminal_write("Verifying the remote repository...", "white")
    run_in_background(lambda: apply_remote(action, url), remote_result_handler(success))


# Builds the "what to do when the remote verify/change finishes" function
def remote_result_handler(success_message, during_startup=False):
    def handle(result):
        if result == "ok":
            terminal_write(success_message, "green")
            set_check(4, True)
        elif result == "unverified":
            terminal_write("The GitHub repository could not be found or accessed.", "yellow")
            terminal_write("Please check the repository URL and your GitHub permissions.", "yellow")
        else:
            terminal_write("Failed to connect to the remote repository.", "red")

        if during_startup:
            if result != "ok":
                set_check(4, False)
            finish_startup()
        elif result == "ok":
            refresh_remote_label()

    return handle


# =====================================================================
# Layout + entry point
# =====================================================================

# The `gitpal` command. There is no console to print errors to, so a crash is shown in a box.
def main():
    hide_console_windows()

    try:
        run_app()
    except Exception as error:
        from tkinter import messagebox
        messagebox.showerror("GitPal", f"GitPal crashed:\n\n{error}")
        raise


def run_app():
    global window, terminal_text, remote_label

    # A Git command that wants a password should fail (and show its error) instead of
    # waiting for typing in a console the user can't see
    os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")

    window = tk.Tk()
    window.title("GitPal")
    window.geometry("1100x740")
    window.minsize(1000, 650)
    window.configure(bg=BG)

    window.columnconfigure(0, weight=3)
    window.columnconfigure(1, weight=1)
    window.rowconfigure(3, weight=1)

    # ---------- Header ----------
    title_label = tk.Label(window, text="GitPal", font=("Arial", 32, "bold"), fg=ACCENT, bg=BG)
    title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=40, pady=(20, 0))

    line = tk.Frame(window, height=2, bg=ACCENT)
    line.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=20)

    # ---------- Git Authentication Checker ----------
    auth_box, auth_body = make_box(window, "Git Authentication Checker", height=80)
    auth_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5)

    check_names = ["Git installation", "gh installation", "Github authentication",
                   "Git repository", "remote repository"]

    for column, name in enumerate(check_names):
        auth_body.columnconfigure(column, weight=1)

        cell = tk.Frame(auth_body, bg=BG)
        cell.grid(row=0, column=column, sticky="w")

        tk.Label(cell, text=f"Checking {name}:", font=CHECK_FONT, fg=WHITE, bg=BG).pack(side="left")

        status_label = tk.Label(cell, text=" ...", font=CHECK_FONT, fg=WHITE, bg=BG)
        status_label.pack(side="left")
        check_status.append(status_label)

    # ---------- Left column: current remote + terminal ----------
    left_column = tk.Frame(window, bg=BG)
    left_column.grid(row=3, column=0, sticky="nsew", padx=(20, 10), pady=10)

    remote_box, remote_body = make_box(left_column, height=64)
    remote_box.pack(fill="x")

    remote_label = tk.Label(remote_body, text="Current Remote: ...",
                            font=("Arial", 10, "bold"), fg=WHITE, bg=BG)
    remote_label.pack(side="left", padx=5)

    change_remote_button = make_button(remote_body, "Change Remote", change_remote,
                                       font=("Arial", 10, "bold"), width=150, height=36)
    change_remote_button.pack(side="right", padx=5)

    terminal_box, terminal_body = make_box(left_column)
    terminal_box.pack(fill="both", expand=True, pady=(10, 0))

    terminal_label = tk.Label(terminal_body, text=f"Terminal: {os.getcwd()}",
                              font=("Arial", 10, "bold"), fg=WHITE, bg=BG)
    terminal_label.pack(anchor="w", padx=5)

    terminal_text = tk.Text(terminal_body, width=1, height=1, bg=BG, fg=WHITE, bd=0,
                            font=("Consolas", 11), highlightthickness=0, wrap="word",
                            state="disabled")
    terminal_text.pack(fill="both", expand=True, padx=5, pady=(5, 0))

    for color_name, color_value in COLORS.items():
        terminal_text.tag_config(color_name, foreground=color_value)

    # ---------- Right column: buttons ----------
    buttons_box, buttons_body = make_box(window, "Buttons")
    buttons_box.grid(row=3, column=1, sticky="nsew", padx=(10, 20), pady=10)

    button_commands = {
        "Repository Status": show_status,
        "Stage Changes": stage_changes,
        "Commit Changes": commit_changes,
        "Push Changes": push_changes,
        "Exit": window.destroy,
    }

    # Every button except Exit gets disabled while a job runs or after a failed startup check
    action_buttons.append(change_remote_button)

    for name, command in button_commands.items():
        button = make_button(buttons_body, name, command)
        button.pack(fill="x", padx=15, pady=8)

        if name != "Exit":
            action_buttons.append(button)

    # ---------- Go ----------
    window.after(50, check_jobs)
    window.after(200, start_checks)
    window.mainloop()


if __name__ == "__main__":
    main()
