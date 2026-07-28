# Quick Start Guide - Insider Trading Monitor

## 🚀 Run the Scraper

```bash
cd "/Users/yiding/Dropbox/My Mac (Yis-MacBook-Pro.local)/Documents/earnings/Insider Trading Monitor"
python3 scrape_insider_trading.py
```

**🎯 Features:**
- **Automatic Filtering:** Transactions < $100,000 are filtered out
- **Smart Sorting:** Results sorted by relationship importance (CFO > CEO > Chairman > Director)

## 📊 What You Get

The scraper extracts **all insider transactions** from [Finviz's Top Insider Trading page](https://finviz.com/insidertrading?or=-10&tv=100000&tc=1&o=-transactionValue).

### Output Files (Both Created Automatically):

1. **`insider_trading_YYYYMMDD_HHMMSS.json`** - Structured JSON format
2. **`insider_trading_YYYYMMDD_HHMMSS.csv`** - Excel-compatible CSV format

### Data Extracted:

| Field | Description |
|-------|-------------|
| `ticker` | Stock symbol (e.g., "SGP", "KKR") |
| `owner` | Insider name |
| `relationship` | Role (Director, CEO, Chairman, etc.) |
| `date` | Transaction date |
| `transaction_type` | "Buy" or "Sale" |
| `cost` | Price per share |
| `shares` | Number of shares traded |
| `value` | Total transaction value ($) |
| `shares_total` | Total shares owned after transaction |
| `sec_form_link` | Link to SEC Form 4 filing |
| `sec_form_date` | SEC filing date |

## 💡 Example Output

```
SGP      RA CAPITAL MANAGEMENT, L.P.    Director    Feb 09 '26   Buy   59,040,000    3,690,000
KKR      BARAKETT TIMOTHY R             Director    Feb 09 '26   Buy   5,246,500     50,000
RDDT     FARRELL SARAH E                Director    Feb 10 '26   Buy   6,549,030     43,800
```

## 🎯 Common Use Cases

### 1. Quick Daily Check
```bash
python3 scrape_insider_trading.py
```

### 2. Custom Filename
```bash
python3 scrape_insider_trading.py --filename daily_insiders_20260216
```

### 3. JSON Only
```bash
python3 scrape_insider_trading.py --output json
```

### 4. CSV Only (for Excel)
```bash
python3 scrape_insider_trading.py --output csv
```

### 5. Quiet Mode (No Terminal Output)
```bash
python3 scrape_insider_trading.py --quiet
```

### 6. Custom Value Filter
```bash
# Only show $500K+ transactions
python3 scrape_insider_trading.py --min-value 500000

# Only show $1M+ transactions
python3 scrape_insider_trading.py --min-value 1000000

# Only show $5M+ transactions (high-conviction signals)
python3 scrape_insider_trading.py --min-value 5000000
```

## 📈 Analyzing the Data

### Relationship Importance Ranking

The scraper automatically sorts transactions by relationship importance:

1. **CFO** (Score 5) - Best financial insight
2. **CEO** (Score 4) - Ultimate decision-maker  
3. **Chairman/C-suite** (Score 3) - Strategic leadership
4. **Director** (Score 2) - Board oversight
5. **Other** (Score 1) - Other insiders

### High-Value Insider Buys (Bullish Signal)

Look for:
- **CFO/CEO purchases** - Highest conviction signals
- **Large purchases** (>$1M) by executives/directors
- **Multiple insiders buying** the same stock
- Buying at **52-week lows**

### Red Flags

Watch for:
- **Large insider selling** by multiple executives
- **CEO/CFO selling** large positions
- Selling before **earnings announcements**

## 🔄 Automation Options

### Daily Cron Job (Mac/Linux)
```bash
# Edit crontab
crontab -e

# Add line to run at 6 PM daily
0 18 * * * cd "/path/to/Insider Trading Monitor" && python3 scrape_insider_trading.py --quiet
```

### launchd (Mac)
Similar to the earnings scraper setup

## 📝 Files in This Folder

- `scrape_insider_trading.py` - Main scraper script
- `README.md` - Full documentation
- `QUICK_START.md` - This quick reference
- `requirements.txt` - Python dependencies
- `insider_trading_scraper.log` - Execution logs
- `insider_trading_*.json` - JSON output files
- `insider_trading_*.csv` - CSV output files

## 🔍 View the Latest Data

```bash
# View latest JSON
cat insider_trading_*.json | tail -100

# View latest CSV in Excel/Numbers
open insider_trading_*.csv

# Count transactions
cat insider_trading_*.json | grep '"ticker"' | wc -l
```

## 💪 Pro Tips

1. **Run after market close** (4 PM ET) to capture the day's filings
2. **Compare with your portfolio** - Are your holdings seeing insider buying?
3. **Track high-conviction buys** - Insiders buying >$500K worth
4. **Cross-reference with earnings** - Insiders often buy before good earnings
5. **Look for clusters** - Multiple insiders buying = strong signal

## 🆘 Troubleshooting

**Script fails?**
- Check internet connection
- Verify Finviz is accessible: https://finviz.com
- Check logs: `cat insider_trading_scraper.log`

**No data?**
- The page may be temporarily down
- Try again in a few minutes
- Check if Finviz changed their HTML structure

## 📚 Full Documentation

See `README.md` for complete documentation including:
- Detailed API reference
- Output format specifications
- Advanced usage examples
- Integration ideas

---

**Happy Trading! 📊📈**
