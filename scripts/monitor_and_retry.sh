#!/bin/bash
#
# Worktree Task Monitor & Auto-Retry Script
#
# Purpose: Monitor worktree-task tmux sessions for stalled states (429 errors,
#          rate limits, etc.) and automatically send keystrokes to retry.
#
# Usage: ./monitor_and_retry.sh [--dry-run] [--verbose]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/../.monitor_retry.log"
MAX_LOG_SIZE=1048576  # 1MB

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--verbose]"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Rotate log if too large
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
    fi

    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    if [[ "$VERBOSE" == "true" ]] || [[ "$level" == "ERROR" ]] || [[ "$level" == "ACTION" ]]; then
        case $level in
            ERROR)
                echo -e "${RED}[$level]${NC} $message" >&2
                ;;
            ACTION)
                echo -e "${GREEN}[$level]${NC} $message"
                ;;
            WARN)
                echo -e "${YELLOW}[$level]${NC} $message"
                ;;
            *)
                echo -e "${BLUE}[$level]${NC} $message"
                ;;
        esac
    fi
}

# Get all worktree-task tmux sessions
# New format: <project>-<branch> (e.g., worktree-task-plugin-feature-add-dashboard)
# Old format: <branch> (e.g., feature-add-account-scheduler)
#
# Strategy: Match sessions that contain common branch prefixes or project names
# You can customize this by setting WORKTREE_SESSION_PATTERN environment variable
get_worktree_sessions() {
    local pattern="${WORKTREE_SESSION_PATTERN:-^(.*-)?(feature-|fix-|hotfix-|release-|worktree-|synergy-)}"
    tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$pattern" || true
}

# Check if session is stalled
check_session_stalled() {
    local session=$1
    local output

    # Capture last 50 lines of tmux pane output
    output=$(tmux capture-pane -t "${session}:0" -p -S -50 2>/dev/null || echo "")

    if [[ -z "$output" ]]; then
        log "WARN" "Could not capture output for session: $session"
        return 1
    fi

    # Check for stalled indicators
    local stalled=false
    local reason=""

    # Pattern 1: 429 rate limit errors
    if echo "$output" | grep -q "429.*rate_limited\|exceeded.*token usage\|rate limit"; then
        stalled=true
        reason="429 rate limit detected"
    fi

    # Pattern 2: Retrying messages stuck
    if echo "$output" | grep -q "Retrying in.*attempt [5-9]/10\|Retrying in.*attempt 10/10"; then
        stalled=true
        reason="Stuck in retry loop (attempt 5+)"
    fi

    # Pattern 3: Error messages without progress
    if echo "$output" | grep -q "error.*message\|Error:.*\|Failed to"; then
        # Check if there's been recent activity (look for timestamps or progress indicators)
        if ! echo "$output" | tail -20 | grep -q "⏺\|✻\|Done\|tool uses"; then
            stalled=true
            reason="Error state without progress"
        fi
    fi

    # Pattern 4: Waiting state for too long (heuristic: multiple "Waiting..." lines)
    local waiting_count
    waiting_count=$(echo "$output" | grep -c "Waiting…" 2>/dev/null || echo "0")
    waiting_count=$(echo "$waiting_count" | head -1)  # Ensure single line
    if [[ "$waiting_count" =~ ^[0-9]+$ ]] && [[ $waiting_count -gt 10 ]]; then
        stalled=true
        reason="Stuck in waiting state ($waiting_count occurrences)"
    fi

    if [[ "$stalled" == "true" ]]; then
        log "WARN" "Session $session is stalled: $reason"
        echo "$reason"
        return 0
    fi

    return 1
}

# Send retry keystroke to session
send_retry_key() {
    local session=$1
    local reason=$2

    if [[ "$DRY_RUN" == "true" ]]; then
        log "ACTION" "[DRY-RUN] Would send Enter key to session: $session (reason: $reason)"
        return 0
    fi

    # Send Enter key to retry
    if tmux send-keys -t "${session}:0" Enter 2>/dev/null; then
        log "ACTION" "Sent retry keystroke to session: $session (reason: $reason)"
        return 0
    else
        log "ERROR" "Failed to send keystroke to session: $session"
        return 1
    fi
}

# Main monitoring loop
main() {
    log "INFO" "Starting worktree task monitor (dry-run: $DRY_RUN, verbose: $VERBOSE)"

    local sessions
    sessions=$(get_worktree_sessions)

    if [[ -z "$sessions" ]]; then
        log "INFO" "No worktree-task sessions found"
        return 0
    fi

    local total=0
    local stalled=0
    local retried=0

    while IFS= read -r session; do
        ((total++))
        log "DEBUG" "Checking session: $session"

        local reason
        if reason=$(check_session_stalled "$session"); then
            ((stalled++))
            if send_retry_key "$session" "$reason"; then
                ((retried++))
            fi
        else
            log "DEBUG" "Session $session is healthy"
        fi
    done <<< "$sessions"

    log "INFO" "Monitor complete: $total sessions checked, $stalled stalled, $retried retried"

    # Summary output
    if [[ "$stalled" -gt 0 ]]; then
        echo -e "${YELLOW}Summary:${NC} Checked $total sessions, found $stalled stalled, retried $retried"
    elif [[ "$VERBOSE" == "true" ]]; then
        echo -e "${GREEN}Summary:${NC} All $total sessions are healthy"
    fi
}

# Run main function
main

exit 0
