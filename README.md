# Worktree Task Plugin

Manage large coding tasks using git worktrees and background Claude Code sessions.

## Features

- **Launch**: Spawn autonomous Claude Code instances in separate git worktrees
- **Status**: Monitor running tasks and their progress
- **Resume**: Recover interrupted tasks (rate limits, API errors, timeouts)
- **Cleanup**: Remove completed tasks and worktrees
- **Merge**: Merge completed feature branches with automatic conflict resolution
- **Rebase**: Rebase branches with automatic conflict resolution
- **Alert**: macOS notifications when tasks complete or fail
- **Auto-Update Check**: Notifies you when plugin updates are available via `/plugin` commands

## Usage

### Via Commands (recommended)

```bash
# Launch a new task
/worktree-task:launch "Implement user authentication with OAuth2"

# Check status
/worktree-task:status

# Resume interrupted task
/worktree-task:resume my-task

# Cleanup completed task
/worktree-task:cleanup my-task --keep-worktree

# Merge completed feature branch (run from target branch like dev/main)
/worktree-task:merge feature-branch

# Rebase current branch onto feature branch
/worktree-task:rebase feature-branch
```

### Via Skill (automatic)

Claude will automatically use this skill when you mention:
- "Run this in background"
- "Execute in a worktree"
- "Spawn a separate task"
- Large, complex implementations

## Structure

```
worktree-task/
├── .claude-plugin/
│   └── plugin.json       # Plugin manifest
├── skills/
│   └── worktree-task/
│       └── SKILL.md      # Skill definition
├── commands/
│   ├── launch.md         # /worktree-task:launch
│   ├── status.md         # /worktree-task:status
│   ├── resume.md         # /worktree-task:resume
│   ├── cleanup.md        # /worktree-task:cleanup
│   ├── merge.md          # /worktree-task:merge
│   └── rebase.md         # /worktree-task:rebase
├── hooks/
│   ├── hooks.json        # Hook registrations
│   └── handlers/
│       ├── on-session-start.py  # Update checker
│       ├── on-stop.py           # Task completion notification
│       └── on-session-end.py    # Session end handler
├── scripts/
│   ├── launch.py         # Task launcher
│   ├── status.py         # Status checker
│   ├── resume.py         # Task resumer
│   ├── cleanup.py        # Cleanup handler
│   ├── merge.py          # Merge with conflict resolution
│   └── rebase.py         # Rebase with conflict resolution
└── references/
    ├── task-prompt-template.md
    └── merge-rebase-prompt-template.md
```

## How It Works

1. **Launch**: Creates a git worktree, starts a tmux session, runs Claude Code with the task prompt
2. **Monitor**: Polls tmux panes to detect completion, errors, or rate limits
3. **Alert**: Sends macOS notifications via `osascript`
4. **Resume**: Detects interrupted state and restarts with context
5. **Cleanup**: Kills tmux session, removes worktree (optionally keeps branch)
6. **Merge/Rebase**:
   - Checks if feature branch has a worktree
   - If yes: enters worktree, rebases feature onto target branch
   - Returns to main repo, performs merge/rebase
   - Uses Claude Code in tmux to automatically resolve conflicts

## Configuration

Tasks are tracked via **tmux sessions** and **git worktrees** - no separate database needed.

- Worktrees: Created in parent directory (e.g., `../worktree-task-<name>`)
- Monitor logs: `.monitor_cron.log` in plugin directory

## Requirements

- macOS (for notifications)
- tmux
- git
- Python 3.8+

## Support & Community

- ⭐ **Star this repo** if you find it useful!
- 🐛 [Report issues](https://github.com/ourines/worktree-task-plugin/issues)
- 💡 [Request features](https://github.com/ourines/worktree-task-plugin/issues/new)
- 🐦 Follow [@user_name](https://x.com/ourines_) for updates

## License

MIT
