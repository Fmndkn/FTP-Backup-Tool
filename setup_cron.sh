#!/bin/bash
# setup_cron.sh - Setup cron job with proper error handling

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="/usr/bin/python3"
SCRIPT_PATH="$SCRIPT_DIR/backup_ftp.py"
LOG_DIR="$SCRIPT_DIR/log"
CRON_LOG="$SCRIPT_DIR/cron.log"

# Create directories if needed
mkdir -p "$LOG_DIR"

# Create cron job
CRON_JOB="0 2 * * * $PYTHON_PATH $SCRIPT_PATH >> $CRON_LOG 2>&1"

# Add to crontab
(crontab -l 2>/dev/null | grep -v "backup_ftp.py"; echo "$CRON_JOB") | crontab -

echo "Cron job installed:"
echo "$CRON_JOB"
echo ""
echo "Logs will be written to:"
echo "  - Script logs: $LOG_DIR/backup.log"
echo "  - Cron output: $CRON_LOG"
echo ""
echo "To check status:"
echo "  tail -f $CRON_LOG"
echo "  tail -f $LOG_DIR/backup.log"