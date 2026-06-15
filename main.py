from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import random
import threading
import time

app = FastAPI(title="Giełda Krzys")

# 🔥 CORS (frontend działa z telefonu / przeglądarki)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELE ----------------
class Company(BaseModel):
    name: str
    symbol: str
    sector: str

class Transaction(BaseModel):
    player_id: int
    symbol: str
    type: str
    amount: float

class Message(BaseModel):
    player: str
    text: str

# ---------------- DANE ----------------
companies = []
prices = []
players = []
messages = []
portfolio = {}

start_companies = [
    {"name": "Microsoft", "symbol": "MSFT", "sector": "Technology"},
    {"name": "Intel", "symbol": "INTC", "sector": "Technology"},
    {"name": "IBM", "symbol": "IBM", "sector": "Technology"},
    {"name": "Coca-Cola", "symbol": "KO", "sector": "Beverages"},
    {"name": "Ford", "symbol": "F", "sector": "Automotive"},
]

# ---------------- INIT ----------------
def init_market():
    for c in start_companies:
        companies.append(c)
        prices.append({
            "symbol": c["symbol"],
            "price": round(random.uniform(50, 200), 2),
            "timestamp": datetime.utcnow()
        })

    players.append({"id": 1, "name": "krzys", "balance": 10000})
    portfolio[1] = {}

init_market()

# ---------------- ROOT (TO BRAKOWAŁO) ----------------
@app.get("/")
def root():
    return {"status": "Backend działa"}

# ---------------- API ----------------
@app.get("/prices")
def get_prices():
    return prices

@app.get("/portfolio/{player_id}")
def get_portfolio(player_id: int):
    return portfolio.get(player_id, {})

@app.get("/ranking")
def ranking():
    return players

@app.post("/transactions")
def add_transaction(tx: Transaction):
    price = next((p for p in prices if p["symbol"] == tx.symbol), None)
    player = players[0]

    if not price:
        return {"error": "brak ceny"}

    if tx.type == "buy":
        cost = price["price"] * tx.amount
        player["balance"] -= cost
        portfolio[tx.player_id][tx.symbol] = portfolio[tx.player_id].get(tx.symbol, 0) + tx.amount

    if tx.type == "sell":
        portfolio[tx.player_id][tx.symbol] -= tx.amount
        player["balance"] += price["price"] * tx.amount

    return {"status": "ok"}

@app.get("/messages")
def get_messages():
    return messages

@app.post("/messages")
def add_message(msg: Message):
    messages.append(msg)
    return {"status": "ok"}

# ---------------- LIVE MARKET ----------------
def market_loop():
    while True:
        time.sleep(5)
        for p in prices:
            move = random.uniform(-0.02, 0.02)
            p["price"] = round(max(p["price"] * (1 + move), 0.1), 2)
            p["timestamp"] = datetime.utcnow()

threading.Thread(target=market_loop, daemon=True).start()