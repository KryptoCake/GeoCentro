#!/bin/bash
# Script to setup cron job for the scraper in crontab

CRON_JOB="*/30 * * * * /var/www/geocentro/venv/bin/python /var/www/geocentro/scraper.py >> /var/www/geocentro/scraper.log 2>&1"

echo "Checking current crontab..."
if crontab -l 2>/dev/null | grep -F "scraper.py" >/dev/null; then
    echo "Cron job for scraper.py is already configured."
else
    echo "Adding cron job to run every 30 minutes..."
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job added successfully."
fi

echo "Current crontab entries:"
crontab -l
