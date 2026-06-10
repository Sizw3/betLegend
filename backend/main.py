from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from strategy import engine
from backtester import run_backtest
from scraper import fetch_today_matches
from typing import Literal, Optional

app = FastAPI(title="Bet Legend API v3", description="XGBoost + Evolutionary Hybrid — Betway Compatible")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class MatchupRequest(BaseModel):
    home_team: str
    away_team: str
    mode: Literal["low_risk", "conservative", "high_risk"] = "conservative"
    betway_odds: Optional[float] = Field(default=None)

class BacktestRequest(BaseModel):
    mode: Literal["low_risk", "conservative", "high_risk"] = "conservative"
    stake: float = Field(default=10.0, ge=1.0, le=1000.0)

@app.post("/api/analyze")
def analyze_matchup(matchup: MatchupRequest):
    return engine.analyze(matchup.home_team, matchup.away_team, matchup.mode, matchup.betway_odds)

@app.post("/api/backtest")
def backtest(req: BacktestRequest):
    return run_backtest(req.mode, req.stake)

@app.get("/api/upcoming")
def upcoming_matches():
    return fetch_today_matches()

@app.get("/api/health")
def health():
    from strategy import _models
    return {"status": "ok", "version": "3.0.0", "models_loaded": list(_models.keys())}
