#!/usr/bin/env python3
"""
Selenium Browser Agent for Claude Code
Uses undetected-chromedriver for reliable browser automation

Usage:
    python3 selenium_browser.py navigate "https://example.com"
    python3 selenium_browser.py screenshot output.png
    python3 selenium_browser.py click "button#submit"
    python3 selenium_browser.py type "input#email" "test@example.com"
    python3 selenium_browser.py get_text "h1"
    python3 selenium_browser.py close
"""

import sys
import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Global driver instance
_driver = None

def get_driver():
    """Get or create Chrome driver using undetected-chromedriver"""
    global _driver

    if _driver is not None:
        try:
            _driver.current_url  # Check if still alive
            return _driver
        except:
            _driver = None

    # Create new Chrome instance with undetected-chromedriver
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless=new")  # Headless mode

    _driver = uc.Chrome(options=options, use_subprocess=True)
    return _driver

def navigate(url):
    """Navigate to URL"""
    driver = get_driver()
    driver.get(url)
    time.sleep(1)  # Wait for page load
    return {"status": "ok", "url": driver.current_url, "title": driver.title}

def screenshot(filename="screenshot.png"):
    """Take screenshot"""
    driver = get_driver()
    driver.save_screenshot(filename)
    return {"status": "ok", "file": filename}

def click(selector):
    """Click element by CSS selector"""
    driver = get_driver()
    try:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()
        return {"status": "ok", "selector": selector}
    except TimeoutException:
        return {"status": "error", "message": f"Element not found: {selector}"}

def type_text(selector, text, clear=True):
    """Type text into element"""
    driver = get_driver()
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        if clear:
            element.clear()
        element.send_keys(text)
        return {"status": "ok", "selector": selector, "text": text}
    except TimeoutException:
        return {"status": "error", "message": f"Element not found: {selector}"}

def get_text(selector):
    """Get text from element"""
    driver = get_driver()
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return {"status": "ok", "selector": selector, "text": element.text}
    except TimeoutException:
        return {"status": "error", "message": f"Element not found: {selector}"}

def get_page_source():
    """Get page HTML source"""
    driver = get_driver()
    return {"status": "ok", "html": driver.page_source[:50000]}  # Limit size

def get_snapshot():
    """Get page structure (simplified)"""
    driver = get_driver()

    # Get basic page info
    info = {
        "url": driver.current_url,
        "title": driver.title,
        "links": [],
        "buttons": [],
        "inputs": [],
        "headings": []
    }

    # Get links
    for el in driver.find_elements(By.TAG_NAME, "a")[:20]:
        try:
            info["links"].append({
                "text": el.text[:100] if el.text else "",
                "href": el.get_attribute("href")
            })
        except:
            pass

    # Get buttons
    for el in driver.find_elements(By.CSS_SELECTOR, "button, input[type='submit']")[:10]:
        try:
            info["buttons"].append({
                "text": el.text or el.get_attribute("value") or "",
                "id": el.get_attribute("id"),
                "class": el.get_attribute("class")
            })
        except:
            pass

    # Get inputs
    for el in driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")[:15]:
        try:
            info["inputs"].append({
                "type": el.get_attribute("type"),
                "name": el.get_attribute("name"),
                "id": el.get_attribute("id"),
                "placeholder": el.get_attribute("placeholder")
            })
        except:
            pass

    # Get headings
    for el in driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3")[:10]:
        try:
            info["headings"].append(el.text[:200])
        except:
            pass

    return {"status": "ok", "snapshot": info}

def close_browser():
    """Close browser"""
    global _driver
    if _driver:
        _driver.quit()
        _driver = None
    return {"status": "ok", "message": "Browser closed"}

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "navigate": lambda: navigate(args[0]) if args else {"error": "URL required"},
        "screenshot": lambda: screenshot(args[0] if args else "screenshot.png"),
        "click": lambda: click(args[0]) if args else {"error": "Selector required"},
        "type": lambda: type_text(args[0], args[1]) if len(args) >= 2 else {"error": "Selector and text required"},
        "get_text": lambda: get_text(args[0]) if args else {"error": "Selector required"},
        "get_source": get_page_source,
        "snapshot": get_snapshot,
        "close": close_browser,
    }

    if command in commands:
        result = commands[command]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

if __name__ == "__main__":
    main()
