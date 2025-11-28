#!/usr/bin/env python3
"""
Hook handler for Stop event.
Sends macOS notification when a worktree task session stops.

Only triggers for sessions running inside a tmux worktree-task session,
not regular Claude Code sessions.
"""

import json
import os
import random
import subprocess
import sys


# Promotional messages - shown occasionally in notifications
PROMO_MESSAGES = [
    "⭐ Star us on GitHub!",
    "🚀 Powered by worktree-task-plugin",
    "💡 Try codex.markets for more API capacity",
]

# Probability of showing promo (30%)
PROMO_CHANCE = 0.3


def is_worktree_task_session() -> bool:
    """
    Check if we're running inside a worktree-task tmux session.

    Returns True only if:
    1. TMUX env var is set (running inside tmux)
    2. Session name starts with 'worktree-'
    """
    # Must be in tmux
    if not os.environ.get("TMUX"):
        return False

    # Check tmux session name
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True, text=True, check=True
        )
        session_name = result.stdout.strip()
        return session_name.startswith("worktree-")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def send_macos_notification(title: str, message: str, sound: str = "default") -> bool:
    """
    Send a macOS notification using osascript.
    Returns True if notification was sent successfully, False otherwise.
    """
    # Escape quotes in message
    escaped_message = message.replace('"', '\\"')
    escaped_title = title.replace('"', '\\"')

    script = f'display notification "{escaped_message}" with title "{escaped_title}" sound name "{sound}"'
    try:
        result = subprocess.run(
            ["osascript", "-e", script], 
            capture_output=True, 
            check=True,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_session_info() -> dict:
    """Get info about the current session."""
    cwd = os.getcwd()
    info = {
        "cwd": cwd,
        "branch": None,
        "tmux_session": None
    }

    # Get current branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=cwd
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
    except FileNotFoundError:
        pass

    # Get tmux session name
    if os.environ.get("TMUX"):
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#S"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                info["tmux_session"] = result.stdout.strip()
        except FileNotFoundError:
            pass

    return info


def main():
    # Early exit: only run for worktree-task sessions
    if not is_worktree_task_session():
        sys.exit(0)

    # Read hook input from stdin (may be empty)
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        hook_input = {}

    session_info = get_session_info()
    branch = session_info.get("branch") or "unknown"
    tmux_session = session_info.get("tmux_session") or "worktree"

    # Extract task name from tmux session (worktree-{task_name})
    task_name = tmux_session.replace("worktree-", "") if tmux_session else "task"

    title = "✅ Worktree Task Completed"
    message = f"'{task_name}' on branch '{branch}' finished"
    
    # Occasionally add a subtle promo
    promo = ""
    if random.random() < PROMO_CHANCE:
        promo = random.choice(PROMO_MESSAGES)

    # Try macOS notification first
    notification_message = f"{message}\n{promo}" if promo else message
    notification_sent = send_macos_notification(title, notification_message)
    
    # Fallback: output systemMessage (always visible to user, no context cost)
    # Only if notification failed or as a reliable backup
    if not notification_sent:
        output = {
            "systemMessage": f"{title}\n{message}" + (f"\n{promo}" if promo else "")
        }
        print(json.dumps(output))

    # Always exit 0 to not block Claude
    sys.exit(0)


if __name__ == "__main__":
    main()
