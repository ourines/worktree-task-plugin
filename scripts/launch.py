#!/usr/bin/env python3
"""
Launch a background Claude Code session in a git worktree.

Usage: launch.py <branch-name> "<task-description>"
"""

import subprocess
import sys
import os
import time
from pathlib import Path


def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def get_git_root() -> Path:
    """Get the root of the git repository."""
    result = run("git rev-parse --show-toplevel", capture=True)
    return Path(result.stdout.strip())


def is_git_clean() -> bool:
    """Check if the git working directory is clean."""
    result = run("git status --porcelain", capture=True)
    return len(result.stdout.strip()) == 0


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run(f"tmux has-session -t {name}", check=False, capture=True)
    return result.returncode == 0


def load_task_template(script_dir: Path, task_desc: str, worktree_dir: str) -> str:
    """Load and populate the task prompt template."""
    template_path = script_dir.parent / "references" / "task-prompt-template.md"

    if template_path.exists():
        template = template_path.read_text()
    else:
        # Fallback template if file doesn't exist
        template = """You are executing a large task autonomously.

## Your Task
$TASK_DESCRIPTION

## CRITICAL: Use Task tool for each phase to avoid context overflow.

Start by reading specs, then create TodoWrite, then execute each phase via Task tool.
"""

    # Substitute variables
    template = template.replace("$TASK_DESCRIPTION", task_desc)
    template = template.replace("$WORKTREE_DIR", worktree_dir)

    return template


def main():
    if len(sys.argv) < 3:
        print("Usage: launch.py <branch-name> \"<task-description>\"")
        print("Example: launch.py feature/add-proxy \"Implement the proxy service\"")
        sys.exit(1)

    branch_name = sys.argv[1]
    task_desc = sys.argv[2]
    script_dir = Path(__file__).parent.resolve()

    # Validate git repo
    try:
        project_dir = get_git_root()
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository")
        sys.exit(1)

    # Check for uncommitted changes
    if not is_git_clean():
        print("Error: Working directory has uncommitted changes")
        print("Please commit or stash your changes first:")
        print("  git add -A && git commit -m 'WIP'")
        print("  # or")
        print("  git stash")
        sys.exit(1)

    # Setup paths
    project_name = project_dir.name
    session_name = branch_name.replace("/", "-").replace(".", "-")
    worktree_dir = project_dir.parent / f"{project_name}-{session_name}"

    print("=== Worktree Task Launcher ===")
    print(f"Branch:    {branch_name}")
    print(f"Worktree:  {worktree_dir}")
    print(f"Session:   {session_name}")
    print()

    # Check if session already exists
    if session_exists(session_name):
        print(f"Error: tmux session '{session_name}' already exists")
        print(f"Use: tmux attach -t {session_name}")
        print(f"Or kill it: tmux kill-session -t {session_name}")
        sys.exit(1)

    # Create worktree
    print("Creating git worktree...")
    result = run(f"git worktree add \"{worktree_dir}\" -b {branch_name}", check=False, capture=True)
    if result.returncode != 0:
        # Try without -b (branch might exist)
        result = run(f"git worktree add \"{worktree_dir}\" {branch_name}", check=False, capture=True)
        if result.returncode != 0:
            print(f"Error: Failed to create worktree")
            print(result.stderr)
            sys.exit(1)
        print(f"  Using existing branch: {branch_name}")
    else:
        print(f"  Created new branch: {branch_name}")

    # Create tmux session
    print("Creating tmux session...")
    run(f"tmux new-session -d -s {session_name} -c \"{worktree_dir}\"")

    # Wait for shell to initialize
    time.sleep(1)

    # Launch Claude Code
    print("Launching Claude Code...")
    run(f"tmux send-keys -t {session_name} 'claude --dangerously-skip-permissions' Enter")

    # Wait for Claude to start
    time.sleep(3)

    # Load and send task prompt
    print("Sending task to Claude...")
    task_prompt = load_task_template(script_dir, task_desc, str(worktree_dir))

    # Escape special characters for tmux
    # Use a temp file to avoid shell escaping issues
    temp_file = Path("/tmp/claude_task_prompt.txt")
    temp_file.write_text(task_prompt)

    # Send via tmux load-buffer and paste
    run(f"tmux load-buffer -b claude_prompt \"{temp_file}\"")
    run(f"tmux paste-buffer -t {session_name} -b claude_prompt")
    run(f"tmux send-keys -t {session_name} Enter")

    # Cleanup temp file
    temp_file.unlink()

    print()
    print("=== Task Launched Successfully ===")
    print()
    print(f"Monitor:  {script_dir}/status.py {session_name}")
    print(f"Attach:   tmux attach -t {session_name}")
    print(f"Kill:     tmux kill-session -t {session_name}")
    print(f"Cleanup:  {script_dir}/cleanup.py {session_name} --remove-worktree")


if __name__ == "__main__":
    main()
