#!/usr/bin/env bash
# Commit the HTML report and its JSON companions, then push to the branch
# that triggered this run. Used by the scheduled GitHub Actions workflows.
set -euo pipefail

session="${1:?usage: commit-earnings-report.sh bmo|amc}"

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
