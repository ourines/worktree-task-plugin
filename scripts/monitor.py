#!/usr/bin/env python3
"""
Monitor a worktree task session for errors and auto-recover.

This script runs in the background and:
1. Polls tmux pane output to detect errors (rate limit, API error, timeout)
2. Automatically sends resume messages when errors are detected
3. Tracks progress via .worktree-task/progress.json in the worktree
4. Sends completion notification when all tasks are done

Usage: monitor.py <session-name> <worktree-dir> [--interval 10]
"""

import subprocess
import sys
import os
import json
import time
import signal
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Configuration
DEFAULT_POLL_INTERVAL = 10  # seconds
MAX_RETRY_COUNT = 5
RATE_LIMIT_WAIT = 65  # seconds to wait after rate limit
ERROR_RETRY_WAIT = 10  # seconds to wait before retry after error
IDLE_TIMEOUT = 300  # seconds of no output change before considering stuck

# Progress file location within worktree
PROGRESS_DIR = ".worktree-task"
PROGRESS_FILE = "progress.json"


def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run(f"tmux has-session -t {name}", check=False, capture=True)
    return result.returncode == 0


def get_tmux_output(name: str, lines: int = 100) -> str:
    """Capture recent output from tmux pane."""
    result = run(f"tmux capture-pane -t {name} -p -S -{lines}", capture=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def send_message(session_name: str, message: str):
    """Send a message to the tmux session."""
    temp_file = Path("/tmp/claude_monitor_prompt.txt")
    temp_file.write_text(message)

    run(f"tmux load-buffer -b claude_monitor \"{temp_file}\"")
    run(f"tmux paste-buffer -t {session_name} -b claude_monitor")
    time.sleep(0.3)
    run(f"tmux send-keys -t {session_name} Enter")

    temp_file.unlink()


def send_notification(title: str, message: str):
    """Send macOS notification."""
    script = f'display notification "{message}" with title "{title}"'
    run(f"osascript -e '{script}'", check=False)


def detect_state(output: str) -> Tuple[str, Optional[str]]:
    """
    Detect the current state from tmux output.

    Returns: (state, details)
    States: running, rate_limit, api_error, timeout, network_error,
            waiting_input, completed, stuck
    """
    output_lower = output.lower()
    last_lines = output.strip().split('\n')[-20:]
    last_text = '\n'.join(last_lines).lower()

    # Check for rate limit
    if "429" in output or "rate_limit" in output_lower or "rate limited" in last_text:
        return "rate_limit", "Rate limit detected"

    # Check for API errors
    if "api error" in last_text or "anthropic error" in last_text:
        return "api_error", "API error detected"

    # Check for timeout
    if "timeout" in last_text and "error" in last_text:
        return "timeout", "Timeout detected"

    # Check for network/connection errors
    if ("connection" in last_text and "error" in last_text) or "network error" in last_text:
        return "network_error", "Network error detected"

    # Check for overloaded
    if "overloaded" in last_text:
        return "overloaded", "Server overloaded"

    # Check for context overflow
    if "context" in last_text and ("overflow" in last_text or "too long" in last_text or "exceeded" in last_text):
        return "context_overflow", "Context overflow detected"

    # Check for completion indicators
    if "all tasks completed" in last_text or "execution complete" in last_text:
        return "completed", "Task completed"

    # Check if waiting at prompt (Claude is idle)
    for line in reversed(last_lines):
        line = line.strip()
        # Prompt patterns: "> ", "claude> ", etc.
        if line and (line == ">" or line.endswith("> ") or re.match(r'^[a-zA-Z]+>\s*$', line)):
            # Check if it's been waiting for a while (need external state for this)
            return "waiting_input", "Waiting at prompt"

    # Check if Claude is actively working
    if any(x in last_text for x in ["thinking", "executing", "reading", "writing", "running"]):
        return "running", None

    return "running", None


def load_progress(worktree_dir: Path) -> dict:
    """Load progress from checkpoint file."""
    progress_file = worktree_dir / PROGRESS_DIR / PROGRESS_FILE
    if not progress_file.exists():
        return {
            "status": "not_started",
            "current_task": None,
            "completed_tasks": [],
            "failed_tasks": [],
            "retry_count": 0,
            "last_error": None,
            "last_activity": None,
            "started_at": None
        }

    try:
        with open(progress_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"status": "error", "error": "Failed to read progress file"}


def save_progress(worktree_dir: Path, progress: dict):
    """Save progress to checkpoint file."""
    progress_dir = worktree_dir / PROGRESS_DIR
    progress_dir.mkdir(exist_ok=True)

    progress["last_activity"] = datetime.now().isoformat()

    progress_file = progress_dir / PROGRESS_FILE
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)


def get_resume_message(state: str, retry_count: int) -> str:
    """Generate appropriate resume message based on state."""
    messages = {
        "rate_limit": "Rate limit has reset. Continue executing the remaining tasks from your todo list. Check .worktree-task/progress.json for last known state.",
        "api_error": f"API error resolved (retry {retry_count}/{MAX_RETRY_COUNT}). Continue from where you left off. If a Task tool call failed, retry it.",
        "timeout": f"Timeout resolved (retry {retry_count}/{MAX_RETRY_COUNT}). Continue executing remaining tasks.",
        "network_error": f"Network restored (retry {retry_count}/{MAX_RETRY_COUNT}). Continue from where you left off.",
        "overloaded": "Server load normalized. Continue executing remaining tasks from your todo list.",
        "context_overflow": "Context was reset. Read .worktree-task/progress.json to see completed tasks, then continue with remaining tasks. Use Task tool for each phase to prevent future overflow.",
        "waiting_input": "Continue executing the remaining tasks. Do not stop until all todos are completed.",
    }
    return messages.get(state, "Continue executing remaining tasks.")


def log(message: str, worktree_dir: Path = None):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)

    # Also write to log file in worktree
    if worktree_dir:
        log_dir = worktree_dir / PROGRESS_DIR
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "monitor.log"
        with open(log_file, "a") as f:
            f.write(log_line + "\n")


class Monitor:
    def __init__(self, session_name: str, worktree_dir: Path, poll_interval: int = DEFAULT_POLL_INTERVAL):
        self.session_name = session_name
        self.worktree_dir = worktree_dir
        self.poll_interval = poll_interval
        self.running = True
        self.last_output_hash = ""
        self.last_activity_time = time.time()
        self.consecutive_idle_checks = 0

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        log(f"Received signal {signum}, shutting down...", self.worktree_dir)
        self.running = False

    def run(self):
        """Main monitoring loop."""
        log(f"Starting monitor for session: {self.session_name}", self.worktree_dir)
        log(f"Worktree: {self.worktree_dir}", self.worktree_dir)
        log(f"Poll interval: {self.poll_interval}s", self.worktree_dir)

        # Initialize progress
        progress = load_progress(self.worktree_dir)
        if progress.get("status") == "not_started":
            progress["status"] = "running"
            progress["started_at"] = datetime.now().isoformat()
            save_progress(self.worktree_dir, progress)

        while self.running:
            try:
                self._check_and_recover()
                time.sleep(self.poll_interval)
            except Exception as e:
                log(f"Error in monitor loop: {e}", self.worktree_dir)
                time.sleep(self.poll_interval)

        log("Monitor stopped", self.worktree_dir)

    def _check_and_recover(self):
        """Check session state and recover if needed."""
        # Check if session still exists
        if not session_exists(self.session_name):
            log("Session no longer exists, stopping monitor", self.worktree_dir)
            self._handle_completion("Session ended")
            self.running = False
            return

        # Get current output
        output = get_tmux_output(self.session_name)
        output_hash = hash(output)

        # Check for activity
        if output_hash != self.last_output_hash:
            self.last_output_hash = output_hash
            self.last_activity_time = time.time()
            self.consecutive_idle_checks = 0
        else:
            self.consecutive_idle_checks += 1

        # Detect state
        state, details = detect_state(output)
        progress = load_progress(self.worktree_dir)

        log(f"State: {state}" + (f" ({details})" if details else ""), self.worktree_dir)

        if state == "completed":
            self._handle_completion("All tasks completed")
            self.running = False
            return

        if state == "running":
            # Check for stuck state (no output change for too long)
            idle_time = time.time() - self.last_activity_time
            if idle_time > IDLE_TIMEOUT:
                log(f"Session appears stuck (no activity for {idle_time:.0f}s)", self.worktree_dir)
                # Don't auto-recover stuck state, just notify
                send_notification("Worktree Task Stuck", f"{self.session_name}: No activity for {idle_time:.0f}s")
            return

        # Handle error states
        if state in ["rate_limit", "api_error", "timeout", "network_error", "overloaded", "context_overflow"]:
            self._handle_error(state, progress)
        elif state == "waiting_input":
            self._handle_waiting(progress)

    def _handle_error(self, state: str, progress: dict):
        """Handle error state with auto-recovery."""
        retry_count = progress.get("retry_count", 0) + 1

        if retry_count > MAX_RETRY_COUNT:
            log(f"Max retries ({MAX_RETRY_COUNT}) exceeded, stopping", self.worktree_dir)
            progress["status"] = "failed"
            progress["last_error"] = f"Max retries exceeded for {state}"
            save_progress(self.worktree_dir, progress)
            send_notification("Worktree Task Failed", f"{self.session_name}: Max retries exceeded")
            self.running = False
            return

        # Wait before retry
        wait_time = RATE_LIMIT_WAIT if state == "rate_limit" else ERROR_RETRY_WAIT
        log(f"Waiting {wait_time}s before retry {retry_count}/{MAX_RETRY_COUNT}...", self.worktree_dir)
        time.sleep(wait_time)

        # Update progress
        progress["retry_count"] = retry_count
        progress["last_error"] = state
        save_progress(self.worktree_dir, progress)

        # Send recovery message
        message = get_resume_message(state, retry_count)
        log(f"Sending resume message: {message[:60]}...", self.worktree_dir)
        send_message(self.session_name, message)

        # Reset idle tracking
        self.last_activity_time = time.time()

    def _handle_waiting(self, progress: dict):
        """Handle waiting at prompt state."""
        # Only nudge if idle for a while
        idle_time = time.time() - self.last_activity_time
        if idle_time < 30:  # Wait at least 30s before nudging
            return

        if self.consecutive_idle_checks < 3:  # Wait for 3 consecutive idle checks
            return

        log("Claude appears idle at prompt, sending continue message", self.worktree_dir)
        message = get_resume_message("waiting_input", 0)
        send_message(self.session_name, message)

        # Reset counters
        self.last_activity_time = time.time()
        self.consecutive_idle_checks = 0

        # Reset retry count on successful nudge
        progress["retry_count"] = 0
        save_progress(self.worktree_dir, progress)

    def _handle_completion(self, reason: str):
        """Handle task completion."""
        log(f"Task completed: {reason}", self.worktree_dir)

        progress = load_progress(self.worktree_dir)
        progress["status"] = "completed"
        progress["completed_at"] = datetime.now().isoformat()
        save_progress(self.worktree_dir, progress)

        send_notification("Worktree Task Completed", f"{self.session_name}: {reason}")


def main():
    if len(sys.argv) < 3:
        print("Usage: monitor.py <session-name> <worktree-dir> [--interval N]")
        print()
        print("Options:")
        print("  --interval N    Poll interval in seconds (default: 10)")
        print()
        print("Example:")
        print("  monitor.py myproj-feature /path/to/worktree --interval 15")
        sys.exit(1)

    session_name = sys.argv[1]
    worktree_dir = Path(sys.argv[2])
    poll_interval = DEFAULT_POLL_INTERVAL

    # Parse options
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--interval" and i + 1 < len(sys.argv):
            poll_interval = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    if not worktree_dir.exists():
        print(f"Error: Worktree directory does not exist: {worktree_dir}")
        sys.exit(1)

    if not session_exists(session_name):
        print(f"Error: Session '{session_name}' not found")
        sys.exit(1)

    monitor = Monitor(session_name, worktree_dir, poll_interval)
    monitor.run()


if __name__ == "__main__":
    main()
