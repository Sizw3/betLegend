"""
build_ticket.py — Conservative Ticket Builder
Analyzes all matches via BetLegend API, applies strategy filters,
removes weak games, and builds an optimized ticket.
"""
import requests
import json
import time

API = "http://localhost:8000/api/analyze"
MODE = "conservative"

# (home, away, available_line, league)
MATCHES = [
    ("Derby Academie", "FC Mali Coura", 1.5, "Ligue 1, Mali"),
    ("Onze Createurs", "AS Bakaridjan", 1.5, "Ligue 1, Mali"),
    ("Afrique Football Elite", "AS Korofina", 2.5, "Ligue 1, Mali"),
    ("Jong Sparta Rotterdam", "FC Groningen", 3.5, "Tweede Divisie, Netherlands"),
    ("JIPPO", "Kings SC Kuopio", 3.5, "Kolmonen, Finland"),
    ("Orebro SK", "GIF Sundsvall", 2.5, "Superettan, Sweden"),
    ("Varbergs BoIS", "Norrby IF", 3.5, "Superettan, Sweden"),
    ("IF Eker Orebro", "IF Karlstad Fotbol", 4.5, "Svenska Cup, Sweden"),
    ("Lidkopings FK", "Skovde AIK", 3.5, "Svenska Cup, Sweden"),
    ("Gilla FC", "EIF Akademi", 4.5, "Kolmonen, Finland"),
    ("Colombia", "Tunisia", 3.5, "Toulon Tournament"),
    ("Kkp Warszawa", "Uks Staszkowka Jelna", 2.5, "1. Liga Women, Poland"),
    ("Sexypoxyt", "Nups", 3.5, "Kolmonen, Finland"),
    ("Leppavaaran Pallo", "PPJ", 3.5, "Kolmonen, Finland"),
    ("Fransta IK", "IFK Ostersund", 3.5, "Division 2, Sweden"),
    ("America FC RJ", "AD Cabofriense", 1.5, "Carioca Serie A2, Brazil"),
    ("San Lorenzo", "Instituto AC Cordoba", 2.5, "Primera LPF Reserves, Argentina"),
    ("Velez Sarsfield", "CA Tigre", 2.5, "Primera LPF Reserves, Argentina"),
    ("CA Sarmiento", "CA Talleres de Cordoba", 2.5, "Primera LPF Reserves, Argentina"),
    ("Argentinos Juniors", "Barracas Central", 2.5, "Primera LPF Reserves, Argentina"),
    ("San Martin de San Juan", "Estudiantes de La Plata", 2.5, "Primera LPF Reserves, Argentina"),
    ("Newells Old Boys", "Boca Juniors", 2.5, "Primera LPF Reserves, Argentina"),
    ("Estudiantes de Rio Cuarto", "CA Huracan", 2.5, "Primera LPF Reserves, Argentina"),
    ("Vitoria BA", "America MG", 2.5, "U20 Brasileiro, Brazil"),
    ("Juventude", "Bahia", 2.5, "U20 Brasileiro, Brazil"),
    ("Gremio", "Fluminense", 2.5, "U20 Brasileiro, Brazil"),
    ("Corinthians", "Avai", 3.5, "U20 Brasileiro, Brazil"),
    ("Botafogo", "Criciuma", 2.5, "U20 Brasileiro, Brazil"),
    ("Chapecoense", "Concordia", 3.5, "U20 Catarinense, Brazil"),
    ("KF Austfjardja", "Fjolnir", 3.5, "2. deild, Iceland"),
    ("Excelsior Maassluis", "IJsselmeervogels", 2.5, "Tweede Divisie, Netherlands"),
    ("Malaga CF", "Las Palmas", 2.5, "LaLiga 2, Spain"),
    ("Haukar Hafnarfjordur", "Kormakur", 3.5, "2. deild, Iceland"),
    ("KFG Gardabaer", "Hviti Riddarinn", 3.5, "2. deild, Iceland"),
    ("Kari", "UMF Selfoss", 4.5, "2. deild, Iceland"),
    ("IF Magni Grenivik", "Dalvik Reynir", 3.5, "2. deild, Iceland"),
    ("Throttur Vogum", "Vikingur Olafsvik", 3.5, "2. deild, Iceland"),
    ("KH Hlidarendi", "Reynir Sandgerdi", 3.5, "2. deild, Iceland"),
    ("UMF Vidir", "Arbaer", 4.5, "3. deild, Iceland"),
    ("UMF Tindastoll", "KF Fjallabyggd", 4.5, "3. deild, Iceland"),
    ("Afturelding", "Stjarnan", 3.5, "Cup, Iceland"),
    ("Portugal", "Nigeria", 3.5, "World Cup 2026 Friendly"),
    ("England", "Costa Rica", 3.5, "World Cup 2026 Friendly"),
    ("Augnablik Kopavogur", "KV Vesturbaer", 4.5, "3. deild, Iceland"),
    ("Marica FC RJ", "Bonsucesso FC RJ", 2.5, "Carioca Serie A2, Brazil"),
    ("Gualaceo SC", "Cumbaya FC", 2.5, "Serie B, Ecuador"),
    ("CD Independiente Juniors", "Club Deportivo Cuenca", 2.5, "Serie B, Ecuador"),
    ("Charlotte Eagles", "Asheville City SC", 2.5, "USL League Two, USA"),
]


# ── Strategy-based filtering logic ──────────────────────────────
# Conservative mode thresholds from strategy.py: 0.60 confidence
CONSERVATIVE_THRESHOLD = 0.60

# Leagues we flag as risky for conservative mode
RISKY_LEAGUES = [
    "3. deild", "Kolmonen", "Women", "U20 Catarinense",
]

# Markets that are too aggressive for conservative
AGGRESSIVE_LINES = {4.5}  # Over 4.5 is too much for conservative


def analyze_match(home, away):
    try:
        body = {"home_team": home, "away_team": away, "mode": MODE}
        r = requests.post(API, json=body, timeout=120)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def pick_best_market(result, available_line, league):
    """
    Given the system's analysis, decide:
    1. What market to bet on (from system recommendation or user's line)
    2. Whether to include or exclude the game
    Returns: (include, market, confidence, reason)
    """
    if "error" in result or not result.get("ranked_markets"):
        return False, "N/A", 0, "❌ Team not found on Sofascore — skipping unknown team."

    ml = result.get("ml_probabilities", {})
    ranked = result.get("ranked_markets", [])
    system_rec = result.get("recommendation", "")
    system_conf = result.get("confidence", 0)

    over_1_5 = ml.get("over_1_5", 50)
    over_2_5 = ml.get("over_2_5", 50)
    under_2_5 = ml.get("under_2_5", 50)
    btts = ml.get("btts", 50)
    home_win = ml.get("home_win", 50)
    away_win = ml.get("away_win", 50)

    # ── Pre-filter: reject based on league risk ──
    is_risky_league = any(rl.lower() in league.lower() for rl in RISKY_LEAGUES)

    # ── Pre-filter: reject over 4.5 lines in conservative mode ──
    if available_line in AGGRESSIVE_LINES:
        # Only include if the system is extremely confident
        if system_conf < 75:
            return False, f"Over {available_line}", system_conf, f"❌ Over {available_line} too aggressive for conservative (system conf: {system_conf}%)."

    # ── Decide best market based on available line ──
    if available_line == 1.5:
        # Over 1.5 — moderate safety
        if over_1_5 >= 65:
            return True, "Over 1.5", round(over_1_5, 1), f"✅ ML Over 1.5 = {over_1_5:.1f}%. Strong."
        elif over_1_5 >= 55:
            return True, "Over 0.5", 99.0, f"⚠️ ML Over 1.5 only {over_1_5:.1f}%. Downgraded to Over 0.5 for safety."
        else:
            return False, "Over 1.5", round(over_1_5, 1), f"❌ ML Over 1.5 = {over_1_5:.1f}%. Too weak."

    elif available_line == 2.5:
        # Over 2.5 — the sweet spot for conservative
        if over_2_5 >= 55:
            return True, "Over 2.5", round(over_2_5, 1), f"✅ ML Over 2.5 = {over_2_5:.1f}%. Good value."
        elif over_1_5 >= 70:
            return True, "Over 1.5", round(over_1_5, 1), f"⚠️ Over 2.5 weak ({over_2_5:.1f}%). Downgraded to Over 1.5 ({over_1_5:.1f}%)."
        elif is_risky_league:
            return False, "Over 2.5", round(over_2_5, 1), f"❌ Risky league + weak signal ({over_2_5:.1f}%). Removed."
        else:
            return True, "Over 1.5", round(over_1_5, 1), f"⚠️ Over 2.5 = {over_2_5:.1f}%. Safe fallback to Over 1.5 ({over_1_5:.1f}%)."

    elif available_line == 3.5:
        # Over 3.5 — aggressive, needs strong backing
        if over_2_5 >= 60:
            return True, "Over 2.5", round(over_2_5, 1), f"✅ Downgraded from 3.5 → Over 2.5 ({over_2_5:.1f}%). Conservative play."
        elif over_1_5 >= 70:
            return True, "Over 1.5", round(over_1_5, 1), f"⚠️ Downgraded from 3.5 → Over 1.5 ({over_1_5:.1f}%)."
        elif is_risky_league:
            return False, "Over 3.5", round(over_2_5, 1), f"❌ Risky league + 3.5 line. Removed."
        else:
            return True, "Over 1.5", round(over_1_5, 1), f"⚠️ 3.5 too high. Fallback Over 1.5 ({over_1_5:.1f}%)."

    elif available_line == 4.5:
        # Over 4.5 — very aggressive
        if over_2_5 >= 65:
            return True, "Over 2.5", round(over_2_5, 1), f"⚠️ Heavily downgraded 4.5 → Over 2.5 ({over_2_5:.1f}%)."
        elif over_1_5 >= 72:
            return True, "Over 1.5", round(over_1_5, 1), f"⚠️ Heavily downgraded 4.5 → Over 1.5 ({over_1_5:.1f}%)."
        else:
            return False, "Over 4.5", round(over_2_5, 1), f"❌ Over 4.5 far too aggressive. ML too weak to justify."

    return True, system_rec, system_conf, f"System pick: {system_rec} ({system_conf}%)."


def main():
    total = len(MATCHES)
    results = []

    print(f"\n{'='*70}")
    print(f"  BET LEGEND — CONSERVATIVE TICKET BUILDER")
    print(f"  {total} matches to analyze")
    print(f"{'='*70}\n")

    for idx, (home, away, line, league) in enumerate(MATCHES, 1):
        print(f"[{idx}/{total}] {home} vs {away} (line: {line})...", end=" ", flush=True)
        data = analyze_match(home, away)
        include, market, conf, reason = pick_best_market(data, line, league)
        verdict = "✅ IN" if include else "❌ OUT"
        results.append({
            "idx": idx,
            "home": home,
            "away": away,
            "league": league,
            "original_line": line,
            "verdict": verdict,
            "selected_market": market,
            "confidence": conf,
            "reason": reason,
            "include": include,
            "system_rec": data.get("recommendation", "N/A"),
            "system_conf": data.get("confidence", 0),
            "ml": data.get("ml_probabilities", {}),
        })
        print(verdict)
        time.sleep(0.3)

    # ── Results ──
    included = [r for r in results if r["include"]]
    excluded = [r for r in results if not r["include"]]

    print(f"\n{'='*70}")
    print(f"  CONSERVATIVE TICKET — FINAL SELECTION")
    print(f"  ✅ Included: {len(included)}  |  ❌ Removed: {len(excluded)}")
    print(f"{'='*70}\n")

    print("  ── YOUR TICKET ──────────────────────────────────")
    for r in included:
        print(f"  ✅ {r['home']} vs {r['away']}")
        print(f"     Market: {r['selected_market']}  |  Conf: {r['confidence']}%  |  {r['league']}")
        print(f"     {r['reason']}")
        print()

    print("  ── REMOVED GAMES ────────────────────────────────")
    for r in excluded:
        print(f"  ❌ {r['home']} vs {r['away']}")
        print(f"     {r['reason']}")
        print()

    # Save reports
    with open("conservative_ticket.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  📄 Report saved to conservative_ticket.json\n")


if __name__ == "__main__":
    main()
