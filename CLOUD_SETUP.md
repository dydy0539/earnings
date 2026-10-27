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

GitHub Actions schedules are best-effort. For this repo, every schedule event
in October 2026 arrived **2–4 hours late**, and some never arrived (for example,
`0 23` ran at 01:07 UTC, `0 0` at 03:29 UTC, and the 14:47 UTC before-open slot
at 18:47 UTC). GitHub also drops a delayed event if its cron line was removed
from the workflow file before delivery. So the workflows do not rely on punctual
delivery:

- Crons start up to 5 hours **before** the window opens. A run that starts
  early sleeps until the open, pulls the branch, re-checks, then scrapes.
- Crons keep firing until a late cutoff. A run that starts late still scrapes
  if that ET date and session has no fresh report yet.

| Workflow | ET open → cutoff (Mon–Fri) | UTC cron | Session |
| --- | --- | --- | --- |
| `.github/workflows/earnings-before-open.yml` | 08:00 → 16:00 | `7,37 8-20 * * 1-5` | `bmo` → suffix `BM` |
| `.github/workflows/earnings-after-close.yml` | 19:00 → 24:00 | `7,37 19-23 * * 1-5` and `7,37 0-4 * * 2-6` | `amc` → suffix `AM` |

The after-close cutoff is midnight ET because the scraper uses the current ET
date. The before-open cutoff is the 16:00 ET close, where the after-close
session begins. When delivery is on time, the first early run sleeps and
scrapes right at 08:00 or 19:00 ET.

America/New_York is EDT (UTC-4) through November 1, 2026, then EST (UTC-5).
China (Asia/Shanghai, UTC+8) does not observe daylight saving time. The windows
are wall-clock US/Eastern, so the open stays 08:00 and 19:00 ET after the change.
In China time, the open is 20:00 (EDT) or 21:00 (EST) for before-open, and
07:00 (EDT) or 08:00 (EST) the next morning for after-close.

Scheduled jobs set `ENFORCE_SCHEDULE_WINDOW=true`. The script decides in
`America/New_York`: skip Saturday and Sunday; wait if the open is at most 5 hours
away; skip if it is further away or past the cutoff; and skip when
`earnings_calendar_final_{YYYYMMDD}_{AM|BM}.json`,
`earnings_filtered_{YYYYMMDD}_{AM|BM}.json`, or
`earnings_report_{YYYYMMDD}_{AM|BM}.html` for that ET date and session already
has `scraped_at` at or after the window open (08:00 ET or 19:00 ET). A manual
`workflow_dispatch` or a local run does not set the variable, so those still
scrape at any time. The after-close `analyze` job is unchanged.

Each workflow serializes its scheduled runs (`concurrency` per workflow and
event), so only one run sleeps at a time. Further schedule events that arrive
meanwhile show as cancelled in the Actions tab; that is expected. Manual runs
use their own group and never wait behind a sleeping run.

To check a decision without scraping:

```bash
SCHEDULE_WINDOW_DRY_RUN=1 SCHEDULE_WINDOW_NOW=2026-10-23T01:07:00+00:00 \
  bash .github/scripts/commit-earnings-report.sh amc
```

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
