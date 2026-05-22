#!/bin/bash
# ==============================================================================
# GeoCentro Scraper Engine - VPS Cron execution helper
# ==============================================================================
# To configure this script to execute every 10 minutes, run `crontab -e` and add:
# */10 * * * * /bin/bash /var/www/GeoCentro/run_scraper.sh >> /var/www/GeoCentro/scraper.log 2>&1
# ==============================================================================

# Resolve the absolute path of this script to guarantee relative path resolution
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Log the execution time
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting cron scraper execution..."

# Activate Python Virtual Environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run scraper
python3 scraper.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Scraper execution completed."
echo "----------------------------------------------------"
