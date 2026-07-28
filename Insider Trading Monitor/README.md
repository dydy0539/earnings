# Insider Trading Monitor

Scrapes and monitors insider trading data from [Finviz](https://finviz.com/insidertrading?or=-10&tv=100000&tc=1&o=-transactionValue).

## Overview

This tool extracts all insider trading transactions from the Finviz "Top Insider Trading Recent Week" page, which shows transactions with $100,000+ value sorted by transaction value.

## Data Extracted

For each insider transaction, the scraper extracts:

- **Ticker**: Stock symbol
- **Owner**: Name of the insider
- **Relationship**: Relationship to company (CEO, Director, etc.)
- **Date**: Transaction date
- **Transaction Type**: Buy or Sale
- **Cost**: Price per share
- **Shares**: Number of shares traded
- **Value ($)**: Total transaction value
- **Shares Total**: Total shares owned after transaction
- **SEC Form 4**: Link to SEC filing and filing date

## Relationship-Based Sorting

All output files (JSON and CSV) are automatically sorted by relationship importance:

| Rank | Relationship | Score | Rationale |
|------|-------------|-------|-----------|
| 1 | **CFO / Chief Financial Officer** | 5 | Highest financial insight into company performance |
| 2 | **CEO / Chief Executive Officer** | 4 | Ultimate decision-maker, strong conviction signal |
| 3 | **Chairman / C-suite (COO, CRO, CTO, etc.)** | 3 | Senior leadership with strategic insight |
| 4 | **Director** | 2 | Board-level oversight and governance |
| 5 | **Other** | 1 | Other insiders (VP, managers, etc.) |

Within each rank, transactions are further sorted by value (highest first).

## Installation

Dependencies are already installed in the parent project. If running standalone:

```bash
pip install requests beautifulsoup4 lxml
```

## Usage

### Basic Usage

Scrape and save to both JSON and CSV (default, filters transactions < $100,000):

```bash
cd "Insider Trading Monitor"
python3 scrape_insider_trading.py
```

**Note:** By default, the scraper filters out any transactions with value less than $100,000.

### Output Formats

**JSON only:**
```bash
python3 scrape_insider_trading.py --output json
```

**CSV only:**
```bash
python3 scrape_insider_trading.py --output csv
```

**Custom filename:**
```bash
python3 scrape_insider_trading.py --filename insider_trades_20260212
```
This creates: `insider_trades_20260212.json` and `insider_trades_20260212.csv`

### Debug Mode

```bash
python3 scrape_insider_trading.py --debug
```

### Quiet Mode (No Summary)

```bash
python3 scrape_insider_trading.py --quiet
```

### Custom Minimum Value Filter

Filter to only show transactions above a specific value:

```bash
# Only show transactions >= $500,000
python3 scrape_insider_trading.py --min-value 500000

# Only show transactions >= $1,000,000 (1M+)
python3 scrape_insider_trading.py --min-value 1000000

# Only show transactions >= $5,000,000 (5M+)
python3 scrape_insider_trading.py --min-value 5000000
```

## Output Files

### JSON Format

```json
{
  "scraped_at": "2026-02-12T10:30:00.000000",
  "source": "https://finviz.com/insidertrading?or=-10&tv=100000&tc=1&o=-transactionValue",
  "total_transactions": 150,
  "transactions": [
    {
      "ticker": "SGP",
      "owner": "RA CAPITAL MANAGEMENT, L.P.",
      "relationship": "Director",
      "date": "Feb 09 '26",
      "transaction_type": "Buy",
      "cost": "16.00",
      "shares": "3,690,000",
      "value": "59,040,000",
      "shares_total": "5,966,439",
      "sec_form_date": "Feb 11 05:15 PM",
      "sec_form_link": "http://www.sec.gov/Archives/edgar/..."
    }
  ]
}
```

### CSV Format

Standard CSV with headers:
```
ticker,owner,relationship,date,transaction_type,cost,shares,value,shares_total,sec_form_date,sec_form_link
SGP,RA CAPITAL MANAGEMENT L.P.,Director,Feb 09 '26,Buy,16.00,"3,690,000","59,040,000","5,966,439",Feb 11 05:15 PM,http://www.sec.gov/...
```

## Example Output

```
================================================================================================
INSIDER TRADING SUMMARY - 2026-02-12 10:30:00
================================================================================================
Ticker   Owner                          Relationship              Date         Type  Value           Shares      
------------------------------------------------------------------------------------------------
SGP      RA CAPITAL MANAGEMENT, L.P.    Director                  Feb 09 '26   Buy   59,040,000      3,690,000   
SGP      Behbahani Ali                  Director                  Feb 09 '26   Buy   15,000,000      937,500     
HCICU    HENNESSY DANIEL J              Chairman and CEO          Feb 06 '26   Buy   6,710,000       671,000     
KKR      BARAKETT TIMOTHY R             Director                  Feb 09 '26   Buy   5,246,500       50,000      
RDDT     FARRELL SARAH E                Director                  Feb 10 '26   Buy   6,549,030       43,800      
================================================================================================
Total transactions: 150
================================================================================================
```

## Automation

To run automatically, you can:

1. **Add to cron** (Linux/Mac):
```bash
# Run daily at 6 PM
0 18 * * * cd "/path/to/Insider Trading Monitor" && python3 scrape_insider_trading.py
```

2. **Add to launchd** (Mac):
Create a plist file similar to the earnings scraper

3. **Windows Task Scheduler**:
Create a scheduled task to run the script

## Logs

All scraping activity is logged to `insider_trading_scraper.log` in the same directory.

## Notes

- The page shows transactions from the recent week with value > $100,000
- Data is sorted by transaction value (highest first)
- Large insider purchases can be bullish signals
- Director/officer buying is typically more significant than selling
- Always cross-reference with company fundamentals

## Future Enhancements

Potential additions:
- Filter by transaction type (buy/sell)
- Filter by minimum transaction value
- Track changes over time
- Alert on specific tickers
- Analyze patterns (e.g., multiple insiders buying)
- Integration with earnings data
