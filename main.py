from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import threading
import time

app = FastAPI(title="Giełda II RP - Wersja Stabilna")

# Włączamy CORS, aby frontend mógł się łączyć
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- TABELA TRENDÓW (Twoje założenia: 50% spadków, 15 dni, przewidywalność) ---
# 1 = Wzrost, -1 = Spadek. Każda lista sumuje się tak, aby zachować balans 50/50.
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

# --- STANU GRY ---
players = {} # Przechowuje: {"nick": {"balance": 1000, "portfolio": {...}}}
prices = [{"symbol": sym, "price": 100.0} for sym in trend_map.keys()]
game_state = {"current_day": 1}

# --- SILNIK RYNKU (Odświeżanie co 4 sekundy) ---
def market_engine():
    while True:
        time.sleep(4)
        # Aktualizacja dnia (symulacja 15 dni gry)
        if game_state["current_day"] < 15:
            game_state["current_day"] += 1
        
        day_idx = game_state["current_day"] - 1
        
        for p in prices:
            sym = p["symbol"]
            direction = trend_map.get(sym, [1]*15)[day_idx]
            
            # Max 9.5% dziennie / 15 ticków = zmiana na tick
            tick_change = (0.095 / 15) * direction
            # Drobny szum rynkowy (0.1%), żeby nie wyglądało jak sztuczna linia
            noise = random.uniform(-0.001, 0.001)
            
            p["price"] = round(p["price"] * (1 + tick_change + noise), 2)
            if p["price"] < 1: p["price"] = 1.0 # Minimalna cena

threading.Thread(target=market_engine, daemon=True).start()

# --- MODELE DANYCH ---
class Transaction(BaseModel):
    username: str
    symbol: str
    amount: float
    type: str 

# --- API ---
@app.post("/api/register")
def register(data: dict):
    username = data.get("username")
    if username in players: return {"error": "Gracz istnieje"}
    players[username] = {"balance": 1000.0, "portfolio": {}}
    return {"status": "ok"}

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    # 1. WALIDACJA ANTY-CHEAT
    if tx.amount <= 0: return {"error": "Ilość musi być dodatnia"}
    
    player = players.get(tx.username)
    if not player: return {"error": "Gracz nie istnieje"}
    
    asset = next((a for a in prices if a["symbol"] == tx.symbol), None)
    if not asset: return {"error": "Aktywo nie istnieje"}
    
    cost = tx.amount * asset["price"]
    
    # 2. OPERACJE
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
    return {"prices": prices, "day": game_state["current_day"]}