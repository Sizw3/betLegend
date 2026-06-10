"""
sportdb_proxy.py - Proxy for SportDB.dev API
Handles live scores and fixture discovery.
"""
import httpx
import os
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/sportdb")

API_KEY = "tPquD9W4TkqF4eIgFOAy1cUMyI0VpH7tdZirRnDV"
BASE_URL = "https://api.sportdb.dev/api/flashscore"

@router.get("/football")
async def get_football(offset: int = 0, tz: int = 0):
    """
    Fetches football matches for any day offset (0: today, 1: tomorrow, etc.)
    """
    url = f"{BASE_URL}/football/live" # The /live endpoint handles offsets for fixtures too
    params = {"offset": offset, "tz": tz}
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=15.0)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_sportdb(q: str):
    """
    Shortcut search for competitions or teams
    """
    url = f"{BASE_URL}/search"
    params = {"q": q}
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=15.0)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/match-details/{event_id}")
async def get_match_details(event_id: str):
    """
    Proxies match details
    """
    url = f"{BASE_URL}/football/details"
    params = {"id": event_id}
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=15.0)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
