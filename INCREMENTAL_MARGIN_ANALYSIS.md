# Incremental Operating Margin Analysis - Setup Complete

## Overview

Your earnings scraper now automatically performs incremental operating margin analysis on all filtered companies. This analysis helps identify companies with improving operational efficiency.

## What Gets Analyzed

For each company in the filtered earnings file, the system:

1. **Identifies the latest fiscal quarter** with available data
2. **Fetches financial data** from the same quarter last year (Q-4)
3. **Calculates incremental operating margin**:
   ```
   Incremental Operating Margin = (Op Income Q - Op Income Q-4) / (Revenue Q - Revenue Q-4)
   ```
4. **Determines if margins are expanding**:
   - Compares incremental margin vs. current operating margin
   - ✓ Yes = Incremental margin > Current margin (improving efficiency)
   - ✗ No = Incremental margin < Current margin (declining efficiency)

## Automated Workflow

### Daily Schedule (Monday-Friday)
- **9:00 AM Eastern**: Scraper runs → Creates filtered file → Analyzer runs automatically
- **9:00 PM Eastern**: Scraper runs → Creates filtered file → Analyzer runs automatically

### Process Flow
```
1. scrape_earnings_selenium_final.py runs (via launchd)
   ↓
2. Creates earnings_calendar_final_YYYYMMDD_XX.json
   ↓
3. Filters companies → earnings_filtered_YYYYMMDD_XX.json
   ↓
4. Automatically runs analyze_incremental_margins.py
   ↓
5. Creates incremental_margins_YYYYMMDD_XX.json
```

## Output Files

### Location
All files are saved in: `/Users/yiding/Dropbox/My Mac (Yis-MacBook-Pro.local)/Documents/earnings/`

### File Naming Convention
- `earnings_filtered_YYYYMMDD_AM.json` - Morning filtered results
- `earnings_filtered_YYYYMMDD_BM.json` - Evening filtered results
- `incremental_margins_YYYYMMDD_AM.json` - Morning margin analysis
- `incremental_margins_YYYYMMDD_BM.json` - Evening margin analysis

### Output Format

```json
{
  "source_file": "earnings_filtered_20260120_AM.json",
  "analyzed_at": "2026-01-25T15:53:11.116245",
  "total_companies": 2,
  "successful_analyses": 2,
  "companies": [
    {
      "company_name": "Netflix, Inc.",
      "ticker": "NFLX",
      "status": "success",
      "incremental_operating_margin": 20.1,
      "latest_operating_margin": 28.22,
      "latest_quarter_date": "2025-09-30",
      "prior_year_quarter_date": "2024-09-30",
      "is_margin_expanding": false,
      "revenue_growth_pct": 17.16,
      "operating_income_growth_pct": 11.64,
      "details": {
        "latest_quarter": {
          "revenue": 11510307000.0,
          "operating_income": 3248247000.0,
          "operating_margin_pct": 28.22
        },
        "prior_year_quarter": {
          "revenue": 9824703000.0,
          "operating_income": 2909477000.0,
          "operating_margin_pct": 29.61
        }
      }
    }
  ]
}
```

## Interpreting Results

### Key Metrics

1. **Incremental Operating Margin**
   - Shows efficiency of growth
   - High value (>50%) = Very efficient growth
   - Negative value = Unprofitable growth

2. **Latest Operating Margin**
   - Current profitability level
   - Compare to industry averages

3. **Is Margin Expanding**
   - `true` = Company is becoming more efficient
   - `false` = Company efficiency is declining despite growth

### Example Interpretation

**Netflix (NFLX)**
- Incremental Margin: 20.1%
- Latest Margin: 28.22%
- Expanding: No

**Analysis**: Netflix is growing (17.16% revenue growth) but with declining efficiency. For every new dollar of revenue, they're only generating $0.20 of operating income, which is below their current 28.22% margin. This suggests increasing costs or investments.

**Interactive Brokers (IBKR)**
- Incremental Margin: 133.66%
- Latest Margin: 87.24%
- Expanding: Yes

**Analysis**: IBKR shows exceptional operational leverage. For every new dollar of revenue, they're generating $1.34 of operating income (>100% due to fixed cost leverage). This is a strong positive signal.

## Manual Usage

If you want to run the analysis manually:

```bash
cd "/Users/yiding/Dropbox/My Mac (Yis-MacBook-Pro.local)/Documents/earnings"

# Analyze the latest filtered file
python3 analyze_incremental_margins.py

# Analyze a specific file
python3 analyze_incremental_margins.py --input earnings_filtered_20260120_AM.json

# Debug mode
python3 analyze_incremental_margins.py --input earnings_filtered_20260120_AM.json --debug
```

## Data Source

- **Financial data**: Yahoo Finance (via yfinance library)
- **Update frequency**: Real-time when script runs
- **Historical depth**: Typically 5-7 quarters available

## Troubleshooting

### No Data Available
If a company shows `status: "data_unavailable"`:
- Company may be private or recently IPO'd
- Yahoo Finance may not have complete data
- Check ticker symbol accuracy

### Calculation Failed
If a company shows `status: "calculation_failed"`:
- Insufficient historical data (need at least 2 quarters)
- Zero revenue growth (division by zero)
- Missing operating income data

### NaN Values
- Indicates missing or future quarter data
- Script automatically skips to next valid quarter

## System Requirements

### Python Packages
- `yfinance>=0.2.0` - Financial data fetching
- `pandas` - Data manipulation
- `numpy` - Numerical operations

All packages are already installed and configured.

## Monitoring

### Log Files
- `margin_analyzer.log` - Analysis execution logs
- `earnings_log.txt` - Scraper execution logs
- `earnings_error.txt` - Scraper error logs

### Check Service Status
```bash
# Check if scraper is scheduled
launchctl list | grep earnings

# View recent log entries
tail -50 earnings_log.txt
tail -50 margin_analyzer.log
```

## Next Steps

The system is now fully automated and will run twice daily on weekdays. You can:

1. **Monitor results** by checking the `incremental_margins_*.json` files
2. **Customize tracking list** by editing `tracking_list.txt`
3. **Adjust filters** in the scraper configuration
4. **Add more analysis** by extending `analyze_incremental_margins.py`

## Summary

✅ **Automated Analysis**: Runs automatically after each scrape
✅ **Comprehensive Data**: Fetches latest quarterly financials
✅ **Smart Calculations**: Handles missing data and edge cases
✅ **Detailed Output**: JSON format with full financial details
✅ **Error Handling**: Graceful failures with detailed logging

The system is production-ready and will provide daily incremental margin analysis for all your tracked and high-growth companies.
