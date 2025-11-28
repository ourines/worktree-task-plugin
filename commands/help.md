---
description: Show help for worktree-task plugin
allowed-tools: ""
---

# Worktree Task Plugin Help

A plugin for managing large coding tasks using git worktrees and background Claude Code sessions.

## Commands

| Command | Description |
|---------|-------------|
| `/worktree-task:launch <task>` | Launch a new background task in a separate worktree |
| `/worktree-task:status [name]` | Check status of all or specific task |
| `/worktree-task:resume <name>` | Resume an interrupted task |
| `/worktree-task:cleanup <name>` | Clean up completed task and worktree |
| `/worktree-task:merge <branch>` | Merge a feature branch into current branch |
| `/worktree-task:rebase <branch>` | Rebase current branch onto a feature branch |
| `/worktree-task:help` | Show this help message |

## Quick Start

```bash
# 1. Launch a complex task in the background
/worktree-task:launch "Implement user authentication with OAuth2"

# 2. Check progress
/worktree-task:status

# 3. When done, merge the changes
/worktree-task:merge feature-auth

# 4. Clean up
/worktree-task:cleanup feature-auth
```

## How It Works

1. **Launch** creates a git worktree (isolated copy of your repo) and spawns a Claude Code instance in a tmux session
2. **Monitor** via `/worktree-task:status` to see progress, logs, and completion state
3. **Resume** if task gets interrupted (rate limits, API errors, network issues)
4. **Merge/Rebase** with automatic conflict resolution powered by Claude
5. **Cleanup** removes the tmux session and worktree when done

## Best Practices

- Use for tasks that take 10+ minutes or require extensive changes
- Keep task descriptions clear and specific
- Check status periodically to monitor progress
- Use `--keep-worktree` with cleanup if you want to review changes first

## File Locations

- Worktrees: Created in parent directory of your repo (e.g., `../worktree-task-<name>`)
- Task prompts: `/tmp/claude_task_prompt.txt` (temporary)
- Monitor logs: `<plugin-dir>/.monitor_cron.log`

## Requirements

- macOS (for notifications)
- tmux
- git
- Python 3.8+

## Links

- GitHub: https://github.com/ourines/worktree-task-plugin
- Issues: https://github.com/ourines/worktree-task-plugin/issues
