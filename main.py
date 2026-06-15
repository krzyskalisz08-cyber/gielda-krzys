from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import random
import threading
import time
import os

app = FastAPI(title="Giełda Krzys")

# Obsługa CORS, aby aplikacja mogła odbierać zapytania z dowolnego urządzenia
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELE DANYCH ----------------
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

# ---------------- BAZA DANYCH W PAMIĘCI ----------------
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

# ---------------- INICJALIZACJA RYNKU ----------------
def init_market():
    for c in start_companies:
        companies.append(c)
        prices.append({
            "symbol": c["symbol"],
            "price": round(random.uniform(50, 200), 2),
            "timestamp": datetime.utcnow()
        })

    # Domyślny profil gracza
    if not any(p["id"] == 1 for p in players):
        players.append({"id": 1, "name": "krzys", "balance": 10000.0})
    portfolio[1] = {}

init_market()

# ---- SERWOWANIE FRONTENDU (Strona główna widoczna na telefonie) ----
@app.get("/", response_class=HTMLResponse)
def get_frontend():
    # Pobiera dokładną ścieżkę do folderu, w którym znajduje się main.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "index.html")
    
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Błąd: Serwer działa, ale nie znaleziono pliku index.html w katalogu głównym</h1>"

# ---------------- ENDPOINTY API ----------------
@app.get("/prices")
def get_prices():
    return prices

@app.get("/portfolio/{player_id}")
def get_portfolio(player_id: int):
    return portfolio.get(player_id, {})

@app.get("/ranking")
def ranking():
    return sorted(players, key=lambda x: x["balance"], reverse=True)

@app.post("/transactions")
def add_transaction(tx: Transaction):
    price_obj = next((p for p in prices if p["symbol"] == tx.symbol), None)
    player = next((p for p in players if p["id"] == tx.player_id), None)

    if not player:
        return {"error": "Nie znaleziono takiego gracza"}
    if not price_obj:
        return {"error": "Brak wyceny dla podanego instrumentu"}

    current_price = price_obj["price"]

    if tx.type == "buy":
        cost = current_price * tx.amount
        if player["balance"] < cost:
            return {"error": "Niewystarczające środki na koncie"}
        
        player["balance"] -= cost
        portfolio[tx.player_id][tx.symbol] = portfolio[tx.player_id].get(tx.symbol, 0.0) + tx.amount

    elif tx.type == "sell":
        owned = portfolio[tx.player_id].get(tx.symbol, 0.0)
        if owned < tx.amount:
            return {"error": "Nie posiadasz tylu akcji na sprzedaż"}
            
        portfolio[tx.player_id][tx.symbol] -= tx.amount
        player["balance"] += current_price * tx.amount

    return {"status": "ok"}

@app.get("/messages")
def get_messages():
    return messages[-50:]

@app.post("/messages")
def add_message(msg: Message):
    messages.append(msg)
    return {"status": "ok"}

# ---------------- SYMULACJA RYNKU LIVE (WĄTEK) ----------------
def market_loop():
    while True:
        time.sleep(3)
        for p in prices:
            move = random.uniform(-0.015, 0.015)
            p["price"] = round(max(p["price"] * (1 + move), 1.0), 2)
            p["timestamp"] = datetime.utcnow()

threading.Thread(target=market_loop, daemon=True).start()