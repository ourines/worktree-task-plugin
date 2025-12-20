# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude Code plugin that enables spawning autonomous agent sessions in separate git worktrees via tmux. Manages large coding tasks that would otherwise overflow context by delegating phases to subagents.

## Architecture

```
├── .claude-plugin/plugin.json    # Plugin manifest (name, version, repo)
├── skills/worktree-task/SKILL.md # Auto-trigger skill definition
├── commands/*.md                 # Slash command definitions (/worktree-task:*)
├── hooks/
│   ├── hooks.json                # Hook registrations (SessionStart, Stop, SessionEnd)
│   └── handlers/*.py             # Hook implementations
├── scripts/*.py                  # Core Python scripts for task management
└── references/*.md               # Prompt templates for spawned agents
```

### Core Flow

1. **launch.py** - Creates worktree + tmux session, launches agent (Claude Code or Codex), sends task prompt
2. **status.py** - Captures tmux pane output, shows git info from worktree
3. **resume.py** - Detects error type (rate_limit, api_error, timeout), sends recovery message
4. **cleanup.py** - Kills tmux session, optionally removes worktree
5. **merge.py / rebase.py** - Spawns Claude in tmux to auto-resolve git conflicts

### Key Design Patterns

- **tmux as state**: Sessions track running tasks, pane capture provides status
- **Worktrees for isolation**: Each task gets its own working directory
- **Template substitution**: `$TASK_DESCRIPTION`, `$WORKTREE_DIR` in `references/*.md`
- **Hook-based updates**: `on-session-start.py` checks GitHub Releases API for updates (24h cache)

## Common Commands

```bash
# Test a script directly
python3 scripts/launch.py feature/test "Test task description"
python3 scripts/status.py                    # List all sessions
python3 scripts/status.py <session-name>     # Detailed session status
python3 scripts/resume.py <session> --check  # Check without sending message
python3 scripts/cleanup.py <session> --remove-worktree

# Manual tmux operations
tmux list-sessions
tmux attach -t <session>
tmux kill-session -t <session>

# Git worktree operations
git worktree list
git worktree remove <path>
```

## Agent Command Options

The plugin supports multiple agent backends via launch.py:

| Flag | Command |
|------|---------|
| (default) | `claude --dangerously-skip-permissions` |
| `--codex` | `codex --yolo -m gpt-5.1-codex-max -c model_reasoning_effort="high"` |
| `--agent-cmd "<cmd>"` | Custom command |
| `--env KEY=VALUE` | Add environment variables |

## Conventions

- Session names: `<project>-<branch>` with `/` and `.` replaced by `-`
- Worktree paths: `../<project>-<branch-safe>` (parent directory)
- Temp files: `/tmp/claude_task_prompt.txt`, `/tmp/claude_merge_prompt.txt`
- Cache: `~/.claude/plugins/.worktree-task-update-cache.json`

## Hook System

Hooks are defined in `hooks/hooks.json` and triggered by Claude Code events:

- **SessionStart** (startup): Checks for plugin updates via GitHub API
- **Stop**: Task completion notification (macOS `osascript`)
- **SessionEnd**: Session end handler

Hook handlers receive JSON on stdin and output JSON with optional `systemMessage`.
