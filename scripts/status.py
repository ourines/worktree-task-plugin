#!/usr/bin/env python3
"""
Monitor status of worktree task sessions.

Usage: status.py [session-name]
"""

import subprocess
import sys
import os
from pathlib import Path


def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run(f"tmux has-session -t {name}", check=False, capture=True)
    return result.returncode == 0


def get_session_cwd(name: str) -> str:
    """Get the current working directory of a tmux session."""
    result = run(f"tmux display-message -t {name} -p '#{{pane_current_path}}'", capture=True)
    return result.stdout.strip()


def get_tmux_output(name: str, lines: int = 30) -> str:
    """Capture recent output from tmux pane."""
    result = run(f"tmux capture-pane -t {name} -p", capture=True)
    output_lines = result.stdout.strip().split('\n')
    return '\n'.join(output_lines[-lines:])


def get_git_info(directory: str) -> dict:
    """Get git information for a directory."""
    info = {
        "branch": "",
        "changed_files": 0,
        "new_commits": 0,
        "recent_commits": []
    }

    try:
        os.chdir(directory)

        # Branch
        result = run("git branch --show-current", capture=True, check=False)
        info["branch"] = result.stdout.strip()

        # Changed files
        result = run("git status --porcelain", capture=True, check=False)
        info["changed_files"] = len([l for l in result.stdout.strip().split('\n') if l])

        # New commits (compared to origin)
        result = run("git log origin/HEAD..HEAD --oneline", capture=True, check=False)
        commits = [l for l in result.stdout.strip().split('\n') if l]
        info["new_commits"] = len(commits)
        info["recent_commits"] = commits[:5]

    except Exception:
        pass

    return info


def print_separator():
    print("═" * 64)


def list_all_sessions():
    """List all tmux sessions and git worktrees."""
    print()
    print_separator()
    print("  WORKTREE TASK STATUS")
    print_separator()
    print()

    print("=== Active tmux Sessions ===")
    result = run("tmux list-sessions", check=False, capture=True)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("  No tmux sessions running")
        print()

    print("=== Git Worktrees ===")
    result = run("git worktree list", check=False, capture=True)
    print(result.stdout)

    print_separator()
    print("  Use: status.py <session-name> for detailed status")
    print_separator()


def show_session_status(session_name: str):
    """Show detailed status for a specific session."""
    if not session_exists(session_name):
        print(f"Error: Session '{session_name}' not found")
        print()
        print("Available sessions:")
        result = run("tmux list-sessions", check=False, capture=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("  No sessions running")
        sys.exit(1)

    worktree_dir = get_session_cwd(session_name)

    print()
    print_separator()
    print(f"  WORKTREE TASK: {session_name}")
    print_separator()
    print()

    print(f"Directory: {worktree_dir}")
    print()

    if worktree_dir and Path(worktree_dir).exists():
        git_info = get_git_info(worktree_dir)

        print("=== Git Status ===")
        print(f"Branch: {git_info['branch']}")
        print(f"Changed files: {git_info['changed_files']}")
        print(f"New commits: {git_info['new_commits']}")
        print()

        if git_info['recent_commits']:
            print("=== Recent Commits ===")
            for commit in git_info['recent_commits']:
                print(f"  {commit}")
            print()

    print("=== Last Activity (tmux output) ===")
    print(get_tmux_output(session_name))
    print()

    print_separator()
    print("  Actions:")
    print(f"    Attach:  tmux attach -t {session_name}")
    print(f"    Kill:    tmux kill-session -t {session_name}")
    print_separator()


def main():
    if len(sys.argv) < 2:
        list_all_sessions()
    else:
        show_session_status(sys.argv[1])


if __name__ == "__main__":
    main()
