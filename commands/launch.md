---
description: Launch a new background worktree task
allowed-tools: Bash
---

# Launch Worktree Task

Launch a background Claude Code session in a separate git worktree to execute a large task autonomously.

## Usage

Provide:
1. **Branch name** - The git branch for this task (e.g., `feature/add-proxy-support`)
2. **Task description** - What the background Claude should do

## Example

User: "Launch a worktree task on branch feature/add-auth to implement the authentication module"

## Execution

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/launch.py "<branch-name>" "<task-description>"
```

## Prerequisites

- Git working directory must be clean (commit or stash changes first)
- tmux must be installed
- Branch name will be created if it doesn't exist

## What Happens

1. Creates a git worktree at `../<project>-<branch-name>`
2. Creates a tmux session named after the branch
3. Launches Claude Code with `--dangerously-skip-permissions`
4. Sends the task prompt with instructions to use Task tool for each phase

## After Launch

Use `/worktree:status` to monitor progress or `tmux attach -t <session>` to take over interactively.
