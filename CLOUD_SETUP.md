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
Schedules run only from the default branch `main`.

GitHub Actions schedules are best-effort. They cannot hit an exact minute. Crons
that fire at minute 0 (the top of every hour) are especially late, and GitHub
sometimes drops the event entirely. The workflows therefore retry many times
**off minute 0**, and the commit script skips a retry when it is outside the ET
window or when that ET date and session already has a fresh report.

| Workflow | ET window (Mon–Fri) | UTC cron (off minute 0) | Session |
| --- | --- | --- | --- |
| `.github/workflows/earnings-before-open.yml` | [08:00, 11:00) | `7,17,27,37,47 12-14 * * 1-5` | `bmo` → suffix `BM` |
| `.github/workflows/earnings-after-close.yml` | [19:00, 22:00) | `7,17,27,37,47 23 * * 1-5` and `7,17,27,37,47 0-1 * * 2-6` | `amc` → suffix `AM` |

America/New_York is EDT (UTC-4) through November 1, 2026, then EST (UTC-5).
China (Asia/Shanghai, UTC+8) does not observe daylight saving time. The windows
are wall-clock US/Eastern, so the open stays 08:00 and 19:00 ET after the change.

Before-open cron `7,17,27,37,47` at 12:00–14:00 UTC:

- EDT: 08:07–10:47 ET (20:07–22:47 China time), inside the window
- EST: 07:07–09:47 ET (20:07–22:47 China time). Starts before 08:00 ET are skipped,
  so the same cron still covers 08:07–09:47 EST (21:07–22:47 China time)

After-close:

- `7,17,27,37,47` at 23:00 UTC Mon–Fri is 19:07–19:47 EDT (07:07–07:47 China time
  the next calendar day) and 18:07–18:47 EST (07:07–07:47 China time). EST slots
  before 19:00 ET are skipped.
- `7,17,27,37,47` at 00:00–01:00 UTC Tue–Sat is 20:07–21:47 EDT the previous
  weekday (08:07–09:47 China time) or 19:07–20:47 EST (08:07–09:47 China time).

Scheduled jobs set `ENFORCE_SCHEDULE_WINDOW=true`. The script makes one decision
in `America/New_York`: skip Saturday and Sunday, skip outside the window above,
and skip when `earnings_calendar_final_{YYYYMMDD}_{AM|BM}.json`,
`earnings_filtered_{YYYYMMDD}_{AM|BM}.json`, or
`earnings_report_{YYYYMMDD}_{AM|BM}.html` for that ET date and session already
has `scraped_at` at or after the window open (08:00 ET or 19:00 ET). A manual
`workflow_dispatch` or a local run does not set the variable, so those still
scrape at any time. The after-close `analyze` job is unchanged.

These retries only help when GitHub is minutes late, or drops some of the
slots. If every schedule event is delayed by hours, a run can still land after
the window closes and will be skipped. GitHub still cannot promise 08:00 or
19:00 ET exactly.

The runner commits `earnings_report_*.html` plus the calendar and filtered JSON, as
`github-actions[bot]`. Either workflow can also be started by hand from the
Actions tab (`workflow_dispatch`).

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
