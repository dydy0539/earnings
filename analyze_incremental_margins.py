#!/usr/bin/env python3
"""
Incremental Operating Margin Analyzer
Analyzes companies from filtered earnings files and calculates incremental operating margins.
"""

import json
import os
import sys
from datetime import datetime
import yfinance as yf
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import re

# SEC EDGAR and Claude API imports
try:
    from edgar import Company, set_identity
    EDGAR_AVAILABLE = True
except ImportError:
    EDGAR_AVAILABLE = False
    logging.warning("edgartools not installed. SEC 8-K fetching disabled.")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("anthropic not installed. AI parsing disabled.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('margin_analyzer.log'),
        logging.StreamHandler()
    ]
)

class IncrementalMarginAnalyzer:
    def __init__(self, debug=False, use_adjusted=True):
        self.debug = debug
        self.use_adjusted = use_adjusted
        self.claude_client = None

        # Initialize Claude client if available
        if ANTHROPIC_AVAILABLE and self.use_adjusted:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                self.claude_client = anthropic.Anthropic(api_key=api_key)
            else:
                logging.warning("ANTHROPIC_API_KEY not set. AI parsing disabled.")

        # Set SEC EDGAR identity (required by SEC)
        if EDGAR_AVAILABLE:
            set_identity("EarningsAnalyzer earnings@example.com")

    def debug_print(self, message):
        """Print debug messages if debug mode is enabled"""
        if self.debug:
            logging.debug(message)

    def get_earnings_press_release(self, ticker):
        """
        Fetch the most recent earnings press release from SEC EDGAR 8-K filings.
        Returns the text content of the press release or None if not found.
        """
        if not EDGAR_AVAILABLE:
            self.debug_print(f"{ticker}: edgartools not available")
            return None

        try:
            # Get company filings
            company = Company(ticker)

            # Get recent 8-K filings
            filings = company.get_filings(form="8-K")

            if not filings or len(filings) == 0:
                self.debug_print(f"{ticker}: No 8-K filings found")
                return None

            # Look through recent filings for Item 2.02 (Results of Operations)
            for filing in filings[:10]:  # Check last 10 filings
                try:
                    # Get filing details
                    filing_obj = filing

                    # Check if this is an earnings release (Item 2.02)
                    items = getattr(filing_obj, 'items', None)
                    if items and '2.02' in str(items):
                        self.debug_print(f"{ticker}: Found Item 2.02 filing dated {filing_obj.filing_date}")

                        # Get the press release text (usually in Exhibit 99.1)
                        try:
                            # Try to get attachments/exhibits
                            attachments = filing_obj.attachments
                            for attachment in attachments:
                                if '99' in str(attachment.document) or 'ex99' in str(attachment.document).lower():
                                    text = attachment.text()
                                    if text and len(text) > 500:  # Sanity check
                                        self.debug_print(f"{ticker}: Extracted press release ({len(text)} chars)")
                                        return {
                                            'text': text,
                                            'filing_date': str(filing_obj.filing_date),
                                            'source': f"SEC 8-K {filing_obj.accession_number}"
                                        }
                        except Exception as e:
                            self.debug_print(f"{ticker}: Error extracting exhibit: {e}")
                            # Fall back to full filing text
                            try:
                                text = filing_obj.text()
                                if text and len(text) > 500:
                                    return {
                                        'text': text,
                                        'filing_date': str(filing_obj.filing_date),
                                        'source': f"SEC 8-K {filing_obj.accession_number}"
                                    }
                            except:
                                pass
                except Exception as e:
                    self.debug_print(f"{ticker}: Error processing filing: {e}")
                    continue

            self.debug_print(f"{ticker}: No Item 2.02 earnings release found")
            return None

        except Exception as e:
            logging.error(f"{ticker}: Error fetching SEC filings - {e}")
            return None

    def extract_adjusted_figures(self, press_release, ticker):
        """
        Use Claude API to extract adjusted operating income from press release text.
        Returns structured data with adjusted figures or None if not found.
        """
        if not self.claude_client:
            self.debug_print(f"{ticker}: Claude client not available")
            return None

        try:
            prompt = f"""Analyze this earnings press release for {ticker} and extract financial figures.

I need you to find and extract:
1. Adjusted Operating Income (or Non-GAAP Operating Income) for the most recent quarter
2. Adjusted Operating Income for the same quarter last year (year-over-year comparison)
3. Revenue for the most recent quarter
4. Revenue for the same quarter last year
5. The fiscal quarter and year these figures apply to (e.g., "Q4 2024" or "Q1 FY2025")

If "Adjusted Operating Income" is not explicitly stated, look for:
- Non-GAAP Operating Income
- Adjusted Income from Operations
- Operating Income excluding special items

Respond in JSON format only:
{{
    "quarter": "Q4 2024",
    "adjusted_operating_income": 1234567890,
    "adjusted_operating_income_prior_year": 1100000000,
    "revenue": 50000000000,
    "revenue_prior_year": 45000000000,
    "metric_name": "Adjusted Operating Income",
    "found": true,
    "notes": "any relevant notes about the figures"
}}

If adjusted operating income figures are not found in the press release, set "found": false.

All monetary values should be in raw numbers (not millions or billions) - convert if needed.

Press Release Text:
{press_release['text'][:15000]}"""  # Limit text to avoid token limits

            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                if result.get('found', False):
                    result['source'] = press_release['source']
                    result['filing_date'] = press_release['filing_date']
                    self.debug_print(f"{ticker}: Extracted adjusted figures: {result['metric_name']}")
                    return result

            self.debug_print(f"{ticker}: No adjusted figures found in press release")
            return None

        except Exception as e:
            logging.error(f"{ticker}: Error parsing with Claude - {e}")
            return None

    def save_press_releases(self, companies, output_dir="press_releases"):
        """Save press releases for all companies to files for manual analysis"""
        os.makedirs(output_dir, exist_ok=True)
        saved = []

        for company in companies:
            ticker = company.get('ticker')
            name = company.get('name', ticker)
            logging.info(f"Fetching press release for {ticker}...")

            press_release = self.get_earnings_press_release(ticker)
            if press_release:
                filename = f"{output_dir}/{ticker}_{press_release['filing_date']}.txt"
                with open(filename, 'w') as f:
                    f.write(f"Ticker: {ticker}\n")
                    f.write(f"Company: {name}\n")
                    f.write(f"Filing Date: {press_release['filing_date']}\n")
                    f.write(f"Source: {press_release['source']}\n")
                    f.write("="*80 + "\n\n")
                    f.write(press_release['text'])
                saved.append({'ticker': ticker, 'file': filename})
                logging.info(f"{ticker}: Saved press release to {filename}")
            else:
                logging.warning(f"{ticker}: No press release found")

        return saved

    def get_adjusted_financials(self, ticker):
        """
        Orchestrate fetching adjusted operating income from SEC 8-K filings.
        Returns adjusted figures or None if unavailable.
        """
        if not self.use_adjusted:
            self.debug_print(f"{ticker}: Adjusted figures disabled")
            return None

        if not EDGAR_AVAILABLE or not self.claude_client:
            self.debug_print(f"{ticker}: SEC/Claude integration not available")
            return None

        # Fetch press release from SEC EDGAR
        press_release = self.get_earnings_press_release(ticker)
        if not press_release:
            self.debug_print(f"{ticker}: No press release found")
            return None

        # Extract adjusted figures using Claude
        adjusted_figures = self.extract_adjusted_figures(press_release, ticker)
        if not adjusted_figures:
            self.debug_print(f"{ticker}: Could not extract adjusted figures")
            return None

        return adjusted_figures

    def get_latest_filtered_file(self, time_suffix=None):
        """
        Find the most recent filtered earnings file.
        If time_suffix is provided (AM or BM), look for that specific file from today.
        Otherwise, find the most recent file.
        """
        if time_suffix:
            # Get today's date in YYYYMMDD format
            today = datetime.now().strftime("%Y%m%d")
            filename = f"earnings_filtered_{today}_{time_suffix}.json"
            if os.path.exists(filename):
                return filename
            else:
                logging.warning(f"File {filename} not found, looking for latest file...")
        
        # Find most recent filtered file
        filtered_files = sorted(Path('.').glob('earnings_filtered_*.json'), 
                               key=os.path.getmtime, reverse=True)
        if filtered_files:
            return str(filtered_files[0])
        return None
    
    def get_quarterly_financials(self, ticker):
        """
        Fetch quarterly financial data for a ticker using yfinance.
        Returns dictionary with latest quarter and prior year quarter data.
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get quarterly financials
            quarterly_income = stock.quarterly_financials
            
            if quarterly_income is None or quarterly_income.empty:
                logging.warning(f"{ticker}: No quarterly financial data available")
                return None
            
            # Transpose to have dates as rows
            df = quarterly_income.T
            df = df.sort_index(ascending=False)  # Most recent first
            
            self.debug_print(f"{ticker}: Found {len(df)} quarters of data")
            
            # Get latest quarter (Q0) and year-ago quarter (Q4)
            if len(df) < 2:
                logging.warning(f"{ticker}: Not enough historical data (only {len(df)} quarters)")
                return None
            
            # Helper function to check if a quarter has valid data
            def has_valid_data(df_row, revenue_fields, op_income_fields):
                """Check if quarter has non-null revenue and operating income"""
                def safe_get(df_row, field_names):
                    for field in field_names:
                        if field in df_row.index:
                            val = df_row[field]
                            # Check for None, NaN, or missing values
                            if val is not None and not pd.isna(val):
                                return float(val)
                    return None
                
                revenue = safe_get(df_row, revenue_fields)
                op_income = safe_get(df_row, op_income_fields)
                return revenue is not None and op_income is not None
            
            # Revenue and operating income field names
            revenue_fields = ['Total Revenue', 'Revenue', 'Total Revenues', 'Net Sales']
            op_income_fields = ['Operating Income', 'Operating Income Or Loss', 
                               'Income From Continuing Operations', 'EBIT',
                               'Operating Revenue']
            
            # Find the most recent quarter with valid data
            q0_data = None
            q0_date = None
            q0_index = None
            for i in range(len(df)):
                if has_valid_data(df.iloc[i], revenue_fields, op_income_fields):
                    q0_data = df.iloc[i]
                    q0_date = df.index[i]
                    q0_index = i
                    break
            
            if q0_data is None:
                logging.warning(f"{ticker}: No valid data in recent quarters")
                return None
            
            # Look for quarter approximately 4 quarters ago from q0
            q4_data = None
            q4_date = None
            target_q4_index = q0_index + 4
            
            # Try to find a quarter with valid data around 4 quarters ago
            for offset in [0, -1, 1, -2, 2]:  # Try exact, then nearby quarters
                check_index = target_q4_index + offset
                if 0 <= check_index < len(df):
                    if has_valid_data(df.iloc[check_index], revenue_fields, op_income_fields):
                        q4_data = df.iloc[check_index]
                        q4_date = df.index[check_index]
                        break
            
            if q4_data is None:
                logging.warning(f"{ticker}: Cannot find year-ago quarter data with valid values")
                return None
            
            self.debug_print(f"{ticker}: Using Q0={q0_date.strftime('%Y-%m-%d')}, Q-4={q4_date.strftime('%Y-%m-%d')}")
            
            # Extract key metrics using the helper function
            def safe_get(df_row, field_names):
                """Try multiple field names and return first found"""
                for field in field_names:
                    if field in df_row.index:
                        val = df_row[field]
                        if val is not None and not pd.isna(val):
                            return float(val)
                return None
            
            q0_revenue = safe_get(q0_data, revenue_fields)
            q4_revenue = safe_get(q4_data, revenue_fields)
            q0_op_income = safe_get(q0_data, op_income_fields)
            q4_op_income = safe_get(q4_data, op_income_fields)
            
            if q0_revenue is None or q4_revenue is None:
                logging.warning(f"{ticker}: Missing revenue data")
                return None
            if q0_op_income is None or q4_op_income is None:
                logging.warning(f"{ticker}: Missing operating income data")
                return None
            
            result = {
                'ticker': ticker,
                'latest_quarter_date': q0_date.strftime('%Y-%m-%d'),
                'prior_year_quarter_date': q4_date.strftime('%Y-%m-%d'),
                'latest_quarter': {
                    'revenue': q0_revenue,
                    'operating_income': q0_op_income,
                    'operating_margin': (q0_op_income / q0_revenue * 100) if q0_revenue != 0 else None
                },
                'prior_year_quarter': {
                    'revenue': q4_revenue,
                    'operating_income': q4_op_income,
                    'operating_margin': (q4_op_income / q4_revenue * 100) if q4_revenue != 0 else None
                }
            }
            
            self.debug_print(f"{ticker}: Successfully fetched financial data")
            return result
            
        except Exception as e:
            logging.error(f"{ticker}: Error fetching financial data - {e}")
            return None
    
    def calculate_incremental_margin(self, financial_data, adjusted_data=None):
        """
        Calculate incremental operating margin:
        (Op Income Q - Op Income Q-4) / (Revenue Q - Revenue Q-4)

        If adjusted_data is provided, also calculates adjusted incremental margin.
        """
        try:
            q0 = financial_data['latest_quarter']
            q4 = financial_data['prior_year_quarter']

            revenue_delta = q0['revenue'] - q4['revenue']
            op_income_delta = q0['operating_income'] - q4['operating_income']

            if revenue_delta == 0:
                logging.warning(f"{financial_data['ticker']}: Zero revenue growth")
                return None

            incremental_margin = (op_income_delta / revenue_delta) * 100

            result = {
                'incremental_operating_margin': incremental_margin,
                'revenue_growth': ((q0['revenue'] - q4['revenue']) / q4['revenue'] * 100),
                'operating_income_growth': ((q0['operating_income'] - q4['operating_income']) / q4['operating_income'] * 100) if q4['operating_income'] != 0 else None,
                'is_margin_expanding': incremental_margin > q0['operating_margin'] if q0['operating_margin'] else None
            }

            # Calculate adjusted incremental margin if available
            if adjusted_data and adjusted_data.get('found'):
                adj_op_income = adjusted_data.get('adjusted_operating_income')
                adj_op_income_prior = adjusted_data.get('adjusted_operating_income_prior_year')
                adj_revenue = adjusted_data.get('revenue')
                adj_revenue_prior = adjusted_data.get('revenue_prior_year')

                if all([adj_op_income, adj_op_income_prior, adj_revenue, adj_revenue_prior]):
                    adj_revenue_delta = adj_revenue - adj_revenue_prior
                    adj_op_income_delta = adj_op_income - adj_op_income_prior

                    if adj_revenue_delta != 0:
                        adj_incremental_margin = (adj_op_income_delta / adj_revenue_delta) * 100
                        adj_operating_margin = (adj_op_income / adj_revenue * 100) if adj_revenue != 0 else None

                        result['adjusted_incremental_operating_margin'] = adj_incremental_margin
                        result['adjusted_operating_margin'] = adj_operating_margin
                        result['adjusted_revenue_growth'] = ((adj_revenue - adj_revenue_prior) / adj_revenue_prior * 100) if adj_revenue_prior != 0 else None
                        result['adjusted_operating_income_growth'] = ((adj_op_income - adj_op_income_prior) / adj_op_income_prior * 100) if adj_op_income_prior != 0 else None
                        result['is_adjusted_margin_expanding'] = adj_incremental_margin > adj_operating_margin if adj_operating_margin else None
                        result['adjusted_source'] = adjusted_data.get('source')
                        result['adjusted_metric_name'] = adjusted_data.get('metric_name')
                        result['adjusted_quarter'] = adjusted_data.get('quarter')

            return result

        except Exception as e:
            logging.error(f"Error calculating incremental margin: {e}")
            return None
    
    def analyze_companies(self, filtered_file_path, manual_results=None):
        """
        Analyze all companies in the filtered earnings file.

        Args:
            filtered_file_path: Path to filtered earnings JSON file
            manual_results: Optional dict of manually-analyzed adjusted figures keyed by ticker
        """
        try:
            with open(filtered_file_path, 'r') as f:
                data = json.load(f)

            companies = data.get('companies', [])
            if not companies:
                logging.warning(f"No companies found in {filtered_file_path}")
                return None

            logging.info(f"Analyzing {len(companies)} companies from {filtered_file_path}")
            if manual_results:
                logging.info(f"Using manual results for {len(manual_results)} companies")

            results = []

            for company in companies:
                ticker = company.get('ticker')
                name = company.get('name', ticker)

                logging.info(f"Processing {ticker} - {name}")

                # Get financial data
                financial_data = self.get_quarterly_financials(ticker)

                if financial_data is None:
                    results.append({
                        'company_name': name,
                        'ticker': ticker,
                        'status': 'data_unavailable',
                        'incremental_operating_margin': None,
                        'latest_operating_margin': None,
                        'error': 'Could not fetch financial data'
                    })
                    continue

                # Get adjusted figures - check manual results first, then fall back to API
                adjusted_data = None
                if manual_results and ticker in manual_results:
                    adjusted_data = manual_results[ticker].copy()
                    adjusted_data['found'] = True  # Mark as valid
                    adjusted_data['source'] = 'manual'
                    logging.info(f"{ticker}: Using manual adjusted figures")
                elif self.use_adjusted:
                    logging.info(f"{ticker}: Fetching adjusted figures from SEC 8-K...")
                    adjusted_data = self.get_adjusted_financials(ticker)
                    if adjusted_data:
                        logging.info(f"{ticker}: Found adjusted figures - {adjusted_data.get('metric_name', 'N/A')}")
                    else:
                        logging.info(f"{ticker}: No adjusted figures available, using GAAP only")

                # Calculate incremental margin (GAAP and adjusted if available)
                margin_analysis = self.calculate_incremental_margin(financial_data, adjusted_data)
                
                if margin_analysis is None:
                    results.append({
                        'company_name': name,
                        'ticker': ticker,
                        'status': 'calculation_failed',
                        'incremental_operating_margin': None,
                        'latest_operating_margin': financial_data['latest_quarter'].get('operating_margin'),
                        'error': 'Could not calculate incremental margin'
                    })
                    continue
                
                # Compile result
                result = {
                    'company_name': name,
                    'ticker': ticker,
                    'status': 'success',
                    'incremental_operating_margin': round(margin_analysis['incremental_operating_margin'], 2),
                    'latest_operating_margin': round(financial_data['latest_quarter']['operating_margin'], 2),
                    'latest_quarter_date': financial_data['latest_quarter_date'],
                    'prior_year_quarter_date': financial_data['prior_year_quarter_date'],
                    'is_margin_expanding': margin_analysis['is_margin_expanding'],
                    'revenue_growth_pct': round(margin_analysis['revenue_growth'], 2),
                    'operating_income_growth_pct': round(margin_analysis['operating_income_growth'], 2) if margin_analysis['operating_income_growth'] else None,
                    'details': {
                        'latest_quarter': {
                            'revenue': financial_data['latest_quarter']['revenue'],
                            'operating_income': financial_data['latest_quarter']['operating_income'],
                            'operating_margin_pct': round(financial_data['latest_quarter']['operating_margin'], 2)
                        },
                        'prior_year_quarter': {
                            'revenue': financial_data['prior_year_quarter']['revenue'],
                            'operating_income': financial_data['prior_year_quarter']['operating_income'],
                            'operating_margin_pct': round(financial_data['prior_year_quarter']['operating_margin'], 2)
                        }
                    }
                }

                # Add adjusted figures if available
                if 'adjusted_incremental_operating_margin' in margin_analysis:
                    result['adjusted_incremental_operating_margin'] = round(margin_analysis['adjusted_incremental_operating_margin'], 2)
                    result['adjusted_operating_margin'] = round(margin_analysis['adjusted_operating_margin'], 2) if margin_analysis.get('adjusted_operating_margin') else None
                    result['is_adjusted_margin_expanding'] = margin_analysis.get('is_adjusted_margin_expanding')
                    result['adjusted_source'] = margin_analysis.get('adjusted_source')
                    result['adjusted_metric_name'] = margin_analysis.get('adjusted_metric_name')
                    result['adjusted_quarter'] = margin_analysis.get('adjusted_quarter')
                    if adjusted_data:
                        result['details']['adjusted'] = {
                            'revenue': adjusted_data.get('revenue'),
                            'revenue_prior_year': adjusted_data.get('revenue_prior_year'),
                            'operating_income': adjusted_data.get('adjusted_operating_income'),
                            'operating_income_prior_year': adjusted_data.get('adjusted_operating_income_prior_year'),
                            'metric_name': adjusted_data.get('metric_name'),
                            'notes': adjusted_data.get('notes')
                        }

                results.append(result)

                # Log results
                log_msg = f"{ticker}: GAAP Inc. Margin = {result['incremental_operating_margin']:.2f}%"
                if 'adjusted_incremental_operating_margin' in result:
                    log_msg += f", Adj. Inc. Margin = {result['adjusted_incremental_operating_margin']:.2f}%"
                log_msg += f", Expanding = {result['is_margin_expanding']}"
                logging.info(log_msg)
            
            return {
                'source_file': filtered_file_path,
                'analyzed_at': datetime.now().isoformat(),
                'total_companies': len(companies),
                'successful_analyses': sum(1 for r in results if r['status'] == 'success'),
                'companies': results
            }
            
        except Exception as e:
            logging.error(f"Error analyzing companies: {e}")
            return None
    
    def save_results(self, results, output_filename):
        """Save analysis results to JSON file"""
        try:
            with open(output_filename, 'w') as f:
                json.dump(results, f, indent=2)
            logging.info(f"Results saved to {output_filename}")
            return True
        except Exception as e:
            logging.error(f"Error saving results: {e}")
            return False

def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze incremental operating margins for earnings companies')
    parser.add_argument('--input', '-i', help='Input filtered earnings file (default: latest)')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--suffix', '-s', choices=['AM', 'BM'], help='Time suffix (AM or BM) to use for today\'s file')
    parser.add_argument('--no-adjusted', action='store_true', help='Skip fetching adjusted figures from SEC 8-K filings')
    parser.add_argument('--extract-only', action='store_true',
        help='Only extract press releases to files for manual analysis')
    parser.add_argument('--manual-results', '-m',
        help='JSON file with manually-analyzed adjusted figures')
    parser.add_argument('--press-release-dir', default='press_releases',
        help='Directory for press release extraction (default: press_releases)')

    args = parser.parse_args()

    use_adjusted = not args.no_adjusted
    analyzer = IncrementalMarginAnalyzer(debug=args.debug, use_adjusted=use_adjusted)

    # Find input file
    if args.input:
        input_file = args.input
    else:
        input_file = analyzer.get_latest_filtered_file(args.suffix)

    if not input_file or not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        sys.exit(1)

    logging.info(f"Processing file: {input_file}")

    # Handle extract-only mode
    if args.extract_only:
        with open(input_file, 'r') as f:
            data = json.load(f)
        companies = data.get('companies', [])

        if not companies:
            logging.error("No companies found in input file")
            sys.exit(1)

        saved = analyzer.save_press_releases(companies, args.press_release_dir)

        print("\n" + "="*80)
        print(f"PRESS RELEASE EXTRACTION COMPLETE")
        print("="*80)
        print(f"Extracted {len(saved)} press releases to {args.press_release_dir}/")
        print("\nFiles saved:")
        for item in saved:
            print(f"  - {item['ticker']}: {item['file']}")

        print("\n" + "-"*80)
        print("NEXT STEPS:")
        print("-"*80)
        print("1. Analyze press releases using Claude Code with this prompt:")
        print()
        print('   "Analyze these press releases and extract adjusted operating income')
        print('    for each company. Return a JSON file with this format:')
        print('    {')
        print('      "TICKER": {')
        print('        "quarter": "Q4 2025",')
        print('        "adjusted_operating_income": 2500000000,')
        print('        "adjusted_operating_income_prior_year": 2100000000,')
        print('        "revenue": 12000000000,')
        print('        "revenue_prior_year": 10500000000,')
        print('        "metric_name": "Adjusted Operating Income",')
        print('        "notes": "Excludes restructuring charges"')
        print('      }')
        print('    }"')
        print()
        print("2. Save the JSON output to a file (e.g., adjusted_figures.json)")
        print()
        print("3. Run the analysis with manual results:")
        print(f"   python analyze_incremental_margins.py -i {input_file} -m adjusted_figures.json")
        print("="*80)
        sys.exit(0)

    # Load manual results if provided
    manual_results = None
    if args.manual_results:
        if not os.path.exists(args.manual_results):
            logging.error(f"Manual results file not found: {args.manual_results}")
            sys.exit(1)
        with open(args.manual_results, 'r') as f:
            manual_results = json.load(f)
        logging.info(f"Loaded manual results for {len(manual_results)} companies")

    # Analyze companies
    results = analyzer.analyze_companies(input_file, manual_results=manual_results)
    
    if results is None:
        logging.error("Analysis failed")
        sys.exit(1)
    
    # Determine output filename based on input filename
    # Extract date and suffix from input filename
    # earnings_filtered_YYYYMMDD_XX.json -> incremental_margins_YYYYMMDD_XX.json
    import re
    match = re.search(r'earnings_filtered_(\d{8})_(AM|BM)\.json', input_file)
    if match:
        date_str = match.group(1)
        suffix = match.group(2)
        output_file = f"incremental_margins_{date_str}_{suffix}.json"
    else:
        # Fallback
        output_file = f"incremental_margins_{datetime.now().strftime('%Y%m%d')}.json"
    
    # Save results
    if analyzer.save_results(results, output_file):
        logging.info(f"Analysis complete: {results['successful_analyses']}/{results['total_companies']} companies analyzed successfully")
        
        # Print summary
        print("\n" + "="*120)
        print(f"INCREMENTAL OPERATING MARGIN ANALYSIS - {date_str if 'date_str' in locals() else 'N/A'}")
        print("="*120)

        # Check if any company has adjusted figures
        has_adjusted = any(company.get('adjusted_incremental_operating_margin') is not None
                         for company in results['companies'] if company['status'] == 'success')

        if has_adjusted:
            print(f"{'Company':<30} {'GAAP Inc.':<12} {'Adj. Inc.':<12} {'GAAP Mrg':<10} {'Adj. Mrg':<10} {'Expanding':<10} {'Source':<25}")
            print("-"*120)

            for company in results['companies']:
                if company['status'] == 'success':
                    inc_margin = f"{company['incremental_operating_margin']:.1f}%" if company['incremental_operating_margin'] else "N/A"
                    adj_inc_margin = f"{company['adjusted_incremental_operating_margin']:.1f}%" if company.get('adjusted_incremental_operating_margin') else "-"
                    latest_margin = f"{company['latest_operating_margin']:.1f}%" if company['latest_operating_margin'] else "N/A"
                    adj_margin = f"{company['adjusted_operating_margin']:.1f}%" if company.get('adjusted_operating_margin') else "-"
                    # Use adjusted margin expansion status if available, otherwise GAAP
                    if company.get('adjusted_incremental_operating_margin') is not None:
                        expanding = "Yes" if company.get('is_adjusted_margin_expanding') else "No"
                    else:
                        expanding = "Yes" if company['is_margin_expanding'] else "No"
                    source = company.get('adjusted_source', '-')[:24] if company.get('adjusted_source') else "-"
                    print(f"{company['company_name'][:29]:<30} {inc_margin:<12} {adj_inc_margin:<12} {latest_margin:<10} {adj_margin:<10} {expanding:<10} {source:<25}")
                else:
                    print(f"{company['company_name'][:29]:<30} {'ERROR':<12} {'-':<12} {'ERROR':<10} {'-':<10} {'N/A':<10} {'-':<25}")
        else:
            print(f"{'Company':<40} {'Inc. Margin':<15} {'Latest Margin':<15} {'Expanding':<10}")
            print("-"*80)

            for company in results['companies']:
                if company['status'] == 'success':
                    inc_margin = f"{company['incremental_operating_margin']:.2f}%" if company['incremental_operating_margin'] else "N/A"
                    latest_margin = f"{company['latest_operating_margin']:.2f}%" if company['latest_operating_margin'] else "N/A"
                    expanding = "Yes" if company['is_margin_expanding'] else "No"
                    print(f"{company['company_name'][:39]:<40} {inc_margin:<15} {latest_margin:<15} {expanding:<10}")
                else:
                    print(f"{company['company_name'][:39]:<40} {'ERROR':<15} {'ERROR':<15} {'N/A':<10}")

        print("="*120)
        if use_adjusted and not has_adjusted:
            print("Note: No adjusted figures were available from SEC 8-K filings. Showing GAAP only.")
        elif not use_adjusted:
            print("Note: Adjusted figures disabled (--no-adjusted flag). Showing GAAP only.")
        print(f"Results saved to: {output_file}")
        print("="*120)
    else:
        logging.error("Failed to save results")
        sys.exit(1)

if __name__ == "__main__":
    main()
