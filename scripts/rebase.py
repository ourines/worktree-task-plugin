#!/usr/bin/env python3
"""
Rebase a feature branch onto current branch using worktree + tmux.

Usage: rebase.py <feature-branch>

Flow:
1. Check if feature-branch has a worktree
2. If yes, enter worktree and rebase onto current branch
3. Return to main repo and rebase current branch onto feature-branch
4. Use Claude Code in tmux to auto-resolve conflicts
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from typing import Optional


def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def get_git_root() -> Path:
    """Get the root of the git repository."""
    result = run("git rev-parse --show-toplevel", capture=True)
    return Path(result.stdout.strip())


def get_current_branch() -> str:
    """Get the current git branch."""
    result = run("git branch --show-current", capture=True)
    return result.stdout.strip()


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run(f"tmux has-session -t {name}", check=False, capture=True)
    return result.returncode == 0


def get_worktree_path(branch: str) -> Optional[str]:
    """Get the worktree path for a branch, or None if not found."""
    result = run("git worktree list --porcelain", capture=True)
    lines = result.stdout.strip().split('\n')

    current_path = None
    for line in lines:
        if line.startswith('worktree '):
            current_path = line.split(' ', 1)[1]
        elif line.startswith('branch '):
            branch_name = line.split('/')[-1]  # Extract branch name from refs/heads/...
            if branch_name == branch:
                return current_path

    return None


def load_rebase_template(script_dir: Path, feature_branch: str, target_branch: str, worktree_dir: Optional[str]) -> str:
    """Load and populate the rebase prompt template."""
    template_path = script_dir.parent / "references" / "merge-rebase-prompt-template.md"

    if template_path.exists():
        template = template_path.read_text()
    else:
        # Fallback template
        template = """You are performing an automated git rebase with conflict resolution.

## Task
Rebase `$TARGET_BRANCH` onto `$FEATURE_BRANCH`

## Worktree
$WORKTREE_INFO

## Steps
1. If worktree exists: cd to worktree, rebase onto $TARGET_BRANCH, resolve conflicts, commit
2. Return to main repo: cd to git root
3. Checkout $TARGET_BRANCH
4. Rebase onto $FEATURE_BRANCH
5. If conflicts: resolve them intelligently, continue rebase

## Conflict Resolution Strategy
- Read conflicting files carefully
- Understand both sides of the conflict
- Choose the correct resolution (prefer keeping both changes when possible)
- After resolving: git add <files> && git rebase --continue
- Test if possible (run build/tests)

Execute autonomously. Report when done.
"""

    # Substitute variables
    template = template.replace("$FEATURE_BRANCH", feature_branch)
    template = template.replace("$TARGET_BRANCH", target_branch)

    if worktree_dir:
        worktree_info = f"Worktree exists at: {worktree_dir}"
    else:
        worktree_info = "No worktree (direct rebase)"

    template = template.replace("$WORKTREE_INFO", worktree_info)

    return template


def main():
    if len(sys.argv) < 2:
        print("Usage: rebase.py <feature-branch>")
        print("Example: rebase.py featureA")
        sys.exit(1)

    feature_branch = sys.argv[1]
    script_dir = Path(__file__).parent.resolve()

    # Validate git repo
    try:
        project_dir = get_git_root()
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository")
        sys.exit(1)

    # Get current branch (target branch)
    target_branch = get_current_branch()

    if not target_branch:
        print("Error: Could not determine current branch")
        sys.exit(1)

    if target_branch == feature_branch:
        print(f"Error: Already on branch '{feature_branch}'")
        print("Switch to the target branch (e.g., dev, main) first")
        sys.exit(1)

    # Check if feature branch exists
    result = run(f"git rev-parse --verify {feature_branch}", check=False, capture=True)
    if result.returncode != 0:
        print(f"Error: Branch '{feature_branch}' does not exist")
        sys.exit(1)

    # Check for worktree
    worktree_path = get_worktree_path(feature_branch)

    print("=== Worktree Rebase ===")
    print(f"Feature branch: {feature_branch}")
    print(f"Target branch:  {target_branch}")
    print(f"Worktree:       {worktree_path or 'None (direct rebase)'}")
    print()

    # Create tmux session
    session_name = f"rebase-{target_branch}-onto-{feature_branch}".replace("/", "-").replace(".", "-")

    if session_exists(session_name):
        print(f"Error: tmux session '{session_name}' already exists")
        print(f"Use: tmux attach -t {session_name}")
        print(f"Or kill it: tmux kill-session -t {session_name}")
        sys.exit(1)

    print("Creating tmux session...")
    run(f"tmux new-session -d -s {session_name} -c \"{project_dir}\"")

    # Wait for shell to initialize
    time.sleep(1)

    # Launch Claude Code
    print("Launching Claude Code...")
    run(f"tmux send-keys -t {session_name} 'claude --dangerously-skip-permissions' Enter")

    # Wait for Claude to start
    time.sleep(3)

    # Load and send rebase prompt
    print("Sending rebase task to Claude...")
    rebase_prompt = load_rebase_template(script_dir, feature_branch, target_branch, worktree_path)

    # Use temp file to avoid shell escaping issues
    temp_file = Path("/tmp/claude_rebase_prompt.txt")
    temp_file.write_text(rebase_prompt)

    # Send via tmux load-buffer and paste
    run(f"tmux load-buffer -b claude_rebase \"{temp_file}\"")
    run(f"tmux paste-buffer -t {session_name} -b claude_rebase")
    run(f"tmux send-keys -t {session_name} Enter")

    # Wait a moment then send another Enter to bypass the permissions confirmation
    time.sleep(1)
    run(f"tmux send-keys -t {session_name} Enter")

    # Cleanup temp file
    temp_file.unlink()

    print()
    print("=== Rebase Task Launched ===")
    print()
    print(f"Monitor:  tmux attach -t {session_name}")
    print(f"Status:   {script_dir}/status.py {session_name}")
    print(f"Kill:     tmux kill-session -t {session_name}")
    print()
    print("Claude will:")
    if worktree_path:
        print(f"  1. Enter worktree: {worktree_path}")
        print(f"  2. Rebase {feature_branch} onto {target_branch}")
        print("  3. Resolve any conflicts")
    print(f"  4. Rebase {target_branch} onto {feature_branch}")
    print("  5. Resolve any rebase conflicts")
    print("  6. Report completion")


if __name__ == "__main__":
    main()
