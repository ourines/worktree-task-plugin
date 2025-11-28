---
description: Merge a feature branch into current branch
allowed-tools: Bash
---

# Merge Feature Branch

Merge a completed feature branch into the current branch using worktree + tmux with automatic conflict resolution.

## Usage

Provide the feature branch name to merge into the current branch.

## Example

User on `dev` branch: "Merge feature-auth into dev"
User on `main` branch: "Merge feature/new-api into main"

## Execution

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge.py "<feature-branch>"
```

## Prerequisites

- Must be on the target branch (e.g., dev, main)
- Feature branch must exist
- tmux must be installed

## What Happens

1. Checks if feature branch has a worktree
2. If worktree exists:
   - Enters the worktree
   - Rebases feature branch onto current branch
   - Resolves any conflicts
3. Returns to main repo
4. Merges feature branch into current branch
5. Resolves any merge conflicts using Claude Code in tmux

## After Launch

Use `tmux attach -t merge-<feature>-to-<target>` to monitor progress.
