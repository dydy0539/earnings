#!/bin/bash

# Earnings Scraper Scheduler Management Script

PLIST_FILE="$HOME/Library/LaunchAgents/com.earnings.scraper.plist"
SCRIPT_DIR="/Users/yiding/Dropbox/My Mac (Yis-MacBook-Pro.local)/Documents/earnings"

case "$1" in
    start)
        echo "Loading earnings scraper scheduler..."
        launchctl load "$PLIST_FILE"
        echo "Scheduler loaded. Will run at 9:00 AM and 9:00 PM on weekdays."
        ;;
    stop)
        echo "Stopping earnings scraper scheduler..."
        launchctl unload "$PLIST_FILE"
        echo "Scheduler stopped."
        ;;
    status)
        echo "Checking scheduler status..."
        if launchctl list | grep -q "com.earnings.scraper"; then
            echo "✅ Scheduler is RUNNING"
            echo "Next run: 9:00 AM and 9:00 PM on weekdays"
        else
            echo "❌ Scheduler is STOPPED"
        fi
        ;;
    test)
        echo "Running scraper manually for testing..."
        cd "$SCRIPT_DIR"
        python3 scrape_earnings_selenium_final.py
        ;;
    logs)
        echo "=== OUTPUT LOG ==="
        if [ -f "$SCRIPT_DIR/earnings_log.txt" ]; then
            tail -20 "$SCRIPT_DIR/earnings_log.txt"
        else
            echo "No output log found."
        fi
        echo ""
        echo "=== ERROR LOG ==="
        if [ -f "$SCRIPT_DIR/earnings_error.txt" ]; then
            tail -20 "$SCRIPT_DIR/earnings_error.txt"
        else
            echo "No error log found."
        fi
        ;;
    edit-time)
        echo "Current schedule: 9:00 AM and 9:00 PM on weekdays (Mon-Fri)"
        echo "To change the time, edit the plist file:"
        echo "nano ~/Library/LaunchAgents/com.earnings.scraper.plist"
        echo ""
        echo "Then restart the scheduler:"
        echo "$0 stop"
        echo "$0 start"
        ;;
    *)
        echo "Earnings Scraper Scheduler Management"
        echo ""
        echo "Usage: $0 {start|stop|status|test|logs|edit-time}"
        echo ""
        echo "Commands:"
        echo "  start     - Start the scheduler (runs 9:00 AM & 9:00 PM weekdays)"
        echo "  stop      - Stop the scheduler"
        echo "  status    - Check if scheduler is running"
        echo "  test      - Run scraper manually for testing"
        echo "  logs      - Show recent log entries"
        echo "  edit-time - Instructions to change schedule time"
        echo ""
        exit 1
        ;;
esac