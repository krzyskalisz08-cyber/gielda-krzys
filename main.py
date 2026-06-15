from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import threading
import time

app = FastAPI()

# CORS dla frontendu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# HARMONOGRAM TRENDÓW (Twoja tabela - 50% wzrostów/spadków)
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
    "ZLOTO": [-1, -1, 1, -1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, 1]
}

# DANE GRY
players = {}
prices = [{"symbol": sym, "price": 100.0} for sym in trend_map.keys()]
game_state = {"current_day": 1}

# SILNIK RYNKU
def market_engine():
    while True:
        time.sleep(4)
        if game_state["current_day"] < 15:
            game_state["current_day"] += 1
        
        day_idx = game_state["current_day"] - 1
        for p in prices:
            direction = trend_map.get(p["symbol"], [1]*15)[day_idx]
            tick_change = (0.095 / 15) * direction
            noise = random.uniform(-0.0005, 0.0005)
            p["price"] = round(p["price"] * (1 + tick_change + noise), 2)
            if p["price"] < 1: p["price"] = 1.0

threading.Thread(target=market_engine, daemon=True).start()

# MODELE API
class Register(BaseModel):
    username: str

class Transaction(BaseModel):
    username: str
    symbol: str
    amount: float
    type: str

# ENDPOINTY
@app.post("/api/register")
def register(data: Register):
    if data.username not in players:
        players[data.username] = {"balance": 1000.0, "portfolio": {}}
    return {"status": "ok"}

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    if tx.amount <= 0: return {"error": "Zła kwota"}
    player = players.get(tx.username)
    if not player: return {"error": "Gracz nie istnieje"}
    
    asset = next((a for a in prices if a["symbol"] == tx.symbol), None)
    cost = tx.amount * asset["price"]
    
    if tx.type == "buy":
        if player["balance"] < cost: return {"error": "Brak środków"}
        player["balance"] -= cost
        player["portfolio"][tx.symbol] = player["portfolio"].get(tx.symbol, 0) + tx.amount
    elif tx.type == "sell":
        if player["portfolio"].get(tx.symbol, 0) < tx.amount: return {"error": "Brak akcji"}
        player["balance"] += cost
        player["portfolio"][tx.symbol] -= tx.amount
    return {"status": "ok"}

@app.get("/api/data")
def get_data():
    return {"prices": prices, "day": game_state["current_day"], "players": players}