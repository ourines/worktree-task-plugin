#!/usr/bin/env python3
"""
Resume a paused/interrupted worktree task session.

Usage: resume.py <session-name> [message]

Examples:
  resume.py proxy                              # Resume with default message
  resume.py proxy "Continue from phase 3"     # Resume with custom message
  resume.py proxy --retry                      # Retry last failed task
"""

import subprocess
import sys
import time
from pathlib import Path


def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run(f"tmux has-session -t {name}", check=False, capture=True)
    return result.returncode == 0


def get_tmux_output(name: str, lines: int = 50) -> str:
    """Capture recent output from tmux pane."""
    result = run(f"tmux capture-pane -t {name} -p", capture=True)
    return result.stdout.strip()


def detect_error_type(output: str) -> str:
    """Detect the type of error from tmux output."""
    output_lower = output.lower()

    if "429" in output or "rate_limit" in output_lower or "rate limited" in output_lower:
        return "rate_limit"
    elif "api error" in output_lower:
        return "api_error"
    elif "timeout" in output_lower:
        return "timeout"
    elif "connection" in output_lower and "error" in output_lower:
        return "connection_error"
    elif ">" in output and output.strip().endswith(">"):
        # Waiting at prompt
        return "waiting_input"
    return "unknown"


def get_resume_message(error_type: str, custom_message: str = None) -> str:
    """Generate appropriate resume message based on error type."""
    if custom_message:
        return custom_message

    messages = {
        "rate_limit": "Rate limit should be reset now. Continue executing the remaining tasks from where you left off.",
        "api_error": "API error may be resolved. Retry the last failed operation and continue.",
        "timeout": "Timeout may be resolved. Retry the last operation and continue.",
        "connection_error": "Connection should be restored. Continue executing the remaining tasks.",
        "waiting_input": "Continue executing the remaining tasks.",
        "unknown": "Continue executing the remaining tasks from where you left off."
    }
    return messages.get(error_type, messages["unknown"])


def send_message(session_name: str, message: str, confirm: bool = True):
    """Send a message to the tmux session."""
    # Use temp file to handle special characters
    temp_file = Path("/tmp/claude_resume_prompt.txt")
    temp_file.write_text(message)

    # Load buffer and paste
    run(f"tmux load-buffer -b claude_resume \"{temp_file}\"")
    run(f"tmux paste-buffer -t {session_name} -b claude_resume")

    if confirm:
        run(f"tmux send-keys -t {session_name} Enter")

    # Cleanup
    temp_file.unlink()


def main():
    if len(sys.argv) < 2:
        print("Usage: resume.py <session-name> [message]")
        print()
        print("Options:")
        print("  --retry     Retry the last failed task")
        print("  --check     Only check status, don't send message")
        print()
        print("Examples:")
        print("  resume.py proxy                              # Resume with auto-detected message")
        print("  resume.py proxy \"Continue from phase 3\"     # Resume with custom message")
        print("  resume.py proxy --retry                      # Retry last failed task")
        print("  resume.py proxy --check                      # Check status only")
        sys.exit(1)

    session_name = sys.argv[1]

    # Parse flags
    check_only = "--check" in sys.argv
    retry_mode = "--retry" in sys.argv

    # Get custom message if provided
    custom_message = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--"):
            custom_message = arg
            break

    # Validate session
    if not session_exists(session_name):
        print(f"Error: Session '{session_name}' not found")
        print()
        print("Available sessions:")
        result = run("tmux list-sessions", check=False, capture=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("  No sessions running")
        sys.exit(1)

    print(f"=== Resume Worktree Task: {session_name} ===")
    print()

    # Get current output
    output = get_tmux_output(session_name)
    error_type = detect_error_type(output)

    print(f"Detected state: {error_type}")
    print()

    # Show last few lines
    print("=== Recent Output ===")
    lines = output.split('\n')[-15:]
    for line in lines:
        print(f"  {line}")
    print()

    if check_only:
        print("Check complete. Use without --check to send resume message.")
        return

    # Generate message
    if retry_mode:
        message = "Retry the last failed operation. If it was a Task tool call, re-execute it with the same parameters."
    else:
        message = get_resume_message(error_type, custom_message)

    print(f"Sending message: {message[:80]}{'...' if len(message) > 80 else ''}")
    print()

    # Send message
    send_message(session_name, message, confirm=True)

    print("Message sent successfully!")
    print()

    # Wait and show response
    print("Waiting for response...")
    time.sleep(5)

    new_output = get_tmux_output(session_name, lines=20)
    print()
    print("=== Current Output ===")
    for line in new_output.split('\n')[-15:]:
        print(f"  {line}")
    print()

    print("=== Actions ===")
    print(f"  Monitor:  python3 {Path(__file__).parent}/status.py {session_name}")
    print(f"  Attach:   tmux attach -t {session_name}")


if __name__ == "__main__":
    main()
