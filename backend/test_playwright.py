from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    response = page.goto("https://www.sofascore.com/api/v1/search/all?q=Saipa")
    print(response.status)
    print(page.content()[:200])
    browser.close()
