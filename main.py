from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
import threading
import time
import os

app = FastAPI(title="Giełda II RP - Stabilna Wersja")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELE DANYCH ----------------
class Transaction(BaseModel):
    username: str
    symbol: str
    type: str # "buy" / "sell"
    amount: float
    leverage: int

class Message(BaseModel):
    player: str
    text: str

class CreatePlayer(BaseModel):
    username: str
    password: str

class AddMoney(BaseModel):
    username: str
    amount: float

class SetTrend(BaseModel):
    symbol: str
    trend: float

# ---------------- STRUKTURA DANYCH II RP ----------------
game_state = {
    "current_day": 1,
    "admin_trends": {},
    "player_impact": {}
}

market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "desc": "Budowa przynosi 40-60 mln zł rocznie. Koszt: 300 mln. Ryzyko średnie. Stabilny wzrost w długiej perspektywie."},
    "MAGI": {"name": "Magistrala Śląsk-Gdynia", "base_price": 80.0, "desc": "Transport węgla. Przychody 30-50 mln zł rocznie. Koszt: 250 mln. Niskie ryzyko, stabilny popyt."},
    "COP": {"name": "Centralny Okręg Przemysłowy", "base_price": 250.0, "desc": "Strategiczny projekt państwowy. Koszt >3 mld zł. Początkowe straty, potem potężne zyski (100-150 mln)."},
    "AZOT": {"name": "Zakłady Azotowe Tarnów", "base_price": 50.0, "desc": "Produkcja nawozów. Koszt: 100 mln. Zysk 5-8 mln rocznie. Stabilny popyt, ryzyko umiarkowane."},
    "STAL": {"name": "Stalowa Wola", "base_price": 120.0, "desc": "Przemysł ciężki i wojskowy. Koszt: 200 mln. Zależne od zamówień rządowych i obronnych."},
    "KOLEJ": {"name": "Spółka Kolejowa (PKP)", "base_price": 150.0, "desc": "Modernizacja sieci. Koszt: 500 mln. Bardzo bezpieczna lokata, podstawa gospodarki."},
    "AUTO": {"name": "Fabryka Samochodów", "base_price": 70.0, "desc": "Budowa pod Warszawą. Koszt: 150 mln. Wysoka niepewność popytu, rynek dopiero startuje."},
    "ZLOTO": {"name": "Złoto (PZBP)", "base_price": 45.0, "desc": "Kruszec lokacyjny, bezpieczna przystań w czasach niepewności geopolitycznej."},
    "MIEDZ": {"name": "Miedź", "base_price": 15.0, "desc": "Surowiec strategiczny dla elektryczności i przemysłu zbrojeniowego COP."},
    "SREBRO": {"name": "Srebro", "base_price": 22.0, "desc": "Wykorzystywane w przemyśle oraz do bicia monet obiegowych w II RP."},
    "USD": {"name": "Dolar Amerykański", "base_price": 5.30, "desc": "Twarda waluta zagraniczna. Kurs zależny od sytuacji na świecie."}
}

prices = []
candles_history = {} 
players = {}  
messages = []

def init_game():
    players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio": {}}
    players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio": {}}
    
    for symbol, data in market_assets.items():
        prices.append({
            "symbol": symbol,
            "name": data["name"],
            "price": data["base_price"],
            "desc": data["desc"]
        })
        game_state["player_impact"][symbol] = 1.0
        
        bp = data["base_price"]
        # Inicjalizacja stabilnych punktów startowych świec
        candles_history[symbol] = {
            "5m": [[i, bp, bp+random.uniform(0,3), bp-random.uniform(0,3), bp+random.uniform(-1,1)] for i in range(15)],
            "1h": [[i, bp, bp+random.uniform(0,6), bp-random.uniform(0,6), bp+random.uniform(-3,3)] for i in range(15)],
            "1d": [[i, bp, bp+random.uniform(0,12), bp-random.uniform(0,12), bp+random.uniform(-5,5)] for i in range(15)]
        }

init_game()

@app.get("/", response_class=HTMLResponse)
def get_frontend():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Błąd: Brak pliku index.html</h1>"

@app.post("/api/register")
def register_player(cp: CreatePlayer):
    if cp.username in players: return {"error": "Ta nazwa jest zajęta!"}
    players[cp.username] = {"password": cp.password, "balance": 5000.0, "portfolio": {}}
    return {"status": f"Zarejestrowano pomyślnie patrol: {cp.username}"}

@app.get("/api/prices")
def get_prices():
    return prices

@app.get("/api/candles/{symbol}/{timeframe}")
def get_candles(symbol: str, timeframe: str):
    if symbol in candles_history and timeframe in candles_history[symbol]:
        return candles_history[symbol][timeframe]
    return []

@app.get("/api/player/{username}/{password}")
def get_player_data(username: str, password: str):
    if username not in players or players[username]["password"] != password:
        return {"error": "Błędny login lub hasło"}
    return {"balance": players[username]["balance"], "portfolio": players[username]["portfolio"], "current_day": game_state["current_day"]}

@app.get("/api/ranking")
def get_ranking():
    ranking_list = [{"name": u, "balance": d["balance"]} for u, d in players.items() if u != "admin"]
    return sorted(ranking_list, key=lambda x: x["balance"], reverse=True)

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    if tx.username not in players: return {"error": "Użytkownik nie istnieje"}
    player = players[tx.username]
    idx = next((i for i, p in enumerate(prices) if p["symbol"] == tx.symbol), None)
    if idx is None: return {"error": "Brak aktywa"}
    
    asset_price = prices[idx]["price"]
    
    if tx.type == "buy":
        required_margin = (asset_price * tx.amount) / tx.leverage
        if player["balance"] < required_margin: return {"error": "Masz za mało pieniędzy!"}
        
        player["balance"] -= required_margin
        player["portfolio"][tx.symbol] = player["portfolio"].get(tx.symbol, [])
        player["portfolio"][tx.symbol].append({"amount": tx.amount, "buy_price": asset_price, "leverage": tx.leverage})
        
        # Max 20% limitu bezpieczeństwa
        game_state["player_impact"][tx.symbol] = min(game_state["player_impact"][tx.symbol] + (tx.amount * 0.002), 1.20)
        
    elif tx.type == "sell":
        positions = player["portfolio"].get(tx.symbol, [])
        total_owned = sum(pos["amount"] for pos in positions)
        if total_owned < tx.amount: return {"error": "Nie masz tylu akcji!"}
        
        amount_to_remove = tx.amount
        refund = 0
        for pos in list(positions):
            if amount_to_remove <= 0: break
            if pos["amount"] <= amount_to_remove:
                profit = ((asset_price - pos["buy_price"]) * pos["amount"]) * pos["leverage"]
                margin = (pos["buy_price"] * pos["amount"]) / pos["leverage"]
                refund += (margin + profit)
                amount_to_remove -= pos["amount"]
                positions.remove(pos)
            else:
                profit = ((asset_price - pos["buy_price"]) * amount_to_remove) * pos["leverage"]
                margin = (pos["buy_price"] * amount_to_remove) / pos["leverage"]
                refund += (margin + profit)
                pos["amount"] -= amount_to_remove
                amount_to_remove = 0
                
        player["balance"] += max(refund, 0.0)
        player["portfolio"][tx.symbol] = positions
        
        # Max 20% limitu bezpieczeństwa
        game_state["player_impact"][tx.symbol] = max(game_state["player_impact"][tx.symbol] - (tx.amount * 0.002), 0.80)

    return {"status": "ok"}

@app.post("/api/admin/money")
def admin_add_money(data: AddMoney):
    if data.username in players:
        players[data.username]["balance"] += data.amount
        return {"status": f"Dodano {data.amount} zł"}
    return {"error": "Brak gracza"}

@app.post("/api/admin/trend")
def admin_set_trend(data: SetTrend):
    game_state["admin_trends"][data.symbol] = data.trend
    return {"status": "Trend zmieniony"}

@app.post("/api/admin/next-day")
def next_day():
    if game_state["current_day"] < 15:
        game_state["current_day"] += 1
        return {"status": f"Nastał Dzień {game_state['current_day']}"}
    return {"error": "Koniec gry"}

@app.get("/api/messages")
def get_messages(): return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    messages.append(msg)
    return {"status": "ok"}

# ---------------- SILNIK GIEŁDOWY ----------------
def market_engine():
    tick_count = 15
    while True:
        time.sleep(4) # Aktualizacja co 4 sekundy
        tick_count += 1
        
        for p in prices:
            sym = p["symbol"]
            open_p = p["price"]
            
            change = random.uniform(-0.012, 0.012)
            day = game_state["current_day"]
            if sym == "PORT" and day > 3: change += 0.003
            if sym == "COP" and day < 6: change -= 0.005
            if sym == "COP" and day >= 6: change += 0.009
            if sym == "STAL" and day > 8: change += 0.005
            
            if sym in game_state["admin_trends"]:
                change += game_state["admin_trends"][sym]
            
            base_calculated_price = open_p * (1 + change)
            impact_modifier = game_state["player_impact"][sym]
            final_price = round(max(base_calculated_price * impact_modifier, 0.1), 2)
            
            p["price"] = final_price
            close_p = final_price
            
            high_p = round(max(open_p, close_p) + random.uniform(0.05, 1.5), 2)
            low_p = round(max(min(open_p, close_p) - random.uniform(0.05, 1.5), 0.05), 2)
            
            for tf in ["5m", "1h", "1d"]:
                hist = candles_history[sym][tf]
                # Co 5 tików zamykamy starą świeczkę i otwieramy nową
                if tick_count % 5 == 0 or len(hist) == 0:
                    hist.append([tick_count, open_p, high_p, low_p, close_p])
                else:
                    last = hist[-1]
                    last[2] = max(last[2], high_p)
                    last[3] = min(last[3], low_p)
                    last[4] = close_p
                
                # Naprawiony bezpiecznik ograniczenia historii (zamiast .shift() używamy wycinania)
                if len(hist) > 22:
                    candles_history[sym][tf] = hist[-22:]

threading.Thread(target=market_engine, daemon=True).start()