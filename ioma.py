#!/usr/bin/env python3
"""
Add an IOMA column to the filtered-companies table in earnings_report_*.html.

IOMA = (current-quarter operating income or adjusted/normalized EBITDA
         − same quarter last year)
        / (current-quarter revenue − same quarter last year revenue)

Morning cron (09:30 UTC) reads earnings_report_{US_EASTERN_DATE}_AM.html.
Evening cron (22:30 UTC) reads earnings_report_{US_EASTERN_DATE}_BM.html.

The report date is always the current US/Eastern calendar date so a Japan or
Singapore local date cannot pick the wrong AM file. If that day's file is
missing and cannot be generated, write no_earnings_file_found.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional until job runs
    BeautifulSoup = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_FILENAME = "no_earnings_file_found"
EASTERN = ZoneInfo("America/New_York")

REVENUE_FIELDS = (
    "Total Revenue",
    "Revenue",
    "Total Revenues",
    "Net Sales",
    "Operating Revenue",
)
# Prefer adjusted/normalized EBITDA when the company publishes it.
INCOME_FIELD_GROUPS = (
    ("Normalized EBITDA", "Adjusted EBITDA", "EBITDA"),
    ("Operating Income", "Total Operating Income As Reported",
     "Operating Income Or Loss", "EBIT"),
)


def calculate_ioma(current_income, prior_income, current_revenue, prior_revenue):
    """Return (current − prior income) / (current − prior revenue), or None."""
    values = (current_income, prior_income, current_revenue, prior_revenue)
    if any(v is None for v in values):
        return None
    try:
        numerator = float(current_income) - float(prior_income)
        denominator = float(current_revenue) - float(prior_revenue)
    except (TypeError, ValueError):
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def format_ioma(value):
    """Render IOMA as a percentage string for the HTML table."""
    if value is None:
        return None
    return f"{value * 100:.2f}%"


def resolve_report_target(now=None):
    """Map a trigger time to (YYYYMMDD in US/Eastern, AM|BM suffix)."""
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    eastern = now.astimezone(EASTERN)
    utc = now.astimezone(timezone.utc)
    # Cron fires at 09:30 UTC (morning / AM file) and 22:30 UTC (evening / BM).
    suffix = "AM" if utc.hour < 16 else "BM"
    return eastern.strftime("%Y%m%d"), suffix


def report_filename(date_str, suffix):
    return f"earnings_report_{date_str}_{suffix}.html"


def _first_number(row, field_names):
    index_map = {str(name).strip().lower(): name for name in row.index}
    for field in field_names:
        key = index_map.get(field.lower())
        if key is None:
            continue
        value = row[key]
        try:
            import pandas as pd
            if value is None or pd.isna(value):
                continue
        except Exception:
            if value is None:
                continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _quarter_metric(row):
    revenue = _first_number(row, REVENUE_FIELDS)
    if revenue is None:
        return None
    for group in INCOME_FIELD_GROUPS:
        income = _first_number(row, group)
        if income is not None:
            return {
                "revenue": revenue,
                "income": income,
                "metric": group[0],
            }
    return None


def pick_comparable_quarters(quarterly_df):
    """
    Choose the latest quarter with usable figures and the year-ago quarter.

    Latest Yahoo rows are sometimes empty (just-announced periods). Skip those
    and match the prior year by calendar date (~365 days), not a fixed offset.
    The same income metric (EBITDA family, else operating income) is required
    for both quarters.
    """
    if quarterly_df is None or getattr(quarterly_df, "empty", True):
        return None

    df = quarterly_df.T.sort_index(ascending=False)
    quarters = []
    for stamp, row in df.iterrows():
        parsed = _quarter_metric(row)
        if parsed is None:
            continue
        quarters.append((stamp, parsed))
    if len(quarters) < 2:
        return None

    current_date, current = quarters[0]
    target = current_date - timedelta(days=365)
    prior = None
    prior_date = None
    best_delta = None
    for stamp, metrics in quarters[1:]:
        # Require the same metric family so EBITDA is not mixed with OI.
        if metrics["metric"] != current["metric"]:
            # Allow OI-vs-OI or EBITDA-vs-EBITDA after re-picking on the pair.
            continue
        delta = abs((stamp - target).days)
        if delta <= 70 and (best_delta is None or delta < best_delta):
            prior = metrics
            prior_date = stamp
            best_delta = delta

    if prior is None:
        # Fall back to the 4th older valid quarter when dates are irregular.
        if len(quarters) >= 5:
            prior_date, prior = quarters[4]
        else:
            return None
        if prior["metric"] != current["metric"]:
            # Recompute both quarters using a metric both actually have.
            shared = _shared_metric(df.loc[current_date], df.loc[prior_date])
            if shared is None:
                return None
            current, prior = shared

    return {
        "current": current,
        "prior": prior,
        "current_date": current_date,
        "prior_date": prior_date,
        "metric": current["metric"],
    }


def _shared_metric(current_row, prior_row):
    for group in INCOME_FIELD_GROUPS:
        current_income = _first_number(current_row, group)
        prior_income = _first_number(prior_row, group)
        current_rev = _first_number(current_row, REVENUE_FIELDS)
        prior_rev = _first_number(prior_row, REVENUE_FIELDS)
        if None not in (current_income, prior_income, current_rev, prior_rev):
            return (
                {"revenue": current_rev, "income": current_income, "metric": group[0]},
                {"revenue": prior_rev, "income": prior_income, "metric": group[0]},
            )
    return None


def fetch_ioma(ticker):
    """Pull quarterly statements from Yahoo Finance and compute IOMA."""
    if not ticker:
        return None
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        stock = yf.Ticker(ticker)
        pair = pick_comparable_quarters(stock.quarterly_financials)
    except Exception:
        return None
    if pair is None:
        return None
    value = calculate_ioma(
        pair["current"]["income"],
        pair["prior"]["income"],
        pair["current"]["revenue"],
        pair["prior"]["revenue"],
    )
    return {
        "ticker": ticker,
        "ioma": value,
        "metric": pair["metric"],
        "current_date": str(pair["current_date"].date())
        if hasattr(pair["current_date"], "date")
        else str(pair["current_date"]),
        "prior_date": str(pair["prior_date"].date())
        if hasattr(pair["prior_date"], "date")
        else str(pair["prior_date"]),
    }


def attach_ioma(companies, fetcher=None):
    """Add an IOMA display value onto each filtered-company dict."""
    fetch = fetcher or fetch_ioma
    for company in companies:
        ticker = company.get("ticker") or company.get("symbol") or ""
        try:
            result = fetch(ticker) if ticker else None
            value = result.get("ioma") if result else None
            company["IOMA"] = format_ioma(value)
        except Exception:
            company["IOMA"] = None
    return companies


def _ioma_cell_html(soup, label):
    td = soup.new_tag("td")
    if label:
        td["class"] = ["num"]
        td.string = label
    else:
        td["class"] = ["empty"]
        td.string = "\u2013"
    return td


def add_ioma_column_to_html(html_text, ioma_by_ticker):
    """Insert or refresh the IOMA column on the filtered-companies table."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required to edit the HTML report")

    soup = BeautifulSoup(html_text, "lxml")
    heading = None
    for tag in soup.find_all("h2"):
        if "Filtered companies" in tag.get_text():
            heading = tag
            break
    if heading is None:
        raise ValueError("Filtered companies heading not found")

    table = heading.find_next("table")
    if table is None:
        raise ValueError("Filtered companies table not found")

    head_row = table.find("thead").find("tr")
    headers = [th.get_text(strip=True) for th in head_row.find_all("th")]
    ticker_idx = headers.index("ticker") if "ticker" in headers else 0

    if "IOMA" in headers:
        ioma_idx = headers.index("IOMA")
        existing = True
    else:
        th = soup.new_tag("th")
        th.string = "IOMA"
        head_row.append(th)
        ioma_idx = len(headers)
        existing = False

    body = table.find("tbody")
    for row in body.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        if len(cells) == 1 and "no companies" in cells[0].get_text().lower():
            cells[0]["colspan"] = str((len(headers) + (0 if existing else 1)))
            continue
        ticker = cells[ticker_idx].get_text(strip=True)
        raw = ioma_by_ticker.get(ticker)
        if isinstance(raw, (int, float)):
            label = format_ioma(raw)
        else:
            label = raw
        cell = _ioma_cell_html(soup, label)
        if existing and ioma_idx < len(cells):
            cells[ioma_idx].replace_with(cell)
        else:
            row.append(cell)

    return str(soup)


def write_missing_file_error(root, date_str, suffix, detail=""):
    path = os.path.join(root, ERROR_FILENAME)
    lines = [
        f"missing: {report_filename(date_str, suffix)}",
        f"us_eastern_date: {date_str}",
        f"session: {suffix}",
    ]
    if detail:
        lines.append(detail.rstrip())
        if not detail.endswith("\n"):
            lines.append("")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    return path


def try_generate_report(date_str, suffix, root=None):
    """Generate the day's HTML report via the existing API scraper."""
    root = root or SCRIPT_DIR
    scraper = os.path.join(root, "scrape_earnings_api.py")
    if not os.path.exists(scraper):
        return False
    session = "bmo" if suffix == "BM" else "amc"
    result = subprocess.run(
        [sys.executable, scraper, "--date", date_str, "--session", session],
        cwd=root,
        check=False,
    )
    return result.returncode == 0


def process_report(report_path, fetcher=None):
    """Read a report, compute IOMA for each filtered ticker, rewrite the file."""
    fetch = fetcher or fetch_ioma
    with open(report_path, encoding="utf-8") as handle:
        html_text = handle.read()
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required to edit the HTML report")
    soup = BeautifulSoup(html_text, "lxml")
    heading = None
    for tag in soup.find_all("h2"):
        if "Filtered companies" in tag.get_text():
            heading = tag
            break
    if heading is None:
        raise ValueError("Filtered companies heading not found")
    table = heading.find_next("table")
    head_row = table.find("thead").find("tr")
    headers = [th.get_text(strip=True) for th in head_row.find_all("th")]
    ticker_idx = headers.index("ticker") if "ticker" in headers else 0

    ioma_by_ticker = {}
    for row in table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if not cells or (len(cells) == 1 and "no companies" in cells[0].get_text().lower()):
            continue
        ticker = cells[ticker_idx].get_text(strip=True)
        if not ticker:
            continue
        try:
            result = fetch(ticker)
            ioma_by_ticker[ticker] = result.get("ioma") if result else None
        except Exception:
            ioma_by_ticker[ticker] = None

    updated = add_ioma_column_to_html(html_text, ioma_by_ticker)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(updated)
    return ioma_by_ticker


def run_job(now=None, root=None, generate_if_missing=True, fetcher=None):
    """
    Evening/morning entry point used by the cron automation.

    Returns the report path on success, or the error-file path if the day's
    report cannot be found or generated.
    """
    root = root or SCRIPT_DIR
    date_str, suffix = resolve_report_target(now)
    report_path = os.path.join(root, report_filename(date_str, suffix))
    error_path = os.path.join(root, ERROR_FILENAME)

    if not os.path.exists(report_path) and generate_if_missing:
        try:
            try_generate_report(date_str, suffix, root=root)
        except Exception as exc:
            write_missing_file_error(
                root, date_str, suffix, detail=f"generate_failed: {exc}"
            )
            return error_path

    if not os.path.exists(report_path):
        write_missing_file_error(root, date_str, suffix)
        return error_path

    if os.path.exists(error_path):
        os.remove(error_path)

    process_report(report_path, fetcher=fetcher)
    return report_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Add IOMA to the day's earnings report")
    parser.add_argument("--now", help="ISO timestamp override (for tests / replay)")
    parser.add_argument("--root", default=SCRIPT_DIR, help="Directory with earnings_report_*.html")
    parser.add_argument("--no-generate", action="store_true",
                        help="Do not scrape a missing report; write no_earnings_file_found instead")
    args = parser.parse_args(argv)

    now = datetime.fromisoformat(args.now) if args.now else None
    path = run_job(now=now, root=args.root, generate_if_missing=not args.no_generate)
    print(path)
    return 0 if os.path.basename(path) != ERROR_FILENAME else 1


if __name__ == "__main__":
    sys.exit(main())
