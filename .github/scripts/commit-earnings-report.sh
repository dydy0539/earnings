#!/usr/bin/env bash
# Commit the HTML report and its JSON companions, then push to the branch
# that triggered this run. Used by the scheduled GitHub Actions workflows.
#
# Scheduled jobs set ENFORCE_SCHEDULE_WINDOW=true. The scrape then runs only
# inside the America/New_York window for that session, on a weekday, and only
# when that ET date+session does not already have a report scraped at or after
# the window open. workflow_dispatch and local runs leave the variable unset
# and scrape immediately.
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

if is_true "${ENFORCE_SCHEDULE_WINDOW:-}" || is_true "${SCHEDULE_WINDOW_DRY_RUN:-}"; then
  set +e
  decision_output="$(
    python3 - "$session" "$repo" <<'PY'
import json
import os
import re
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SHANGHAI = ZoneInfo("Asia/Shanghai")
# Inclusive open, exclusive close. Wall clock in America/New_York, so the
# same hours apply in EDT and EST. GitHub's off-minute retries sit inside
# these windows; a start outside them is skipped.
WINDOWS = {
    "bmo": (time(8, 0), time(11, 0), "BM"),
    "amc": (time(19, 0), time(22, 0), "AM"),
}


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

    decision = "run"
    reason = "inside window and no fresh report"
    fresh_source = ""
    fresh_at = ""
    if now.weekday() >= 5:
        decision = "skip"
        reason = f"weekend in America/New_York ({now:%A})"
    elif wall < open_t:
        decision = "skip"
        reason = f"before window open {open_t:%H:%M} ET"
    elif wall >= close_t:
        decision = "skip"
        reason = f"at or after window close {close_t:%H:%M} ET"
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
    print(f"window=[{open_t:%H:%M}, {close_t:%H:%M}) America/New_York")
    print(f"window_open={window_open.isoformat()}")
    print(f"now_et={now.strftime('%Y-%m-%d %H:%M:%S %Z')} ({now.isoformat()})")
    print(f"now_cn={china.strftime('%Y-%m-%d %H:%M:%S %Z')} ({china.isoformat()})")
    print(f"weekday={now.strftime('%A')} ({now.weekday()})")
    if fresh_at:
        print(f"fresh_scraped_at={fresh_at}")
        print(f"fresh_source={fresh_source}")
    print(f"reason={reason}")
    return 0 if decision == "run" else 10


sys.exit(main())
PY
  )"
  decision_status=$?
  set -e
  printf '%s\n' "$decision_output"
  if [[ "$decision_status" -eq 10 ]]; then
    echo "Skipping scrape."
    exit 0
  fi
  if [[ "$decision_status" -ne 0 ]]; then
    echo "Schedule window check failed (status ${decision_status})." >&2
    exit "$decision_status"
  fi
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

git pull --rebase origin "$GITHUB_REF_NAME"
git push origin "HEAD:${GITHUB_REF_NAME}"
