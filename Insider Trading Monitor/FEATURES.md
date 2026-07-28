# Insider Trading Monitor - Feature Summary

## 🎯 Core Features

### 1. **Web Scraping**
- Automatically extracts insider trading data from [Finviz](https://finviz.com/insidertrading?or=-10&tv=100000&tc=1&o=-transactionValue)
- Captures all 11 data fields per transaction
- Handles 75+ transactions per scrape

### 2. **Smart Filtering** 
- Default: Filters out transactions < $100,000
- Customizable threshold via `--min-value` flag
- Reduces noise and focuses on significant activity

### 3. **Relationship-Based Sorting** ⭐ NEW
- Automatically ranks and sorts by insider importance
- Prioritizes high-conviction signals (CFO/CEO first)
- Applied to both JSON and CSV outputs

### 4. **Dual Output Formats**
- **JSON**: Structured data for programmatic access
- **CSV**: Excel-compatible for manual analysis

### 5. **Comprehensive Logging**
- Activity logs: `insider_trading_scraper.log`
- Success/error tracking
- Filter statistics

---

## 📊 Relationship Scoring System

The scraper uses intelligent ranking to surface the most important insider transactions:

| Score | Relationship | Why It Matters |
|-------|-------------|----------------|
| **5** | CFO / Chief Financial Officer | Best financial insight into company performance. CFOs have detailed knowledge of financials and future guidance. |
| **4** | CEO / Chief Executive Officer | Ultimate decision-maker. CEO buying signals strong confidence in company direction. |
| **3** | Chairman / C-suite Officers | Strategic leaders (COO, CRO, CTO, President, etc.) with operational insight. |
| **2** | Director | Board members with oversight responsibilities. Director buying shows governance-level confidence. |
| **1** | Other | VPs, managers, and other insiders. Still valuable but less strategic insight. |

**Secondary Sort**: Within each rank, transactions are sorted by value (highest first).

---

## 💡 Real-World Example

### Command:
```bash
python3 scrape_insider_trading.py --min-value 500000
```

### Result:
```
Filtered: kept 32, removed 43 below $500,000
Sorted by: CFO (5) > CEO (4) > Chairman/C-suite (3) > Director (2)
```

### Output (Top 5):
1. **HCICU - Chairman and CEO** - $6.7M buy
2. **TDG - President & CEO** - $1.2M buy  
3. **MAT - Chairman & CEO** - $1.0M buy
4. **CBC - President, CEO** - $979K buy
5. **VRNS - CEO, President, Chairman** - $598K buy

**Analysis**: All top transactions are from CEO/Chairman-level executives, the highest conviction signals!

---

## 🚀 Usage Examples

### Basic (Default Settings)
```bash
python3 scrape_insider_trading.py
# Filters: > $100K
# Sorting: By relationship
# Output: JSON + CSV
```

### High-Value C-suite Only
```bash
python3 scrape_insider_trading.py --min-value 1000000
# Only $1M+ transactions
# CEO/CFO/Chairman at top
```

### Custom Analysis
```bash
python3 scrape_insider_trading.py --min-value 250000 --filename weekly_review --output csv
# $250K+ threshold
# CSV only for Excel
# Custom filename
```

### Silent Background Run
```bash
python3 scrape_insider_trading.py --quiet
# No terminal output
# Perfect for cron jobs
```

---

## 📈 Analysis Workflow

### Step 1: Run Scraper
```bash
python3 scrape_insider_trading.py --min-value 500000
```

### Step 2: Review CSV in Excel
- Open `insider_trading_YYYYMMDD_HHMMSS.csv`
- Top rows = Highest importance insiders
- Look for patterns (multiple execs buying same stock)

### Step 3: Identify Signals

**Bullish Signals:**
- ✅ CFO/CEO large purchases ($1M+)
- ✅ Multiple C-suite buying same stock
- ✅ Chairman + CEO both buying
- ✅ Buying near 52-week lows

**Red Flags:**
- ⚠️ Only lower-level insiders buying
- ⚠️ Small transaction sizes
- ⚠️ Directors selling heavily

### Step 4: Cross-Reference
- Check against your portfolio holdings
- Look up company fundamentals
- Review recent earnings results
- Check insider buying history

---

## 🎯 Power User Tips

### 1. Focus on Top Signals
```bash
# Get only CFO/CEO transactions above $1M
python3 scrape_insider_trading.py --min-value 1000000
# Then manually filter CSV for CFO/CEO rows
```

### 2. Weekly Comparison
```bash
# Monday
python3 scrape_insider_trading.py --filename week_start

# Friday  
python3 scrape_insider_trading.py --filename week_end

# Compare the two files to see new insider activity
```

### 3. Track Specific Tickers
```bash
# Run scraper, then grep CSV for your tickers
python3 scrape_insider_trading.py
grep -E "AAPL|TSLA|NVDA" insider_trading_*.csv
```

### 4. Automate Daily
```bash
# Add to crontab (6 PM daily)
0 18 * * * cd "/path/to/Insider Trading Monitor" && python3 scrape_insider_trading.py --quiet
```

---

## 📊 Output Statistics

### Example Run (Feb 16, 2026):

**Raw Scrape:**
- Total transactions scraped: 75

**After Filtering ($100K min):**
- Kept: 75 (0 removed)

**After Sorting:**
- CFO transactions: 4
- CEO/Chairman transactions: 15
- Director transactions: 45
- Other: 11

**File Sizes:**
- JSON: ~33KB
- CSV: ~15KB

---

## 🔍 Technical Details

### Sorting Algorithm
1. Calculate relationship score (1-5) for each transaction
2. Parse transaction value to numeric
3. Sort by: `(relationship_score DESC, value DESC)`
4. Remove internal score field before saving
5. Apply to both JSON and CSV outputs

### Filtering Logic
1. Parse value string: "59,040,000" → 59040000
2. Compare against minimum threshold
3. Keep if `value >= min_value`
4. Log statistics: kept/removed counts

### Data Flow
```
Finviz Website
    ↓
HTML Scraping (BeautifulSoup)
    ↓
Data Extraction (75 transactions)
    ↓
Value Filtering (remove < $100K)
    ↓
Relationship Sorting (CFO first)
    ↓
JSON + CSV Output
```

---

## 🎉 Summary

With these features, you can:

✅ **Find the best insider signals** - CFO/CEO transactions surface first  
✅ **Filter noise** - Focus on significant transactions only  
✅ **Save time** - Pre-sorted by importance  
✅ **Make better decisions** - Prioritized actionable intelligence  
✅ **Automate monitoring** - Set and forget daily scrapes  

The Insider Trading Monitor is now a production-ready tool for tracking high-conviction insider activity! 🚀
