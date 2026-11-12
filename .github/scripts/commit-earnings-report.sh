#!/usr/bin/env bash
# Commit the HTML report and its JSON companions, then push to the branch
# that triggered this run. Used by the scheduled GitHub Actions workflows.
#
# Scheduled jobs set ENFORCE_SCHEDULE_WINDOW=true. The scrape then runs only
# inside the America/New_York window for that session, on a weekday, and only
# when that ET date+session does not already have a report scraped at or after
# the window open. A start up to 5 hours before the open sleeps until it.
# workflow_dispatch and local runs leave the variable unset and scrape
# immediately.
set -euo pipefail

session="${1:?usage: commit-earnings-report.sh bmo|amc}"
case "$session" in
  bmo|amc) ;;
  *)
    echo "usage: commit-earnings-report.sh bmo|amc" >&2
    exit 2
    ;;
esac

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
repo="${SCHEDULE_WINDOW_REPO:-$repo_root}"

is_true() {
  case "${1:-}" in
    true|TRUE|1|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

decide() {
  python3 - "$session" "$repo" <<'PY'
import json
import os
import re
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SHANGHAI = ZoneInfo("Asia/Shanghai")
# Wall clock in America/New_York, so the same hours apply in EDT and EST.
# GitHub delivers schedule events hours late, so a start before the open
# waits for it and a late start still scrapes until the cutoff. The amc
# cutoff is the end of the ET day because the scraper uses the current ET
# date; bmo stops at the 16:00 ET close, where the after-close session begins.
WINDOWS = {
    "bmo": (time(8, 0), time(16, 0), "BM"),
    "amc": (time(19, 0), None, "AM"),
}
# GitHub-hosted jobs are killed after 6 hours.
MAX_WAIT_SECONDS = 5 * 3600


def parse_scraped_at(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def html_meta(text, key):
    match = re.search(
        rf'<span class="k">{re.escape(key)}</span>\s*<span class="v">([^<]*)</span>',
        text,
    )
    return match.group(1).strip() if match else None


def load_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def collect_scraped_at(repo, date_str, session, suffix):
    found = []
    calendar_path = os.path.join(repo, f"earnings_calendar_final_{date_str}_{suffix}.json")
    filtered_path = os.path.join(repo, f"earnings_filtered_{date_str}_{suffix}.json")
    report_path = os.path.join(repo, f"earnings_report_{date_str}_{suffix}.html")

    calendar = load_json(calendar_path)
    if calendar and str(calendar.get("date", "")) == date_str and calendar.get("session") == session:
        parsed = parse_scraped_at(calendar.get("scraped_at"))
        if parsed is not None:
            found.append((parsed, calendar_path))

    filtered = load_json(filtered_path)
    if filtered and str(filtered.get("date", "")) == date_str:
        parsed = parse_scraped_at(filtered.get("scraped_at"))
        if parsed is not None:
            found.append((parsed, filtered_path))

    if os.path.isfile(report_path):
        try:
            text = open(report_path, encoding="utf-8").read()
        except OSError:
            text = ""
        date_meta = html_meta(text, "date")
        session_meta = html_meta(text, "session") or ""
        session_ok = session_meta == session or session_meta.startswith(session + " ") or session_meta.startswith(session + "(")
        if date_meta == date_str and session_ok:
            parsed = parse_scraped_at(html_meta(text, "scraped_at"))
            if parsed is not None:
                found.append((parsed, report_path))
    return found


def main():
    session = sys.argv[1]
    repo = sys.argv[2]
    if session not in WINDOWS:
        print(f"decision=error\nreason=unknown session {session}", file=sys.stderr)
        return 2

    override = os.environ.get("SCHEDULE_WINDOW_NOW", "").strip()
    dry = os.environ.get("SCHEDULE_WINDOW_DRY_RUN", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    if dry and override:
        now = datetime.fromisoformat(override)
        if now.tzinfo is None:
            now = now.replace(tzinfo=ET)
        now = now.astimezone(ET)
    else:
        now = datetime.now(ET)

    open_t, close_t, suffix = WINDOWS[session]
    date_str = now.strftime("%Y%m%d")
    window_open = datetime.combine(now.date(), open_t, tzinfo=ET)
    wall = now.time().replace(tzinfo=None)
    china = now.astimezone(SHANGHAI)

    close_label = f"{close_t:%H:%M}" if close_t else "24:00"
    decision = "run"
    reason = "inside window and no fresh report"
    fresh_source = ""
    fresh_at = ""
    wait_seconds = 0
    if now.weekday() >= 5:
        decision = "skip"
        reason = f"weekend in America/New_York ({now:%A})"
    elif wall < open_t:
        wait_seconds = int((window_open - now).total_seconds()) + 1
        if wait_seconds <= MAX_WAIT_SECONDS:
            decision = "wait"
            reason = f"before window open {open_t:%H:%M} ET; waiting {wait_seconds}s"
        else:
            decision = "skip"
            reason = f"more than {MAX_WAIT_SECONDS // 3600}h before window open {open_t:%H:%M} ET"
    elif close_t is not None and wall >= close_t:
        decision = "skip"
        reason = f"at or after cutoff {close_label} ET"
    else:
        found = collect_scraped_at(repo, date_str, session, suffix)
        fresh = [(stamp, path) for stamp, path in found if stamp >= window_open]
        if fresh:
            stamp, path = max(fresh)
            decision = "skip"
            reason = "fresh report already scraped at or after window open"
            fresh_source = path
            fresh_at = stamp.isoformat()

    print(f"decision={decision}")
    print(f"session={session}")
    print(f"date={date_str}")
    print(f"suffix={suffix}")
    print(f"window=[{open_t:%H:%M}, {close_label}) America/New_York")
    print(f"window_open={window_open.isoformat()}")
    print(f"now_et={now.strftime('%Y-%m-%d %H:%M:%S %Z')} ({now.isoformat()})")
    print(f"now_cn={china.strftime('%Y-%m-%d %H:%M:%S %Z')} ({china.isoformat()})")
    print(f"weekday={now.strftime('%A')} ({now.weekday()})")
    if fresh_at:
        print(f"fresh_scraped_at={fresh_at}")
        print(f"fresh_source={fresh_source}")
    if decision == "wait":
        print(f"wait_seconds={wait_seconds}")
    print(f"reason={reason}")
    return {"run": 0, "skip": 10, "wait": 11}[decision]


sys.exit(main())
PY
}

if is_true "${ENFORCE_SCHEDULE_WINDOW:-}" || is_true "${SCHEDULE_WINDOW_DRY_RUN:-}"; then
  while true; do
    set +e
    decision_output="$(decide)"
    decision_status=$?
    set -e
    printf '%s\n' "$decision_output"
    case "$decision_status" in
      0) break ;;
      10)
        echo "Skipping scrape."
        exit 0
        ;;
      11)
        if is_true "${SCHEDULE_WINDOW_DRY_RUN:-}"; then
          echo "Dry run: not waiting."
          exit 0
        fi
        wait_seconds="$(sed -n 's/^wait_seconds=//p' <<<"$decision_output")"
        echo "Waiting ${wait_seconds}s for the window to open."
        sleep "$wait_seconds"
        # Another run may have committed a fresh report while this one slept.
        if [[ -n "${GITHUB_REF_NAME:-}" ]]; then
          git -C "$repo" pull --ff-only origin "$GITHUB_REF_NAME"
        fi
        ;;
      *)
        echo "Schedule window check failed (status ${decision_status})." >&2
        exit "$decision_status"
        ;;
    esac
  done
  if is_true "${SCHEDULE_WINDOW_DRY_RUN:-}"; then
    echo "Dry run: not scraping."
    exit 0
  fi
fi

python3 scrape_earnings_api.py --session "$session"

if [[ -z "${GITHUB_REF_NAME:-}" ]]; then
  echo "Not in GitHub Actions; report files were written and left uncommitted."
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git add earnings_report_*.html earnings_calendar_final_*.json earnings_filtered_*.json
if git diff --cached --quiet; then
  echo "No report changes to commit."
  exit 0
fi

report="$(git diff --cached --name-only -- 'earnings_report_*.html' | head -1)"
stamp="$(TZ=America/New_York date +%Y-%m-%d)"
git commit -m "Update earnings report ${report:-for ${stamp}} (${session})"

for attempt in 1 2 3 4; do
  git pull --rebase origin "$GITHUB_REF_NAME"
  if git push origin "HEAD:${GITHUB_REF_NAME}"; then
    exit 0
  fi
  sleep $((attempt * 5))
done
echo "Push failed after ${attempt} attempts." >&2
exit 1
