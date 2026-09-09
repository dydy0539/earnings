#!/usr/bin/env python3
"""Unit tests for IOMA calculation, session dating, and HTML column insertion."""

import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pandas as pd

import ioma


SAMPLE_FILTERED_TABLE = """<!DOCTYPE html>
<html><body>
<h2>Filtered companies (2)</h2>
<div class="tablewrap"><table><thead><tr>
<th>ticker</th><th>name</th><th>revenue_millions</th>
</tr></thead><tbody>
<tr><td>ABC</td><td>Abc Inc</td><td class="num">100</td></tr>
<tr><td>XYZ</td><td>Xyz Corp</td><td class="num">200</td></tr>
</tbody></table></div>
<h2>Full calendar</h2>
<table><thead><tr><th>symbol</th></tr></thead><tbody>
<tr><td>ABC</td></tr>
</tbody></table>
</body></html>
"""


class CalculateIomaTests(unittest.TestCase):
    def test_ratio_from_operating_income(self):
        # (150 - 100) / (500 - 400) = 0.5
        self.assertAlmostEqual(ioma.calculate_ioma(150, 100, 500, 400), 0.5)

    def test_prefers_raw_formula_not_percent(self):
        value = ioma.calculate_ioma(118_000_000, 109_400_000, 2_290_000_000, 2_111_700_000)
        self.assertAlmostEqual(value, 8_600_000 / 178_300_000)

    def test_format_percentage(self):
        self.assertEqual(ioma.format_ioma(0.048234), "4.82%")
        self.assertIsNone(ioma.format_ioma(None))

    def test_zero_revenue_delta_is_none(self):
        self.assertIsNone(ioma.calculate_ioma(10, 5, 100, 100))

    def test_missing_inputs_are_none(self):
        self.assertIsNone(ioma.calculate_ioma(None, 5, 100, 80))
        self.assertIsNone(ioma.calculate_ioma(10, 5, None, 80))


class ReportTargetTests(unittest.TestCase):
    def test_morning_utc_uses_am_and_us_eastern_date(self):
        # 09:30 UTC = 05:30 US Eastern on the same calendar date.
        now = datetime(2026, 9, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(ioma.resolve_report_target(now), ("20260908", "AM"))

    def test_evening_utc_uses_bm_and_us_eastern_date(self):
        now = datetime(2026, 9, 8, 22, 30, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(ioma.resolve_report_target(now), ("20260908", "BM"))

    def test_japan_morning_after_utc_evening_still_uses_us_date(self):
        # 08:53 JST on Sep 9 is still the Sep 8 evening job in the US.
        now = datetime(2026, 9, 9, 8, 53, tzinfo=ZoneInfo("Asia/Tokyo"))
        self.assertEqual(ioma.resolve_report_target(now), ("20260908", "BM"))

    def test_singapore_evening_morning_job_uses_us_date_for_am(self):
        # 17:30 SGT on Sep 8 is 09:30 UTC — morning AM file, US date Sep 8.
        now = datetime(2026, 9, 8, 17, 30, tzinfo=ZoneInfo("Asia/Singapore"))
        self.assertEqual(ioma.resolve_report_target(now), ("20260908", "AM"))


class QuarterPickerTests(unittest.TestCase):
    def test_skips_empty_latest_quarter_and_prefers_ebitda(self):
        idx = [
            "Total Revenue",
            "Operating Income",
            "Normalized EBITDA",
            "EBITDA",
        ]
        cols = pd.to_datetime(
            ["2026-07-31", "2026-04-30", "2026-01-31", "2025-10-31", "2025-04-30"]
        )
        data = [
            [None, 2290, 2243, 2295, 2111],
            [None, 90, 78, 82, 82],
            [None, 121, 105, 96, 109],
            [None, 118, 101, 96, 109],
        ]
        df = pd.DataFrame(data, index=idx, columns=cols)
        pair = ioma.pick_comparable_quarters(df)
        self.assertIsNotNone(pair)
        self.assertEqual(pair["metric"], "Normalized EBITDA")
        self.assertEqual(pair["current"]["income"], 121)
        self.assertEqual(pair["prior"]["income"], 109)
        value = ioma.calculate_ioma(
            pair["current"]["income"],
            pair["prior"]["income"],
            pair["current"]["revenue"],
            pair["prior"]["revenue"],
        )
        self.assertAlmostEqual(value, (121 - 109) / (2290 - 2111))


class HtmlColumnTests(unittest.TestCase):
    def test_adds_ioma_column_to_filtered_table_only(self):
        updated = ioma.add_ioma_column_to_html(SAMPLE_FILTERED_TABLE, {"ABC": 0.5, "XYZ": None})
        self.assertIn("<th>IOMA</th>", updated)
        self.assertIn("50.00%", updated)
        # Full calendar table must not receive the new column.
        self.assertEqual(updated.count("<th>IOMA</th>"), 1)

    def test_refreshes_existing_ioma_column(self):
        once = ioma.add_ioma_column_to_html(SAMPLE_FILTERED_TABLE, {"ABC": 0.2, "XYZ": 0.1})
        twice = ioma.add_ioma_column_to_html(once, {"ABC": 0.4, "XYZ": 0.1})
        self.assertEqual(twice.count("<th>IOMA</th>"), 1)
        self.assertIn("40.00%", twice)
        self.assertNotIn("20.00%", twice)


class JobMissingFileTests(unittest.TestCase):
    def test_writes_error_file_when_report_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            error_path = ioma.run_job(
                now=datetime(2026, 9, 8, 22, 30, tzinfo=ZoneInfo("UTC")),
                root=tmp,
                generate_if_missing=False,
            )
            self.assertEqual(os.path.basename(error_path), "no_earnings_file_found")
            with open(error_path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("earnings_report_20260908_BM.html", text)

    def test_updates_existing_report_and_removes_stale_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "earnings_report_20260908_BM.html")
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(SAMPLE_FILTERED_TABLE)
            stale = os.path.join(tmp, "no_earnings_file_found")
            with open(stale, "w", encoding="utf-8") as handle:
                handle.write("stale\n")

            def fake_fetch(ticker):
                return {"ioma": 0.25} if ticker == "ABC" else None

            path = ioma.run_job(
                now=datetime(2026, 9, 8, 22, 30, tzinfo=ZoneInfo("UTC")),
                root=tmp,
                generate_if_missing=False,
                fetcher=fake_fetch,
            )
            self.assertEqual(path, report)
            self.assertFalse(os.path.exists(stale))
            with open(report, encoding="utf-8") as handle:
                html = handle.read()
            self.assertIn("25.00%", html)
            self.assertIn("<th>IOMA</th>", html)


class AttachIomaTests(unittest.TestCase):
    def test_attaches_formatted_column(self):
        companies = [{"ticker": "ABC", "name": "Abc"}]

        def fake_fetch(ticker):
            return {"ioma": 0.1234}

        ioma.attach_ioma(companies, fetcher=fake_fetch)
        self.assertEqual(companies[0]["IOMA"], "12.34%")


if __name__ == "__main__":
    unittest.main()
