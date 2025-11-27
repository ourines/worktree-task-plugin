---
description: Rebase current branch onto a feature branch
allowed-tools: Bash
---

# Rebase onto Feature Branch

Rebase the current branch onto a feature branch using worktree + tmux with automatic conflict resolution.

## Usage

Provide the feature branch name to rebase the current branch onto.

## Example

User on `dev` branch: "Rebase dev onto featureA"
User on `main` branch: "Rebase main onto feature/add-auth"

## Execution

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rebase.py "<feature-branch>"
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
4. Rebases current branch onto feature branch
5. Resolves any rebase conflicts using Claude Code in tmux

## After Launch

Use `tmux attach -t rebase-<target>-onto-<feature>` to monitor progress.
