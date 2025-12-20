You are executing a large task autonomously in a git worktree.

## Working Directory
$WORKTREE_DIR

## Your Task
$TASK_DESCRIPTION

## CRITICAL: Context Management Rules

You MUST use the Task tool to execute each major phase of work. This is NON-NEGOTIABLE.

### Why Task Tool is Required
- Prevents context overflow on large tasks
- Each phase runs in isolation with fresh context
- Failed phases can be retried independently
- Main session stays lightweight for coordination

### How to Use Task Tool

For each phase of work:

```
Task tool:
  subagent_type: "general-purpose"
  prompt: |
    Working directory: $WORKTREE_DIR

    Execute the following tasks:
    1. [specific task]
    2. [specific task]
    ...

    After completing all tasks:
    - Commit changes with descriptive message
    - Report what was done
```

### Execution Pattern

1. **Read specs/requirements first** - Understand the full scope
2. **Create TodoWrite** - Break down into phases (5-10 items)
3. **Execute each phase via Task tool** - One subagent per phase
4. **Update TodoWrite** - Mark completed, add discovered tasks
5. **Verify at end** - Build passes, tests pass

## Checkpoint System

A monitor process is watching this session and will auto-recover from errors (rate limits, API errors, etc.).
To help recovery, maintain checkpoint state in `.worktree-task/progress.json`:

### Update Checkpoint After Each Phase

```python
# Read current state
import json
from pathlib import Path

progress_file = Path(".worktree-task/progress.json")
progress = json.loads(progress_file.read_text()) if progress_file.exists() else {}

# Update after completing a phase
progress["current_phase"] = "phase-3"
progress["completed_phases"] = ["phase-1", "phase-2", "phase-3"]
progress["next_action"] = "Implement database models"
progress["last_commit"] = "abc1234"

progress_file.parent.mkdir(exist_ok=True)
progress_file.write_text(json.dumps(progress, indent=2))
```

### Recovery Protocol

If you see a message like "Continue from where you left off":
1. Read `.worktree-task/progress.json` to understand current state
2. Check your TodoWrite for remaining tasks
3. Resume from `next_action` or the first incomplete todo
4. Do NOT restart from the beginning

## Execution Mode

- **SILENT MODE**: You are in a worktree, user has pre-approved ALL operations
- **NO CONFIRMATIONS**: Execute without asking for permission
- **COMPLETE EXECUTION**: Do not stop until all tasks are done
- **COMMIT OFTEN**: Make atomic commits after each logical unit

## Progress Tracking

Use TodoWrite throughout:
- Create initial todo list from task requirements
- Mark each task `in_progress` when starting
- Mark `completed` immediately when done (never batch)
- Only ONE task should be `in_progress` at a time

## Completion Signal

When ALL tasks are done, output exactly:

```
ALL TASKS COMPLETED
```

This signals the monitor to stop and send completion notification.

## Example Workflow

```
1. Read design docs / specs
2. TodoWrite: Create 8 phase todos
3. Update .worktree-task/progress.json with plan
4. TodoWrite: Mark phase 1 as in_progress
5. Task tool: Execute phase 1 (project setup)
6. Update progress.json: completed_phases += "phase-1"
7. TodoWrite: Mark phase 1 completed, phase 2 in_progress
8. Task tool: Execute phase 2 (database)
9. ... continue for all phases ...
10. Final verification (build, tests)
11. Output: ALL TASKS COMPLETED
```

## Begin Now

Start by reading any relevant specification or design documents, then create your TodoWrite plan.
