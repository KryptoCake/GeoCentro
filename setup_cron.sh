#!/bin/bash
# Script to setup cron jobs for the scraper and backup in crontab

SCRAPER_JOB="*/30 * * * * /var/www/geocentro/venv/bin/python /var/www/geocentro/scraper.py >> /var/www/geocentro/scraper.log 2>&1"
BACKUP_JOB="0 2 * * * /var/www/geocentro/venv/bin/python /var/www/geocentro/backup_vps.py >> /var/www/geocentro/backups/backup.log 2>&1"

echo "Checking current crontab..."

# 1. Setup Scraper Job
if crontab -l 2>/dev/null | grep -F "scraper.py" >/dev/null; then
    echo "Cron job for scraper.py is already configured."
else
    echo "Adding cron job for scraper.py to run every 30 minutes..."
    (crontab -l 2>/dev/null; echo "$SCRAPER_JOB") | crontab -
    echo "Scraper cron job added successfully."
fi

# 2. Setup Backup Job
if crontab -l 2>/dev/null | grep -F "backup_vps.py" >/dev/null; then
    echo "Cron job for backup_vps.py is already configured."
else
    echo "Adding cron job for backup_vps.py to run daily at 2:00 AM..."
    (crontab -l 2>/dev/null; echo "$BACKUP_JOB") | crontab -
    echo "Backup cron job added successfully."
fi

echo "Current crontab entries:"
crontab -l
