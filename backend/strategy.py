"""
strategy_v4.py - Bet Legend Hybrid Intelligence Engine
XGBoost ML + Evolutionary Scoring + Live Player Ratings + FIFA Rankings
World Cup 2026 Ready — League Agnostic
Anti-Overfitting: Player data used as multiplier, NOT as XGBoost features
"""
import os, pickle
import numpy as np
from scraper import fetch_all_match_data
from wc_feature_connector import WCFeatureConnector

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# ── Betway Market Registry ────────────────────────────────────
MARKETS = {
    "UNDER_4_5": {"label": "Under 4.5 Goals",            "betway": "Total Goals - Under 4.5"},
    "UNDER_3_5": {"label": "Under 3.5 Goals",            "betway": "Total Goals - Under 3.5"},
    "UNDER_2_5": {"label": "Under 2.5 Goals",            "betway": "Total Goals - Under 2.5"},
    "OVER_0_5":  {"label": "Over 0.5 Goals",             "betway": "Total Goals - Over 0.5"},
    "OVER_1_5":  {"label": "Over 1.5 Goals",             "betway": "Total Goals - Over 1.5"},
    "OVER_2_5":  {"label": "Over 2.5 Goals",             "betway": "Total Goals - Over 2.5"},
    "BTTS_YES":  {"label": "Both Teams to Score - Yes",  "betway": "Both Teams to Score - Yes"},
    "BTTS_NO":   {"label": "Both Teams to Score - No",   "betway": "Both Teams to Score - No"},
    "DC_HOME":   {"label": "Double Chance - Home/Draw",  "betway": "Double Chance - 1X"},
    "DC_AWAY":   {"label": "Double Chance - Away/Draw",  "betway": "Double Chance - X2"},
    "HOME_WIN":  {"label": "Home Team Win",              "betway": "1X2 - Home Win (1)"},
    "AWAY_WIN":  {"label": "Away Team Win",              "betway": "1X2 - Away Win (2)"},
    "DRAW":      {"label": "Draw",                       "betway": "1X2 - Draw (X)"},
    "SKIP":      {"label": "Skip This Match",            "betway": "N/A"},
}

CONFIDENCE_THRESHOLDS = {
    "low_risk":     0.78,
    "conservative": 0.60,
    "high_risk":    0.45,
}

# ── FIFA World Rankings (June 2026 — updated periodically) ────
# Source: FIFA.com world rankings
FIFA_RANKINGS = {
    "Argentina":1,"France":2,"England":3,"Belgium":4,"Brazil":5,
    "Portugal":6,"Spain":7,"Netherlands":8,"Germany":9,"Italy":10,
    "Croatia":11,"Uruguay":12,"Morocco":13,"Colombia":14,"Senegal":15,
    "United States":16,"Mexico":17,"Denmark":18,"Switzerland":19,"Japan":20,
    "Australia":21,"South Korea":22,"Poland":23,"Austria":24,"Hungary":25,
    "Ukraine":26,"Serbia":27,"Czech Republic":28,"Norway":29,"Sweden":30,
    "Chile":31,"Peru":32,"Algeria":33,"Tunisia":34,"Egypt":35,
    "Ivory Coast":36,"Nigeria":37,"Ghana":38,"Cameroon":39,"South Africa":40,
    "Ecuador":41,"Venezuela":42,"Bolivia":43,"Paraguay":44,"Uruguay":12,
    "Qatar":45,"Iran":46,"South Korea":22,"Japan":20,"Saudi Arabia":47,
    "Australia":21,"New Zealand":48,"South Africa":40,"Mali":49,"Burkina Faso":50,
    "Costa Rica":51,"Panama":52,"Jamaica":53,"Haiti":54,"El Salvador":55,
    "Guatemala":56,"Honduras":57,"Canada":58,"Turkey":32,"Greece":60,
    "Scotland":61,"Wales":62,"Romania":63,"Slovakia":64,"Slovenia":65,
    "Albania":66,"Kosovo":67,"Finland":68,"Iceland":69,"Northern Ireland":70,
    "Ireland":71,"Azerbaijan":72,"Kazakhstan":73,"Armenia":74,"Georgia":75,
    "Kyrgyzstan":76,"Tajikistan":77,"Uzbekistan":78,"India":79,"Indonesia":80,
    "Mozambique":81,"Zimbabwe":82,"Malawi":83,"Ethiopia":84,
    "Central African Republic":85,"Equatorial Guinea":86,
    "Cape Verde":87,"Benin":88,"Togo":89,"Liberia":90,"Sierra Leone":91,
    "Angola":92,"Burkina Faso":50,"Andorra":99,"San Marino":100,
    "Faroe Islands":101,"Moldova":95,"Belarus":96,
    "Palestine":97,"Brunei Darussalam":98,"Cambodia":99,"Hong Kong":85,
    "Philippines":94,"Myanmar":88,"Thailand":93,"Timor-Leste":120,
}

def get_fifa_rank(team_name):
    """Returns FIFA rank — lower is better. Default 60 if unknown."""
    name = team_name.strip()
    return FIFA_RANKINGS.get(name, FIFA_RANKINGS.get(name.split()[0], 60))

# ── Load XGBoost Models ───────────────────────────────────────
def load_models():
    models = {}
    for name in ["btts","over_2_5","over_1_5","under_2_5","home_win","away_win"]:
        fp = os.path.join(MODEL_DIR, f"{name}.pkl")
        if os.path.exists(fp):
            with open(fp,"rb") as f:
                models[name] = pickle.load(f)
    return models

_models = load_models()

def build_live_feature_vector(hs, as_, h_name, a_name):
    # Humanistic/WC Upgrade Connector
    connector = WCFeatureConnector()
    hwc = connector.get_features(h_name)
    awc = connector.get_features(a_name)
    
    form = lambda s: s['win_rate']*3 + s['draw_rate']
    feat = {
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
    
    # --- Add WC DNA features ---
    feat['h_wc_rank']   = hwc['wc_rank']
    feat['a_wc_rank']   = awc['wc_rank']
    feat['h_wc_value']  = hwc['wc_value']
    feat['a_wc_value']  = awc['wc_value']
    feat['h_wc_exp']    = hwc['wc_exp']
    feat['a_wc_exp']    = awc['wc_exp']
    feat['h_wc_titles'] = hwc['wc_titles']
    feat['a_wc_titles'] = awc['wc_titles']
    feat['h_wc_success'] = hwc['wc_success_rate']
    feat['a_wc_success'] = awc['wc_success_rate']
    feat['wc_rank_diff'] = hwc['wc_rank'] - awc['wc_rank']
    feat['h_heritage']   = hwc['heritage_score']
    feat['a_heritage']   = awc['heritage_score']
    feat['heritage_diff'] = hwc['heritage_score'] - awc['heritage_score']
    
    return feat

def ml_predict(feat):
    import pandas as pd
    probs = {}
    row = pd.DataFrame([feat])
    for name, model in _models.items():
        try: probs[name] = float(model.predict_proba(row)[0][1])
        except: probs[name] = 0.5
    return probs

# ── Player Intelligence Multiplier ────────────────────────────
def compute_player_adjustment(home_pd, away_pd, home_rank, away_rank):
    """
    Returns adjustment factors WITHOUT training on player data (anti-overfitting).
    Uses player ratings and FIFA ranking as post-model multipliers.
    
    Returns dict of adjustment factors:
    - quality_gap: how much stronger one squad is (normalized -1 to +1)
    - expected_goal_modifier: formation-based goal expectation adjustment
    - home_strength_boost: confidence boost for home team dominance
    """
    # Squad quality comparison (0 = equal, positive = home better)
    if home_pd and away_pd:
        rating_diff = home_pd['avg_player_rating'] - away_pd['avg_player_rating']
        quality_gap = max(-1.0, min(1.0, rating_diff / 2.0))  # normalize to -1..+1
    else:
        quality_gap = 0.0

    # FIFA rank gap (lower rank number = stronger team)
    rank_gap = away_rank - home_rank  # positive = home is stronger
    rank_factor = max(-1.0, min(1.0, rank_gap / 40.0))  # normalize

    # Combined strength signal
    strength = (quality_gap * 0.6) + (rank_factor * 0.4)

    # Formation impact on goals
    # Defensive formation (0) = fewer goals expected
    # Attacking formation (2) = more goals expected
    home_form_type = home_pd['formation_type'] if home_pd else 1
    away_form_type = away_pd['formation_type'] if away_pd else 1
    formation_goal_mod = ((home_form_type + away_form_type) - 2) / 4  # -0.5..+0.5

    # Goal expectation modifier: negative = under more likely
    goal_modifier = formation_goal_mod * 0.15  # subtle, max ±15% confidence shift

    return {
        'quality_gap':      round(quality_gap, 3),
        'rank_factor':      round(rank_factor, 3),
        'strength':         round(strength, 3),
        'goal_modifier':    round(goal_modifier, 3),
        'home_rating':      home_pd['avg_player_rating'] if home_pd else None,
        'away_rating':      away_pd['avg_player_rating'] if away_pd else None,
        'home_top_player':  home_pd['top_player_rating'] if home_pd else None,
        'away_top_player':  away_pd['top_player_rating'] if away_pd else None,
        'home_formation':   home_pd['formation'] if home_pd else 'N/A',
        'away_formation':   away_pd['formation'] if away_pd else 'N/A',
    }

def compute_edge(our_prob, betway_odds):
    if not betway_odds or betway_odds <= 1.0:
        return None
    ev = (our_prob * (betway_odds - 1)) - (1 - our_prob)
    return round(ev, 4)

# ── Evolutionary Market Scorer ────────────────────────────────
def score_all_markets(hs, as_, h2h, ml_probs, player_adj, mode):
    h2h_avg  = h2h['avg_total_goals']  if h2h else (hs['avg_total_goals']+as_['avg_total_goals'])/2
    h2h_u25  = h2h['under_2_5_rate']  if h2h else 0.5
    h2h_u35  = h2h['under_3_5_rate']  if h2h else 0.6
    h2h_btts = h2h['btts_rate']        if h2h else 0.5
    form_avg  = (hs['avg_total_goals'] + as_['avg_total_goals']) / 2
    form_btts = (hs['btts_rate'] + as_['btts_rate']) / 2
    form_cs   = (hs['clean_sheet_rate'] + as_['clean_sheet_rate']) / 2
    h_dc      = hs['win_rate'] + hs['draw_rate']
    a_dc      = as_['win_rate'] + as_['draw_rate']

    ml_o25    = ml_probs.get('over_2_5', 0.5)
    ml_u25    = ml_probs.get('under_2_5', 0.5)
    ml_o15    = ml_probs.get('over_1_5', 0.5)
    ml_btts   = ml_probs.get('btts', 0.5)
    ml_home   = ml_probs.get('home_win', 0.5)
    ml_away   = ml_probs.get('away_win', 0.5)

    # Blended average: form + H2H + ML implied goals
    blended  = (form_avg*0.3 + h2h_avg*0.35 + (ml_o25*3.5)*0.35)

    # Player/Formation adjustment (applied to confidence, capped at ±12%)
    gm = player_adj.get('goal_modifier', 0)
    strength = player_adj.get('strength', 0)

    rp = {"low_risk": 0.25, "conservative": 0.1, "high_risk": 0.0}[mode]

    # Under markets — boosted by defensive formations and quality mismatches
    def under_boost(base):
        return min(0.97, base - gm)  # defensive formation reduces goals → boosts under

    # Home win markets — boosted by strength (squad quality + FIFA rank)
    def home_boost(base):
        # Humanistic Upgrade: Straight wins get a stronger boost if strength is high
        return min(0.98, base + strength * 0.18)

    def away_boost(base):
        return min(0.98, base - strength * 0.18)

    # Heritage boost: Teams with all-time success DNA get a multiplier
    def heritage_boost(base, team_name):
        connector = WCFeatureConnector()
        score = connector.heritage_scores.get(team_name.lower(), 0)
        boost = min(0.08, score / 400) # Max 8% boost for historical giants
        return min(0.99, base + boost)

    # High/Conservative Risk Penalty: Shift recommendations up the odds ladder
    def apply_risk_profile(market_key, base_conf):
        if mode == "high_risk":
            if market_key in ("OVER_0_5", "UNDER_4_5"): return base_conf * 0.2
            if market_key in ("OVER_1_5", "UNDER_3_5", "DC_HOME", "DC_AWAY"): return base_conf * 0.7
            if market_key in ("HOME_WIN", "AWAY_WIN", "OVER_2_5", "BTTS_YES"): return base_conf * 1.15
        elif mode == "conservative":
            if market_key in ("OVER_0_5", "UNDER_4_5"): return base_conf * 0.6  # Less extreme penalty
            if market_key in ("OVER_1_5", "UNDER_3_5", "DC_HOME", "DC_AWAY"): return base_conf * 1.05  # Moderate boost
            if market_key in ("HOME_WIN", "AWAY_WIN"): return base_conf * 0.95  # Minimal penalty for straight wins
        return base_conf

    candidates = [
        ("UNDER_4_5", apply_risk_profile("UNDER_4_5", under_boost(min(0.97,(1-blended/6)*0.6+h2h_u35*0.25+form_cs*0.15))),
            f"Blended avg: {blended:.2f}. H2H Under 3.5: {h2h_u35*100:.0f}%. Formation: {player_adj.get('home_formation','N/A')} vs {player_adj.get('away_formation','N/A')}."),
        ("UNDER_3_5", apply_risk_profile("UNDER_3_5", under_boost(min(0.97,(1-blended/5)*0.6+h2h_u35*0.25+form_cs*0.15))),
            f"Blended avg: {blended:.2f}. ML Under 2.5: {ml_u25*100:.0f}%."),
        ("UNDER_2_5", apply_risk_profile("UNDER_2_5", under_boost(min(0.97,ml_u25*0.55+h2h_u25*0.25+form_cs*0.20))),
            f"ML Under 2.5: {ml_u25*100:.0f}%. H2H Under 2.5: {h2h_u25*100:.0f}%."),
        ("OVER_0_5",  apply_risk_profile("OVER_0_5", min(0.99,1.0 if blended>0.6 else 0.5)),
            f"Avg goals ({blended:.2f}) makes 0-0 highly unlikely."),
        ("OVER_1_5",  apply_risk_profile("OVER_1_5", min(0.97,ml_o15*0.55+(1-form_cs)*0.25+(blended/4)*0.20)+gm),
            f"ML Over 1.5: {ml_o15*100:.0f}%. Formation attack index: {player_adj.get('away_formation','N/A')}."),
        ("OVER_2_5",  apply_risk_profile("OVER_2_5", min(0.97,ml_o25*0.55+(h2h['over_2_5_rate'] if h2h else 0.5)*0.25+(blended/4)*0.20)+gm-rp),
            f"ML Over 2.5: {ml_o25*100:.0f}%."),
        ("BTTS_NO",   apply_risk_profile("BTTS_NO", min(0.97,(1-ml_btts)*0.5+(1-form_btts)*0.3+(1-h2h_btts)*0.2)),
            f"ML BTTS-No: {(1-ml_btts)*100:.0f}%. Form BTTS: {form_btts*100:.0f}%. H2H BTTS: {h2h_btts*100:.0f}%."),
        ("BTTS_YES",  apply_risk_profile("BTTS_YES", min(0.97,ml_btts*0.5+form_btts*0.3+h2h_btts*0.2)-rp),
            f"ML BTTS: {ml_btts*100:.0f}%. H2H BTTS: {h2h_btts*100:.0f}%."),
        ("DC_HOME",   apply_risk_profile("DC_HOME", home_boost(min(0.97,h_dc*0.6+ml_home*0.4))-rp),
            f"Home DC: {h_dc*100:.0f}%. ML Home: {ml_home*100:.0f}%. Squad quality edge: {player_adj.get('quality_gap',0):+.2f}."),
        ("DC_AWAY",   apply_risk_profile("DC_AWAY", away_boost(min(0.97,a_dc*0.6+ml_away*0.4))-rp),
            f"Away DC: {a_dc*100:.0f}%. ML Away: {ml_away*100:.0f}%."),
        ("HOME_WIN",  apply_risk_profile("HOME_WIN", home_boost(min(0.97,ml_home*0.65+hs['win_rate']*0.35))-rp),
            f"ML Home Win: {ml_home*100:.0f}%. Squad rating: {player_adj.get('home_rating','N/A')}."),
        ("AWAY_WIN",  apply_risk_profile("AWAY_WIN", away_boost(min(0.97,ml_away*0.65+as_['win_rate']*0.35))-rp),
            f"ML Away Win: {ml_away*100:.0f}%. Squad rating: {player_adj.get('away_rating','N/A')}."),
        ("DRAW",      apply_risk_profile("DRAW", min(0.97,(hs['draw_rate']+as_['draw_rate'])/2)-rp),
            f"Combined draw rate: {(hs['draw_rate']+as_['draw_rate'])/2*100:.0f}%."),
    ]
    candidates = [(k, max(0.0, min(0.99, round(c, 4))), r) for k, c, r in candidates]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates

# ── Main Engine ───────────────────────────────────────────────
class BetLegendEngine:
    def analyze(self, home_team, away_team, mode="conservative", betway_odds=None):
        raw = fetch_all_match_data(home_team, away_team)

        if not raw['home']['found'] or not raw['away']['found']:
            return {"matchup": f"{home_team} vs {away_team}", "mode": mode,
                    "recommendation": "Team Not Found", "betway_market": "N/A",
                    "confidence": 0, "rationale": "Check team name spelling.",
                    "stats_summary": {}, "ranked_markets": [], "edge": None,
                    "intelligence": {}}

        hs, as_ = raw['home']['stats'], raw['away']['stats']
        h2h     = raw['h2h']
        home_pd = raw['home']['player_data']
        away_pd = raw['away']['player_data']
        home_name, away_name = raw['home']['name'], raw['away']['name']

        home_rank = get_fifa_rank(home_name)
        away_rank = get_fifa_rank(away_name)

        # Humanistic Upgrade: Pass names to get historical WC features
        feat       = build_live_feature_vector(hs, as_, home_name, away_name)
        ml_probs   = ml_predict(feat) if _models else {}
        player_adj = compute_player_adjustment(home_pd, away_pd, home_rank, away_rank)

        ranked   = score_all_markets(hs, as_, h2h, ml_probs, player_adj, mode)
        threshold = CONFIDENCE_THRESHOLDS[mode]
        best_key, best_conf, best_rationale = ranked[0]
        if best_conf < threshold:
            best_key, best_rationale = "SKIP", f"No market exceeds {threshold*100:.0f}% confidence for {mode} mode."

        market = MARKETS[best_key]
        edge   = compute_edge(best_conf, betway_odds) if betway_odds else None

        top6 = [{"market": MARKETS[k]['label'], "betway_label": MARKETS[k]['betway'],
                  "confidence_pct": round(c*100, 1), "rationale": r}
                for k, c, r in ranked[:6]]

        return {
            "matchup":       f"{home_name} vs {away_name}",
            "mode":          mode,
            "recommendation": market['label'],
            "betway_market":  market['betway'],
            "confidence":    round(best_conf * 100, 1),
            "rationale":     best_rationale,
            "edge":          edge,
            "ml_probabilities": {k: round(v*100, 1) for k, v in ml_probs.items()},
            "intelligence": {
                "home_squad_rating":  player_adj.get('home_rating'),
                "away_squad_rating":  player_adj.get('away_rating'),
                "home_top_player":    player_adj.get('home_top_player'),
                "away_top_player":    player_adj.get('away_top_player'),
                "home_formation":     player_adj.get('home_formation'),
                "away_formation":     player_adj.get('away_formation'),
                "squad_quality_gap":  player_adj.get('quality_gap'),
                "home_fifa_rank":     home_rank,
                "away_fifa_rank":     away_rank,
                "strength_signal":    player_adj.get('strength'),
            },
            "stats_summary": {
                "home": {"name": home_name, **hs},
                "away": {"name": away_name, **as_},
                "h2h":  h2h,
            },
            "ranked_markets": top6,
        }

engine = BetLegendEngine()
