import sys

def handle_git_error(error_message):

    if "non-fast-forward" in error_message or "fetch first" in error_message:
        explanation = (
            "Your local branch is behind the remote branch. "
            "The remote repository contains commits that are not "
            "present in your local repository."
        )

        recommended = (
            "Pull the remote changes before pushing again. " 
            "You may need to resolve merge conflicts first."
        )

    else:
        explanation = (
            "Git was unable to complete the requested operation."
        )

        recommended = ("Review the Git error and try again.")

    return {
        "error": error_message,
        "explanation": explanation,
        "recommended": recommended
    }

def handle_keyboard_interrupt():
    print("\nOperation canceled by user.")
    sys.exit()