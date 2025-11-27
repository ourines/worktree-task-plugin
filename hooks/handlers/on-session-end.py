#!/usr/bin/env python3
"""
Hook handler for SessionEnd event.
Sends macOS notification and logs when a worktree session ends.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def send_macos_notification(title: str, message: str, sound: str = "default"):
    """Send a macOS notification using osascript."""
    script = f'''
    display notification "{message}" with title "{title}" sound name "{sound}"
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True)


def send_terminal_notifier(title: str, message: str, subtitle: str = None):
    """Send notification via terminal-notifier if available."""
    try:
        cmd = [
            "terminal-notifier",
            "-title", title,
            "-message", message,
            "-sound", "default",
            "-group", "worktree-task"
        ]
        if subtitle:
            cmd.extend(["-subtitle", subtitle])
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def log_session_end(session_id: str, reason: str, cwd: str):
    """Log session end to a file for history tracking."""
    log_dir = Path.home() / ".claude" / "plugins" / "worktree-task" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "session-history.log"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "reason": reason,
        "cwd": cwd
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_session_info() -> dict:
    """Try to determine session context."""
    cwd = os.getcwd()

    info = {
        "cwd": cwd,
        "is_worktree": False,
        "branch": None,
        "project": None
    }

    # Get current branch
    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=cwd
        )
        if branch_result.returncode == 0:
            info["branch"] = branch_result.stdout.strip()
    except Exception:
        pass

    # Check if worktree by path pattern
    if "-" in os.path.basename(cwd) and "worktree" not in cwd.lower():
        # Might be a worktree like "project-feature-branch"
        info["is_worktree"] = True

    # Also check git worktree list
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, cwd=cwd
        )
        git_common = result.stdout.strip()
        git_dir_result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=cwd
        )
        git_dir = git_dir_result.stdout.strip()

        # If git-dir != git-common-dir, we're in a worktree
        if git_common != git_dir and ".git/worktrees" in git_dir:
            info["is_worktree"] = True
    except Exception:
        pass

    # Extract project name
    info["project"] = os.path.basename(cwd)

    return info


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_id = hook_input.get("session_id", "unknown")
    reason = hook_input.get("reason", "unknown")  # e.g., "clear", "logout", "exit"

    session_info = get_session_info()

    # Log all worktree session ends
    if session_info.get("is_worktree"):
        log_session_end(session_id, reason, session_info.get("cwd", ""))

        branch = session_info.get("branch", "unknown")
        project = session_info.get("project", "unknown")

        title = "Worktree Session Ended"
        message = f"Branch: {branch}"
        subtitle = f"Reason: {reason}"

        # Try terminal-notifier first, fallback to osascript
        if not send_terminal_notifier(title, message, subtitle):
            send_macos_notification(title, f"{message} ({reason})")

    # Always exit 0 to not block Claude
    sys.exit(0)


if __name__ == "__main__":
    main()
