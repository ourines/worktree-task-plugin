You are performing an automated git merge/rebase with conflict resolution.

## Task
Merge/rebase branch `$FEATURE_BRANCH` into/onto `$TARGET_BRANCH`

## Worktree Information
$WORKTREE_INFO

## Execution Steps

### Phase 1: Prepare Feature Branch (if worktree exists)
If the worktree exists:
1. `cd <worktree-path>`
2. `git fetch origin`
3. `git rebase $TARGET_BRANCH`
4. If conflicts occur:
   - Read conflicting files carefully
   - Resolve conflicts intelligently (prefer keeping both changes when possible)
   - `git add <resolved-files>`
   - `git rebase --continue`
5. Repeat until rebase completes
6. Commit if needed

### Phase 2: Merge/Rebase in Main Repo
1. `cd <git-root>`
2. `git checkout $TARGET_BRANCH`
3. `git pull origin $TARGET_BRANCH` (ensure up-to-date)
4. Execute the merge/rebase:
   - For merge: `git merge $FEATURE_BRANCH`
   - For rebase: `git rebase $FEATURE_BRANCH`
5. If conflicts occur:
   - Read conflicting files carefully
   - Understand both sides of the conflict
   - Resolve intelligently
   - For merge: `git add <files> && git commit`
   - For rebase: `git add <files> && git rebase --continue`
6. Verify the result

### Phase 3: Verification
1. Check git status: `git status`
2. Review recent commits: `git log --oneline -5`
3. If project has tests/build: run them
4. Report completion status

## Conflict Resolution Strategy

When encountering conflicts:

1. **Read both sides**: Use `git diff` to understand what each side changed
2. **Understand intent**: Why did each side make their changes?
3. **Intelligent merge**:
   - If changes are in different parts: keep both
   - If changes conflict logically: choose the more recent/correct one
   - If unsure: prefer the target branch's version (safer)
4. **Test after resolution**: Run build/tests if available
5. **Clear commit message**: Explain what was resolved and why

## Error Handling

- If rebase fails and cannot be resolved: `git rebase --abort` and report
- If merge fails and cannot be resolved: `git merge --abort` and report
- Always report the current state before aborting

## Execution Mode

- **AUTONOMOUS**: Execute without asking for permission
- **COMPLETE**: Do not stop until done or blocked
- **REPORT**: Provide clear status at the end

## Begin Now

Start by checking if the worktree exists, then proceed with the steps above.
