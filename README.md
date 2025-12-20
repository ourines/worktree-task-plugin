# Worktree Task Plugin

[![GitHub release](https://img.shields.io/github/v/release/ourines/worktree-task-plugin)](https://github.com/ourines/worktree-task-plugin/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Manage large coding tasks using git worktrees and background agent sessions. Spawns autonomous Claude Code or Codex instances that run independently, freeing your main session.

## Features

- **Launch**: Spawn autonomous agent instances in separate git worktrees
  - Default: Claude Code (`claude --dangerously-skip-permissions`)
  - `--codex`: Quick switch to Codex CLI
  - `--agent-cmd`: Custom agent command
- **Auto-Recovery**: Background monitor automatically detects and recovers from errors (rate limits, API errors, timeouts)
- **Status**: Monitor running tasks and their progress
- **Resume**: Manually recover interrupted tasks
- **Cleanup**: Remove completed tasks and worktrees
- **Merge/Rebase**: Automatic conflict resolution powered by Claude
- **Alerts**: macOS notifications when tasks complete or fail
- **Auto-Update**: Notifies when plugin updates are available

## Usage

### Via Commands (recommended)

```bash
# Launch a new task (auto-recovery enabled by default)
/worktree-task:launch "Implement user authentication with OAuth2"

# Launch with Codex instead of Claude
/worktree-task:launch --codex "Refactor database layer"

# Launch without auto-recovery
/worktree-task:launch --no-monitor "Quick fix task"

# Check status of all tasks
/worktree-task:status

# Check specific task
/worktree-task:status my-task

# Resume interrupted task manually
/worktree-task:resume my-task

# Cleanup completed task
/worktree-task:cleanup my-task --keep-worktree

# Merge feature branch (run from target branch)
/worktree-task:merge feature-branch

# Rebase current branch onto feature branch
/worktree-task:rebase feature-branch

# Show help
/worktree-task:help
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
│   ├── rebase.md         # /worktree-task:rebase
│   └── help.md           # /worktree-task:help
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
│   ├── rebase.py         # Rebase with conflict resolution
│   └── monitor.py        # Auto-recovery background monitor
└── references/
    ├── task-prompt-template.md
    └── merge-rebase-prompt-template.md
```

## How It Works

1. **Launch**: Creates a git worktree, starts a tmux session, runs the agent with task prompt
2. **Auto-Recovery**: Background monitor polls for errors and automatically resumes (rate limits, API errors, timeouts)
3. **Monitor**: Check progress via `/worktree-task:status`
4. **Alert**: macOS notifications via `osascript` on completion/failure
5. **Cleanup**: Kills tmux session, stops monitor, removes worktree
6. **Merge/Rebase**: Uses Claude in tmux to automatically resolve conflicts

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
