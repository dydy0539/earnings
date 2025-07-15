#!/usr/bin/env python3
"""
Final Selenium-based scraper for EarningsWhispers.com
Properly handles the website's specific cookie acceptance mechanism.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
import json
import time
import os
import glob
from datetime import datetime
import re

class EarningsSeleniumScraper:
    def __init__(self, headless=True, debug=False):
        self.debug = debug
        self.setup_driver(headless)
        
    def find_chromedriver_path(self):
        """Find the ChromeDriver executable in webdriver-manager cache"""
        wdm_path = os.path.expanduser("~/.wdm/drivers/chromedriver/mac64/*/chromedriver-mac-arm64/chromedriver")
        chromedriver_paths = glob.glob(wdm_path)
        
        if chromedriver_paths:
            # Sort by version and get the latest
            latest_path = sorted(chromedriver_paths)[-1]
            self.debug_print(f"Found ChromeDriver at: {latest_path}")
            return latest_path
        
        # Fallback paths
        fallback_paths = [
            "/usr/local/bin/chromedriver",
            "/opt/homebrew/bin/chromedriver",
            "chromedriver"  # If in PATH
        ]
        
        for path in fallback_paths:
            if os.path.exists(path) or path == "chromedriver":
                self.debug_print(f"Using fallback ChromeDriver: {path}")
                return path
                
        raise Exception("ChromeDriver not found. Please check installation.")
        
    def setup_driver(self, headless):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # Find ChromeDriver path manually
            chromedriver_path = self.find_chromedriver_path()
            
            # Create service with explicit path
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            
            self.debug_print(f"Successfully initialized ChromeDriver from: {chromedriver_path}")
            
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print("Please make sure Chrome browser is installed")
            raise
    
    def debug_print(self, message):
        """Print debug messages if debug mode is enabled"""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def scrape_calendar(self, date_str):
        """
        Scrape earnings calendar for a specific date
        date_str format: YYYYMMDD (e.g., '20250714')
        """
        url = f"https://www.earningswhispers.com/calendar/{date_str}"
        print(f"Scraping earnings calendar for {date_str}")
        
        try:
            # Navigate to the page
            self.debug_print(f"Navigating to {url}")
            self.driver.get(url)
            
            # Handle cookie acceptance
            self.handle_cookie_wall()
            
            # Wait for the page to load and JavaScript to execute
            self.debug_print("Waiting for calendar data to load...")
            self.wait_for_calendar_data()
            
            # Extract earnings data
            earnings_data = self.extract_earnings_data(date_str)
            
            return earnings_data
            
        except Exception as e:
            print(f"Error scraping calendar: {e}")
            return None
    
    def handle_cookie_wall(self):
        """Handle the specific cookie acceptance mechanism used by EarningsWhispers"""
        try:
            # Wait a moment for the page to load
            time.sleep(3)
            
            # Strategy 1: Look for the generic cookie consent banner first
            generic_cookie_selectors = [
                "button[data-cookie-string]",
                "button[class*='accept-policy']",
                "button[onclick*='acceptAndReload']"
            ]
            
            for selector in generic_cookie_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            self.debug_print(f"Found and clicking generic cookie button: {selector}")
                            element.click()
                            time.sleep(2)
                            # Page will reload after cookie acceptance
                            return
                except Exception as e:
                    self.debug_print(f"Generic cookie selector {selector} failed: {e}")
                    continue
            
            # Strategy 2: Look for the specific "Accept Cookies" button in the main content
            main_cookie_selectors = [
                "#acceptCookies",
                "button[onclick='acceptAndReload()']",
                "button:contains('Accept Cookies')"
            ]
            
            for selector in main_cookie_selectors:
                try:
                    if selector.startswith("#") or selector.startswith(".") or selector.startswith("button["):
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    else:
                        # For contains selectors, use XPath
                        elements = self.driver.find_elements(By.XPATH, f"//button[contains(text(), 'Accept Cookies')]")
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            self.debug_print(f"Found and clicking main cookie button: {selector}")
                            element.click()
                            time.sleep(3)
                            # Wait for page to reload/refresh
                            self.wait.until(lambda driver: "Accept Cookies" not in driver.page_source)
                            return
                except Exception as e:
                    self.debug_print(f"Main cookie selector {selector} failed: {e}")
                    continue
            
            # Strategy 3: Execute JavaScript to accept cookies directly
            try:
                self.debug_print("Attempting JavaScript cookie acceptance...")
                result = self.driver.execute_script("""
                    // Try to find and click accept cookies button
                    var acceptBtn = document.querySelector('#acceptCookies') || 
                                   document.querySelector('button[onclick*="acceptAndReload"]') ||
                                   document.querySelector('button[data-cookie-string]');
                    
                    if (acceptBtn) {
                        acceptBtn.click();
                        return 'clicked';
                    }
                    
                    // Try to call acceptAndReload function directly if it exists
                    if (typeof acceptAndReload === 'function') {
                        acceptAndReload();
                        return 'function_called';
                    }
                    
                    // Set cookie manually
                    document.cookie = '.AspNet.Consent=yes; expires=Sat, 11 Jul 2026 12:54:56 GMT; path=/; secure; samesite=strict';
                    location.reload();
                    return 'manual_cookie';
                """)
                
                if result:
                    self.debug_print(f"JavaScript cookie acceptance result: {result}")
                    time.sleep(5)  # Wait for page reload
                    return
                    
            except Exception as e:
                self.debug_print(f"JavaScript cookie acceptance failed: {e}")
            
            self.debug_print("Cookie acceptance completed or not needed")
                    
        except Exception as e:
            self.debug_print(f"Cookie handling error: {e}")
    
    def wait_for_calendar_data(self):
        """Wait for the calendar data to load via JavaScript"""
        try:
            # Wait for the page title to confirm we're on the right page
            self.wait.until(lambda driver: "Earnings Scheduled" in driver.title or "Earnings Calendar" in driver.title)
            self.debug_print(f"Page title confirmed: {self.driver.title}")
            
            # Wait for body content to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check if we still see cookie wall
            if "Accept Cookies" in self.driver.page_source:
                self.debug_print("Still seeing cookie wall, attempting additional handling...")
                self.handle_cookie_wall()
                time.sleep(3)
            
            # Give JavaScript time to execute and load data
            self.debug_print("Waiting for JavaScript to execute and load earnings data...")
            time.sleep(15)  # Increased wait time for data loading
            
            # Check if calendar data has loaded
            self.check_calendar_loaded()
            
        except TimeoutException as e:
            self.debug_print(f"Timeout waiting for calendar data: {e}")
        except Exception as e:
            self.debug_print(f"Error waiting for calendar data: {e}")
    
    def check_calendar_loaded(self):
        """Check if calendar data has actually loaded"""
        try:
            # Get page source length
            page_length = len(self.driver.page_source)
            self.debug_print(f"Page source length: {page_length}")
            
            # Check if cookie wall is still present
            has_cookie_wall = "Accept Cookies" in self.driver.page_source
            self.debug_print(f"Cookie wall present: {has_cookie_wall}")
            
            # Look for specific calendar-related content
            calendar_indicators = [
                "getcalctrls",
                "calendar",
                "earnings",
                "eps",
                "whisper",
                "company",
                "symbol"
            ]
            
            page_source = self.driver.page_source.lower()
            found_indicators = [ind for ind in calendar_indicators if ind in page_source]
            self.debug_print(f"Found calendar indicators: {found_indicators}")
            
            # Execute JavaScript to check for dynamic content
            try:
                js_result = self.driver.execute_script("""
                    return {
                        hasTable: document.querySelector('table') !== null,
                        hasList: document.querySelector('ul') !== null,
                        hasCalendarContent: document.body.innerText.includes('earnings') || document.body.innerText.includes('EPS'),
                        bodyTextLength: document.body.innerText.length,
                        scripts: document.querySelectorAll('script').length,
                        hasCookieWall: document.body.innerText.includes('Accept Cookies'),
                        hasCompanyData: document.body.innerText.includes('Company') || document.body.innerText.includes('Symbol'),
                        calendarElements: document.querySelectorAll('[id*="cal"], [class*="cal"], [class*="earn"]').length
                    };
                """)
                self.debug_print(f"JavaScript check result: {js_result}")
                
            except Exception as e:
                self.debug_print(f"JavaScript execution error: {e}")
            
        except Exception as e:
            self.debug_print(f"Error checking calendar loaded: {e}")
    
    def extract_earnings_data(self, date_str):
        """Extract earnings data from the loaded page"""
        earnings_data = {
            'date': date_str,
            'scraped_at': datetime.now().isoformat(),
            'companies': [],
            'status': 'success'
        }
        
        try:
            # Check if we still have cookie wall
            if "Accept Cookies" in self.driver.page_source:
                earnings_data['status'] = 'cookie_wall_present'
                earnings_data['message'] = 'Cookie acceptance required but not completed'
                return earnings_data
            
            # Try multiple strategies to find earnings data
            companies = []
            
            # Strategy 1: Look for tables
            companies.extend(self.extract_from_tables())
            
            # Strategy 2: Look for specific class patterns
            companies.extend(self.extract_from_divs())
            
            # Strategy 3: Look for data attributes
            companies.extend(self.extract_from_data_attributes())
            
            # Strategy 4: Look for specific patterns in text
            companies.extend(self.extract_from_text_patterns())
            
            # Strategy 5: Look in page source for structured data
            companies.extend(self.extract_from_page_source())
            
            # Strategy 6: Look for specific EarningsWhispers content patterns
            companies.extend(self.extract_from_ew_patterns())
            
            # Remove duplicates and clean data
            companies = self.deduplicate_companies(companies)
            
            earnings_data['companies'] = companies
            
            if len(companies) == 0:
                earnings_data['status'] = 'no_data_found'
                earnings_data['message'] = f'No earnings data found for {date_str}. This might be a future date with no scheduled earnings.'
            
            self.debug_print(f"Total companies found: {len(companies)}")
            
            # Apply filtering criteria and save filtered results
            if companies:
                # Load tracking list
                tracking_list = self.load_tracking_list()
                filtered_companies = self.filter_companies_by_criteria(companies, tracking_list)
                if filtered_companies:
                    filtered_data = {
                        'date': date_str,
                        'scraped_at': datetime.now().isoformat(),
                        'filter_criteria': {
                            'revenue_growth_rules': [
                                '>10M revenue and >50% growth',
                                '>100M revenue and >30% growth',
                                '>500M revenue and >25% growth', 
                                '>1000M revenue and >20% growth',
                                '>5000M revenue and >15% growth'
                            ],
                            'tracking_list': sorted(list(tracking_list)) if tracking_list else [],
                            'tracking_list_count': len(tracking_list) if tracking_list else 0
                        },
                        'companies': filtered_companies,
                        'total_filtered': len(filtered_companies),
                        'total_original': len(companies)
                    }
                    
                    # Save filtered results
                    filtered_filename = f"earnings_filtered_{date_str}.json"
                    self.save_to_file(filtered_data, filtered_filename)
                    self.debug_print(f"Saved {len(filtered_companies)} filtered companies to {filtered_filename}")
            
            # Save page source for debugging
            if self.debug:
                with open('debug_selenium_final_page.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.debug_print("Saved page source to debug_selenium_final_page.html")
            
            return earnings_data
            
        except Exception as e:
            self.debug_print(f"Error extracting earnings data: {e}")
            earnings_data['status'] = 'error'
            earnings_data['message'] = str(e)
            return earnings_data
    
    def extract_from_tables(self):
        """Extract data from HTML tables"""
        companies = []
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            self.debug_print(f"Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                self.debug_print(f"Processing table {i+1}")
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    self.debug_print(f"Table {i+1} has {len(rows)} rows")
                    
                    # Find header row to identify "Reported Revenue" column
                    header_row = None
                    reported_revenue_col = -1
                    
                    if len(rows) > 0:
                        header_cells = rows[0].find_elements(By.TAG_NAME, "th")
                        if not header_cells:  # Try td if no th elements
                            header_cells = rows[0].find_elements(By.TAG_NAME, "td")
                        
                        for col_idx, header_cell in enumerate(header_cells):
                            header_text = header_cell.text.strip().lower()
                            if 'reported revenue' in header_text and 'estimate' not in header_text:
                                reported_revenue_col = col_idx
                                self.debug_print(f"Found 'Reported Revenue' column at index {col_idx}")
                                break
                    
                    for j, row in enumerate(rows[1:]):  # Skip header
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            company_data = {}
                            
                            # Extract text from cells
                            for k, cell in enumerate(cells):
                                text = cell.text.strip()
                                if k == 0 and text and re.match(r'^[A-Z]{1,5}$', text):
                                    company_data['symbol'] = text
                                elif k == 1 and text:
                                    company_data['company_name'] = text
                                elif k == reported_revenue_col and text and reported_revenue_col > -1:
                                    # This is the reported revenue column
                                    company_data['reported_revenue'] = text
                                elif k > 1 and text:
                                    company_data[f'cell_{k}'] = text
                            
                            if company_data:
                                company_data['source'] = f'table_{i+1}_row_{j+1}'
                                companies.append(company_data)
                                self.debug_print(f"Found company from table: {company_data}")
                                
                except Exception as e:
                    self.debug_print(f"Error processing table {i+1}: {e}")
                    
        except Exception as e:
            self.debug_print(f"Error extracting from tables: {e}")
        
        return companies
    
    def extract_from_divs(self):
        """Extract data from div elements with specific classes"""
        companies = []
        try:
            # Look for common class patterns
            selectors = [
                "*[class*='company']",
                "*[class*='earnings']",
                "*[class*='symbol']",
                "*[class*='ticker']",
                "*[class*='eps']",
                "*[id*='company']",
                "*[id*='earnings']",
                "*[class*='cal']",
                ".stock",
                ".earning"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.debug_print(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if text:
                                # Try to extract symbol from text
                                symbol_match = re.search(r'\b([A-Z]{1,5})\b', text)
                                if symbol_match:
                                    company_data = {
                                        'symbol': symbol_match.group(1),
                                        'raw_text': text,
                                        'source': selector
                                    }
                                    companies.append(company_data)
                                    self.debug_print(f"Found company from div: {company_data}")
                                    
                        except Exception as e:
                            self.debug_print(f"Error processing element: {e}")
                            
                except Exception as e:
                    self.debug_print(f"Error with selector {selector}: {e}")
                    
        except Exception as e:
            self.debug_print(f"Error extracting from divs: {e}")
        
        return companies
    
    def extract_from_data_attributes(self):
        """Extract data from elements with data attributes"""
        companies = []
        try:
            # Look for data attributes
            selectors = [
                "[data-symbol]",
                "[data-company]",
                "[data-ticker]",
                "[data-eps]",
                "[data-earnings]"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.debug_print(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            company_data = {}
                            
                            # Extract data attributes
                            for attr in ['data-symbol', 'data-company', 'data-ticker', 'data-eps', 'data-earnings']:
                                value = element.get_attribute(attr)
                                if value:
                                    company_data[attr.replace('data-', '')] = value
                            
                            if company_data:
                                company_data['source'] = selector
                                companies.append(company_data)
                                self.debug_print(f"Found company from data attributes: {company_data}")
                                
                        except Exception as e:
                            self.debug_print(f"Error processing data attribute element: {e}")
                            
                except Exception as e:
                    self.debug_print(f"Error with data selector {selector}: {e}")
                    
        except Exception as e:
            self.debug_print(f"Error extracting from data attributes: {e}")
        
        return companies
    
    def extract_from_text_patterns(self):
        """Extract data using text pattern matching"""
        companies = []
        try:
            # Get all text content from the body
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for stock ticker patterns in context
            lines = body_text.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    # Look for patterns like "AAPL - Apple Inc." or "MSFT $2.50"
                    ticker_matches = re.findall(r'\b([A-Z]{1,5})\b', line)
                    
                    # Filter out common false positives
                    false_positives = {
                        'AM', 'PM', 'EST', 'PST', 'GMT', 'UTC', 'USD', 'CEO', 'CFO', 'EPS', 
                        'Q1', 'Q2', 'Q3', 'Q4', 'THE', 'AND', 'FOR', 'BUT', 'NOT', 'YOU',
                        'ALL', 'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET',
                        'USE', 'MAN', 'NEW', 'NOW', 'WAY', 'MAY', 'SAY', 'SUN', 'MON', 'TUE',
                        'WED', 'THU', 'FRI', 'SAT', 'JAN', 'FEB', 'MAR', 'APR', 'JUN', 'JUL',
                        'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'TOP', 'END', 'KEY', 'OPEN', 'BMO',
                        'AMC', 'TBD', 'NONE', 'VIEW', 'LIST', 'ONLY', 'ET', 'PT', 'CT', 'MT'
                    }
                    
                    valid_tickers = [t for t in ticker_matches if t not in false_positives]
                    
                    for ticker in valid_tickers:
                        # Additional validation - check if line has financial context
                        if any(word in line.lower() for word in ['earnings', 'eps', '$', 'revenue', 'profit', 'consensus', 'estimate', 'whisper']):
                            company_data = {
                                'symbol': ticker,
                                'context_line': line,
                                'source': 'text_pattern'
                            }
                            companies.append(company_data)
                            self.debug_print(f"Found company from text: {company_data}")
                            
        except Exception as e:
            self.debug_print(f"Error extracting from text patterns: {e}")
        
        return companies
    
    def extract_from_page_source(self):
        """Extract data from raw page source"""
        companies = []
        try:
            page_source = self.driver.page_source
            
            # Look for JSON data patterns
            json_patterns = [
                r'"symbol"\s*:\s*"([A-Z]{1,5})"',
                r'"ticker"\s*:\s*"([A-Z]{1,5})"',
                r'"Symbol"\s*:\s*"([A-Z]{1,5})"'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, page_source)
                for match in matches:
                    company_data = {
                        'symbol': match,
                        'source': 'page_source_json'
                    }
                    companies.append(company_data)
                    self.debug_print(f"Found company from page source: {company_data}")
            
            # Look for JavaScript function calls with stock symbols
            js_patterns = [
                r'getcalctrls\(["\'](\d{8})["\']',  # Date extraction
                r'adddownload\(["\'](\d{8})["\']'    # Download function
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, page_source)
                self.debug_print(f"Found JS pattern matches: {matches}")
                
        except Exception as e:
            self.debug_print(f"Error extracting from page source: {e}")
        
        return companies
    
    def extract_from_ew_patterns(self):
        """Extract data using EarningsWhispers-specific patterns"""
        companies = []
        try:
            # Look for specific EarningsWhispers calendar patterns
            # Check for calendar grid or list structures
            ew_selectors = [
                "[id*='showcal']",
                "[class*='showcal']",
                "[id*='calctrl']",
                "[class*='calendar']",
                ".showlist",
                "#showcal"
            ]
            
            for selector in ew_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.debug_print(f"Found {len(elements)} EW-specific elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Get inner HTML to look for calendar data
                            inner_html = element.get_attribute('innerHTML')
                            
                            # Look for stock symbols in the calendar content
                            symbol_matches = re.findall(r'\b([A-Z]{2,5})\b', inner_html)
                            
                            false_positives = {
                                'HTML', 'DIV', 'SPAN', 'CLASS', 'STYLE', 'HREF', 'SRC', 'ALT',
                                'TEXT', 'FONT', 'SIZE', 'COLOR', 'BOLD', 'LINK', 'BUTTON',
                                'FORM', 'INPUT', 'TABLE', 'TBODY', 'THEAD', 'CELL', 'ROW',
                                'AM', 'PM', 'ET', 'PT', 'CT', 'MT', 'EST', 'PST', 'GMT', 'UTC'
                            }
                            
                            valid_symbols = [s for s in symbol_matches if s not in false_positives]
                            
                            for symbol in valid_symbols:
                                company_data = {
                                    'symbol': symbol,
                                    'source': f'ew_pattern_{selector}',
                                    'raw_html': inner_html[:200]  # First 200 chars for context
                                }
                                companies.append(company_data)
                                self.debug_print(f"Found company from EW pattern: {company_data}")
                                
                        except Exception as e:
                            self.debug_print(f"Error processing EW element: {e}")
                            
                except Exception as e:
                    self.debug_print(f"Error with EW selector {selector}: {e}")
                    
        except Exception as e:
            self.debug_print(f"Error extracting from EW patterns: {e}")
        
        return companies
    
    def deduplicate_companies(self, companies):
        """Remove duplicate companies and clean the data"""
        symbol_to_best_company = {}
        
        for company in companies:
            symbol = company.get('symbol', '').upper().strip()
            
            # Skip if symbol is invalid
            if not symbol or len(symbol) > 5:
                continue
                
            # Additional validation - must be valid stock symbol format
            if not re.match(r'^[A-Z]{1,5}$', symbol):
                continue
                
            # Skip common false positives that might have slipped through
            false_positives = {
                'AM', 'PM', 'ET', 'PT', 'CT', 'MT', 'EST', 'PST', 'GMT', 'UTC',
                'HTML', 'DIV', 'SPAN', 'CLASS', 'STYLE', 'HREF', 'SRC', 'ALT',
                'TEXT', 'FONT', 'SIZE', 'COLOR', 'BOLD', 'LINK', 'BUTTON',
                'FORM', 'INPUT', 'TABLE', 'TBODY', 'THEAD', 'CELL', 'ROW',
                'CEO', 'CFO', 'EPS', 'Q1', 'Q2', 'Q3', 'Q4', 'THE', 'AND',
                'FOR', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD', 'HER', 'WAS',
                'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'USE', 'MAN', 'NEW', 'NOW',
                'WAY', 'MAY', 'SAY', 'TOP', 'END', 'KEY', 'OPEN', 'BMO', 'AMC',
                'TBD', 'NONE', 'VIEW', 'LIST', 'ONLY'
            }
            
            if symbol in false_positives:
                continue
            
            # Calculate data richness score for this company
            data_score = self.calculate_data_richness(company)
            
            # Keep the best version (highest data score) for each symbol
            if symbol not in symbol_to_best_company or data_score > symbol_to_best_company[symbol]['score']:
                symbol_to_best_company[symbol] = {
                    'company': company,
                    'score': data_score
                }
        
        # Process the best companies
        unique_companies = []
        for symbol, best_data in symbol_to_best_company.items():
            company = best_data['company']
            
            # Clean up the company data
            cleaned_company = {
                'symbol': symbol,
                'source': company.get('source', 'unknown')
            }
            
            # Add other fields if they exist and are meaningful
            if 'company_name' in company and company['company_name']:
                cleaned_company['company_name'] = company['company_name'].strip()
            if 'raw_text' in company and company['raw_text'] and len(company['raw_text']) < 500:
                cleaned_company['raw_text'] = company['raw_text'].strip()
            if 'context_line' in company and company['context_line']:
                cleaned_company['context_line'] = company['context_line'].strip()
                
            # Extract financial data from raw text
            financial_data = self.extract_financial_data(company)
            if financial_data:
                cleaned_company.update(financial_data)
                
            unique_companies.append(cleaned_company)
            
        self.debug_print(f"Deduplicated from {len(companies)} to {len(unique_companies)} companies")
        return unique_companies
    
    def calculate_data_richness(self, company):
        """Calculate how much useful data a company entry contains"""
        score = 0
        
        # Score based on presence of fields
        if 'company_name' in company and company['company_name']:
            score += 10
        if 'reported_revenue' in company and company['reported_revenue']:
            score += 100  # High priority for reported revenue
        if 'raw_text' in company and company['raw_text']:
            score += len(company['raw_text'])  # Longer text = more data
        if 'context_line' in company and company['context_line']:
            score += len(company['context_line'])
        
        # Bonus for financial indicators
        text_content = ' '.join([
            company.get('raw_text', ''),
            company.get('context_line', ''),
            company.get('company_name', ''),
            company.get('reported_revenue', '')
        ]).lower()
        
        if 'reported revenue' in text_content:
            score += 80  # Higher priority for reported revenue
        elif 'revenue' in text_content and 'estimate' not in text_content:
            score += 50  # Regular revenue but not estimate
        elif 'revenue' in text_content:
            score += 20  # Revenue estimate (lower priority)
            
        if 'bil' in text_content or 'million' in text_content:
            score += 30
        if '%' in text_content:
            score += 20
        if 'earnings' in text_content:
            score += 20
        
        return score
    
    def load_tracking_list(self):
        """Load the tracking list from tracking_list.txt"""
        tracking_list = set()
        tracking_file = "tracking_list.txt"
        
        try:
            if os.path.exists(tracking_file):
                with open(tracking_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip().upper()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            tracking_list.add(line)
                            
                self.debug_print(f"Loaded {len(tracking_list)} symbols from tracking list: {sorted(tracking_list)}")
            else:
                self.debug_print("No tracking_list.txt file found - using empty tracking list")
                
        except Exception as e:
            self.debug_print(f"Error loading tracking list: {e}")
            
        return tracking_list
    
    def extract_financial_data(self, company):
        """Extract revenue and growth data from company text"""
        financial_data = {}
        
        # Get all text sources
        text_sources = []
        if 'raw_text' in company:
            text_sources.append(company['raw_text'])
        if 'context_line' in company:
            text_sources.append(company['context_line'])
        if 'company_name' in company:
            text_sources.append(company['company_name'])
        if 'reported_revenue' in company:
            text_sources.append(f"Reported Revenue: {company['reported_revenue']}")
        
        combined_text = ' '.join(text_sources)
        
        # Extract revenue (prioritize "Reported Revenue" over "Revenue Estimate")
        revenue_patterns = [
            # First try to find "Reported Revenue" specifically
            r'Reported Revenue:\s*\$?([0-9,]+(?:\.[0-9]+)?)\s*(Bil|Billion|B)',
            r'Reported Revenue:\s*\$?([0-9,]+(?:\.[0-9]+)?)\s*(Mil|Million|M)',
            r'Reported\s+Revenue[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(Bil|Billion|B)',
            r'Reported\s+Revenue[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(Mil|Million|M)',
            # Fallback to general revenue patterns (avoiding "Estimate")
            r'Revenue:\s*\$?([0-9,]+(?:\.[0-9]+)?)\s*(Bil|Billion|B)(?!\s*Estimate)',
            r'Revenue:\s*\$?([0-9,]+(?:\.[0-9]+)?)\s*(Mil|Million|M)(?!\s*Estimate)',
            r'\$([0-9,]+(?:\.[0-9]+)?)\s*(Bil|Billion|B)(?!\s*Estimate)',
            r'\$([0-9,]+(?:\.[0-9]+)?)\s*(Mil|Million|M)(?!\s*Estimate)',
            r'([0-9,]+(?:\.[0-9]+)?)\s*(Bil|Billion|B)\s*Revenue(?!\s*Estimate)',
            r'([0-9,]+(?:\.[0-9]+)?)\s*(Mil|Million|M)\s*Revenue(?!\s*Estimate)'
        ]
        
        for pattern in revenue_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                unit = match.group(2).lower()
                
                # Convert to millions
                if unit.startswith('bil') or unit == 'b':
                    revenue_millions = amount * 1000
                else:  # mil, million, m
                    revenue_millions = amount
                    
                financial_data['revenue_millions'] = revenue_millions
                financial_data['revenue_raw'] = match.group(0)
                break
        
        # Extract growth rate
        growth_patterns = [
            r'([+-]?[0-9]+(?:\.[0-9]+)?)\s*%',
            r'([+-]?[0-9]+(?:\.[0-9]+)?)\s*percent',
            r'growth:\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%'
        ]
        
        for pattern in growth_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                growth_rate = float(match.group(1))
                financial_data['growth_rate'] = growth_rate
                financial_data['growth_raw'] = match.group(0)
                break
        
        return financial_data if financial_data else None
    
    def filter_companies_by_criteria(self, companies, tracking_list=None):
        """Filter companies based on revenue and growth criteria"""
        filtered_companies = []
        
        if tracking_list is None:
            tracking_list = set()
        else:
            tracking_list = set(symbol.upper().strip() for symbol in tracking_list)
        
        for company in companies:
            symbol = company.get('symbol', '')
            revenue = company.get('revenue_millions', 0)
            growth = company.get('growth_rate', 0)
            
            # Check if company is in tracking list
            if symbol in tracking_list:
                self.debug_print(f"{symbol}: In tracking list")
                filtered_companies.append(self.format_filtered_company(company, reason="tracking_list"))
                continue
            
            # Apply revenue and growth criteria
            if self.meets_criteria(revenue, growth):
                self.debug_print(f"{symbol}: Meets criteria - Revenue: ${revenue}M, Growth: {growth}%")
                filtered_companies.append(self.format_filtered_company(company, reason="revenue_growth_criteria"))
            else:
                self.debug_print(f"{symbol}: Does not meet criteria - Revenue: ${revenue}M, Growth: {growth}%")
        
        return filtered_companies
    
    def meets_criteria(self, revenue, growth):
        """Check if company meets any of the filtering criteria"""
        criteria = [
            (10, 50),      # >10M revenue and >50% growth
            (100, 30),     # >100M revenue and >30% growth  
            (500, 25),     # >500M revenue and >25% growth
            (1000, 20),    # >1000M revenue and >20% growth
            (5000, 15),    # >5000M revenue and >15% growth
        ]
        
        for min_revenue, min_growth in criteria:
            if revenue > min_revenue and growth > min_growth:
                return True
        
        return False
    
    def format_filtered_company(self, company, reason="unknown"):
        """Format company data for filtered output"""
        return {
            'ticker': company.get('symbol', ''),
            'name': company.get('company_name', ''),
            'revenue_millions': company.get('revenue_millions', 0),
            'revenue_raw': company.get('revenue_raw', ''),
            'growth_rate': company.get('growth_rate', 0),
            'growth_raw': company.get('growth_raw', ''),
            'source': company.get('source', ''),
            'filter_reason': reason
        }
    
    def save_to_file(self, data, filename):
        """Save scraped data to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving to file: {e}")
    
    def close(self):
        """Close the WebDriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()


def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        scraper = EarningsSeleniumScraper(headless=False, debug=True)  # Set headless=False to see browser
        
        # Try both the original date and a more recent date for comparison
        test_dates = ["20250714", "20241201"]  # Future date and recent past date
        
        for date_str in test_dates:
            print(f"\n{'='*50}")
            print(f"Testing scraper for {date_str}")
            print(f"{'='*50}")
            
            data = scraper.scrape_calendar(date_str)
            
            if data:
                print(f"Status: {data.get('status', 'unknown')}")
                if 'message' in data:
                    print(f"Message: {data['message']}")
                
                companies = data.get('companies', [])
                print(f"Total companies found: {len(companies)}")
                
                # Save to file
                filename = f"earnings_calendar_final_{date_str}.json"
                scraper.save_to_file(data, filename)
                
                # Print summary
                print(f"\n=== EARNINGS CALENDAR SUMMARY for {date_str} ===")
                
                if len(companies) > 0:
                    # Remove duplicates for display
                    unique_companies = {}
                    for company in companies:
                        symbol = company.get('symbol', 'N/A')
                        if symbol not in unique_companies:
                            unique_companies[symbol] = company
                    
                    for i, (symbol, company) in enumerate(list(unique_companies.items())[:10]):
                        print(f"  - {symbol}: {company.get('company_name', company.get('context_line', 'N/A'))}")
                    
                    if len(unique_companies) > 10:
                        print(f"  ... and {len(unique_companies) - 10} more unique companies")
                else:
                    print("  No companies found - this may be expected for future dates")
                    
            else:
                print("Failed to scrape data")
            
            print(f"{'='*50}\n")
            
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main() 