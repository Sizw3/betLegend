import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
    "Cache-Control": "max-age=0"
}

with httpx.Client(headers=headers) as client:
    resp = client.get("https://api.sofascore.com/api/v1/search/all?q=Saipa")
    print("Status:", resp.status_code)
    try:
        print(json.dumps(resp.json())[:200])
    except Exception as e:
        print("Error:", e)
