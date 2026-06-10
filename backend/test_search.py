from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    response = page.goto("https://www.sofascore.com/api/v1/search/all?q=Real%20Madrid%20Barcelona")
    data = json.loads(page.content()[page.content().find('{'):page.content().rfind('}')+1])
    for res in data.get('results', []):
        if res['type'] == 'event':
            print(res['entity']['id'], res['entity']['homeTeam']['name'], res['entity']['awayTeam']['name'])
            break
    browser.close()
