"""
model_trainer.py - XGBoost Training Pipeline
Downloads multi-league, multi-season data from football-data.co.uk
Trains calibrated XGBoost classifiers for 6 Betway markets
"""
import pandas as pd
import numpy as np
import requests
import io
import os
import pickle
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

DATA_URLS = [
    "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2223/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2122/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2021/E0.csv",
    "https://www.football-data.co.uk/mmz4281/2425/D1.csv",
    "https://www.football-data.co.uk/mmz4281/2324/D1.csv",
    "https://www.football-data.co.uk/mmz4281/2223/D1.csv",
    "https://www.football-data.co.uk/mmz4281/2425/SP1.csv",
    "https://www.football-data.co.uk/mmz4281/2324/SP1.csv",
    "https://www.football-data.co.uk/mmz4281/2223/SP1.csv",
    "https://www.football-data.co.uk/mmz4281/2425/I1.csv",
    "https://www.football-data.co.uk/mmz4281/2324/I1.csv",
    "https://www.football-data.co.uk/mmz4281/2425/F1.csv",
    "https://www.football-data.co.uk/mmz4281/2324/F1.csv",
]

TARGETS = {
    "btts":      lambda df: ((df["FTHG"] > 0) & (df["FTAG"] > 0)).astype(int),
    "over_2_5":  lambda df: (df["FTHG"] + df["FTAG"] > 2).astype(int),
    "over_1_5":  lambda df: (df["FTHG"] + df["FTAG"] > 1).astype(int),
    "under_2_5": lambda df: (df["FTHG"] + df["FTAG"] < 3).astype(int),
    "home_win":  lambda df: (df["FTR"] == "H").astype(int),
    "away_win":  lambda df: (df["FTR"] == "A").astype(int),
}

def download_data():
    dfs = []
    for url in DATA_URLS:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text), on_bad_lines='skip')
                if len(df) > 10:
                    dfs.append(df)
                    print(f"  ✅ {url.split('/')[-2]}/{url.split('/')[-1]}: {len(df)} matches")
        except Exception as e:
            print(f"  ⚠️ Failed: {url.split('/')[-1]} ({e})")
    return pd.concat(dfs, ignore_index=True) if dfs else None

def build_features(df):
    needed = ['HomeTeam','AwayTeam','FTHG','FTAG','FTR']
    df = df.dropna(subset=needed).copy().reset_index(drop=True)
    for col in ['HS','AS','HST','AST']:
        if col not in df.columns:
            df[col] = np.nan
    
    team_hist = {}

    def get_stats(team, n=7):
        hist = team_hist.get(team, [])[-n:]
        if not hist:
            return dict(avg_gf=1.3, avg_ga=1.2, avg_sot=4.2, win_rate=0.4,
                        draw_rate=0.28, btts_rate=0.52, over_rate=0.52,
                        cs_rate=0.28, form=1.5)
        weights = np.array([0.85 ** (len(hist)-1-i) for i in range(len(hist))])
        weights /= weights.sum()
        gfs   = np.array([h['gf'] for h in hist])
        gas   = np.array([h['ga'] for h in hist])
        sots  = np.array([h.get('sot', 4) for h in hist])
        pts   = np.array([h['pts'] for h in hist])
        return dict(
            avg_gf=float(np.dot(gfs, weights)),
            avg_ga=float(np.dot(gas, weights)),
            avg_sot=float(np.dot(sots, weights)),
            win_rate=float(np.mean([h['res']=='W' for h in hist])),
            draw_rate=float(np.mean([h['res']=='D' for h in hist])),
            btts_rate=float(np.mean([h['gf']>0 and h['ga']>0 for h in hist])),
            over_rate=float(np.mean([h['gf']+h['ga']>2 for h in hist])),
            cs_rate=float(np.mean([h['ga']==0 for h in hist])),
            form=float(np.dot(pts, weights)),
        )

    rows = []
    for _, row in df.iterrows():
        ht, at = row['HomeTeam'], row['AwayTeam']
        hs = get_stats(ht)
        as_ = get_stats(at)
        feat = {}
        for k, v in hs.items(): feat[f'h_{k}'] = v
        for k, v in as_.items(): feat[f'a_{k}'] = v
        feat['comb_goals']    = (hs['avg_gf'] + as_['avg_gf'] + hs['avg_ga'] + as_['avg_ga']) / 2
        feat['h_attack_edge'] = hs['avg_gf'] - as_['avg_ga']
        feat['a_attack_edge'] = as_['avg_gf'] - hs['avg_ga']
        feat['btts_prob']     = (hs['btts_rate'] + as_['btts_rate']) / 2
        feat['form_diff']     = hs['form'] - as_['form']
        feat['cs_combined']   = (hs['cs_rate'] + as_['cs_rate']) / 2
        rows.append(feat)

        hg, ag, ftr = int(row['FTHG']), int(row['FTAG']), row['FTR']
        if ht not in team_hist: team_hist[ht] = []
        team_hist[ht].append({'gf':hg,'ga':ag,'sot':row.get('HST',4),'res':'W' if ftr=='H' else ('D' if ftr=='D' else 'L'),'pts':3 if ftr=='H' else (1 if ftr=='D' else 0)})
        if at not in team_hist: team_hist[at] = []
        team_hist[at].append({'gf':ag,'ga':hg,'sot':row.get('AST',4),'res':'W' if ftr=='A' else ('D' if ftr=='D' else 'L'),'pts':3 if ftr=='A' else (1 if ftr=='D' else 0)})

    return pd.DataFrame(rows), df

def train_models():
    os.makedirs(MODEL_DIR, exist_ok=True)
    print("📥 Downloading match data from football-data.co.uk...")
    raw = download_data()
    if raw is None or len(raw) < 200:
        print("❌ Insufficient data."); return False
    print(f"📊 Total matches loaded: {len(raw)}")
    print("⚙️  Engineering recency-weighted features...")
    X, clean_df = build_features(raw)
    
    model_results = {}
    feature_cols = list(X.columns)
    
    for name, target_fn in TARGETS.items():
        try:
            y = target_fn(clean_df)
            mask = ~(X.isna().any(axis=1) | y.isna())
            Xc, yc = X[mask], y[mask]
            if len(Xc) < 100: continue
            X_tr, X_te, y_tr, y_te = train_test_split(Xc, yc, test_size=0.2, random_state=42)
            
            base = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.04,
                                 subsample=0.8, colsample_bytree=0.75,
                                 eval_metric='logloss', random_state=42)
            clf = CalibratedClassifierCV(base, cv=3, method='isotonic')
            clf.fit(X_tr, y_tr)
            
            acc = accuracy_score(y_te, clf.predict(X_te))
            auc = roc_auc_score(y_te, clf.predict_proba(X_te)[:,1])
            print(f"  🎯 {name:12s}  Acc={acc:.3f}  AUC={auc:.3f}  n={len(Xc)}")
            
            with open(os.path.join(MODEL_DIR, f"{name}.pkl"), 'wb') as f:
                pickle.dump(clf, f)
            model_results[name] = {'acc': round(acc,3), 'auc': round(auc,3)}
        except Exception as e:
            print(f"  ⚠️  {name} skipped: {e}")
    
    with open(os.path.join(MODEL_DIR, "feature_cols.pkl"), 'wb') as f:
        pickle.dump(feature_cols, f)
    
    print(f"\n✅ {len(model_results)} models saved to ./models/")
    return model_results

if __name__ == "__main__":
    train_models()
