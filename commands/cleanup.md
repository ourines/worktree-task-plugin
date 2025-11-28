---
description: Clean up a completed worktree task
allowed-tools: Bash
---

# Cleanup Worktree Task

Clean up a completed or abandoned worktree task by killing the tmux session and optionally removing the git worktree.

## Usage

Provide:
1. **Session name** - The tmux session to clean up
2. **--remove-worktree** (optional) - Also remove the git worktree directory

## Example

User: "Cleanup the my-feature worktree task"
User: "Cleanup my-feature and remove the worktree"

## Execution

```bash
# Kill session only (keep worktree for review)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.py <session-name>

# Kill session AND remove worktree
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.py <session-name> --remove-worktree
```

## What It Does

1. Kills the tmux session
2. Lists remaining git worktrees
3. If `--remove-worktree`: removes the worktree directory
4. Shows next steps (merge branch, create PR)

## After Cleanup

The branch still exists. To complete:
- Merge: `git merge <branch-name>`
- Create PR: `gh pr create --head <branch-name>`
- Delete branch: `git branch -d <branch-name>`

## Note

Always review changes before removing the worktree. Use `/worktree:status` to check commits first.
