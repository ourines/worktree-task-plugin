#!/usr/bin/env python3
"""
Hook handler for Stop event.
Sends macOS notification when a Claude session stops.
"""

import json
import os
import subprocess
import sys


def send_macos_notification(title: str, message: str, sound: str = "default"):
    """Send a macOS notification using osascript."""
    script = f'''
    display notification "{message}" with title "{title}" sound name "{sound}"
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True)


def send_terminal_notifier(title: str, message: str):
    """Send notification via terminal-notifier if available."""
    try:
        subprocess.run([
            "terminal-notifier",
            "-title", title,
            "-message", message,
            "-sound", "default",
            "-group", "worktree-task"
        ], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_session_info() -> dict:
    """Try to determine which worktree session this might be."""
    cwd = os.getcwd()
    # Check if we're in a worktree
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True, text=True, cwd=cwd
    )

    info = {
        "cwd": cwd,
        "is_worktree": False,
        "branch": None
    }

    # Get current branch
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=cwd
    )
    if branch_result.returncode == 0:
        info["branch"] = branch_result.stdout.strip()

    # Check if this is a worktree (not main working tree)
    if "worktree" in result.stdout.lower():
        info["is_worktree"] = True

    return info


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_info = get_session_info()

    # Only send notification if this appears to be a worktree session
    # (to avoid notifying on every normal Claude session)
    if session_info.get("is_worktree") or "worktree" in session_info.get("cwd", "").lower():
        branch = session_info.get("branch", "unknown")
        title = "Worktree Task Stopped"
        message = f"Task on branch '{branch}' has stopped"

        # Try terminal-notifier first (better UX), fallback to osascript
        if not send_terminal_notifier(title, message):
            send_macos_notification(title, message)

    # Always exit 0 to not block Claude
    sys.exit(0)


if __name__ == "__main__":
    main()
