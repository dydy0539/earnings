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

`com.earnings.api.scraper.plist`, installed at `~/Library/LaunchAgents/`, targets
**19:00 and 08:00 US/Eastern, Mon–Fri ET** (plus once at load/boot to catch missed
runs). Because the Mac clock is SGT (no DST) while ET shifts, each target has two
adjacent local slots and the later run overwrites with fresher data:

- After-close (19:00 ET Mon–Fri): 07:00 + 08:00 SGT Tue–Sat → suffix `AM`
- Before-open (08:00 ET Mon–Fri): 20:00 + 21:00 SGT Mon–Fri → suffix `BM`

The `earnings_report_*.html` is the final output per session; the two JSONs are
intermediary and freely overwritten. Logs: `earnings_api_log.txt` /
`earnings_api_error.txt` (gitignored).

```bash
# manage it
launchctl unload ~/Library/LaunchAgents/com.earnings.api.scraper.plist
launchctl load   ~/Library/LaunchAgents/com.earnings.api.scraper.plist
tail -f earnings_api_log.txt
```

The older Selenium job (`com.earnings.scraper.plist`, Mon–Fri 09:00/21:00) is still
installed and untouched.

## Cloud schedule (GitHub Actions)

Weekday runs happen on GitHub-hosted runners and push the HTML report back to the
branch the workflow ran from (normally `main`). The laptop does not need to be on.

| Workflow | ET target | UTC cron | Session |
| --- | --- | --- | --- |
| `.github/workflows/earnings-before-open.yml` | 08:00 Mon–Fri | `0 12 * * 1-5` and `0 13 * * 1-5` | `bmo` → suffix `BM` |
| `.github/workflows/earnings-after-close.yml` | 19:00 Mon–Fri | `0 23 * * 1-5` and `0 0 * * 2-6` | `amc` → suffix `AM` |

Each target has two UTC slots so the same wall-clock time still lands in the right
session when US daylight saving time changes. The later run overwrites that session's
files. Schedules run only after these workflow files are on `main`. Either workflow
can also be started by hand from the Actions tab (`workflow_dispatch`).

The runner commits `earnings_report_*.html` plus the calendar and filtered JSON, as
`github-actions[bot]`.

## Cloud routines (disabled)

Two Claude Code cloud routines were set up to run this in Anthropic's cloud and commit
results to GitHub, but earningswhispers.com returns **403 for datacenter IPs**, so they
are disabled. Kept for reference at <https://claude.ai/code/routines>:

| Routine | Cron (UTC) | Status |
| --- | --- | --- |
| `earnings-scraper-afterclose` | `0 1 * * 2-6` | disabled |
| `earnings-scraper-beforeopen` | `0 13 * * 1-5` | disabled |

## Testing by hand

```bash
python3 scrape_earnings_api.py                     # session/date from current ET time
python3 scrape_earnings_api.py --session bmo       # force before-open session, today ET
```
