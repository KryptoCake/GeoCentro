#!/bin/bash
# Script to verify all services and scraper database status

echo "=============================================="
echo "   GeoCentro Status Verification Report"
echo "=============================================="
echo ""

echo "1. System Services Status:"
echo "--------------------------"
GEOCENTRO_STATUS=$(systemctl is-active geocentro)
NGINX_STATUS=$(systemctl is-active nginx)
echo "Gunicorn (geocentro.service): $GEOCENTRO_STATUS"
echo "Nginx (nginx.service):        $NGINX_STATUS"
echo ""

echo "2. Ports Listening:"
echo "-------------------"
if command -v ss &> /dev/null; then
    ss -tulpn | grep -E '8082|8085' || echo "No active listener on 8082 (Nginx) or 8085 (Gunicorn)"
else
    netstat -tulpn | grep -E '8082|8085' || echo "No active listener on 8082 (Nginx) or 8085 (Gunicorn)"
fi
echo ""

echo "3. Database Sismos Count:"
echo "-------------------------"
DB_PATH="/var/www/geocentro/geocentro.db"
if [ -f "$DB_PATH" ]; then
    if command -v sqlite3 &> /dev/null; then
        COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM sismos;")
        LATEST_DATE=$(sqlite3 "$DB_PATH" "SELECT max(fecha_utc) FROM sismos;")
        echo "Total earthquakes in DB: $COUNT"
        echo "Latest earthquake date:  $LATEST_DATE"
    else
        echo "sqlite3 command not found. Database file exists: $(ls -lh $DB_PATH)"
    fi
else
    echo "Database file not found at $DB_PATH yet."
fi
echo ""

echo "4. Last 5 Scraper Log Lines:"
echo "----------------------------"
LOG_PATH="/var/www/geocentro/scraper.log"
if [ -f "$LOG_PATH" ]; then
    tail -n 5 "$LOG_PATH"
else
    echo "Log file not found at $LOG_PATH yet."
fi
echo ""

echo "5. Backup Configuration and Status:"
echo "-----------------------------------"
BACKUP_SCRIPT="/var/www/geocentro/backup_vps.py"
if [ -f "$BACKUP_SCRIPT" ]; then
    echo "Backup script exists at $BACKUP_SCRIPT"
    if [ -x "$BACKUP_SCRIPT" ]; then
        echo "Backup script is executable."
    else
        echo "WARNING: Backup script is NOT executable! Run: chmod +x $BACKUP_SCRIPT"
    fi
else
    echo "Backup script not found at $BACKUP_SCRIPT yet."
fi

# Check cron job
if crontab -l 2>/dev/null | grep -F "backup_vps.py" >/dev/null; then
    echo "Daily backup cron job: Configured"
else
    echo "Daily backup cron job: NOT configured"
fi

# Check existing backups
BACKUP_DIR="/var/www/geocentro/backups"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "geocentro_backup_*.tar.gz" | wc -l)
    echo "Backups stored locally in $BACKUP_DIR: $BACKUP_COUNT"
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        echo "Latest backup files:"
        ls -lh "$BACKUP_DIR"/geocentro_backup_*.tar.gz | tail -n 3
    fi
else
    echo "Backup directory not created yet."
fi
echo ""
echo "=============================================="
