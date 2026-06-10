"""
verify_ticket.py — Batch Ticket Verification Script
Calls the BetLegend backend API for each match in the ticket.
"""
import requests
import json
import time
import sys

API = "http://localhost:8000/api/analyze"
MODE = "low_risk"

# User's ticket: (home_team, away_team, user_market, user_odds)
TICKET = [
    ("SK Kladno", "FK Arsenal Ceska Lipa", "Over 0.5", 1.21),
    ("KS Stare Oborzyska", "Kkp Bydgoszcz", "Over 0.5", 1.14),
    ("Jong Sparta Rotterdam", "FC Groningen", "Over 0.5", 1.28),
    ("Orebro SK", "GIF Sundsvall", "Over 0.5", 1.13),
    ("Varbergs BoIS", "Norrby IF", "Over 0.5", 1.48),
    ("Lidkopings FK", "Skovde AIK", "Over 1.5", 1.35),
    ("Gilla FC", "EIF Akademi", "Over 0.5", 1.13),
    ("Colombia", "Tunisia", "Over 0.5", 1.35),
    ("Sexypoxyt", "Nups", "Over 0.5", 1.18),
    ("Leppavaaran Pallo", "PPJ", "Over 0.5", 1.21),
    ("Fransta IK", "IFK Ostersund", "Over 0.5", 1.22),
    ("America FC RJ", "AD Cabofriense", "Over 0.5", 1.29),
    ("San Lorenzo", "Instituto AC Cordoba", "Over 0.5", 1.19),
    ("Velez Sarsfield", "CA Tigre", "Over 1.5", 1.37),
    ("CA Sarmiento", "CA Talleres de Cordoba", "Over 0.5", 1.14),
    ("Argentinos Juniors", "Barracas Central", "Over 0.5", 1.13),
    ("San Martin de San Juan", "Estudiantes de La Plata", "Over 1.5", 1.38),
    ("Newells Old Boys", "Boca Juniors", "Over 0.5", 1.20),
    ("Estudiantes de Rio Cuarto", "CA Huracan", "Over 0.5", 1.12),
    ("Vitoria BA", "America MG", "Over 0.5", 1.15),
    ("Juventude", "Bahia", "Over 0.5", 1.08),
    ("Gremio", "Fluminense", "Over 0.5", 1.19),
    ("Malaga CF", "Las Palmas", "Over 0.5", 1.24),
    ("Portugal", "Nigeria", "Over 0.5", 1.71),
    ("England", "Costa Rica", "Over 1.5", 1.23),
]

def analyze_match(home, away, odds):
    """Call the backend API for a single match."""
    try:
        body = {"home_team": home, "away_team": away, "mode": MODE, "betway_odds": odds}
        r = requests.post(API, json=body, timeout=120)
        if r.status_code == 200:
            return r.json()
        else:
            return {"error": f"HTTP {r.status_code}", "matchup": f"{home} vs {away}"}
    except Exception as e:
        return {"error": str(e), "matchup": f"{home} vs {away}"}


def check_user_bet_alignment(result, user_market):
    """
    Check if the system's analysis supports the user's chosen market.
    Returns (verdict, confidence, reasoning)
    """
    if "error" in result or not result.get("ranked_markets"):
        return "⚠️ UNABLE", 0, "Could not find team data on Sofascore."

    ml = result.get("ml_probabilities", {})
    ranked = result.get("ranked_markets", [])
    confidence = result.get("confidence", 0)
    recommendation = result.get("recommendation", "")
    
    # Extract relevant ML probabilities
    over_1_5_ml = ml.get("over_1_5", 50)
    over_2_5_ml = ml.get("over_2_5", 50)
    btts_ml = ml.get("btts", 50)
    
    # For Over 0.5 — this is extremely low bar (just 1 goal needed)
    # If ML says Over 1.5 is high, Over 0.5 is almost certain
    if user_market == "Over 0.5":
        if over_1_5_ml >= 60:
            return "✅ APPROVE", over_1_5_ml, f"ML Over 1.5 = {over_1_5_ml}%, so Over 0.5 is very safe."
        elif over_1_5_ml >= 40:
            return "✅ APPROVE", over_1_5_ml, f"ML Over 1.5 = {over_1_5_ml}%. Over 0.5 should land comfortably."
        else:
            return "⚠️ CAUTION", over_1_5_ml, f"ML Over 1.5 only {over_1_5_ml}%. Low-scoring match expected."

    # For Over 1.5 — moderate bar (2+ goals needed)
    elif user_market == "Over 1.5":
        if over_1_5_ml >= 65:
            return "✅ APPROVE", over_1_5_ml, f"ML Over 1.5 = {over_1_5_ml}%. Strong signal."
        elif over_1_5_ml >= 50:
            return "✅ APPROVE", over_1_5_ml, f"ML Over 1.5 = {over_1_5_ml}%. Decent signal."
        elif over_1_5_ml >= 35:
            return "⚠️ ALTER", over_1_5_ml, f"ML Over 1.5 = {over_1_5_ml}%. Consider switching to Over 0.5 for safety."
        else:
            return "❌ REMOVE", over_1_5_ml, f"ML Over 1.5 only {over_1_5_ml}%. High risk of 0-0 or 1-0."
    
    # For Over 2.5
    elif user_market == "Over 2.5":
        if over_2_5_ml >= 55:
            return "✅ APPROVE", over_2_5_ml, f"ML Over 2.5 = {over_2_5_ml}%."
        elif over_2_5_ml >= 40:
            return "⚠️ ALTER", over_2_5_ml, f"ML Over 2.5 = {over_2_5_ml}%. Consider Over 1.5 instead."
        else:
            return "❌ REMOVE", over_2_5_ml, f"ML Over 2.5 only {over_2_5_ml}%. Too risky for low_risk mode."
    
    return "⚠️ UNABLE", 0, "Unknown market type."


def main():
    results = []
    total = len(TICKET)
    
    print(f"\n{'='*70}")
    print(f"  BET LEGEND — BATCH TICKET VERIFICATION ({MODE.upper()} MODE)")
    print(f"  {total} matches to analyze")
    print(f"{'='*70}\n")
    
    for idx, (home, away, market, odds) in enumerate(TICKET, 1):
        print(f"[{idx}/{total}] Analyzing: {home} vs {away}...", end=" ", flush=True)
        data = analyze_match(home, away, odds)
        verdict, conf, reason = check_user_bet_alignment(data, market)
        results.append({
            "idx": idx,
            "match": f"{home} vs {away}",
            "user_bet": f"{market} @ {odds}",
            "verdict": verdict,
            "ml_conf": conf,
            "reason": reason,
            "system_rec": data.get("recommendation", "N/A"),
            "system_conf": data.get("confidence", 0),
            "full_data": data,
        })
        print(f"{verdict}")
        time.sleep(0.3)  # small delay between requests
    
    # Print summary report
    approved = [r for r in results if "APPROVE" in r["verdict"]]
    altered  = [r for r in results if "ALTER" in r["verdict"]]
    removed  = [r for r in results if "REMOVE" in r["verdict"]]
    caution  = [r for r in results if "CAUTION" in r["verdict"]]
    unable   = [r for r in results if "UNABLE" in r["verdict"]]
    
    print(f"\n{'='*70}")
    print(f"  TICKET VERIFICATION REPORT")
    print(f"{'='*70}")
    print(f"  ✅ Approved: {len(approved)}  |  ⚠️ Alter: {len(altered)}  |  ❌ Remove: {len(removed)}  |  ⚠️ Caution: {len(caution)}  |  ⚠️ Unable: {len(unable)}")
    print(f"{'='*70}\n")
    
    for r in results:
        print(f"  {r['verdict']}  [{r['idx']:2d}] {r['match']}")
        print(f"         Your Bet: {r['user_bet']}")
        print(f"         System:   {r['system_rec']} ({r['system_conf']}% conf)")
        print(f"         Reason:   {r['reason']}")
        print()
    
    # Save JSON report
    report_path = "ticket_report.json"
    with open(report_path, "w") as f:
        json.dump([{k:v for k,v in r.items() if k != "full_data"} for r in results], f, indent=2)
    print(f"  📄 Full report saved to: {report_path}")
    
    # Also save the full data for debugging
    full_path = "ticket_report_full.json"
    with open(full_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  📄 Full data saved to: {full_path}\n")


if __name__ == "__main__":
    main()
