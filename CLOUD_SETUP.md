# Cloud Scraper Setup

The daily earnings scrape also runs in **Anthropic's cloud** via Claude Code scheduled
cloud agents ("routines"), in parallel with the local launchd job on the Mac. The local
setup is untouched — the cloud runs are a redundant, always-on copy whose output is
committed to this GitHub repo (`dydy0539/earnings`).

## What runs in the cloud

`scrape_earnings_api.py` — a browser-free port of `scrape_earnings_selenium_final.py`.
It calls the site's own JSON endpoint (`https://www.earningswhispers.com/api/caldata/{YYYYMMDD}`)
instead of driving Chrome, then applies the same tracking-list / revenue-growth filter
and writes the same files:

- `earnings_calendar_final_{YYYYMMDD}_{AM|BM}.json`
- `earnings_filtered_{YYYYMMDD}_{AM|BM}.json`
- `earnings_report_{YYYYMMDD}_{AM|BM}.html` — one combined human-readable report
  per job, mirroring the fields of the two JSONs (filtered table + full calendar)

Naming stays compatible with the historical files: `AM` = the after-market-close scrape
(evening ET), `BM` = the before-open scrape (morning ET). The date is always the current
US/Eastern date; the API only returns reliable rows for the current date (past dates roll
companies forward to their next quarter).

## Routines

Two routines, managed at <https://claude.ai/code/routines> (cron is UTC):

| Routine | Cron (UTC) | Meaning |
| --- | --- | --- |
| `earnings-scraper-afterclose` | `0 1 * * 2-6` | Mon–Fri ~21:00 ET, after market close |
| `earnings-scraper-beforeopen` | `0 13 * * 1-5` | Mon–Fri ~9:00 ET, before the open |

Each routine clones this repo, runs `python3 scrape_earnings_api.py`, and commits +
pushes the two output JSONs to `main`. If the script fails because the site changed,
the agent is instructed to diagnose and minimally fix `scrape_earnings_api.py`, then
commit the fix alongside the data.

## Local vs cloud

- The Mac's launchd job (`com.earnings.scraper.plist`) keeps running the Selenium
  scraper as before and writes into the Dropbox folder.
- The cloud routines write the same filenames into GitHub commits. If you later
  `git pull` in the Dropbox folder, same-named files may conflict with locally
  produced ones; the data should be near-identical — resolve however you like.
- `analyze_incremental_margins.py` remains a manual step and reads the newest
  `earnings_filtered_*.json` wherever you run it.

## Testing by hand

```bash
python3 scrape_earnings_api.py                     # session/date from current ET time
python3 scrape_earnings_api.py --session bmo       # force before-open session, today ET
```
