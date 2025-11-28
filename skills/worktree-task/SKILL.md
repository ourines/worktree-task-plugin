---
name: worktree-task
description: 使用 git worktree + 背景代理会话管理大型任务（默认启动 Claude Code；可用 --codex 快速切到 Codex CLI，或通过 --agent-cmd 指定任意命令）。适合用户希望在不阻塞当前会话的情况下执行大型或多步骤任务。
---

# Worktree Task Manager

This skill manages large coding tasks by spawning autonomous agent instances (默认 Claude Code，可选 `--codex`/`--agent-cmd`) in separate git worktrees via tmux sessions.

## When to Use

- User wants to execute a large task (>20 subtasks) without blocking current session
- User mentions "background", "parallel", "worktree", or "autonomous" execution
- Task involves creating a new service, major refactoring, or implementing complex features
- User wants to continue other work while a large task runs

## Available Commands

Use these slash commands for precise control:

| Command | Description |
|---------|-------------|
| `/worktree:launch` | Launch a new background task |
| `/worktree:status` | Check status of all or specific tasks |
| `/worktree:resume` | Resume an interrupted task |
| `/worktree:cleanup` | Clean up completed tasks |

## Core Workflow

### 1. Launch a Task

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/launch.py <branch-name> "<task-description>"
```

Example:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/launch.py feature/my-task "Execute the task: implement new feature. Read the tasks.md and implement all phases."
```

The script will:
1. Verify git status is clean (or prompt to commit/stash)
2. Create a git worktree with the specified branch
3. Create a tmux session
4. Launch Claude Code by default (use `--codex` for default Codex command or `--agent-cmd` to switch, e.g., `codex --yolo -m gpt-5.1-codex-max -c model_reasoning_effort="high"`)
5. Send the task with instructions to use Task tool for each phase

### 2. Monitor Progress

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py [session-name]
```

Without arguments, lists all active sessions. With a session name, shows detailed status.

### 3. Resume an Interrupted Task

If a task is interrupted (rate limit, API error, timeout):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resume.py <session-name> [message]
```

Options:
- `--retry` - Retry the last failed task
- `--check` - Only check status, don't send message

### 4. Cleanup

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup.py <session-name> [--remove-worktree]
```

## Alerts

This plugin automatically sends macOS notifications when:
- A background task completes successfully
- A task encounters an error (rate limit, API error)
- A session ends

Configure alerts in `hooks/hooks.json`.

## Critical Instructions for Spawned Claude

The spawned agent receives these critical instructions:

1. **MUST use Task tool** - Each major phase must be executed via `Task` tool to prevent context overflow
2. **Silent mode** - No confirmations needed, user has pre-approved all operations
3. **Complete execution** - Do not stop until all tasks are done
4. **Track with TodoWrite** - Create and update todo list for visibility
5. **Commit often** - Make atomic commits after each logical unit

## Notes

- Worktrees are created in parent directory: `../<project>-<branch-name>`
- tmux session names have `/` and `.` replaced with `-`
- Use `tmux attach -t <session>` to take over interactively
- The spawned Claude runs with full permissions (`--dangerously-skip-permissions`)

---

> 💡 More Claude Code plugins: [github.com/ourines](https://github.com/ourines)
