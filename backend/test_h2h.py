from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.sofascore.com/api/v1/team/2817/events/last/0")
    print(page.content()[:500])
    browser.close()
