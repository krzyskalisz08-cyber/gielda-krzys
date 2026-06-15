from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
import threading
import time
import os

app = FastAPI(title="Giełda II RP - Realna Symulacja Chronologiczna V2")

# Bezpieczne ustawienia CORS dla urządzeń na obozie
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- MODELE PYDANTIC ----
class Transaction(BaseModel):
    username: str
    symbol: str
    type: str  # "BUY" lub "SELL_POSITION"
    amount: float

class Message(BaseModel):
    player: str
    text: str

class CreatePlayer(BaseModel):
    username: str
    password: str

class AddMoney(BaseModel):
    username: str
    amount: float

# ---- BAZA DANYCH AKTYWÓW II RP (Zgodna z Twoją tabelą docx) ----
market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "price": 100.0, "history": [100.0]},
    "MAGI": {"name": "Magistrala Śląsk-Gdynia", "base_price": 80.0, "price": 80.0, "history": [80.0]},
    "COP": {"name": "Centralny Okręg Przemysłowy", "base_price": 150.0, "price": 150.0, "history": [150.0]},
    "AZOT": {"name": "Zakłady Azotowe Tarnów", "base_price": 60.0, "price": 60.0, "history": [60.0]},
    "STAL": {"name": "Stalowa Wola", "base_price": 100.0, "price": 100.0, "history": [100.0]},
    "KOLEJ": {"name": "Spółki Kolejowe PKP", "base_price": 120.0, "price": 120.0, "history": [120.0]},
    "AUTO": {"name": "Państwowe Zakłady Inżynierii", "base_price": 70.0, "price": 70.0, "history": [70.0]},
    "ZLOTO": {"name": "Złoto Rezerwy", "base_price": 45.0, "price": 45.0, "history": [45.0]},
    "SREBRO": {"name": "Srebro", "base_price": 25.0, "price": 25.0, "history": [25.0]},
    "MIEDZ": {"name": "Miedź Przemysłowa", "base_price": 35.0, "price": 35.0, "history": [35.0]},
}

# ---- STAN GRY W PAMIĘCI ----
game_state = {
    "current_day": 1,
    "players": {
        "admin": {"password": "druh", "balance": 9999999.0, "portfolio": []}
    },
    "messages": [{"player": "system", "text": "Terminal RTI II RP został uruchomiony mobilnie."}],
    "news": [{"title": "Otwarcie Giełdy", "content": "System giełdowy obozu gotowy do obsługi patroli."}],
    "player_impact": {sym: 1.0 for sym in market_assets.keys()}
}

# Dokładne odwzorowanie trendów z Twojej tabeli docx (15 dni jako 15 okresów/lat)
trends_by_day = {
    1:  {"PORT": 0.02,  "MAGI": 0.01,  "COP": 0.00,  "AZOT": 0.00,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.02,  "MIEDZ": 0.01},  # 1918-1920
    2:  {"PORT": 0.05,  "MAGI": 0.01,  "COP": 0.00,  "AZOT": 0.00,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.01,  "MIEDZ": 0.03},  # 1921
    3:  {"PORT": 0.06,  "MAGI": 0.02,  "COP": 0.00,  "AZOT": 0.00,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.01,  "MIEDZ": 0.02},  # 1922
    4:  {"PORT": 0.08,  "MAGI": 0.03,  "COP": 0.01,  "AZOT": 0.01,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.01,  "MIEDZ": 0.01},  # 1923
    5:  {"PORT": 0.07,  "MAGI": 0.04,  "COP": 0.02,  "AZOT": 0.02,  "STAL": 0.00,  "ZLOTO": 0.02,  "SREBRO": 0.02,  "MIEDZ": 0.04},  # 1924 (Grabski)
    6:  {"PORT": 0.05,  "MAGI": 0.05,  "COP": 0.02,  "AZOT": 0.03,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.01,  "MIEDZ": 0.05},  # 1925
    7:  {"PORT": 0.09,  "MAGI": 0.08,  "COP": 0.03,  "AZOT": 0.05,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.02,  "MIEDZ": 0.04},  # 1926-1927
    8:  {"PORT": 0.08,  "MAGI": 0.07,  "COP": 0.04,  "AZOT": 0.06,  "STAL": 0.00,  "ZLOTO": 0.01,  "SREBRO": 0.01,  "MIEDZ": 0.05},  # 1928
    9:  {"PORT": 0.06,  "MAGI": 0.06,  "COP": 0.04,  "AZOT": 0.08,  "STAL": 0.00,  "ZLOTO": 0.02,  "SREBRO": 0.01,  "MIEDZ": 0.04},  # 1929
    10: {"PORT": -0.03, "MAGI": -0.04, "COP": -0.06, "AZOT": -0.05, "STAL": -0.02, "ZLOTO": 0.07,  "SREBRO": -0.05, "MIEDZ": -0.07}, # 1930 (Kryzys!)
    11: {"PORT": -0.05, "MAGI": -0.06, "COP": -0.09, "AZOT": -0.07, "STAL": -0.04, "ZLOTO": 0.09,  "SREBRO": -0.08, "MIEDZ": -0.11}, # 1931-1932 (Dno kryzysu)
    12: {"PORT": 0.04,  "MAGI": 0.06,  "COP": 0.01,  "AZOT": 0.02,  "STAL": 0.01,  "ZLOTO": 0.03,  "SREBRO": 0.01,  "MIEDZ": 0.02},  # 1933
    13: {"PORT": 0.06,  "MAGI": 0.04,  "COP": 0.05,  "AZOT": 0.04,  "STAL": 0.03,  "ZLOTO": 0.02,  "SREBRO": 0.02,  "MIEDZ": 0.04},  # 1934-1935
    14: {"PORT": 0.08,  "MAGI": 0.07,  "COP": 0.13,  "AZOT": 0.08,  "STAL": 0.16,  "ZLOTO": 0.02,  "SREBRO": 0.04,  "MIEDZ": 0.07},  # 1936-1937 (Kwiatkowski)
    15: {"PORT": 0.10,  "MAGI": 0.08,  "COP": 0.15,  "AZOT": 0.09,  "STAL": 0.19,  "ZLOTO": 0.03,  "SREBRO": 0.05,  "MIEDZ": 0.09},  # 1938-1939 (Boom przedwojenny)
}

def market_tick_worker():
    """Wątek w tle: aktualizuje ceny dokładnie co 60 sekund (wykres minutowy)"""
    while True:
        time.sleep(60)
        day = game_state["current_day"]
        day_trends = trends_by_day.get(day, trends_by_day[15])
        
        for sym, asset in market_assets.items():
            trend = day_trends.get(sym, 0.02)
            noise = random.uniform(-0.012, 0.012)
            
            impact = (game_state["player_impact"][sym] - 1.0) * 0.03
            
            total_change = (trend * 0.6) + (noise * 0.4) + impact
            total_change = max(min(total_change, 0.07), -0.07)
            
            new_price = round(asset["price"] * (1 + total_change), 2)
            if new_price < 0.10: new_price = 0.10
            
            asset["price"] = new_price
            asset["history"].append(new_price)
            if len(asset["history"]) > 40:
                asset["history"].pop(0)
                
        for sym in game_state["player_impact"]:
            game_state["player_impact"][sym] = 1.0 + (game_state["player_impact"][sym] - 1.0) * 0.85

# Uruchomienie automatycznego rynku minutowego w osobnym wątku
threading.Thread(target=market_tick_worker, daemon=True).start()

# ---- INTERFEJS WIZUALNY (BEZPIECZNA ŚCIEŻKA DLA RENDERA) ----
@app.get("/", response_class=HTMLResponse)
def get_gui():
    # Pobiera bezwzględną ścieżkę do folderu, w którym znajduje się main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "index.html")
    
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # Alternatywne wyszukiwanie awaryjne w folderze roboczym
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
            
    return """
    <div style="background:#1f1212; color:#ff5350; padding:20px; font-family:sans-serif; text-align:center; border:2px solid red; margin:50px;">
        <h2>⚠️ BŁĄD SYSTEMU GIEŁDY II RP ⚠️</h2>
        <p>Serwer Render działa, ale nie może znaleźć pliku <b>index.html</b>!</p>
        <p>Upewnij się, że plik <b>index.html</b> znajduje się w tym samym folderze (repozytorium GitHub) co plik <b>main.py</b>.</p>
    </div>
    """

# ---- ENDPOINTY INTERFEJSU API ----
@app.get("/api/game-data")
def get_game_data():
    return {
        "current_day": game_state["current_day"],
        "assets": {sym: {"name": a["name"], "price": a["price"], "history": a["history"]} for sym, a in market_assets.items()},
        "news": game_state["news"]
    }

@app.post("/api/login")
def login(data: CreatePlayer):
    p = game_state["players"].get(data.username)
    if p and p["password"] == data.password:
        return {"status": "ok", "username": data.username, "balance": p["balance"], "portfolio": p["portfolio"]}
    elif not p:
        game_state["players"][data.username] = {"password": data.password, "balance": 5000.0, "portfolio": []}
        return {"status": "registered", "username": data.username, "balance": 5000.0, "portfolio": []}
    raise HTTPException(status_code=401, detail="Błędne hasło patrolu!")

@app.get("/api/player/{username}")
def get_player_data(username: str):
    p = game_state["players"].get(username)
    if not p: raise HTTPException(status_code=404, detail="Brak patrolu.")
    return {"balance": p["balance"], "portfolio": p["portfolio"]}

@app.post("/api/transaction")
def execute_transaction(t: Transaction):
    p = game_state["players"].get(t.username)
    if not p: raise HTTPException(status_code=404, detail="Brak gracza.")
    
    if t.type == "BUY":
        asset = market_assets.get(t.symbol)
        if not asset: raise HTTPException(status_code=404, detail="Brak aktywa.")
        cost = t.amount * asset["price"]
        if p["balance"] < cost:
            raise HTTPException(status_code=400, detail=f"Brak środków! Wymagane: {cost:.2f} zł.")
        
        p["balance"] -= cost
        p["portfolio"].append({
            "id": int(time.time() * 1000) + random.randint(0, 999),
            "symbol": t.symbol,
            "buy_price": asset["price"],
            "amount": t.amount
        })
        game_state["player_impact"][t.symbol] += 0.01 * t.amount
        return {"status": "Pomyślnie zakupiono aktywa!", "balance": p["balance"]}
        
    elif t.type == "SELL_POSITION":
        position_id = int(t.amount)
        target_pos = None
        for pos in p["portfolio"]:
            if pos["id"] == position_id:
                target_pos = pos
                break
        if not target_pos:
            raise HTTPException(status_code=404, detail="Nie znaleziono tej pozycji transakcyjnej.")
            
        current_price = market_assets[target_pos["symbol"]]["price"]
        revenue = target_pos["amount"] * current_price
        p["balance"] += revenue
        p["portfolio"].remove(target_pos)
        game_state["player_impact"][target_pos["symbol"]] -= 0.01 * target_pos["amount"]
        return {"status": "Pozycja upłynniona na rynku!", "balance": p["balance"]}

# ---- SYSTEM CZATU OBOZOWEGO ----
@app.get("/api/messages")
def get_messages():
    return game_state["messages"]

@app.post("/api/messages")
def add_message(msg: Message):
    game_state["messages"].append({"player": msg.player, "text": msg.text})
    if len(game_state["messages"]) > 30:
        game_state["messages"].pop(0)
    return {"status": "Wysłano"}

# ---- PANEL DRUHA PROWADZĄCEGO ----
@app.post("/api/admin/next-day")
def admin_next_day():
    if game_state["current_day"] < 15:
        game_state["current_day"] += 1
        d = game_state["current_day"]
        game_state["news"].insert(0, {
            "title": f"Rozpoczęto Dzień/Rok {d} symulacji",
            "content": "Wchodzimy w kolejną fazę makroekonomiczną II RP. Śledź wykresy na żywo!"
        })
        return {"status": f"Przewinięto pomyślnie do dnia {d}"}
    return {"error": "Osiągnięto już ostatni, 15. dzień obozu."}

@app.post("/api/admin/money")
def admin_give_money(data: AddMoney):
    p = game_state["players"].get(data.username)
    if not p: raise HTTPException(status_code=404, detail="Brak takiego patrolu.")
    p["balance"] += data.amount
    return {"status": f"Dodano pomyślnie {data.amount} zł dla {data.username}"}