#!/usr/bin/env python3
"""
Hook handler for SessionStart event.
Checks if the plugin has upstream updates available and notifies the user.

This hook runs at session start and provides a non-blocking notification
if updates are available, without interrupting the session.

Update detection uses Claude Code's plugin system:
- Reads installed plugin info from ~/.claude/plugins/installed_plugins.json
- Fetches latest release info from GitHub Releases API
- Suggests using /plugin commands to update
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


# Cache settings
CACHE_FILE = Path.home() / ".claude" / "plugins" / ".worktree-task-update-cache.json"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

# Plugin identification
PLUGIN_NAME = "worktree-task"
MARKETPLACE_NAME = "worktree-task-plugin"
PLUGIN_ID = f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"

# GitHub repository info
GITHUB_OWNER = "ourines"
GITHUB_REPO = "worktree-task-plugin"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Promotional links (shown occasionally in update notifications)
PROMO_LINKS = {
    "twitter": "https://x.com/ourines_",
    "github": f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}",
}


def get_claude_plugins_dir() -> Path:
    """Get the Claude Code plugins directory."""
    return Path.home() / ".claude" / "plugins"


def load_cache() -> dict:
    """Load update check cache from disk."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(cache: dict) -> None:
    """Save update check cache to disk."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except IOError:
        pass


def is_cache_valid(cache: dict) -> bool:
    """Check if cache is still valid (within TTL)."""
    last_check = cache.get("last_check", 0)
    return (time.time() - last_check) < CACHE_TTL_SECONDS


def get_installed_plugin_info() -> dict:
    """
    Read installed plugin info from Claude Code's installed_plugins.json.
    
    Returns dict with:
    - version: str
    - gitCommitSha: str
    - installPath: str
    - found: bool
    """
    result = {
        "version": "",
        "gitCommitSha": "",
        "installPath": "",
        "found": False
    }
    
    plugins_file = get_claude_plugins_dir() / "installed_plugins.json"
    if not plugins_file.exists():
        return result
    
    try:
        with open(plugins_file, "r") as f:
            data = json.load(f)
        
        plugin_info = data.get("plugins", {}).get(PLUGIN_ID, {})
        if plugin_info:
            result["version"] = plugin_info.get("version", "")
            result["gitCommitSha"] = plugin_info.get("gitCommitSha", "")
            result["installPath"] = plugin_info.get("installPath", "")
            result["found"] = True
    except (json.JSONDecodeError, IOError):
        pass
    
    return result


def get_marketplace_info() -> dict:
    """
    Read marketplace info from Claude Code's known_marketplaces.json.
    
    Returns dict with:
    - repo: str (e.g., "ourines/worktree-task-plugin")
    - installLocation: str
    - found: bool
    """
    result = {
        "repo": "",
        "installLocation": "",
        "found": False
    }
    
    marketplaces_file = get_claude_plugins_dir() / "known_marketplaces.json"
    if not marketplaces_file.exists():
        return result
    
    try:
        with open(marketplaces_file, "r") as f:
            data = json.load(f)
        
        marketplace_info = data.get(MARKETPLACE_NAME, {})
        if marketplace_info:
            source = marketplace_info.get("source", {})
            result["repo"] = source.get("repo", "")
            result["installLocation"] = marketplace_info.get("installLocation", "")
            result["found"] = True
    except (json.JSONDecodeError, IOError):
        pass
    
    return result


def run_git_command(cmd: list, cwd: str = None) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5  # Reduced from 15s to 5s for faster startup
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""


def get_local_commit_sha(install_path: str) -> str:
    """Get the actual commit SHA from the installed plugin directory (not from installed_plugins.json)."""
    if not install_path or not os.path.isdir(install_path):
        return ""
    success, sha = run_git_command(["git", "rev-parse", "HEAD"], install_path)
    return sha if success else ""


def fetch_github_release() -> dict:
    """
    Fetch latest release info from GitHub Releases API.
    
    Returns dict with:
    - tag_name: str (e.g., "v1.0.0")
    - name: str (release title)
    - body: str (release notes in markdown)
    - published_at: str
    - html_url: str (link to release page)
    - found: bool
    - error: str
    """
    result = {
        "tag_name": "",
        "name": "",
        "body": "",
        "published_at": "",
        "html_url": "",
        "found": False,
        "error": ""
    }
    
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "worktree-task-plugin"
            }
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            result["tag_name"] = data.get("tag_name", "")
            result["name"] = data.get("name", "")
            result["body"] = data.get("body", "")
            result["published_at"] = data.get("published_at", "")
            result["html_url"] = data.get("html_url", "")
            result["found"] = True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["error"] = "No releases found"
        else:
            result["error"] = f"HTTP error: {e.code}"
    except urllib.error.URLError as e:
        result["error"] = f"Network error: {e.reason}"
    except (json.JSONDecodeError, TimeoutError) as e:
        result["error"] = str(e)
    
    return result


def parse_version(tag: str) -> tuple:
    """Parse version tag like 'v1.2.3' into tuple (1, 2, 3) for comparison."""
    import re
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    if match:
        return tuple(int(x) for x in match.groups())
    return (0, 0, 0)


def check_remote_updates(install_path: str, local_sha: str, local_version: str) -> dict:
    """
    Check if there are updates available using GitHub Releases API.
    Falls back to git commit comparison if no releases found.
    
    Returns dict with:
    - has_updates: bool
    - update_type: str ("release" or "commit")
    - remote_version: str (for release updates)
    - remote_sha: str (for commit updates)
    - release_name: str
    - release_notes: str
    - release_url: str
    - behind_count: int
    - error: str
    """
    result = {
        "has_updates": False,
        "update_type": "",
        "remote_version": "",
        "remote_sha": "",
        "release_name": "",
        "release_notes": "",
        "release_url": "",
        "behind_count": 0,
        "error": ""
    }
    
    # Try GitHub Releases API first
    release_info = fetch_github_release()
    
    if release_info["found"]:
        remote_version = release_info["tag_name"]
        result["remote_version"] = remote_version
        result["release_name"] = release_info["name"] or remote_version
        result["release_url"] = release_info["html_url"]
        
        # Parse release notes (truncate if too long)
        body = release_info["body"] or ""
        if len(body) > 500:
            body = body[:500] + "..."
        result["release_notes"] = body
        
        # Compare versions
        if local_version:
            local_ver = parse_version(local_version)
            remote_ver = parse_version(remote_version)
            if remote_ver > local_ver:
                result["has_updates"] = True
                result["update_type"] = "release"
                return result
    
    # Fallback: Check git commits if no release or version match
    if not install_path or not os.path.isdir(install_path):
        result["error"] = release_info.get("error", "Install path not found")
        return result
    
    # Check if it's a git repository
    success, _ = run_git_command(["git", "rev-parse", "--git-dir"], install_path)
    if not success:
        result["error"] = "Not a git repository"
        return result
    
    # Fetch updates from remote (silent)
    success, _ = run_git_command(["git", "fetch", "--quiet", "origin"], install_path)
    if not success:
        result["error"] = "Failed to fetch from remote"
        return result
    
    # Get current branch
    success, branch = run_git_command(["git", "branch", "--show-current"], install_path)
    if not success:
        branch = "main"
    
    # Get remote HEAD commit
    remote_ref = f"origin/{branch}"
    success, remote_sha = run_git_command(["git", "rev-parse", remote_ref], install_path)
    if success:
        result["remote_sha"] = remote_sha[:8]
    
    # Compare with local SHA
    if local_sha and remote_sha:
        if local_sha != remote_sha and not remote_sha.startswith(local_sha[:8]):
            success, behind_count = run_git_command(
                ["git", "rev-list", "--count", f"{local_sha}..{remote_ref}"],
                install_path
            )
            if success and behind_count.isdigit():
                count = int(behind_count)
                if count > 0:
                    result["has_updates"] = True
                    result["update_type"] = "commit"
                    result["behind_count"] = count
    
    return result


def format_release_notes(notes: str, max_lines: int = 5) -> str:
    """Format release notes for display, limiting lines."""
    if not notes:
        return ""
    lines = notes.strip().split("\n")
    formatted = []
    for line in lines[:max_lines]:
        # Clean up markdown formatting for terminal display
        line = line.strip()
        if line.startswith("- "):
            formatted.append(f"  • {line[2:]}")
        elif line.startswith("* "):
            formatted.append(f"  • {line[2:]}")
        elif line.startswith("# "):
            continue  # Skip headers
        elif line.startswith("## "):
            formatted.append(f"  {line[3:]}")
        elif line:
            formatted.append(f"  {line}")
    if len(lines) > max_lines:
        formatted.append(f"  ... and {len(lines) - max_lines} more")
    return "\n".join(formatted)


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        hook_input = {}

    source = hook_input.get("source", "startup")

    # Only check on startup, skip for resume/clear/compact to avoid repeated checks
    if source != "startup":
        sys.exit(0)

    # Prepare output
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart"
        }
    }

    # Get installed plugin info
    plugin_info = get_installed_plugin_info()
    if not plugin_info["found"]:
        # Plugin not found in installed_plugins.json, skip check
        print(json.dumps(output))
        sys.exit(0)

    # Get marketplace info
    marketplace_info = get_marketplace_info()
    install_path = plugin_info["installPath"] or marketplace_info["installLocation"]

    if not install_path:
        print(json.dumps(output))
        sys.exit(0)

    # Get actual local commit SHA from install directory (not from installed_plugins.json which may be stale)
    local_sha = get_local_commit_sha(install_path)
    if not local_sha:
        # Fallback to installed_plugins.json if git command fails
        local_sha = plugin_info["gitCommitSha"]
    local_version = plugin_info["version"]

    # Check cache - skip network requests if recently checked with same local SHA
    cache = load_cache()
    if is_cache_valid(cache) and cache.get("local_sha") == local_sha:
        # Use cached result
        if cache.get("has_updates") and cache.get("message"):
            output["systemMessage"] = cache["message"]
        print(json.dumps(output))
        sys.exit(0)

    # Check for updates (use version for release comparison)
    update_info = check_remote_updates(install_path, local_sha, local_version)

    message = None
    if update_info.get("has_updates"):
        update_type = update_info["update_type"]

        if update_type == "release":
            # Release-based update notification
            remote_version = update_info["remote_version"]
            release_name = update_info["release_name"]

            message = f"🚀 Worktree Task Plugin: New release available!"
            message += f"\n   {local_version or 'current'} → {remote_version}"
            if release_name and release_name != remote_version:
                message += f" ({release_name})"

            # Show release notes
            if update_info["release_notes"]:
                formatted_notes = format_release_notes(update_info["release_notes"])
                if formatted_notes:
                    message += f"\n\n📋 What's New:\n{formatted_notes}"

            # Release URL
            if update_info["release_url"]:
                message += f"\n\n🔗 Details: {update_info['release_url']}"
        else:
            # Commit-based update notification (fallback)
            behind_count = update_info["behind_count"]
            local_sha_short = local_sha[:8] if local_sha else "unknown"
            remote_sha = update_info["remote_sha"]

            message = f"🔄 Worktree Task Plugin: {behind_count} update(s) available"
            if local_sha_short and remote_sha:
                message += f" ({local_sha_short} → {remote_sha})"

        # Update commands
        message += f"\n\n📦 To update:\n"
        message += f"  /plugin uninstall {PLUGIN_ID}\n"
        message += f"  /plugin install {PLUGIN_ID}"

        # Promotional footer (subtle, at the very end)
        message += f"\n\n─────────────────────────────"
        message += f"\n⭐ Like this plugin? Star us: {PROMO_LINKS['github']}"

        output["systemMessage"] = message

    # Save to cache
    save_cache({
        "last_check": time.time(),
        "local_sha": local_sha,
        "has_updates": update_info.get("has_updates", False),
        "message": message
    })

    # Output JSON result
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
