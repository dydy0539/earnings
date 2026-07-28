#!/usr/bin/env python3
"""
Reusable scraping helpers for projects that need either:
- Selenium-driven browser scraping for JavaScript-heavy pages.
- requests + BeautifulSoup fetching for static HTML pages.

Project-specific scrapers should subclass one of these base classes and keep
site-specific parsing logic in their own module.
"""

from __future__ import annotations

import time
from typing import Dict, Iterable, Optional

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class SeleniumScraperBase:
    """Base class for Selenium scrapers.

    This class owns ChromeDriver setup, basic navigation, common waits, debug
    logging, page-source saving, and cleanup. Subclasses should implement the
    website-specific parsing and workflow.
    """

    def __init__(
        self,
        headless: bool = True,
        debug: bool = False,
        wait_timeout: int = 30,
        user_agent: str = DEFAULT_USER_AGENT,
        window_size: str = "1920,1080",
        extra_chrome_args: Optional[Iterable[str]] = None,
    ):
        self.debug = debug
        self.wait_timeout = wait_timeout
        self.user_agent = user_agent
        self.window_size = window_size
        self.extra_chrome_args = list(extra_chrome_args or [])
        self.setup_driver(headless=headless)

    def debug_print(self, message: str) -> None:
        """Print debug messages when debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def build_chrome_options(self, headless: bool) -> Options:
        """Build Chrome options shared across Selenium scraping projects."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--window-size={self.window_size}")
        chrome_options.add_argument(f"--user-agent={self.user_agent}")

        for arg in self.extra_chrome_args:
            chrome_options.add_argument(arg)

        return chrome_options

    def setup_driver(self, headless: bool) -> None:
        """Initialize ChromeDriver using webdriver-manager."""
        try:
            chrome_options = self.build_chrome_options(headless=headless)
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            self.debug_print("Successfully initialized ChromeDriver with webdriver-manager")
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print("Please make sure Chrome browser is installed")
            raise

    def open_page(self, url: str) -> None:
        """Navigate the browser to a URL."""
        self.debug_print(f"Navigating to {url}")
        self.driver.get(url)

    def wait_for_body(self) -> None:
        """Wait until the document body is present."""
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    def click_first_available(
        self,
        css_selectors: Iterable[str],
        wait_after_click: float = 2.0,
    ) -> bool:
        """Click the first visible/enabled element matching any CSS selector."""
        for selector in css_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        self.debug_print(f"Clicking element for selector: {selector}")
                        element.click()
                        time.sleep(wait_after_click)
                        return True
            except Exception as e:
                self.debug_print(f"Selector {selector} failed: {e}")
        return False

    def save_page_source(self, filename: str) -> None:
        """Save the current page source for debugging."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        self.debug_print(f"Saved page source to {filename}")

    def close(self, force: bool = False) -> None:
        """Close the WebDriver."""
        if hasattr(self, "driver"):
            self.driver.quit()


class RequestsScraperBase:
    """Base class for static HTML scraping with requests + BeautifulSoup."""

    def __init__(
        self,
        debug: bool = False,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ):
        self.debug = debug
        self.timeout = timeout
        self.headers = headers or {"User-Agent": DEFAULT_USER_AGENT}
        self.session = requests.Session()

    def debug_print(self, message: str) -> None:
        """Print debug messages when debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def fetch(self, url: str) -> requests.Response:
        """Fetch a URL and raise for non-success status codes."""
        self.debug_print(f"Fetching {url}")
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response

    def fetch_soup(self, url: str, parser: str = "html.parser") -> BeautifulSoup:
        """Fetch a URL and return a BeautifulSoup document."""
        response = self.fetch(url)
        return BeautifulSoup(response.content, parser)
