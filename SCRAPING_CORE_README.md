# Reusable Scraping Core

`scraping_core.py` contains generalized scraping helpers that can be copied into other projects.

## SeleniumScraperBase

Use this for JavaScript-heavy websites that need a real browser.

```python
from selenium.webdriver.common.by import By
from scraping_core import SeleniumScraperBase


class MySiteScraper(SeleniumScraperBase):
    def scrape(self, url):
        self.open_page(url)
        self.wait_for_body()

        rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
        return [row.text for row in rows]


scraper = MySiteScraper(headless=True, debug=True)
try:
    data = scraper.scrape("https://example.com")
finally:
    scraper.close()
```

Included utilities:

- ChromeDriver setup via `webdriver-manager`
- Common Chrome options and user agent
- `open_page(url)` for navigation
- `wait_for_body()` for basic page readiness
- `click_first_available(selectors)` for cookie/consent buttons
- `save_page_source(filename)` for debugging
- `close()` for WebDriver cleanup

## RequestsScraperBase

Use this for static HTML websites that do not require JavaScript rendering.

```python
from scraping_core import RequestsScraperBase


class MyStaticScraper(RequestsScraperBase):
    def scrape(self, url):
        soup = self.fetch_soup(url)
        return [a.get_text(strip=True) for a in soup.select("a")]


scraper = MyStaticScraper(debug=True)
links = scraper.scrape("https://example.com")
```

Included utilities:

- Shared `requests.Session`
- Browser-like user agent
- Timeout handling
- `fetch(url)` returning a checked `Response`
- `fetch_soup(url)` returning a BeautifulSoup document

## Current Usage

`scrape_earnings_selenium_final.py` now inherits from `SeleniumScraperBase`.
The reusable browser mechanics live in `scraping_core.py`; the EarningsWhispers-specific logic remains in the earnings scraper.
