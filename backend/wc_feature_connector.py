"""
wc_feature_connector.py - Connects teams to local WC dataset features (Now with Heritage Score)
"""
import pandas as pd
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(PROJECT_DIR, "dataset")
TRAIN_PATH = os.path.join(DATASET_DIR, "train.csv")
TEST_PATH = os.path.join(DATASET_DIR, "test.csv")
HERITAGE_PATH = os.path.join(PROJECT_DIR, "WorldCups.csv")

class WCFeatureConnector:
    def __init__(self):
        self.df_train = pd.read_csv(TRAIN_PATH) if os.path.exists(TRAIN_PATH) else pd.DataFrame()
        self.df_test  = pd.read_csv(TEST_PATH) if os.path.exists(TEST_PATH) else pd.DataFrame()
        self.df_history = pd.read_csv(HERITAGE_PATH) if os.path.exists(HERITAGE_PATH) else pd.DataFrame()
        
        # 1. 2002-2026 Core Stats
        self.combined = pd.concat([self.df_train, self.df_test], ignore_index=True)
        self.combined = self.combined.sort_values('version', ascending=False).drop_duplicates(subset=['team'])
        self.team_map = {row['team'].lower(): row for _, row in self.combined.iterrows()}

        # 2. 1930-2014 Heritage Aggregation
        self.heritage_scores = self._calculate_heritage()

    def _calculate_heritage(self):
        """
        Calculates a Heritage Score based on all-time tournament performance.
        Winner: 10, RunnerUp: 5, Third: 3, Fourth: 1
        """
        scores = {}
        if self.df_history.empty:
            return scores
        
        # Function to clean and normalize names for historical mapping
        def clean(name):
            if not isinstance(name, str): return ""
            n = name.strip().lower()
            if n == "germany fr": return "germany"
            if n == "soviet union": return "russia"
            if n == "czechoslovakia": return "czechia"
            if n == "yugoslavia": return "serbia"
            return n

        for _, row in self.df_history.iterrows():
            w, r, t, f = clean(row['Winner']), clean(row['RunnersUp']), clean(row['Third']), clean(row['Fourth'])
            scores[w] = scores.get(w, 0) + 10
            scores[r] = scores.get(r, 0) + 5
            scores[t] = scores.get(t, 0) + 3
            scores[f] = scores.get(f, 0) + 1
        return scores

    def get_features(self, team_name):
        team_name_lower = team_name.lower()
        heritage = self.heritage_scores.get(team_name_lower, 0)
        
        if team_name_lower in self.team_map:
            row = self.team_map[team_name_lower]
            return {
                "wc_rank": row.get('fifa_rank_pre_tournament', 100),
                "wc_value": row.get('squad_total_market_value_eur', 0) / 1e6,
                "wc_age": row.get('squad_avg_age', 27.0),
                "wc_exp": row.get('world_cup_participations_before', 0),
                "wc_titles": row.get('world_cup_titles_before', 0),
                "wc_success_rate": (row.get('groups_passed_before', 0) + 1) / (row.get('world_cup_participations_before', 0) + 1),
                "heritage_score": heritage
            }
        
        # Defaults for unknown teams
        return {
            "wc_rank": 100,
            "wc_value": 0,
            "wc_age": 27.0,
            "wc_exp": 0,
            "wc_titles": 0,
            "wc_success_rate": 0.1,
            "heritage_score": heritage
        }
