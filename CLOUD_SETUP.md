# Scraper Setup (API-based)

`scrape_earnings_api.py` is a browser-free port of `scrape_earnings_selenium_final.py`.
It calls the site's own JSON endpoint (`https://www.earningswhispers.com/api/caldata/{YYYYMMDD}`)
instead of driving Chrome, applies the same tracking-list / revenue-growth filter, and
writes three files per job into the repo root:

- `earnings_calendar_final_{YYYYMMDD}_{AM|BM}.json`
- `earnings_filtered_{YYYYMMDD}_{AM|BM}.json`
- `earnings_report_{YYYYMMDD}_{AM|BM}.html` — one combined human-readable report
  per job, mirroring the fields of the two JSONs (filtered table + full calendar)

Naming stays compatible with the historical files: `AM` = the after-market-close scrape
(evening ET), `BM` = the before-open scrape (morning ET). The date is always the current
US/Eastern date; the API only returns reliable rows for the current date (past dates roll
companies forward to their next quarter).

## Local schedule (active)

`com.earnings.api.scraper.plist`, installed at `~/Library/LaunchAgents/`, runs the API
scraper **Mon–Fri at 09:00 and 19:00 local time** (plus once at load/boot to catch missed
runs). Logs: `earnings_api_log.txt` / `earnings_api_error.txt` (gitignored).

- 09:00 SGT ≈ 20:00–21:00 ET previous evening → after-close session, suffix `AM`
- 19:00 SGT ≈ 06:00–07:00 ET → before-open session, suffix `BM`

```bash
# manage it
launchctl unload ~/Library/LaunchAgents/com.earnings.api.scraper.plist
launchctl load   ~/Library/LaunchAgents/com.earnings.api.scraper.plist
tail -f earnings_api_log.txt
```

The older Selenium job (`com.earnings.scraper.plist`, Mon–Fri 09:00/21:00) is still
installed and untouched.

## Cloud routines (disabled)

Two Claude Code cloud routines were set up to run this in Anthropic's cloud and commit
results to GitHub, but earningswhispers.com returns **403 for datacenter IPs**, so they
are disabled (they cannot scrape from cloud hosts). Kept for reference at
<https://claude.ai/code/routines>:

| Routine | Cron (UTC) | Status |
| --- | --- | --- |
| `earnings-scraper-afterclose` | `0 1 * * 2-6` | disabled |
| `earnings-scraper-beforeopen` | `0 13 * * 1-5` | disabled |

## Testing by hand

```bash
python3 scrape_earnings_api.py                     # session/date from current ET time
python3 scrape_earnings_api.py --session bmo       # force before-open session, today ET
```
