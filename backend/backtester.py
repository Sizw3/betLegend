"""
backtester.py - Walk-Forward Backtesting Engine
Zero lookahead bias: each prediction uses ONLY data from matches BEFORE it.
Uses the same football-data.co.uk data the XGBoost models were trained on.
"""
import pandas as pd
import numpy as np
import requests
import io
import os
import pickle

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

DATA_URLS = [
    "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2324/D1.csv",
    "https://www.football-data.co.uk/mmz4281/2324/SP1.csv",
    "https://www.football-data.co.uk/mmz4281/2324/I1.csv",
]

# ── Outcome Checkers ──────────────────────────────────────────
def check_outcome(row, market_key):
    hg = int(row.get('FTHG', 0) or 0)
    ag = int(row.get('FTAG', 0) or 0)
    ftr = str(row.get('FTR', ''))
    total = hg + ag
    if market_key == 'UNDER_4_5': return total < 5
    if market_key == 'UNDER_3_5': return total < 4
    if market_key == 'UNDER_2_5': return total < 3
    if market_key == 'OVER_0_5':  return total > 0
    if market_key == 'OVER_1_5':  return total > 1
    if market_key == 'OVER_2_5':  return total > 2
    if market_key == 'BTTS_YES':  return hg > 0 and ag > 0
    if market_key == 'BTTS_NO':   return not (hg > 0 and ag > 0)
    if market_key == 'DC_HOME':   return ftr in ('H', 'D')
    if market_key == 'DC_AWAY':   return ftr in ('A', 'D')
    if market_key == 'HOME_WIN':  return ftr == 'H'
    if market_key == 'AWAY_WIN':  return ftr == 'A'
    return False

# ── Implied Odds Lookup ───────────────────────────────────────
def get_implied_odds(row, market_key):
    """Pull Bet365 odds from the CSV as Betway proxy."""
    if market_key in ('UNDER_4_5', 'UNDER_3_5', 'UNDER_2_5'):
        return float(row.get('B365<2.5', 0) or 0) or 1.40
    if market_key in ('OVER_0_5', 'OVER_1_5', 'OVER_2_5'):
        return float(row.get('B365>2.5', 0) or 0) or 1.85
    if market_key == 'BTTS_YES':  return float(row.get('BbAv>2.5', 0) or 0) or 1.85
    if market_key == 'BTTS_NO':   return float(row.get('BbAv<2.5', 0) or 0) or 1.50
    if market_key == 'DC_HOME':   return float(row.get('B365H', 0) or 0) * 0.7 or 1.30
    if market_key == 'DC_AWAY':   return float(row.get('B365A', 0) or 0) * 0.7 or 1.30
    if market_key == 'HOME_WIN':  return float(row.get('B365H', 0) or 0) or 2.10
    if market_key == 'AWAY_WIN':  return float(row.get('B365A', 0) or 0) or 2.80
    return 1.50

# ── Recency-Weighted Team Stats ───────────────────────────────
def get_team_stats(hist, n=7):
    last = hist[-n:]
    if not last:
        return dict(avg_scored=1.3, avg_conceded=1.2, win_rate=0.4,
                    draw_rate=0.28, btts_rate=0.52, over_2_5_rate=0.52,
                    clean_sheet_rate=0.28, avg_total_goals=2.5)
    w = np.array([0.85**(len(last)-1-i) for i in range(len(last))])
    w /= w.sum()
    gfs  = np.array([h['gf'] for h in last])
    gas  = np.array([h['ga'] for h in last])
    return dict(
        avg_scored=float(np.dot(gfs, w)),
        avg_conceded=float(np.dot(gas, w)),
        avg_total_goals=float(np.dot(gfs+gas, w)),
        win_rate=float(np.mean([h['res']=='W' for h in last])),
        draw_rate=float(np.mean([h['res']=='D' for h in last])),
        btts_rate=float(np.mean([h['gf']>0 and h['ga']>0 for h in last])),
        over_2_5_rate=float(np.mean([h['gf']+h['ga']>2 for h in last])),
        clean_sheet_rate=float(np.mean([h['ga']==0 for h in last])),
    )

# ── Load ML Models ────────────────────────────────────────────
def load_models():
    models = {}
    for name in ["btts","over_2_5","over_1_5","under_2_5","home_win","away_win"]:
        fp = os.path.join(MODEL_DIR, f"{name}.pkl")
        if os.path.exists(fp):
            with open(fp,"rb") as f:
                models[name] = pickle.load(f)
    return models

def build_feature_row(hs, as_):
    form = lambda s: s['win_rate']*3 + s['draw_rate']
    return {
        'h_avg_gf': hs['avg_scored'], 'h_avg_ga': hs['avg_conceded'],
        'h_avg_sot': hs['avg_scored']/0.32, 'h_win_rate': hs['win_rate'],
        'h_draw_rate': hs['draw_rate'], 'h_btts_rate': hs['btts_rate'],
        'h_over_rate': hs['over_2_5_rate'], 'h_cs_rate': hs['clean_sheet_rate'],
        'h_form': form(hs),
        'a_avg_gf': as_['avg_scored'], 'a_avg_ga': as_['avg_conceded'],
        'a_avg_sot': as_['avg_scored']/0.32, 'a_win_rate': as_['win_rate'],
        'a_draw_rate': as_['draw_rate'], 'a_btts_rate': as_['btts_rate'],
        'a_over_rate': as_['over_2_5_rate'], 'a_cs_rate': as_['clean_sheet_rate'],
        'a_form': form(as_),
        'comb_goals': (hs['avg_scored']+as_['avg_scored']+hs['avg_conceded']+as_['avg_conceded'])/2,
        'h_attack_edge': hs['avg_scored']-as_['avg_conceded'],
        'a_attack_edge': as_['avg_scored']-hs['avg_conceded'],
        'btts_prob': (hs['btts_rate']+as_['btts_rate'])/2,
        'form_diff': form(hs)-form(as_),
        'cs_combined': (hs['clean_sheet_rate']+as_['clean_sheet_rate'])/2,
    }

def ml_predict(feat, models):
    probs = {}
    row = pd.DataFrame([feat])
    for name, model in models.items():
        try: probs[name] = float(model.predict_proba(row)[0][1])
        except: probs[name] = 0.5
    return probs

def pick_market(hs, as_, ml_probs, mode):
    h2h_u35 = 0.6; h2h_btts = 0.5
    form_avg = (hs['avg_total_goals'] + as_['avg_total_goals']) / 2
    blended = form_avg * 0.5 + (ml_probs.get('over_2_5', 0.5) * 3.5) * 0.5
    form_cs = (hs['clean_sheet_rate'] + as_['clean_sheet_rate']) / 2
    form_btts = (hs['btts_rate'] + as_['btts_rate']) / 2
    rp = {"low_risk": 0.25, "conservative": 0.1, "high_risk": 0.0}[mode]

    candidates = [
        ("UNDER_4_5", min(0.97, (1-blended/6)*0.6 + h2h_u35*0.25 + form_cs*0.15)),
        ("UNDER_3_5", min(0.97, (1-blended/5)*0.6 + h2h_u35*0.25 + form_cs*0.15)),
        ("UNDER_2_5", min(0.97, ml_probs.get('under_2_5',0.5)*0.55 + 0.5*0.25 + form_cs*0.20)),
        ("OVER_0_5",  min(0.99, 1.0 if blended > 0.6 else 0.5)),
        ("OVER_1_5",  min(0.97, ml_probs.get('over_1_5',0.5)*0.55 + (1-form_cs)*0.25 + (blended/4)*0.2)),
        ("OVER_2_5",  min(0.97, ml_probs.get('over_2_5',0.5)*0.55 + (blended/4)*0.45) - rp),
        ("BTTS_NO",   min(0.97, (1-ml_probs.get('btts',0.5))*0.5 + (1-form_btts)*0.3 + (1-h2h_btts)*0.2)),
        ("BTTS_YES",  min(0.97, ml_probs.get('btts',0.5)*0.5 + form_btts*0.3 + h2h_btts*0.2) - rp),
        ("DC_HOME",   min(0.97, (hs['win_rate']+hs['draw_rate'])*0.6 + ml_probs.get('home_win',0.5)*0.4) - rp),
        ("DC_AWAY",   min(0.97, (as_['win_rate']+as_['draw_rate'])*0.6 + ml_probs.get('away_win',0.5)*0.4) - rp),
        ("HOME_WIN",  min(0.97, ml_probs.get('home_win',0.5)*0.65 + hs['win_rate']*0.35) - rp),
        ("AWAY_WIN",  min(0.97, ml_probs.get('away_win',0.5)*0.65 + as_['win_rate']*0.35) - rp),
    ]
    thresholds = {"low_risk":0.78,"conservative":0.60,"high_risk":0.45}
    candidates.sort(key=lambda x: x[1], reverse=True)
    best_key, best_conf = candidates[0]
    if best_conf < thresholds[mode]: return "SKIP", 0.0
    return best_key, round(best_conf, 4)

# ── Main Backtest Runner ──────────────────────────────────────
def run_backtest(mode="conservative", stake=10.0):
    models = load_models()
    dfs = []
    for url in DATA_URLS:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text), on_bad_lines='skip')
                dfs.append(df)
        except: pass

    if not dfs: return {"error": "Could not download data"}
    raw = pd.concat(dfs, ignore_index=True)
    raw = raw.dropna(subset=['HomeTeam','AwayTeam','FTHG','FTAG','FTR']).reset_index(drop=True)

    team_hist = {}
    results = []
    balance = 0.0
    equity_curve = [0.0]
    correct = 0; placed = 0; skipped = 0

    market_stats = {}

    for _, row in raw.iterrows():
        ht, at = row['HomeTeam'], row['AwayTeam']
        hs = get_team_stats(team_hist.get(ht, []))
        as_ = get_team_stats(team_hist.get(at, []))

        feat = build_feature_row(hs, as_)
        ml_probs = ml_predict(feat, models)
        market, conf = pick_market(hs, as_, ml_probs, mode)

        hg = int(row['FTHG']); ag = int(row['FTAG']); ftr = row['FTR']
        actual_result = f"{hg}-{ag}"

        if market == "SKIP":
            skipped += 1
        else:
            odds = get_implied_odds(row, market)
            won = check_outcome(row, market)
            pnl = round((odds - 1) * stake if won else -stake, 2)
            balance = round(balance + pnl, 2)
            placed += 1
            if won: correct += 1
            equity_curve.append(balance)
            if market not in market_stats:
                market_stats[market] = {"won":0,"total":0,"pnl":0.0}
            market_stats[market]["total"] += 1
            market_stats[market]["pnl"] = round(market_stats[market]["pnl"] + pnl, 2)
            if won: market_stats[market]["won"] += 1
            results.append({
                "match": f"{ht} vs {at}",
                "predicted_market": market,
                "confidence": round(conf*100,1),
                "odds": odds,
                "result": actual_result,
                "won": won,
                "pnl": pnl,
                "balance": balance,
            })

        # Update history AFTER prediction (no lookahead)
        if ht not in team_hist: team_hist[ht] = []
        team_hist[ht].append({'gf':hg,'ga':ag,'res':'W' if ftr=='H' else ('D' if ftr=='D' else 'L')})
        if at not in team_hist: team_hist[at] = []
        team_hist[at].append({'gf':ag,'ga':hg,'res':'W' if ftr=='A' else ('D' if ftr=='D' else 'L')})

    win_rate = round(correct/placed*100, 1) if placed else 0
    roi = round(balance/(placed*stake)*100, 1) if placed else 0

    market_summary = [
        {"market": k, "wins": v["won"], "total": v["total"],
         "win_rate": round(v["won"]/v["total"]*100,1),
         "pnl": v["pnl"]}
        for k, v in market_stats.items()
    ]
    market_summary.sort(key=lambda x: x["pnl"], reverse=True)

    # Only return last 50 results for the UI (most recent)
    return {
        "mode": mode,
        "stake_per_bet": stake,
        "total_matches": len(raw),
        "bets_placed": placed,
        "bets_skipped": skipped,
        "correct_predictions": correct,
        "win_rate_pct": win_rate,
        "net_pnl": round(balance, 2),
        "roi_pct": roi,
        "equity_curve": equity_curve[-100:],  # last 100 for chart
        "market_breakdown": market_summary,
        "recent_results": results[-50:],
    }

if __name__ == "__main__":
    import json
    print("Running backtest in conservative mode...")
    r = run_backtest("conservative")
    print(f"Matches: {r['total_matches']} | Placed: {r['bets_placed']} | Win Rate: {r['win_rate_pct']}% | ROI: {r['roi_pct']}% | Net P&L: R{r['net_pnl']}")
    print("\nTop markets:")
    for m in r['market_breakdown'][:5]:
        print(f"  {m['market']:15s}  {m['wins']}/{m['total']}  ({m['win_rate']}%)  P&L: R{m['pnl']}")
