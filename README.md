# EarningsWhispers.com Scraper

This project contains two different approaches to scrape earnings calendar data from EarningsWhispers.com:

## 🔍 What We Discovered

1. **The website loads earnings data dynamically via JavaScript** - specifically through a call to `getcalctrls("20250714", "1")`
2. **Cookie acceptance is required** but is handled automatically by our scripts
3. **The page structure is correct** - we can access the page and it shows "Earnings Scheduled for Monday, July 14, 2025"
4. **Two scraping approaches are needed:**
   - **BeautifulSoup**: For basic HTML content (faster, simpler)
   - **Selenium**: For JavaScript-loaded content (more complete, handles dynamic loading)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. For JavaScript-Loaded Content (Recommended)

You'll need ChromeDriver for Selenium. Choose one option:

**Option A: Install ChromeDriver manually**
```bash
# Download ChromeDriver from https://chromedriver.chromium.org/
# Extract and place in your PATH
```

**Option B: Use webdriver-manager (automated)**
```bash
pip install webdriver-manager
# The script will automatically download ChromeDriver
```

## 📋 Available Scripts

### 1. `scrape_earnings_calendar.py` - BeautifulSoup Approach
- **Pros**: Fast, lightweight, no browser dependencies
- **Cons**: Cannot handle JavaScript-loaded content
- **Best for**: Static HTML content, testing connectivity

```bash
python3 scrape_earnings_calendar.py
```

### 2. `scrape_earnings_selenium.py` - Selenium Approach  
- **Pros**: Handles JavaScript, complete page rendering, dynamic content
- **Cons**: Requires ChromeDriver, slower, more resource-intensive
- **Best for**: Full dynamic content scraping

```bash
python3 scrape_earnings_selenium.py
```

## 🛠️ Setup Instructions

### For macOS (your system):

1. **Install Chrome Browser** (if not already installed):
   - Download from https://www.google.com/chrome/

2. **Install ChromeDriver** (choose one method):

   **Method A: Manual Installation**
   ```bash
   # Download ChromeDriver matching your Chrome version
   # From: https://chromedriver.chromium.org/downloads
   
   # Extract and move to PATH
   sudo mv chromedriver /usr/local/bin/
   sudo chmod +x /usr/local/bin/chromedriver
   ```

   **Method B: Using webdriver-manager** (already included in requirements.txt)
   ```bash
   pip install webdriver-manager
   # Script will auto-download ChromeDriver
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 📊 Output Format

Both scripts generate JSON files with the following structure:

```json
{
  "date": "20250714",
  "scraped_at": "2025-07-11T20:44:46.259709",
  "companies": [
    {
      "symbol": "AAPL",
      "company_name": "Apple Inc.",
      "time": "After Market Close",
      "consensus": "$1.25",
      "whisper": "$1.28"
    }
  ]
}
```

## 🔧 Configuration

### Debug Mode
Both scripts support debug mode for troubleshooting:

```python
# Enable debug mode to see detailed output
scraper = EarningsCalendarScraper(debug=True)  # BeautifulSoup
scraper = EarningsSeleniumScraper(headless=False, debug=True)  # Selenium
```

### Headless Mode (Selenium)
```python
# Run without opening browser window
scraper = EarningsSeleniumScraper(headless=True)
```

## 📅 Changing the Target Date

To scrape a different date, modify the `date_str` variable in either script:

```python
date_str = "20250714"  # Format: YYYYMMDD
```

## 🐛 Troubleshooting

### Common Issues:

1. **ChromeDriver not found**:
   - Make sure ChromeDriver is installed and in PATH
   - Or use webdriver-manager (automatic)

2. **No companies found**:
   - The date might not have earnings data
   - JavaScript might need more time to load
   - Check debug output for more details

3. **Connection issues**:
   - Check internet connection
   - The site might be blocking requests
   - Try adding delays between requests

### Debug Files Generated:
- `debug_initial_page.html` - Initial page load
- `debug_final_page.html` - After JavaScript execution
- `debug_selenium_page.html` - Selenium page source
- `earnings_calendar_*.json` - Scraped data

## 📈 Current Status

**For July 14, 2025:**
- ✅ Page loads successfully
- ✅ Correct date and title detected
- ✅ Cookie handling works
- ⚠️ JavaScript-loaded content detection needed
- ⚠️ ChromeDriver setup required for full functionality

## 🎯 Next Steps

1. **Set up ChromeDriver** using one of the methods above
2. **Run the Selenium scraper** to get complete data
3. **Modify the date** to scrape different earnings dates
4. **Customize extraction logic** based on actual page structure

## 🔍 Technical Details

The website uses:
- **Dynamic loading** via `getcalctrls()` JavaScript function
- **Cookie acceptance** requirements
- **AJAX/API calls** to load earnings data
- **Bootstrap framework** for UI
- **D3.js** for data visualization

## 📝 Notes

- The site appears to be legitimate and accessible
- Rate limiting might be in place
- Some features may require user registration
- Data availability varies by date 