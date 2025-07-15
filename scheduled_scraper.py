#!/usr/bin/env python3
"""
Scheduled earnings scraper that runs automatically
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from scrape_earnings_selenium_final import EarningsSeleniumScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_earnings_scraper():
    """Run the earnings scraper"""
    scraper = None
    try:
        logging.info("Starting scheduled earnings scraper...")
        
        # Get today's date in YYYYMMDD format
        today = datetime.now().strftime("%Y%m%d")
        
        scraper = EarningsSeleniumScraper(headless=True, debug=False)
        data = scraper.scrape_calendar(today)
        
        if data and data.get('status') == 'success':
            companies = data.get('companies', [])
            logging.info(f"Successfully scraped {len(companies)} companies for {today}")
        else:
            logging.warning(f"Scraping failed or no data found for {today}")
            
    except Exception as e:
        logging.error(f"Error in scheduled scraper: {e}")
    finally:
        if scraper:
            scraper.close()

def main():
    """Main scheduler function"""
    scheduler = BlockingScheduler()
    
    # Schedule to run Monday-Friday at 6:00 AM
    scheduler.add_job(
        run_earnings_scraper,
        CronTrigger(hour=6, minute=0, day_of_week='mon-fri'),
        id='earnings_scraper',
        name='Daily Earnings Scraper'
    )
    
    # Schedule to run immediately for testing (optional)
    # scheduler.add_job(run_earnings_scraper, 'interval', seconds=10, id='test_run')
    
    logging.info("Scheduler started. Jobs:")
    for job in scheduler.get_jobs():
        logging.info(f"  - {job.name}: {job.trigger}")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")
        scheduler.shutdown()

if __name__ == "__main__":
    main()