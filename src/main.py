import subprocess
from error_handler import handle_keyboard_interrupt
from git_auth import is_github_authenticated, authenticate_github, is_gh_installed, is_git_installed
from git_remote import has_git_remote, git_remote_origin, remote_repository, verify_git_remote
from git_operations import collect_staged_files, get_repository_status, stages_changes, git_push_changes, has_staged_changes, is_git_repository
from git_staging import stage_changes
from file_operations import check_file_directory
from ui.loading import loading_screen
from ui.colors import color_text
from ui.tables import print_menu_table, print_confirm_commit_table, print_repository_changes_table
from ui.colors import console
import time
import sys

# Back to Main Menu
def return_to_menu():
    user_input = console.input("\n[bold cyan]Back to Main Menu? (y/n) > [/bold cyan]")

    if user_input.lower() != 'y':
        exit_gitpal()

# System Exit
def exit_gitpal():
    print("\nExited GitPal.\n")
    sys.exit()

# Main Menu
def main_menu():
    while True:

        print_menu_table()

        console.rule("[bold cyan]GitPal Menu[/bold cyan]")
        user_choice = console.input("[bold cyan]Select an option > [/bold cyan]")

        if user_choice == "1":

            if check_file_directory():
                repo_status = get_repository_status()

                if repo_status is None:
                    color_text("\nFailed to retrieve repository status.", "red")

                elif not repo_status:
                    color_text("\nWorking tree is clean.", "green")

                else:
                    print_repository_changes_table(repo_status)

            return_to_menu()

        elif user_choice == "2":

            stage_changes()

            return_to_menu()

        elif user_choice == "3":

            staged_changes = has_staged_changes()

            if staged_changes is None:
                color_text("\nFailed to retrieve repository status.", "red")

            elif not staged_changes:
                color_text("\nThere are no staged changes to commit.", "yellow")
                color_text("Please stage changes before committing.", "yellow")

                return_to_menu()

            else:
                files_with_status = collect_staged_files()
                print_confirm_commit_table(files_with_status)
                confirm = console.input("\n[bold cyan]Are you sure you want to continue? (y/n) > [/bold cyan]")

                if confirm.lower() != 'y':
                    color_text("\nCommit canceled.", "yellow")
                    return_to_menu()

                else:
                    console.rule("[bold cyan]Enter a commit message[/bold cyan]")
                    commit_message = console.input("\n[bold cyan]Type your commit message > [/bold cyan]")

                    if stages_changes(commit_message):
                        color_text("\nSuccessfully committed changes.", "green")

                        return_to_menu()
                    else:
                        color_text("\nFailed to commit changes.", "red")

                        return_to_menu()

        elif user_choice == "4":

            push_results = git_push_changes()

            if push_results is True:
                color_text("\nSuccessfully pushed changes.", "green")

                return_to_menu()

            else:
                color_text("\nAttention: Push failed.", "red")

                color_text("\nGit Error:", "red")
                print(push_results["error"])

                print("\nWhy this happened:")
                print(push_results["explanation"])

                color_text("\nRecommended action:", "yellow")
                print(push_results['recommended'])

                return_to_menu()

        elif user_choice == "5":
            remote_repository()

        elif user_choice == "6":
            exit_gitpal()

        else:
            print("\nInvalid option. Please try again.")


# Main program execution
def main():
    try:
        # ==========================================
        # 0. CHECK GITHUB CLI IF INSTALLED
        # ==========================================

        loading_screen("Checking Git installation: ")

        if is_git_installed():
            color_text("Git is installed.\n", "green")
        else:
            color_text("Git is not installed.", "red")
            color_text("Please install the Git to use this tool.", "yellow")
            color_text("Visit: (https://git-scm.com/downloads) for installation instructions.", "yellow")
            exit_gitpal()

        loading_screen("Checking gh installation: ")

        if is_gh_installed():
            color_text("GitHub CLI is installed.\n", "green")
        else:
            color_text("GitHub CLI is not installed.", "red")
            color_text("Please install the GitHub CLI to use this tool.", "yellow")
            color_text("Visit: https://cli.github.com/ for installation instructions.", "yellow")
            exit_gitpal()

        # ==========================================
        # 1. CHECK GITHUB AUTHENTICATION
        # ==========================================

        loading_screen("Checking Github authentication: ")

        if is_github_authenticated():
            color_text("GitHub account is already authenticated.\n", "green")

        else:
            color_text("GitHub authentication failed.", "yellow")

            console.rule("[bold cyan]GitHub Authentication[/bold cyan]")
            user_auth_answer = console.input(
                "[bold cyan]Do you want to authenticate with GitHub? (y/n) > [/bold cyan]"
            )

            if user_auth_answer.lower() == 'y':

                if authenticate_github():
                    color_text("Successfully authenticated with GitHub.\n", "green")

                else:
                    print("GitHub authentication canceled.")
                    exit_gitpal()

            else:
                print("GitHub authentication canceled.")
                exit_gitpal()

        # ==========================================
        # 2. CHECK LOCAL GIT REPOSITORY
        # ==========================================

        loading_screen("Checking Git repository: ")

        if is_git_repository():
            color_text("This is a Git repository.\n", "green")

        else:
            color_text("This is not a Git repository.", "red")

            console.rule("[bold cyan]Git Repository Initialization[/bold cyan]")
            user_answer = console.input(
                "[bold cyan]Do you want to initialize a new Git repository here? (y/n) > [/bold cyan]"
            )

            if user_answer.lower() == 'y':

                # Run the git command 'git init'
                init_git_repo = subprocess.run(
                    ['git', 'init'],
                    capture_output=True,
                    text=True
                )

                if init_git_repo.returncode == 0:
                    color_text("\nSuccessfully initialized a new Git repository.", "green")

                    # Check if the repository is now initialized
                    if is_git_repository():
                        color_text("This is now a Git repository.\n", "green")
                    else:
                        color_text("Failed to verify the Git repository initialization.\n", "red")

                else:
                    color_text("\nFailed to initialize a Git repository.", "red")
                    color_text("\nGit Error:", "red")
                    print(init_git_repo.stderr)

            else:
                print("\nGit repository initialization canceled.")
                exit_gitpal()

        # ==========================================
        # 3. CHECK GIT REMOTE
        # ==========================================

        if has_git_remote():

            loading_screen("Checking remote repository: ")

            color_text("This Git repository is connected to a remote repository.", "green")
        else:
            color_text("This Git repository is not connected to any remote repository.", "red")

            console.rule("[bold cyan]Remote Repository Connection[/bold cyan]")
            user_input = console.input("[bold cyan]Do you want to connect this into an existing remote repository? (y/n) > [/bold cyan]")

            if user_input.lower() == 'y':
                remote_origin_input = console.input("\n[bold cyan]Paste your remote origin repository link here > [/bold cyan]")

                print()
                loading_screen("Verifying the remote repository: ")

                if verify_git_remote(remote_origin_input):

                    if git_remote_origin(remote_origin_input):
                        color_text("Successfully connected to the remote repository.", "green")

                    else:
                        color_text("Failed to connect to the remote repository", "red")

                else:
                    color_text("The GitHub repository could not be found or accessed.", "yellow")
                    color_text("Please check the repository URL and your GitHub permissions.", "yellow")

                    time.sleep(3)


            else:
                print("\nRemote repository connection canceled.")


        # ==========================================
        # 4. MAIN MENU
        # ==========================================

        main_menu()

    except KeyboardInterrupt:
        handle_keyboard_interrupt()

if __name__ == "__main__":
    main()