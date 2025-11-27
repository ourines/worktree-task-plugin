---
description: Check status of worktree tasks
allowed-tools: Bash
---

# Worktree Task Status

Check the status of background worktree tasks.

## Usage

- Without arguments: List all active tmux sessions and git worktrees
- With session name: Show detailed status for that session

## Example

User: "Check status of worktree tasks"
User: "What's the status of the proxy task?"

## Execution

```bash
# List all tasks
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py

# Check specific task
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py <session-name>
```

## Output Includes

- Active tmux sessions
- Git worktrees
- Current branch and changed files
- Recent commits
- Last activity (tmux output)

## Quick Actions

After checking status, you can:
- `/worktree:resume <session>` - Resume an interrupted task
- `/worktree:cleanup <session>` - Clean up a completed task
- `tmux attach -t <session>` - Take over interactively
