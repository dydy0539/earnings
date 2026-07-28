#!/usr/bin/env python3
"""
Finviz Insider Trading Scraper
Scrapes the top insider trading transactions from Finviz
URL: https://finviz.com/insidertrading?or=-10&tv=100000&tc=1&o=-transactionValue
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('insider_trading_scraper.log'),
        logging.StreamHandler()
    ]
)

class InsiderTradingScraper:
    def __init__(self, debug=False, min_value=100000):
        self.debug = debug
        self.min_value = min_value
        self.url = "https://finviz.com/insidertrading?or=-10&tv=100000&tc=1&o=-transactionValue"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def debug_print(self, message):
        """Print debug messages if debug mode is enabled"""
        if self.debug:
            logging.debug(message)
    
    def parse_value(self, value_str):
        """
        Parse value string to float
        Examples: "59,040,000" -> 59040000.0, "5,246,500" -> 5246500.0
        """
        try:
            # Remove commas and convert to float
            return float(value_str.replace(',', ''))
        except (ValueError, AttributeError):
            return 0.0
    
    def get_relationship_score(self, relationship):
        """
        Assign numerical score to relationship based on importance
        
        Scoring:
        - CFO/Chief Financial Officer: 5
        - CEO/Chief Executive Officer: 4
        - Chairman/C-suite (COO, CRO, etc.): 3
        - Director: 2
        - Other: 1
        
        Args:
            relationship: String describing the insider's relationship to company
        
        Returns:
            Integer score (1-5)
        """
        if not relationship:
            return 1
        
        relationship_lower = relationship.lower()
        
        # CFO - Score 5
        if 'cfo' in relationship_lower or 'chief financial officer' in relationship_lower:
            return 5
        
        # CEO - Score 4
        if 'ceo' in relationship_lower or 'chief executive officer' in relationship_lower:
            return 4
        
        # Chairman and other C-suite - Score 3
        # Check for full phrases and specific titles
        if any(title in relationship_lower for title in [
            'chairman', 'executive chairman', 
            'chief operating officer',
            'chief revenue officer',
            'chief technology officer',
            'chief information officer',
            'chief marketing officer',
            'president',
            'chief '  # Any other "Chief X" title
        ]):
            return 3
        
        # Check for C-suite abbreviations only at word boundaries
        import re
        if re.search(r'\b(coo|cro|cto|cio|cmo)\b', relationship_lower):
            return 3
        
        # Director - Score 2
        if 'director' in relationship_lower:
            return 2
        
        # Everything else - Score 1
        return 1
    
    def filter_transactions(self, transactions, min_value=100000):
        """
        Filter transactions by minimum value
        
        Args:
            transactions: List of transaction dictionaries
            min_value: Minimum transaction value (default: 100,000)
        
        Returns:
            Filtered list of transactions
        """
        if not transactions:
            return []
        
        filtered = []
        removed_count = 0
        
        for txn in transactions:
            value = self.parse_value(txn.get('value', '0'))
            
            if value >= min_value:
                filtered.append(txn)
            else:
                removed_count += 1
                self.debug_print(f"Filtered out {txn['ticker']} - ${value:,.0f} < ${min_value:,.0f}")
        
        logging.info(f"Filtered transactions: kept {len(filtered)}, removed {removed_count} below ${min_value:,.0f}")
        return filtered
    
    def sort_by_relationship(self, transactions):
        """
        Sort transactions by relationship importance (highest score first)
        
        Args:
            transactions: List of transaction dictionaries
        
        Returns:
            Sorted list of transactions
        """
        if not transactions:
            return []
        
        # Add relationship score to each transaction for sorting
        for txn in transactions:
            txn['relationship_score'] = self.get_relationship_score(txn.get('relationship', ''))
        
        # Sort by relationship score (descending), then by value (descending)
        sorted_txns = sorted(
            transactions, 
            key=lambda x: (x['relationship_score'], self.parse_value(x.get('value', '0'))),
            reverse=True
        )
        
        logging.info(f"Sorted {len(sorted_txns)} transactions by relationship importance")
        return sorted_txns
    
    def scrape_insider_trading(self):
        """
        Scrape insider trading data from Finviz
        Returns list of transactions with all details
        """
        try:
            logging.info(f"Fetching data from {self.url}")
            
            # Make request
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            self.debug_print(f"Response status: {response.status_code}")
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the insider trading table
            # The table has class "styled-table-new" or just find the main data table
            table = soup.find('table', class_='styled-table-new')
            
            if not table:
                # Try alternative: find table with insider trading data
                tables = soup.find_all('table')
                self.debug_print(f"Found {len(tables)} tables")
                # The data table is usually one of the larger tables
                for t in tables:
                    rows = t.find_all('tr')
                    if len(rows) > 10:  # Data table should have many rows
                        table = t
                        break
            
            if not table:
                logging.error("Could not find insider trading table")
                return None
            
            # Extract table headers
            header_row = table.find('tr')
            if not header_row:
                logging.error("Could not find table headers")
                return None
            
            headers = []
            for th in header_row.find_all(['th', 'td']):
                header_text = th.get_text(strip=True)
                if header_text:
                    headers.append(header_text)
            
            self.debug_print(f"Headers: {headers}")
            
            # Extract data rows
            transactions = []
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 9:  # Should have at least 9 columns
                    continue
                
                try:
                    # Extract data from each cell
                    ticker = cells[0].get_text(strip=True)
                    owner = cells[1].get_text(strip=True)
                    relationship = cells[2].get_text(strip=True)
                    date = cells[3].get_text(strip=True)
                    transaction_type = cells[4].get_text(strip=True)
                    cost = cells[5].get_text(strip=True)
                    shares = cells[6].get_text(strip=True)
                    value = cells[7].get_text(strip=True)
                    shares_total = cells[8].get_text(strip=True)
                    
                    # Get SEC Form 4 link if available
                    sec_form_link = ""
                    sec_form_date = ""
                    if len(cells) > 9:
                        sec_link_cell = cells[9].find('a')
                        if sec_link_cell:
                            sec_form_link = sec_link_cell.get('href', '')
                            sec_form_date = cells[9].get_text(strip=True)
                    
                    transaction = {
                        'ticker': ticker,
                        'owner': owner,
                        'relationship': relationship,
                        'date': date,
                        'transaction_type': transaction_type,
                        'cost': cost,
                        'shares': shares,
                        'value': value,
                        'shares_total': shares_total,
                        'sec_form_date': sec_form_date,
                        'sec_form_link': sec_form_link
                    }
                    
                    transactions.append(transaction)
                    self.debug_print(f"Extracted: {ticker} - {owner} - {transaction_type} - ${value}")
                    
                except Exception as e:
                    logging.warning(f"Error parsing row: {e}")
                    continue
            
            logging.info(f"Successfully scraped {len(transactions)} insider transactions")
            
            # Filter transactions by minimum value
            transactions = self.filter_transactions(transactions, min_value=self.min_value)
            
            return transactions
            
        except requests.RequestException as e:
            logging.error(f"Error fetching data: {e}")
            return None
        except Exception as e:
            logging.error(f"Error scraping insider trading data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_to_json(self, transactions, filename=None):
        """Save transactions to JSON file (sorted by relationship)"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"insider_trading_{timestamp}.json"
        
        try:
            # Sort by relationship importance
            sorted_transactions = self.sort_by_relationship(transactions.copy())
            
            # Remove relationship_score field before saving (internal use only)
            for txn in sorted_transactions:
                txn.pop('relationship_score', None)
            
            data = {
                'scraped_at': datetime.now().isoformat(),
                'source': self.url,
                'total_transactions': len(sorted_transactions),
                'transactions': sorted_transactions
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Data saved to {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"Error saving JSON: {e}")
            return None
    
    def save_to_csv(self, transactions, filename=None):
        """Save transactions to CSV file (sorted by relationship)"""
        if not transactions:
            logging.warning("No transactions to save")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"insider_trading_{timestamp}.csv"
        
        try:
            # Sort by relationship importance
            sorted_transactions = self.sort_by_relationship(transactions.copy())
            
            # Remove relationship_score field before saving (internal use only)
            for txn in sorted_transactions:
                txn.pop('relationship_score', None)
            
            fieldnames = list(sorted_transactions[0].keys())
            
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(sorted_transactions)
            
            logging.info(f"Data saved to {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"Error saving CSV: {e}")
            return None
    
    def print_summary(self, transactions):
        """Print a summary of the transactions (sorted by relationship)"""
        if not transactions:
            print("No transactions found")
            return
        
        # Sort by relationship importance
        sorted_transactions = self.sort_by_relationship(transactions.copy())
        
        print("\n" + "="*120)
        print(f"INSIDER TRADING SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*120)
        print(f"{'Ticker':<8} {'Owner':<30} {'Relationship':<25} {'Date':<12} {'Type':<5} {'Value':<15} {'Shares':<12}")
        print("-"*120)
        
        for txn in sorted_transactions[:50]:  # Show first 50
            ticker = txn['ticker'][:7]
            owner = txn['owner'][:29]
            relationship = txn['relationship'][:24]
            date = txn['date']
            txn_type = txn['transaction_type']
            value = txn['value']
            shares = txn['shares']
            
            print(f"{ticker:<8} {owner:<30} {relationship:<25} {date:<12} {txn_type:<5} {value:<15} {shares:<12}")
        
        if len(sorted_transactions) > 50:
            print(f"\n... and {len(sorted_transactions) - 50} more transactions")
        
        print("="*120)
        print(f"Total transactions: {len(sorted_transactions)}")
        print(f"Sorted by: CFO (5) > CEO (4) > Chairman/C-suite (3) > Director (2) > Other (1)")
        print("="*120)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape insider trading data from Finviz')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--output', '-o', choices=['json', 'csv', 'both'], default='both', 
                       help='Output format (default: both)')
    parser.add_argument('--filename', '-f', help='Custom filename (without extension)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress summary output')
    parser.add_argument('--min-value', '-m', type=float, default=100000,
                       help='Minimum transaction value to include (default: 100000)')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = InsiderTradingScraper(debug=args.debug, min_value=args.min_value)
    
    # Scrape data
    logging.info("Starting insider trading scraper...")
    transactions = scraper.scrape_insider_trading()
    
    if not transactions:
        logging.error("Failed to scrape data")
        sys.exit(1)
    
    # Save data
    json_filename = None
    csv_filename = None
    
    if args.output in ['json', 'both']:
        json_file = f"{args.filename}.json" if args.filename else None
        json_filename = scraper.save_to_json(transactions, json_file)
    
    if args.output in ['csv', 'both']:
        csv_file = f"{args.filename}.csv" if args.filename else None
        csv_filename = scraper.save_to_csv(transactions, csv_file)
    
    # Print summary
    if not args.quiet:
        scraper.print_summary(transactions)
        print(f"\nFiles saved:")
        if json_filename:
            print(f"  - JSON: {json_filename}")
        if csv_filename:
            print(f"  - CSV: {csv_filename}")
    
    logging.info("Scraping complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
