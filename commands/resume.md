---
description: Resume an interrupted worktree task
allowed-tools: Bash
---

# Resume Worktree Task

Resume a background worktree task that was interrupted (rate limit, API error, timeout, or waiting for input).

## Usage

Provide:
1. **Session name** - The tmux session to resume
2. **Message** (optional) - Custom instruction for Claude

## Example

User: "Resume the my-feature worktree task"
User: "Resume my-feature with message 'Continue from phase 4'"

## Execution

```bash
# Auto-detect error and send appropriate message
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resume.py <session-name>

# Send custom message
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resume.py <session-name> "<message>"

# Retry last failed operation
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resume.py <session-name> --retry

# Check status only (don't send message)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resume.py <session-name> --check
```

## Auto-Detection

The script automatically detects:
- `rate_limit` - Waits and sends resume message
- `api_error` - Sends retry message
- `timeout` - Sends retry message
- `waiting_input` - Sends continue message

## What It Does

1. Checks if session exists
2. Captures recent output to detect error type
3. Generates appropriate resume message
4. Sends message to Claude with Enter confirmation
5. Shows response after brief wait
