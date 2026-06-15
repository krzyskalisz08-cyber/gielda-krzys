from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
import threading
import time
import os

app = FastAPI(title="Giełda II RP - Realna Symulacja Chronologiczna")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- TWOJA TABELA TRENDÓW (50% spadków, 15 dni) ---
trend_map = {
    "PORT":  [1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1],
    "MAGI":  [-1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, 1, 1],
    "COP":   [1, -1, -1, 1, 1, -1, 1, -1, 1, 1, -1, -1, 1, -1, -1],
    "AZOT":  [-1, -1, 1, 1, -1, 1, -1, 1, 1, -1, 1, -1, 1, -1, 1],
    "STAL":  [1, 1, -1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, -1, -1],
    "KOLEJ": [-1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, 1],
    "AUTO":  [1, -1, 1, -1, 1, 1, -1, -1, 1, -1, 1, -1, 1, 1, -1],
    "MIEDZ": [-1, 1, 1, -1, -1, 1, 1, -1, 1, 1, -1, 1, -1, -1, 1],
    "SREBRO":[1, -1, 1, 1, -1, -1, 1, 1, -1, -1, 1, 1, -1, 1, -1],
    "ZLOTO": [-1, -1, 1, -1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, 1],
    "USD":   [1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1]
}

class Transaction(BaseModel):
    username: str; symbol: str; type: str; amount: float; leverage: int
class Message(BaseModel):
    player: str; text: str
class Article(BaseModel):
    title: str; content: str
class CreatePlayer(BaseModel):
    username: str; password: str
class AddMoney(BaseModel):
    username: str; amount: float
class SetPercentChange(BaseModel):
    symbol: str; percent: float
class DeletePlayer(BaseModel):
    username: str

market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "desc": "Port Gdynia..."},
    "MAGI": {"name": "Magistrala", "base_price": 80.0, "desc": "Linia 201..."},
    "COP": {"name": "COP", "base_price": 150.0, "desc": "Okręg przemysłowy..."},
    "AZOT": {"name": "Azoty", "base_price": 60.0, "desc": "Fabryka..."},
    "STAL": {"name": "Stalowa Wola", "base_price": 100.0, "desc": "Zakłady..."},
    "KOLEJ": {"name": "Koleje", "base_price": 120.0, "desc": "PKP..."},
    "AUTO": {"name": "PZInż", "base_price": 70.0, "desc": "Warszawa..."},
    "ZLOTO": {"name": "Złoto", "base_price": 45.0, "desc": "Rezerwy..."},
    "MIEDZ": {"name": "Miedź", "base_price": 20.0, "desc": "Metal..."},
    "SREBRO": {"name": "Srebro", "base_price": 25.0, "desc": "Mennica..."},
    "USD": {"name": "Dolar", "base_price": 5.20, "desc": "Waluta..."}
}

prices = []
candles_history = {} 
players = {}  
messages = []
articles = [{"title": "System", "content": "Wprowadzono stabilny harmonogram 50/50."}]
game_state = {"current_day": 1, "player_trend_impulse": {}}

def init_game():
    players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio_long": {}, "portfolio_short": {}}
    for symbol, data in market_assets.items():
        prices.append({"symbol": symbol, "name": data["name"], "price": data["base_price"], "desc": data["desc"], "daily_change": 0.0})
        game_state["player_trend_impulse"][symbol] = 0.0
        bp = data["base_price"]
        candles_history[symbol] = {"5m": [["12:00", bp, bp+0.5, bp-0.5, bp]], "1h": [["12:00", bp, bp+1, bp-1, bp]], "1d": [["Dzień 1", bp, bp+2, bp-2, bp]]}
init_game()

# --- ZAKTUALIZOWANY SILNIK RYNKU (ZGODNIE Z TWOJĄ TABELĄ) ---
def market_engine():
    tick_count = 15
    while True:
        time.sleep(4)
        tick_count += 1
        day = game_state["current_day"]
        day_idx = min(day - 1, 14)
        
        for p in prices:
            sym = p["symbol"]
            open_p = p["price"]
            
            # Pobieramy kierunek z tabeli
            direction = trend_map.get(sym, [1]*15)[day_idx]
            
            # Mechanizm: 9.5% limit dzienny / 15 ticków + impuls gracza
            tick_change = (0.095 / 15) * direction
            player_change = (game_state["player_trend_impulse"].get(sym, 0.0) / 40.0)
            noise = random.uniform(-0.001, 0.001)
            
            total_change = tick_change + player_change + noise
            close_p = round(max(open_p * (1 + total_change), 0.02), 2)
            
            p["price"] = close_p
            p["daily_change"] = round(((close_p - 100.0) / 100.0) * 100, 2)
            game_state["player_trend_impulse"][sym] *= 0.95
            
            # Świece (zachowano Twoją logikę historyczną)
            high_p = round(max(open_p, close_p) + random.uniform(0.01, 0.05), 2)
            low_p = round(min(open_p, close_p) - random.uniform(0.01, 0.05), 2)
            hist = candles_history[sym]["5m"]
            hist.append([f"12:{tick_count%60:02d}", open_p, high_p, low_p, close_p])
            if len(hist) > 15: candles_history[sym]["5m"] = hist[-15:]

        # Margin Call (zostawione bez zmian)
        for username, player in list(players.items()):
            for sym, pos_list in player.get("portfolio_long", {}).items():
                price = next((x["price"] for x in prices if x["symbol"] == sym), 1.0)
                for pos in list(pos_list):
                    if (pos["buy_price"] - price) * pos["amount"] * pos["leverage"] >= pos["margin_allocated"]:
                        pos_list.remove(pos)

threading.Thread(target=market_engine, daemon=True).start()

# Tutaj wklej resztę swoich endpointów (od @app.get("/") do końca pliku z poprzedniego kodu)