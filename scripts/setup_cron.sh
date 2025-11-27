#!/bin/bash
#
# Setup cron job for worktree task monitoring
#
# This script installs a cron job that runs every 30 minutes to monitor
# and auto-retry stalled worktree tasks.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="${SCRIPT_DIR}/monitor_and_retry.sh"
CRON_COMMENT="# Worktree Task Monitor - Auto-retry stalled tasks"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Setting up cron job for worktree task monitoring${NC}"
echo

# Check if monitor script exists
if [[ ! -f "$MONITOR_SCRIPT" ]]; then
    echo -e "${RED}Error: Monitor script not found at $MONITOR_SCRIPT${NC}"
    exit 1
fi

# Make sure script is executable
chmod +x "$MONITOR_SCRIPT"

# Create cron entry
CRON_ENTRY="*/30 * * * * $MONITOR_SCRIPT >> ${SCRIPT_DIR}/../.monitor_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -F "$MONITOR_SCRIPT" >/dev/null; then
    echo -e "${YELLOW}Cron job already exists. Updating...${NC}"
    # Remove old entry
    crontab -l 2>/dev/null | grep -v "$MONITOR_SCRIPT" | crontab -
fi

# Add new cron entry
(crontab -l 2>/dev/null || true; echo "$CRON_COMMENT"; echo "$CRON_ENTRY") | crontab -

echo -e "${GREEN}✓ Cron job installed successfully${NC}"
echo
echo "Schedule: Every 30 minutes"
echo "Script: $MONITOR_SCRIPT"
echo "Log: ${SCRIPT_DIR}/../.monitor_cron.log"
echo
echo "Current crontab:"
echo "----------------------------------------"
crontab -l | grep -A1 "Worktree Task Monitor" || echo "(no entries found)"
echo "----------------------------------------"
echo
echo -e "${GREEN}To view logs:${NC}"
echo "  tail -f ${SCRIPT_DIR}/../.monitor_cron.log"
echo
echo -e "${GREEN}To test manually:${NC}"
echo "  $MONITOR_SCRIPT --verbose"
echo
echo -e "${GREEN}To remove cron job:${NC}"
echo "  crontab -l | grep -v '$MONITOR_SCRIPT' | crontab -"
echo
