# Worktree Task Plugin

Manage large coding tasks using git worktrees and background Claude Code sessions.

## Features

- **Launch**: Spawn autonomous Claude Code instances in separate git worktrees
- **Status**: Monitor running tasks and their progress
- **Resume**: Recover interrupted tasks (rate limits, API errors, timeouts)
- **Cleanup**: Remove completed tasks and worktrees
- **Alert**: macOS notifications when tasks complete or fail

## Usage

### Via Commands (recommended)

```bash
# Launch a new task
/worktree:launch "Implement user authentication with OAuth2"

# Check status
/worktree:status

# Resume interrupted task
/worktree:resume my-task

# Cleanup completed task
/worktree:cleanup my-task --keep-worktree
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
│   ├── launch.md         # /worktree:launch
│   ├── status.md         # /worktree:status
│   ├── resume.md         # /worktree:resume
│   └── cleanup.md        # /worktree:cleanup
├── hooks/
│   ├── hooks.json        # Hook registrations
│   └── handlers/
│       ├── on-stop.py    # Task completion notification
│       └── on-session-end.py
├── scripts/
│   ├── launch.py         # Task launcher
│   ├── status.py         # Status checker
│   ├── resume.py         # Task resumer
│   └── cleanup.py        # Cleanup handler
└── references/
    └── task-prompt-template.md
```

## How It Works

1. **Launch**: Creates a git worktree, starts a tmux session, runs Claude Code with the task prompt
2. **Monitor**: Polls tmux panes to detect completion, errors, or rate limits
3. **Alert**: Sends macOS notifications via `osascript`
4. **Resume**: Detects interrupted state and restarts with context
5. **Cleanup**: Kills tmux session, removes worktree (optionally keeps branch)

## Configuration

Tasks are tracked in `~/.claude/worktree-tasks/tasks.json`.

Logs are stored in `~/.claude/worktree-tasks/logs/`.

## Requirements

- macOS (for notifications)
- tmux
- git
- Python 3.8+
