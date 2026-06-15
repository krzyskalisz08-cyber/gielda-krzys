from fastapi import FastAPI
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

# --- TWOJA TABELA TRENDÓW ---
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
    username: str
    symbol: str
    type: str
    amount: float
    leverage: int

class Message(BaseModel):
    player: str
    text: str

class Article(BaseModel):
    title: str
    content: str

class CreatePlayer(BaseModel):
    username: str
    password: str

class AddMoney(BaseModel):
    username: str
    amount: float

class SetPercentChange(BaseModel):
    symbol: str
    percent: float

class DeletePlayer(BaseModel):
    username: str

market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "desc": "Kompleks portowy zlokalizowany nad Zatoką Gdańską."},
    "MAGI": {"name": "Magistrala Śląsk-Gdynia", "base_price": 80.0, "desc": "Magistrala kolejowa Herby Nowe – Gdynia."},
    "COP": {"name": "Centralny Okręg Przemysłowy", "base_price": 150.0, "desc": "Okręg przemysłu ciężkiego."},
    "AZOT": {"name": "Zakłady Azotowe Tarnów", "base_price": 60.0, "desc": "Państwowa Fabryka Związków Azotowych."},
    "STAL": {"name": "Stalowa Wola", "base_price": 100.0, "desc": "Zakłady Południowe."},
    "KOLEJ": {"name": "Spółki Kolejowe i Transportowe", "base_price": 120.0, "desc": "Ogólnokrajowa infrastruktura."},
    "AUTO": {"name": "Państwowe Zakłady Inżynierii", "base_price": 70.0, "desc": "Państwowe Zakłady Inżynierii."},
    "ZLOTO": {"name": "Złoto", "base_price": 45.0, "desc": "Kruszec lokacyjny."},
    "MIEDZ": {"name": "Miedź", "base_price": 20.0, "desc": "Metal przemysłowy."},
    "SREBRO": {"name": "Srebro", "base_price": 25.0, "desc": "Kruszec o podwójnym zastosowaniu."},
    "USD": {"name": "Dolar Amerykański", "base_price": 5.20, "desc": "Główna waluta rezerwowa."}
}

prices = []
candles_history = {} 
players = {}  
messages = []
articles = [{"title": "Otwarcie Rynku", "content": "System zsynchronizowany z tabelą trendów."}]
game_state = {"current_day": 1, "player_trend_impulse": {}}

def init_game():
    players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio_long": {}, "portfolio_short": {}}
    players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
    for symbol, data in market_assets.items():
        prices.append({"symbol": symbol, "name": data["name"], "price": data["base_price"], "desc": data["desc"], "daily_change": 0.0})
        game_state["player_trend_impulse"][symbol] = 0.0
        bp = data["base_price"]
        candles_history[symbol] = {"5m": [["12:00", bp, bp+0.5, bp-0.5, bp]], "1h": [["12:00", bp, bp+1, bp-1, bp]], "1d": [["Dzień 1", bp, bp+2, bp-2, bp]]}

init_game()

@app.get("/", response_class=HTMLResponse)
def get_frontend():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f: return f.read()
    return "<h1>Status: Backend działa</h1>"

@app.post("/api/register")
def register_player(cp: CreatePlayer):
    if cp.username in players: return {"error": "Zajęte"}
    players[cp.username] = {"password": cp.password, "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
    return {"status": "ok"}

@app.get("/api/prices")
def get_prices(): return prices

@app.get("/api/candles/{symbol}/{timeframe}")
def get_candles(symbol, timeframe): return candles_history.get(symbol, {}).get(timeframe, [])

@app.get("/api/player/{username}/{password}")
def get_player_data(username, password):
    if username not in players or players[username]["password"] != password: return {"error": "Błąd"}
    return {"balance": players[username]["balance"], "portfolio_long": players[username].get("portfolio_long", {}), "portfolio_short": players[username].get("portfolio_short", {}), "current_day": game_state["current_day"]}

@app.get("/api/admin/players-list")
def admin_get_players(): return [{"username": u, "password": d["password"], "balance": d["balance"]} for u, d in players.items()]

@app.post("/api/admin/delete-player")
def admin_delete_player(dp: DeletePlayer):
    if dp.username in players and dp.username != "admin": del players[dp.username]
    return {"status": "ok"}

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    # (Tutaj wklej dokładnie swój stary kod transakcji, nie chciałem go ruszać)
    return {"status": "ok"}

@app.post("/api/admin/money")
def admin_add_money(data: AddMoney):
    if data.username in players: players[data.username]["balance"] += data.amount
    return {"status": "ok"}

@app.post("/api/admin/change-percent")
def admin_change_percent(data: SetPercentChange):
    idx = next((i for i, p in enumerate(prices) if p["symbol"] == data.symbol), None)
    if idx is not None: prices[idx]["price"] = round(max(prices[idx]["price"] * (1 + data.percent/100.0), 0.01), 2)
    return {"status": "ok"}

@app.post("/api/admin/article")
def admin_add_article(art: Article):
    articles.append({"title": art.title, "content": art.content})
    return {"status": "ok"}

@app.post("/api/admin/next-day")
def next_day():
    if game_state["current_day"] < 15: game_state["current_day"] += 1
    return {"status": "ok"}

@app.get("/api/messages")
def get_messages(): return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    messages.append(msg)
    return {"status": "ok"}

@app.get("/api/articles")
def get_articles(): return articles

# --- SILNIK RYNKU Z TABELĄ 50/50 ---
def market_engine():
    tick_count = 15
    while True:
        time.sleep(4)
        tick_count += 1
        day_idx = min(game_state["current_day"] - 1, 14)
        for p in prices:
            sym = p["symbol"]
            open_p = p["price"]
            direction = trend_map.get(sym, [1]*15)[day_idx]
            
            # 50/50 trend + noise
            change = (0.095 / 15) * direction + random.uniform(-0.001, 0.001)
            close_p = round(max(open_p * (1 + change), 0.02), 2)
            p["price"] = close_p
            p["daily_change"] = round(((close_p - 100.0) / 100.0) * 100, 2)
            
            # Logika świec (zachowana Twoja)
            h, l = max(open_p, close_p) + 0.05, min(open_p, close_p) - 0.05
            hist = candles_history[sym]["5m"]
            hist.append([f"12:{tick_count%60:02d}", open_p, h, l, close_p])
            if len(hist) > 15: candles_history[sym]["5m"] = hist[-15:]

        # Margin Call (Twój kod)
        for u, pl in list(players.items()):
            for sym, pos_list in pl.get("portfolio_long", {}).items():
                cur = next((x["price"] for x in prices if x["symbol"] == sym), 1.0)
                for pos in list(pos_list):
                    if (pos["buy_price"] - cur) * pos["amount"] * pos["leverage"] >= pos["margin_allocated"]:
                        pos_list.remove(pos)

threading.Thread(target=market_engine, daemon=True).start()