import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Toggle this to False to skip Sofascore live requests and use local cache only
USE_LIVE_SCRAPING = True 

def get_json_from_page(page, url):
    page.goto(url)
    content = page.content()
    start = content.find('{')
    end = content.rfind('}') + 1
    if start != -1 and end != 0:
        try:
            return json.loads(content[start:end])
        except:
            return None
    return None

# ── Formation Classifier ───────────────────────────────────────
def classify_formation(formation_str):
    """
    Returns: 0=Defensive (5-back/park-the-bus)
             1=Balanced (4-4-2, 4-3-3)
             2=Attacking (3-4-3, 3-5-2)
    """
    if not formation_str:
        return 1
    parts = [int(x) for x in re.findall(r'\d+', formation_str)]
    if not parts:
        return 1
    defenders = parts[0]
    forwards  = parts[-1]
    if defenders >= 5 or forwards <= 1:
        return 0  # defensive
    elif forwards >= 3 or defenders <= 3:
        return 2  # attacking
    return 1      # balanced

# ── Team Player Ratings from Last N Match Lineups ─────────────
def fetch_team_player_data(page, team_id, events, n=3):
    """
    Scrapes the last n match lineups for a team and computes:
    - avg_player_rating   (mean Sofascore rating of outfield starters)
    - top_player_rating   (best individual starter rating)
    - formation_type      (0/1/2)
    - last_formation      (e.g. "4-3-3")
    """
    ratings_pool = []
    top_ratings  = []
    formations   = []
    count = 0

    for ev in events:
        if ev.get('status', {}).get('type') != 'finished':
            continue
        eid     = ev.get('id')
        home_id = ev.get('homeTeam', {}).get('id')
        side    = 'home' if home_id == team_id else 'away'

        lineup_data = get_json_from_page(page, f"https://www.sofascore.com/api/v1/event/{eid}/lineups")
        if not lineup_data:
            continue

        team_lineup = lineup_data.get(side, {})
        formation   = team_lineup.get('formation', '')
        players     = team_lineup.get('players', [])

        match_ratings = []
        for pl in players:
            # Only outfield starters (not substitutes)
            if pl.get('substitute', True):
                continue
            rating = pl.get('statistics', {}).get('rating')
            if rating:
                match_ratings.append(float(rating))

        if match_ratings:
            ratings_pool.append(sum(match_ratings) / len(match_ratings))
            top_ratings.append(max(match_ratings))
        if formation:
            formations.append(formation)

        count += 1
        if count >= n:
            break

    if not ratings_pool:
        return None

    last_formation = formations[0] if formations else '4-4-2'
    return {
        'avg_player_rating': round(sum(ratings_pool) / len(ratings_pool), 3),
        'top_player_rating': round(sum(top_ratings) / len(top_ratings), 3),
        'formation':         last_formation,
        'formation_type':    classify_formation(last_formation),
    }

# ── Per-Team Rolling Stats ────────────────────────────────────
def parse_team_events(events, team_id, num_matches=10):
    results = []
    for ev in events:
        if ev.get('status', {}).get('type') != 'finished':
            continue
        h_score = ev.get('homeScore', {}).get('display', 0) or 0
        a_score = ev.get('awayScore', {}).get('display', 0) or 0
        home_id = ev.get('homeTeam', {}).get('id')
        total   = h_score + a_score
        if home_id == team_id:
            scored, conceded = h_score, a_score
            result = 'W' if h_score > a_score else ('D' if h_score == a_score else 'L')
        else:
            scored, conceded = a_score, h_score
            result = 'W' if a_score > h_score else ('D' if a_score == h_score else 'L')

        results.append({
            'total_goals': total, 'scored': scored, 'conceded': conceded,
            'result': result, 'btts': h_score > 0 and a_score > 0,
            'clean_sheet': conceded == 0,
        })
        if len(results) == num_matches:
            break

    if not results:
        return None
    n = len(results)
    return {
        'matches_analyzed':  n,
        'avg_total_goals':   round(sum(r['total_goals'] for r in results) / n, 2),
        'avg_scored':        round(sum(r['scored'] for r in results) / n, 2),
        'avg_conceded':      round(sum(r['conceded'] for r in results) / n, 2),
        'win_rate':          round(sum(1 for r in results if r['result'] == 'W') / n, 3),
        'draw_rate':         round(sum(1 for r in results if r['result'] == 'D') / n, 3),
        'btts_rate':         round(sum(1 for r in results if r['btts']) / n, 3),
        'clean_sheet_rate':  round(sum(1 for r in results if r['clean_sheet']) / n, 3),
        'over_2_5_rate':     round(sum(1 for r in results if r['total_goals'] > 2) / n, 3),
        'under_2_5_rate':    round(sum(1 for r in results if r['total_goals'] < 3) / n, 3),
    }

# ── H2H Stats ─────────────────────────────────────────────────
def parse_h2h_events(events, num_matches=10):
    results = []
    for ev in events:
        if ev.get('status', {}).get('type') != 'finished':
            continue
        h = ev.get('homeScore', {}).get('display', 0) or 0
        a = ev.get('awayScore', {}).get('display', 0) or 0
        results.append({'total_goals': h + a, 'btts': h > 0 and a > 0})
        if len(results) == num_matches:
            break

    if not results:
        return None
    n = len(results)
    return {
        'matches_analyzed': n,
        'avg_total_goals':  round(sum(r['total_goals'] for r in results) / n, 2),
        'btts_rate':        round(sum(1 for r in results if r['btts']) / n, 3),
        'over_2_5_rate':    round(sum(1 for r in results if r['total_goals'] > 2) / n, 3),
        'under_2_5_rate':   round(sum(1 for r in results if r['total_goals'] < 3) / n, 3),
        'under_3_5_rate':   round(sum(1 for r in results if r['total_goals'] < 4) / n, 3),
        'over_3_5_rate':    round(sum(1 for r in results if r['total_goals'] > 3) / n, 3),
    }

# ── Master Fetch Function ─────────────────────────────────────
def fetch_all_match_data(home_team_name: str, away_team_name: str):
    """
    Full intelligence fetch:
    - Last 10 matches per team (goals, results, BTTS, clean sheets)
    - Player ratings + formation from last 3 match lineups
    - H2H meeting history
    """
    cache_key = f"{home_team_name}_{away_team_name}".replace(" ", "_").lower()
    cache_file = os.path.join(CACHE_DIR, f"match_{cache_key}.json")
    
    # 6 hour cache for specific matchups
    if os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < 21600:
        with open(cache_file, 'r') as f:
            return json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        Stealth().apply_stealth_sync(page)

        if not USE_LIVE_SCRAPING:
            # If scraping is disabled and no cache exists, return an empty but safe structure
            # to be filled by the Intelligence Layer / Local Dataset later
            browser.close()
            return data

        data = {
            "home": {"name": home_team_name, "id": None, "found": False, "stats": None, "player_data": None},
            "away": {"name": away_team_name, "id": None, "found": False, "stats": None, "player_data": None},
            "h2h": None, "event_id": None,
        }

        # ── Home Team ─────────────────────────────────────────
        home_search = get_json_from_page(page, f"https://www.sofascore.com/api/v1/search/all?q={home_team_name}")
        if home_search:
            for res in home_search.get('results', []):
                if res.get('type') == 'team':
                    tid = res['entity']['id']
                    data['home']['id']   = tid
                    data['home']['name'] = res['entity']['name']
                    data['home']['found'] = True
                    events_data = get_json_from_page(page, f"https://www.sofascore.com/api/v1/team/{tid}/events/last/0")
                    if events_data and events_data.get('events'):
                        evs = events_data['events']
                        data['home']['stats']       = parse_team_events(evs, tid, 10)
                        data['home']['player_data'] = fetch_team_player_data(page, tid, evs, n=3)
                    break

        # ── Away Team ─────────────────────────────────────────
        away_search = get_json_from_page(page, f"https://www.sofascore.com/api/v1/search/all?q={away_team_name}")
        if away_search:
            for res in away_search.get('results', []):
                if res.get('type') == 'team':
                    tid = res['entity']['id']
                    data['away']['id']   = tid
                    data['away']['name'] = res['entity']['name']
                    data['away']['found'] = True
                    events_data = get_json_from_page(page, f"https://www.sofascore.com/api/v1/team/{tid}/events/last/0")
                    if events_data and events_data.get('events'):
                        evs = events_data['events']
                        data['away']['stats']       = parse_team_events(evs, tid, 10)
                        data['away']['player_data'] = fetch_team_player_data(page, tid, evs, n=3)
                    break

        # ── H2H ───────────────────────────────────────────────
        if data['home']['found'] and data['away']['found']:
            q = f"{home_team_name} {away_team_name}"
            matchup_search = get_json_from_page(page, f"https://www.sofascore.com/api/v1/search/all?q={q}")
            if matchup_search:
                for res in matchup_search.get('results', []):
                    if res.get('type') == 'event':
                        eid  = res['entity']['id']
                        data['event_id'] = eid
                        h2h  = get_json_from_page(page, f"https://www.sofascore.com/api/v1/event/{eid}/h2h/events")
                        if h2h and h2h.get('events'):
                            data['h2h'] = parse_h2h_events(h2h['events'], 10)
                        break

        browser.close()
        
        with open(cache_file, 'w') as f:
            json.dump(data, f)
            
        return data

# ── Upcoming Matches Fetcher ───────────────────────────────────
def fetch_today_matches():
    """Fetches today's football matches from ESPN's public API to avoid Cloudflare blocks."""
    from datetime import datetime
    import requests
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    cache_file = os.path.join(CACHE_DIR, f"upcoming_{date_str}.json")
    
    # 1 hour cache for upcoming matches
    if os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < 3600:
        with open(cache_file, 'r') as f:
            return json.load(f)

    url = "http://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            return []
        
        data = res.json()
        events = data.get('events', [])
        
        result = []
        for ev in events:
            comp = ev.get('competitions', [{}])[0]
            competitors = comp.get('competitors', [])
            
            home = next((c['team']['name'] for c in competitors if c.get('homeAway') == 'home'), None)
            away = next((c['team']['name'] for c in competitors if c.get('homeAway') == 'away'), None)
            
            # Extract league from the top-level leagues array if possible, else fallback to season slug
            league_name = ev.get('season', {}).get('slug', 'Unknown League').replace('-', ' ').title()
            
            # Optionally check if there's a note or exact league name inside competitions
            notes = ev.get('competitions', [{}])[0].get('notes', [])
            if notes and isinstance(notes, list):
                league_name = notes[0].get('headline', league_name)

            if home and away:
                result.append({
                    "home_team": home,
                    "away_team": away,
                    "tournament": league_name,
                    "priority": 1,
                    "start_timestamp": int(datetime.strptime(ev.get('date'), "%Y-%m-%dT%H:%MZ").timestamp()) if ev.get('date') else 0
                })
        
        # Sort by start time
        result.sort(key=lambda x: x['start_timestamp'])
        
        with open(cache_file, 'w') as f:
            json.dump(result, f)
            
        return result
    except Exception as e:
        print(f"Error fetching from ESPN: {e}")
        return []

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'today':
        matches = fetch_today_matches()
        for m in matches[:10]:
            print(f"{m['tournament']}: {m['home_team']} vs {m['away_team']}")
    else:
        result = fetch_all_match_data("Portugal", "Nigeria")
        print(json.dumps({k: v for k, v in result.items() if k != 'h2h'}, indent=2))
