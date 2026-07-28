# Quick Reference Guide - Automated Incremental Margin Analysis

## 📊 What You Get Daily

Every weekday at 9 AM and 9 PM Eastern Time, the system automatically:

1. Scrapes earnings calendar from EarningsWhispers.com
2. Filters for your tracked companies + high-growth companies
3. **NEW**: Analyzes incremental operating margins for each company
4. Saves results to JSON files

## 📁 Output Files

### Three Files Per Run:

1. **`earnings_calendar_final_YYYYMMDD_XX.json`**
   - Raw scraped data (all companies)

2. **`earnings_filtered_YYYYMMDD_XX.json`**
   - Filtered companies (tracked + high-growth)

3. **`incremental_margins_YYYYMMDD_XX.json`** ⭐ NEW
   - Incremental margin analysis with financial metrics

Where `XX` = `AM` (morning run) or `BM` (evening run)

## 🔍 Quick Analysis Guide

### Look for These Signals:

✅ **Strong Companies**
- High incremental margin (>50%)
- `is_margin_expanding: true`
- Growing revenue + operating income

⚠️ **Watch List**
- Low incremental margin (<20%)
- `is_margin_expanding: false`
- May indicate pricing pressure or rising costs

❌ **Red Flags**
- Negative incremental margin
- Declining operating income despite revenue growth
- Unprofitable growth

## 💡 Real Example

```json
{
  "company_name": "Interactive Brokers Group Inc",
  "ticker": "IBKR",
  "incremental_operating_margin": 133.66,    // 🔥 Exceptional!
  "latest_operating_margin": 87.24,
  "is_margin_expanding": true,               // ✅ Getting better
  "revenue_growth_pct": 12.9,
  "operating_income_growth_pct": 21.22       // 📈 Faster than revenue
}
```

**Translation**: IBKR is generating $1.34 of operating income for every $1 of new revenue. This shows strong operational leverage and improving efficiency.

## 🛠️ Manual Commands

```bash
# Navigate to project
cd "/Users/yiding/Dropbox/My Mac (Yis-MacBook-Pro.local)/Documents/earnings"

# Run analysis on latest file
python3 analyze_incremental_margins.py

# Run on specific file
python3 analyze_incremental_margins.py --input earnings_filtered_20260120_AM.json

# Check system status
launchctl list | grep earnings

# View recent logs
tail -50 margin_analyzer.log
tail -50 earnings_log.txt
```

## 📈 Understanding the Metrics

### Incremental Operating Margin
```
(Current Quarter Op Income - Last Year Op Income) 
÷ 
(Current Quarter Revenue - Last Year Revenue)
```

**What it means:**
- >100%: Exceptional leverage (fixed costs being absorbed)
- 50-100%: Very efficient growth
- 20-50%: Healthy growth
- 0-20%: Low efficiency growth
- <0%: Unprofitable growth

### Is Margin Expanding?
- Compares incremental margin to current operating margin
- `true` = Company is becoming MORE efficient
- `false` = Company is becoming LESS efficient

## 🎯 Your Tracking List

Current tracked tickers (edit `tracking_list.txt` to modify):
- AAPL, TSLA, NVDA, GOOGL, MSFT
- AMZN, META, NFLX, JPM, C
- WFC, BLK, ASML, BAC, MS

## 🔧 Troubleshooting

**No incremental_margins file created?**
- Check if filtered file has companies
- View logs: `tail margin_analyzer.log`

**Data unavailable for a company?**
- Normal for private companies or recent IPOs
- Yahoo Finance may not have data yet

**Script not running automatically?**
- Check: `launchctl list | grep earnings`
- Reload: `launchctl unload ~/Library/LaunchAgents/com.earnings.scraper.plist && launchctl load ~/Library/LaunchAgents/com.earnings.scraper.plist`

## 📅 Schedule

**Monday-Friday:**
- 9:00 AM ET (10:00 PM JST) - Morning analysis
- 9:00 PM ET (10:00 AM JST next day) - Evening analysis

**Weekends:**
- No runs scheduled (markets closed)

## 🎉 You're All Set!

The system is fully automated. Just check the `incremental_margins_*.json` files each day to see your analysis results.

For detailed documentation, see `INCREMENTAL_MARGIN_ANALYSIS.md`
