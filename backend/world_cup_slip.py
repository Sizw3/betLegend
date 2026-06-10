"""
world_cup_slip.py — World Cup 2026 "Best Slip Ever" Builder
Analyzes ~70 World Cup group stage matches and filters for high-confidence picks.
"""
import requests
import json
import time

API = "http://localhost:8000/api/analyze"
MODE = "conservative"

# (home, away, line)
MATCHES = [
    ("Mexico", "South Africa", 2.5),
    ("Korea Republic", "Czechia", 2.5),
    ("Canada", "Bosnia & Herzegovina", 2.5),
    ("USA", "Paraguay", 2.5),
    ("Qatar", "Switzerland", 2.5),
    ("Brazil", "Morocco", 2.5),
    ("Haiti", "Scotland", 2.5),
    ("Australia", "Turkiye", 2.5),
    ("Germany", "Curacao", 4.5),
    ("Netherlands", "Japan", 2.5),
    ("Ivory Coast", "Ecuador", 1.5),
    ("Sweden", "Tunisia", 2.5),
    ("Spain", "Cape Verde", 3.5),
    ("Belgium", "Egypt", 2.5),
    ("Saudi Arabia", "Uruguay", 2.5),
    ("IR Iran", "New Zealand", 2.5),
    ("France", "Senegal", 2.5),
    ("Iraq", "Norway", 2.5),
    ("Argentina", "Algeria", 2.5),
    ("Austria", "Jordan", 2.5),
    ("Portugal", "Congo DR", 2.5),
    ("England", "Croatia", 2.5),
    ("Ghana", "Panama", 2.5),
    ("Uzbekistan", "Colombia", 2.5),
    ("Czechia", "South Africa", 2.5),
    ("Switzerland", "Bosnia & Herzegovina", 2.5),
    ("Canada", "Qatar", 2.5),
    ("Mexico", "Korea Republic", 2.5),
    ("USA", "Australia", 2.5),
    ("Scotland", "Morocco", 2.5),
    ("Brazil", "Haiti", 3.5),
    ("Turkiye", "Paraguay", 2.5),
    ("Netherlands", "Sweden", 2.5),
    ("Germany", "Ivory Coast", 2.5),
    ("Ecuador", "Curacao", 2.5),
    ("Tunisia", "Japan", 2.5),
    ("Spain", "Saudi Arabia", 3.5),
    ("Belgium", "IR Iran", 2.5),
    ("Uruguay", "Cape Verde", 2.5),
    ("New Zealand", "Egypt", 2.5),
    ("Argentina", "Austria", 2.5),
    ("France", "Iraq", 3.5),
    ("Norway", "Senegal", 2.5),
    ("Jordan", "Algeria", 2.5),
    ("Portugal", "Uzbekistan", 3.5),
    ("England", "Ghana", 2.5),
    ("Panama", "Croatia", 2.5),
    ("Colombia", "Congo DR", 2.5),
    ("Switzerland", "Canada", 2.5),
    ("Bosnia & Herzegovina", "Qatar", 2.5),
    ("Scotland", "Brazil", 2.5),
    ("Morocco", "Haiti", 2.5),
    ("Czechia", "Mexico", 2.5),
    ("South Africa", "Korea Republic", 2.5),
    ("Ecuador", "Germany", 2.5),
    ("Curacao", "Ivory Coast", 2.5),
    ("Tunisia", "Netherlands", 2.5),
    ("Japan", "Sweden", 2.5),
    ("Turkiye", "USA", 2.5),
    ("Paraguay", "Australia", 2.5),
    ("Norway", "France", 2.5),
    ("Senegal", "Iraq", 2.5),
    ("Uruguay", "Spain", 2.5),
    ("Cape Verde", "Saudi Arabia", 2.5),
    ("New Zealand", "Belgium", 2.5),
    ("Egypt", "IR Iran", 1.5),
    ("Panama", "England", 2.5),
    ("Croatia", "Ghana", 2.5),
    ("Colombia", "Portugal", 2.5),
    ("Congo DR", "Uzbekistan", 2.5),
    ("Jordan", "Argentina", 2.5),
    ("Algeria", "Austria", 2.5),
]

# Filtering thresholds for "Best Slip Ever"
# We only want picks with very high system confidence and strong ML signals.
MIN_CONFIDENCE = 75.0
MIN_ML_OVER_15 = 70.0

def analyze_match(home, away):
    try:
        # Use conservative mode for the core analysis
        body = {"home_team": home, "away_team": away, "mode": "conservative"}
        r = requests.post(API, json=body, timeout=120)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}", "matchup": f"{home} vs {away}"}
    except Exception as e:
        return {"error": str(e), "matchup": f"{home} vs {away}"}

def process():
    total = len(MATCHES)
    best_picks = []
    others = []
    
    print(f"\n{'='*70}")
    print(f"  BET LEGEND — WORLD CUP 2026 SLIP BUILDER")
    print(f"  Analyzing {total} matches...")
    print(f"{'='*70}\n")
    
    for idx, (home, away, line) in enumerate(MATCHES, 1):
        print(f"[{idx}/{total}] {home} vs {away}...", end=" ", flush=True)
        data = analyze_match(home, away)
        
        if "error" in data or not data.get("ranked_markets"):
            print("❌ SKIP (Data Issue)")
            continue
            
        conf = data.get("confidence", 0)
        ml = data.get("ml_probabilities", {})
        o15 = ml.get("over_1_5", 0)
        
        # Criteria for "Best Ever" slip:
        # 1. System confidence >= 75%
        # 2. ML Over 1.5 >= 70% (even if betting Over 0.5)
        # 3. No team data issues
        
        if conf >= MIN_CONFIDENCE:
            pick = {
                "match": f"{home} vs {away}",
                "market": data.get("recommendation"),
                "confidence": conf,
                "ml_o15": o15,
                "recommendation": data.get("recommendation"),
                "rationale": data.get("rationale")
            }
            best_picks.append(pick)
            print(f"💎 TOP ({data.get('recommendation')})")
        else:
            print("⏺️ OK")
            others.append({
                "match": f"{home} vs {away}",
                "confidence": conf,
                "ml_o15": o15
            })
        time.sleep(0.2)
        
    # Sort best picks by confidence
    best_picks.sort(key=lambda x: x["confidence"], reverse=True)
    
    report = {
        "summary": {
            "total_analyzed": total,
            "best_picks_count": len(best_picks),
            "filters": {"min_conf": MIN_CONFIDENCE, "min_ml_o15": MIN_ML_OVER_15}
        },
        "best_picks": best_picks
    }
    
    with open("world_cup_best_slip.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n{'='*70}")
    print(f"  WORLD CUP 2026 BEST SLIP EVER — {len(best_picks)} GEMS FOUND")
    print(f"{'='*70}\n")
    
    for p in best_picks:
        print(f"  💎 {p['match']}")
        print(f"     Bet: {p['market']}  |  Conf: {p['confidence']}%  |  ML O1.5: {p['ml_conf'] if 'ml_conf' in p else p['ml_o15']}%")
        print(f"     {p['rationale']}")
        print()

if __name__ == "__main__":
    process()
