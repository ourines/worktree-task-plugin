#!/usr/bin/env python3
"""
Cleanup a completed worktree task.

Usage: cleanup.py <session-name> [--remove-worktree]
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


def get_git_root() -> Path:
    """Get the root of the git repository."""
    result = run("git rev-parse --show-toplevel", capture=True)
    return Path(result.stdout.strip())


def main():
    if len(sys.argv) < 2:
        print("Usage: cleanup.py <session-name> [--remove-worktree]")
        print()
        print("Options:")
        print("  --remove-worktree  Also remove the git worktree directory")
        print()
        print("Examples:")
        print("  cleanup.py feature-add-proxy                    # Kill session only")
        print("  cleanup.py feature-add-proxy --remove-worktree  # Kill session and remove worktree")
        sys.exit(1)

    session_name = sys.argv[1]
    remove_worktree = "--remove-worktree" in sys.argv

    print("=== Worktree Task Cleanup ===")
    print()

    # Kill tmux session
    print(f"Killing tmux session: {session_name}")
    if session_exists(session_name):
        run(f"tmux kill-session -t {session_name}")
        print("  ✓ Session killed")
    else:
        print("  ⚠ Session not found (may already be closed)")
    print()

    # Find worktree path
    try:
        project_dir = get_git_root()
        project_name = project_dir.name
        worktree_dir = project_dir.parent / f"{project_name}-{session_name}"
    except subprocess.CalledProcessError:
        print("Warning: Not in a git repository, cannot determine worktree path")
        worktree_dir = None

    # Show worktrees
    print("=== Git Worktrees ===")
    run("git worktree list", check=False)
    print()

    if remove_worktree and worktree_dir:
        if worktree_dir.exists():
            print(f"Removing worktree: {worktree_dir}")

            # Get branch name before removing
            try:
                os.chdir(worktree_dir)
                result = run("git branch --show-current", capture=True, check=False)
                branch_name = result.stdout.strip()
                os.chdir(project_dir)
            except Exception:
                branch_name = None

            # Remove worktree
            result = run(f"git worktree remove \"{worktree_dir}\" --force", check=False, capture=True)
            if result.returncode == 0:
                print("  ✓ Worktree removed")
            else:
                print(f"  ✗ Failed to remove worktree: {result.stderr}")

            print()
            if branch_name:
                print(f"Branch '{branch_name}' still exists.")
                print(f"To delete if merged:   git branch -d {branch_name}")
                print(f"To force delete:       git branch -D {branch_name}")
        else:
            print(f"Worktree directory not found: {worktree_dir}")
            print()
            print("To list worktrees:     git worktree list")
            print("To remove manually:    git worktree remove <path>")
    elif worktree_dir:
        print(f"Worktree kept at: {worktree_dir}")
        print(f"To remove later: git worktree remove \"{worktree_dir}\"")

    print()
    print("=== Cleanup Complete ===")
    print()
    print("Next steps:")
    if worktree_dir and worktree_dir.exists():
        print(f"  1. Review changes: cd \"{worktree_dir}\" && git log --oneline")
    print("  2. Merge branch: git merge <branch-name>")
    print("  3. Or create PR: gh pr create --head <branch-name>")


if __name__ == "__main__":
    main()
