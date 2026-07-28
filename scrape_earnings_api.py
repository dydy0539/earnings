#!/usr/bin/env python3
"""
EarningsWhispers calendar scraper using the site's JSON API.

Cloud-portable replacement for scrape_earnings_selenium_final.py: no browser,
no ChromeDriver, only `requests`. Fetches https://www.earningswhispers.com/api/caldata/{YYYYMMDD}
(the same endpoint the calendar page loads via getcalctrls()) and writes the
same output files as the Selenium scraper:

    earnings_calendar_final_{YYYYMMDD}_{AM|BM}.json   raw calendar for the session
    earnings_filtered_{YYYYMMDD}_{AM|BM}.json         tracking-list / revenue-growth filtered

Session and naming (kept compatible with the historical files):
    after-close run  (ET hour >= 16): releaseTime == 3, suffix "AM"
    before-open run  (ET hour < 16):  releaseTime == 1, suffix "BM"
The date is always "today" in US/Eastern. Files are written next to this
script regardless of the current working directory.

Usage:
    python3 scrape_earnings_api.py                     # session/date from current ET time
    python3 scrape_earnings_api.py --date 20260727 --session amc
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://www.earningswhispers.com/api/caldata/{date}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.earningswhispers.com/calendar",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# releaseTime values used by the API
RELEASE_BEFORE_OPEN = 1
RELEASE_AFTER_CLOSE = 3

SESSIONS = {
    # session: (releaseTime filter, filename suffix, human label)
    "amc": (RELEASE_AFTER_CLOSE, "AM", "After Market Close"),
    "bmo": (RELEASE_BEFORE_OPEN, "BM", "Before Market Open"),
}

FILTER_CRITERIA_RULES = [
    ">10M revenue and >50% growth",
    ">100M revenue and >30% growth",
    ">500M revenue and >25% growth",
    ">1000M revenue and >20% growth",
    ">5000M revenue and >15% growth",
]


def fetch_calendar(date_str, retries=4, backoff=10):
    """Fetch the raw calendar rows for a date, with retries."""
    url = API_URL.format(date=date_str)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200 and resp.text.strip():
                return resp.json()
            if resp.status_code == 204:
                return []
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except (requests.RequestException, ValueError) as e:
            last_error = str(e)
        print(f"Attempt {attempt}/{retries} failed: {last_error}")
        if attempt < retries:
            time.sleep(backoff * attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def compute_financials(row):
    """Revenue in $M and YoY growth % from API fields.

    Prefers reported revenue (`revenue`, in millions) over the estimate
    (`q1RevEst`, in dollars) — same preference as the Selenium scraper's
    "Reported Revenue" pattern. Growth is vs `qSales` (year-ago quarter, $M).
    NOTE: rows are only reliable when querying the current ET date; past-date
    queries roll companies forward to their next quarter with null estimates.
    """
    revenue_millions = None
    reported = False

    if row.get("revenue"):
        revenue_millions = round(row["revenue"], 2)
        reported = True
    elif row.get("q1RevEst"):
        revenue_millions = round(row["q1RevEst"] / 1e6, 2)

    growth_rate = None
    q_sales = row.get("qSales")
    if revenue_millions and q_sales:
        growth_rate = round((revenue_millions - q_sales) / abs(q_sales) * 100, 1)

    return revenue_millions, growth_rate, reported


def build_company(row, session_label):
    revenue_millions, growth_rate, reported = compute_financials(row)
    company = {
        "symbol": (row.get("ticker") or "").upper(),
        "company_name": row.get("company") or "",
        "time": session_label,
        "source": "api/caldata",
        "quarter": row.get("qDate"),
        "eps_estimate": row.get("q1EstEPS"),
        "revenue_estimate_millions": revenue_millions,
        "prior_year_sales_millions": row.get("qSales"),
        # fields present once results are out
        "reported_eps": row.get("eps"),
        "reported_revenue_millions": row.get("revenue"),
        "eps_surprise_pct": row.get("surprise"),
    }
    if revenue_millions is not None:
        company["revenue_millions"] = revenue_millions
        label = "reported" if reported else "est"
        company["revenue_raw"] = f"${revenue_millions:,.2f} Mil ({label})"
    if growth_rate is not None:
        company["growth_rate"] = growth_rate
        company["growth_raw"] = f"{growth_rate}%"
    return company


def load_tracking_list():
    tracking_list = set()
    tracking_file = os.path.join(SCRIPT_DIR, "tracking_list.txt")
    if os.path.exists(tracking_file):
        with open(tracking_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().upper()
                if line and not line.startswith("#"):
                    tracking_list.add(line)
    return tracking_list


def meets_criteria(revenue, growth):
    """Same tiers as scrape_earnings_selenium_final.EarningsSeleniumScraper.meets_criteria."""
    criteria = [(10, 50), (100, 30), (500, 25), (1000, 20), (5000, 15)]
    return any(revenue > r and growth > g for r, g in criteria)


def format_filtered_company(company, reason):
    return {
        "ticker": company.get("symbol", ""),
        "name": company.get("company_name", ""),
        "revenue_millions": company.get("revenue_millions", 0),
        "revenue_raw": company.get("revenue_raw", ""),
        "growth_rate": company.get("growth_rate", 0),
        "growth_raw": company.get("growth_raw", ""),
        "source": company.get("source", ""),
        "filter_reason": reason,
    }


def filter_companies(companies, tracking_list):
    filtered = []
    for company in companies:
        symbol = company.get("symbol", "")
        revenue = company.get("revenue_millions", 0) or 0
        growth = company.get("growth_rate", 0) or 0
        if symbol in tracking_list:
            filtered.append(format_filtered_company(company, "tracking_list"))
        elif meets_criteria(revenue, growth):
            filtered.append(format_filtered_company(company, "revenue_growth_criteria"))
    return filtered


def save_to_file(data, filename):
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {filename}")
    return path


def print_summary(filtered_companies, session_label):
    if not filtered_companies:
        print("No companies passed the filter.")
        return
    print(f"\n{len(filtered_companies)} filtered companies ({session_label}):")
    for c in filtered_companies:
        print(
            f"  {c['ticker']:<6} {c['name'][:40]:<40} "
            f"rev ${c['revenue_millions']:,.0f}M  growth {c['growth_rate']}%  [{c['filter_reason']}]"
        )
    print("\nSeekingAlpha income statement URLs:")
    for c in filtered_companies:
        print(f"  https://seekingalpha.com/symbol/{c['ticker']}/income-statement")


def main():
    parser = argparse.ArgumentParser(description="Scrape EarningsWhispers calendar via JSON API")
    parser.add_argument("--date", help="Date as YYYYMMDD (default: today in US/Eastern)")
    parser.add_argument("--session", choices=["amc", "bmo"],
                        help="amc = after close (suffix AM), bmo = before open (suffix BM); "
                             "default derived from current ET time")
    args = parser.parse_args()

    now_et = datetime.now(ZoneInfo("US/Eastern"))
    date_str = args.date or now_et.strftime("%Y%m%d")
    session = args.session or ("amc" if now_et.hour >= 16 else "bmo")
    release_time, suffix, session_label = SESSIONS[session]

    print(f"Scraping {date_str} session={session} ({session_label}), suffix={suffix}")

    rows = fetch_calendar(date_str)
    print(f"API returned {len(rows)} total companies for {date_str}")

    session_rows = [r for r in rows if r.get("releaseTime") == release_time]
    companies = [build_company(r, session_label) for r in session_rows]

    calendar_data = {
        "date": date_str,
        "scraped_at": datetime.now(ZoneInfo("US/Eastern")).isoformat(),
        "session": session,
        "companies": companies,
        "status": "success" if companies else "no_data_found",
    }
    if not companies:
        calendar_data["message"] = f"No {session_label} earnings found for {date_str}."
    save_to_file(calendar_data, f"earnings_calendar_final_{date_str}_{suffix}.json")

    tracking_list = load_tracking_list()
    filtered_companies = filter_companies(companies, tracking_list)
    filtered_data = {
        "date": date_str,
        "scraped_at": datetime.now(ZoneInfo("US/Eastern")).isoformat(),
        "filter_criteria": {
            "revenue_growth_rules": FILTER_CRITERIA_RULES,
            "tracking_list": sorted(tracking_list),
            "tracking_list_count": len(tracking_list),
        },
        "companies": filtered_companies,
        "total_filtered": len(filtered_companies),
        "total_original": len(companies),
    }
    save_to_file(filtered_data, f"earnings_filtered_{date_str}_{suffix}.json")

    print_summary(filtered_companies, session_label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
