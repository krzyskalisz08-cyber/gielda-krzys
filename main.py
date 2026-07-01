from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
import threading
import time
import os
import json
import datetime
import psycopg2
from psycopg2.extras import Json

app = FastAPI(title="Giełda II RP - Realna Symulacja Chronologiczna")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_lock = threading.Lock()
DATABASE_URL = os.environ.get("DATABASE_URL")

# ---- SYSTEM ZAPISU CLOUD/LOCAL ----
def init_db():
    if not DATABASE_URL:
        print("[ℹ️ SYSTEM] Brak DATABASE_URL. Działam w trybie lokalnych plików JSON.", flush=True)
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gielda_cloud_store (
                key TEXT PRIMARY KEY,
                value JSONB
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[✅ DB SUCCESS] Połączono z bazą PostgreSQL na Neon.tech. Dane są bezpieczne!", flush=True)
    except Exception as e:
        print(f"[❌ DB ERROR] Nie udało się zainicjalizować bazy danych: {e}", flush=True)

def save_data(key, data):
    if not DATABASE_URL:
        try:
            temp_filename = f"{key}.json.tmp"
            with open(temp_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.replace(temp_filename, f"{key}.json")
        except Exception as e:
            print(f"⚠️ Błąd zapisu lokalnego {key}: {e}", flush=True)
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO gielda_cloud_store (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value;
        """, (key, Json(data)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[❌ DB WRITE ERROR] Problem z zapisem klucza '{key}' do chmury: {e}", flush=True)

def save_data_batch(batch_dict):
    if not DATABASE_URL:
        for key, data in batch_dict.items():
            save_data(key, data)
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        for key, data in batch_dict.items():
            cur.execute("""
                INSERT INTO gielda_cloud_store (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value;
            """, (key, Json(data)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[❌ DB BATCH WRITE ERROR] Problem z zapisem pakietu danych do chmury: {e}", flush=True)

def load_data(key, default_value):
    if not DATABASE_URL:
        filename = f"{key}.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.loads(f.read().strip())
            except:
                pass
        return default_value

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT value FROM gielda_cloud_store WHERE key = %s;", (key,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            val = row[0]
            if isinstance(val, str):
                return json.loads(val)
            return val
    except Exception as e:
        print(f"[❌ DB READ ERROR] Problem z odczytem klucza '{key}' z chmury: {e}", flush=True)
    return default_value

# ---- MODELE DANYCH ----
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

# ---- BAZA AKTYWÓW ----
market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "desc": "Kompleks portowy nad Zatoką Gdańską."},
    "MAGI": {"name": "Magistrala Śląsk-Gdynia", "base_price": 80.0, "desc": "Magistrala kolejowa Herby Nowe – Gdynia, linia 201."},
    "COP": {"name": "Centralny Okręg Przemysłowy", "base_price": 150.0, "desc": "Okręg przemysłu ciężkiego w widłach Wisły i Sanu."},
    "AZOT": {"name": "Zakłady Azotowe Tarnów", "base_price": 60.0, "desc": "Państwowa Fabryka Związków Azotowych w Mościcach."},
    "STAL": {"name": "Stalowa Wola", "base_price": 100.0, "desc": "Zakłady Południowe w nowo powstającym mieście."},
    "KOLEJ": {"name": "Spółki Kolejowe i Transportowe", "base_price": 120.0, "desc": "Infrastruktura Polskich Kolei Państwowych (PKP)."},
    "AUTO": {"name": "Państwowe Zakłady Inżynierii", "base_price": 70.0, "desc": "Zakłady PZInż z siedzibą w Warszawie."},
    "ZLOTO": {"name": "Złoto", "base_price": 45.0, "desc": "Kruszec lokacyjny, baza rezerw Banku Polskiego."},
    "MIEDZ": {"name": "Miedź", "base_price": 20.0, "desc": "Metal przemysłowy niezbędny do elektryfikacji kraju."},
    "SREBRO": {"name": "Srebro", "base_price": 25.0, "desc": "Kruszec o podwójnym zastosowaniu rynkowym i menniczym."},
    "USD": {"name": "Dolar Amerykański", "base_price": 5.20, "desc": "Główna waluta rezerwowa oparta na parytecie złota."}
}

MARKET_TRENDS = {
    1: {"USD": 0.072, "PORT": 0.018, "MAGI": 0.009, "COP": -0.012, "STAL": -0.018, "AZOT": -0.015, "KOLEJ": -0.003, "AUTO": -0.006, "ZLOTO": 0.006, "MIEDZ": -0.009, "SREBRO": -0.006},
    2: {"USD": 0.072, "PORT": 0.018, "MAGI": 0.012, "COP": -0.015, "STAL": -0.012, "AZOT": -0.018, "KOLEJ": -0.006, "AUTO": -0.003, "ZLOTO": 0.009, "MIEDZ": -0.006, "SREBRO": -0.009},
    3: {"USD": 0.072, "PORT": 0.015, "MAGI": 0.015, "COP": -0.018, "STAL": -0.015, "AZOT": -0.012, "KOLEJ": -0.009, "AUTO": -0.009, "ZLOTO": 0.003, "MIEDZ": -0.012, "SREBRO": -0.003},
    4: {"USD": 0.072, "PORT": 0.021, "MAGI": 0.006, "COP": -0.009, "STAL": -0.021, "AZOT": -0.015, "KOLEJ": -0.003, "AUTO": -0.012, "ZLOTO": 0.006, "MIEDZ": -0.006, "SREBRO": -0.006},
    5: {"USD": -0.180, "PORT": 0.056, "KOLEJ": 0.050, "MAGI": 0.042, "COP": 0.012, "STAL": 0.015, "AZOT": 0.009, "AUTO": 0.018, "ZLOTO": -0.036, "MIEDZ": 0.024, "SREBRO": 0.018},
    6: {"USD": 0.090, "MIEDZ": 0.042, "SREBRO": 0.030, "ZLOTO": 0.015, "PORT": -0.012, "MAGI": -0.009, "KOLEJ": -0.006, "COP": 0.018, "STAL": 0.021, "AZOT": 0.012, "AUTO": 0.024},
    7: {"PORT": 0.046, "MAGI": 0.052, "KOLEJ": 0.048, "AUTO": 0.054, "AZOT": 0.042, "MIEDZ": 0.024, "SREBRO": 0.018, "COP": 0.036, "STAL": 0.039, "ZLOTO": -0.024, "USD": -0.015},
    8: {"PORT": 0.048, "MAGI": 0.046, "KOLEJ": 0.052, "AUTO": 0.050, "AZOT": 0.045, "MIEDZ": 0.018, "SREBRO": 0.024, "COP": 0.042, "STAL": 0.033, "ZLOTO": -0.021, "USD": -0.018},
    9: {"PORT": 0.050, "MAGI": 0.050, "KOLEJ": 0.044, "AUTO": 0.058, "AZOT": 0.039, "MIEDZ": 0.021, "SREBRO": 0.021, "COP": 0.030, "STAL": 0.045, "ZLOTO": -0.027, "USD": -0.012},
    10: {"SREBRO": -0.110, "MIEDZ": -0.095, "AUTO": -0.100, "ZLOTO": 0.066, "USD": 0.045, "PORT": -0.030, "MAGI": -0.024, "KOLEJ": -0.018, "COP": -0.042, "STAL": -0.048, "AZOT": -0.036},
    11: {"SREBRO": -0.100, "MIEDZ": -0.110, "AUTO": -0.105, "ZLOTO": 0.066, "USD": 0.042, "PORT": -0.024, "MAGI": -0.030, "KOLEJ": -0.015, "COP": -0.048, "STAL": -0.039, "AZOT": -0.042},
    12: {"SREBRO": -0.105, "MIEDZ": -0.100, "AUTO": -0.110, "ZLOTO": 0.066, "USD": 0.048, "PORT": -0.036, "MAGI": -0.018, "KOLEJ": -0.021, "COP": -0.036, "STAL": -0.045, "AZOT": -0.030},
    13: {"PORT": 0.082, "MAGI": 0.074, "KOLEJ": 0.078, "AUTO": 0.036, "COP": 0.042, "STAL": 0.045, "AZOT": 0.030, "MIEDZ": 0.024, "SREBRO": 0.018, "ZLOTO": -0.045, "USD": -0.030},
    14: {"ZLOTO": 0.105, "MIEDZ": 0.034, "AUTO": 0.026, "SREBRO": 0.048, "USD": 0.060, "PORT": -0.015, "MAGI": -0.012, "KOLEJ": -0.009, "COP": 0.018, "STAL": 0.024, "AZOT": 0.015},
    15: {"COP": 0.160, "STAL": 0.140, "MIEDZ": 0.058, "KOLEJ": 0.050, "AUTO": 0.054, "PORT": 0.042, "MAGI": 0.036, "AZOT": 0.048, "ZLOTO": -0.060, "SREBRO": 0.030, "USD": -0.045}
}

init_db()

# Ładowanie stanu początkowego
players = load_data("players", {})
prices = load_data("prices", [])
candles_history = load_data("candles", {})
messages = load_data("messages", [])
articles = load_data("articles", [
    {"title": "Otwarcie Rynku z Chmurą PostgreSQL", "content": "Gra została pomyślnie połączona z trwałą zewnętrzną bazą danych."}
])
game_state = load_data("gamestate", {"current_day": 1, "player_trend_impulse": {}})

def init_game():
    global players, prices, candles_history, game_state
    if not players:
        players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio_long": {}, "portfolio_short": {}}
        players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
        save_data("players", players)
        
    if not prices or not candles_history or "player_trend_impulse" not in game_state or not game_state["player_trend_impulse"]:
        prices = []
        candles_history = {}
        game_state["player_trend_impulse"] = {}
        
        for symbol, data in market_assets.items():
            prices.append({
                "symbol": symbol, 
                "name": data["name"], 
                "price": data["base_price"], 
                "day_open_price": data["base_price"], 
                "desc": data["desc"], 
                "daily_change": 0.0
            })
            game_state["player_trend_impulse"][symbol] = 0.0
            candles_history[symbol] = {"5m": [], "1h": [], "1d": []}
            
        save_data("prices", prices)
        save_data("candles", candles_history)
        save_data("gamestate", game_state)

init_game()

# ---- ENDPOINTY API ----
@app.get("/", response_class=HTMLResponse)
def get_frontend():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f: 
            return f.read()
    return "<h1>Status: Pancerne API z PostgreSQL i Rankingiem działa</h1>"

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/api/register")
def register_player(cp: CreatePlayer):
    with data_lock:
        if cp.username in players: 
            return {"error": "Ta nazwa jest zajęta!"}
        players[cp.username] = {"password": cp.password, "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
        save_data("players", players)
        return {"status": f"Utworzono profil: {cp.username}"}

@app.get("/api/prices")
def get_prices(): 
    with data_lock:
        return prices

@app.get("/api/candles/{symbol}/{timeframe}")
def get_candles(symbol: str, timeframe: str):
    with data_lock:
        if symbol in candles_history and timeframe in candles_history[symbol]: 
            return candles_history[symbol][timeframe]
        return []

@app.get("/api/player/{username}/{password}")
def get_player_data(username: str, password: str):
    with data_lock:
        if username not in players or players[username]["password"] != password: 
            return {"error": "Błąd autoryzacji"}
        return {
            "balance": players[username]["balance"], 
            "portfolio_long": players[username].get("portfolio_long", {}), 
            "portfolio_short": players[username].get("portfolio_short", {}), 
            "current_day": game_state["current_day"]
        }

# ---- NOWY ENDPOINT: RANKING ZASTĘPÓW ----
@app.get("/api/leaderboard")
def get_leaderboard():
    with data_lock:
        leaderboard = []
        
        # Tworzymy mapę ułatwiającą szybkie pobieranie aktualnych cen aktywów
        price_map = {p["symbol"]: p["price"] for p in prices}
        
        for username, data in players.items():
            if username == "admin": 
                continue # Nie wrzucamy konta admina do rywalizacji zastępów
                
            equity = data.get("balance", 0.0)
            
            # Wycena pozycji LONG: depozyt + (aktualna_cena - cena_zakupu) * ilość * dźwignia
            for symbol, positions in data.get("portfolio_long", {}).items():
                current_p = price_map.get(symbol, 0.0)
                for pos in positions:
                    profit = (current_p - pos["buy_price"]) * pos["amount"] * pos["leverage"]
                    equity += (pos["margin_allocated"] + profit)
                    
            # Wycena pozycji SHORT: depozyt + (cena_wejścia - aktualna_cena) * ilość * dźwignia
            for symbol, positions in data.get("portfolio_short", {}).items():
                current_p = price_map.get(symbol, 0.0)
                for pos in positions:
                    profit = (pos["entry_price"] - current_p) * pos["amount"] * pos["leverage"]
                    equity += (pos["margin_allocated"] + profit)
            
            leaderboard.append({
                "username": username,
                "total_equity": round(max(equity, 0.0), 2),
                "cash_balance": round(data.get("balance", 0.0), 2)
            })
            
        # Sortowanie od zastępu z największym majątkiem
        leaderboard.sort(key=lambda x: x["total_equity"], reverse=True)
        return leaderboard

@app.get("/api/admin/players-list")
def admin_get_players():
    with data_lock:
        return [{"username": u, "password": d["password"], "balance": d["balance"]} for u, d in players.items()]

@app.post("/api/admin/delete-player")
def admin_delete_player(dp: DeletePlayer):
    with data_lock:
        if dp.username == "admin": return {"error": "Nie usuwaj admina!"}
        if dp.username in players:
            del players[dp.username]
            save_data("players", players)
            return {"status": f"Usunięto gracza: {dp.username}"}
        return {"error": "Nie znaleziono gracza."}

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    with data_lock:
        if tx.username not in players: return {"error": "Brak gracza"}
        player = players[tx.username]
        
        if "portfolio_long" not in player: player["portfolio_long"] = {}
        if "portfolio_short" not in player: player["portfolio_short"] = {}

        idx = next((i for i, p in enumerate(prices) if p["symbol"] == tx.symbol), None)
        if idx is None: return {"error": "Brak aktywa"}
        
        asset_price = prices[idx]["price"]
        market_cap_reference = 500000.0 
        trade_value = tx.amount * asset_price
        
        # ---- KUPNO LONG ----
        if tx.type == "buy_long":
            margin = trade_value / tx.leverage
            if player["balance"] < margin: return {"error": "Brak środków na depozyt!"}
            player["balance"] -= margin
            player["portfolio_long"][tx.symbol] = player["portfolio_long"].get(tx.symbol, [])
            player["portfolio_long"][tx.symbol].append({"amount": tx.amount, "buy_price": asset_price, "leverage": tx.leverage, "margin_allocated": margin})
            impact = (trade_value / market_cap_reference) * 0.15
            game_state["player_trend_impulse"][tx.symbol] = min(game_state["player_trend_impulse"].get(tx.symbol, 0.0) + impact, 0.25)
            
        # ---- SPRZEDAŻ LONG ----
        elif tx.type == "sell_long":
            positions = player["portfolio_long"].get(tx.symbol, [])
            if sum(pos["amount"] for pos in positions) < tx.amount: return {"error": "Brak jednostek LONG!"}
            amt_to_rem = tx.amount
            refund = 0
            for pos in list(positions):
                if amt_to_rem <= 0: break
                if pos["amount"] <= amt_to_rem:
                    profit = ((asset_price - pos["buy_price"]) * pos["amount"]) * pos["leverage"]
                    refund += (pos["margin_allocated"] + profit)
                    amt_to_rem -= pos["amount"]
                    positions.remove(pos)
                else:
                    fraction = amt_to_rem / pos["amount"]
                    allocated_part = pos["margin_allocated"] * fraction
                    profit = ((asset_price - pos["buy_price"]) * amt_to_rem) * pos["leverage"]
                    refund += (allocated_part + profit)
                    pos["margin_allocated"] -= allocated_part
                    pos["amount"] -= amt_to_rem
                    amt_to_rem = 0
            player["balance"] += max(refund, 0.0)
            player["portfolio_long"][tx.symbol] = positions
            impact = (trade_value / market_cap_reference) * 0.15
            game_state["player_trend_impulse"][tx.symbol] = max(game_state["player_trend_impulse"].get(tx.symbol, 0.0) - impact, -0.25)

        # ---- OTWARCIE SHORT ----
        elif tx.type == "open_short":
            margin = trade_value / tx.leverage
            if player["balance"] < margin: return {"error": "Brak środków na depozyt!"}
            player["balance"] -= margin
            player["portfolio_short"][tx.symbol] = player["portfolio_short"].get(tx.symbol, [])
            player["portfolio_short"][tx.symbol].append({"amount": tx.amount, "entry_price": asset_price, "leverage": tx.leverage, "margin_allocated": margin})
            impact = (trade_value / market_cap_reference) * 0.15
            game_state["player_trend_impulse"][tx.symbol] = max(game_state["player_trend_impulse"].get(tx.symbol, 0.0) - impact, -0.25)

        # ---- ZAMKNIĘCIE SHORT ----
        elif tx.type == "close_short":
            positions = player["portfolio_short"].get(tx.symbol, [])
            if sum(pos["amount"] for pos in positions) < tx.amount: return {"error": "Brak jednostek SHORT!"}
            amt_to_rem = tx.amount
            refund = 0
            for pos in list(positions):
                if amt_to_rem <= 0: break
                if pos["amount"] <= amt_to_rem:
                    profit = ((pos["entry_price"] - asset_price) * pos["amount"]) * pos["leverage"]
                    refund += (pos["margin_allocated"] + profit)
                    amt_to_rem -= pos["amount"]
                    positions.remove(pos)
                else:
                    fraction = amt_to_rem / pos["amount"]
                    allocated_part = pos["margin_allocated"] * fraction
                    profit = ((pos["entry_price"] - asset_price) * amt_to_rem) * pos["leverage"]
                    refund += (allocated_part + profit)
                    pos["margin_allocated"] -= allocated_part
                    pos["amount"] -= amt_to_rem
                    amt_to_rem = 0
            player["balance"] += max(refund, 0.0)
            player["portfolio_short"][tx.symbol] = positions
            impact = (trade_value / market_cap_reference) * 0.15
            game_state["player_trend_impulse"][tx.symbol] = min(game_state["player_trend_impulse"].get(tx.symbol, 0.0) + impact, 0.25)
            
        save_data("players", players)
        save_data("gamestate", game_state)
        return {"status": "ok"}

@app.post("/api/admin/money")
def admin_add_money(data: AddMoney):
    with data_lock:
        if data.username in players:
            players[data.username]["balance"] += data.amount
            save_data("players", players)
            return {"status": f"Przyznano {data.amount} zł"}
        return {"error": "Brak gracza"}

@app.post("/api/admin/change-percent")
def admin_change_percent(data: SetPercentChange):
    with data_lock:
        idx = next((i for i, p in enumerate(prices) if p["symbol"] == data.symbol), None)
        if idx is not None:
            multiplier = 1 + (data.percent / 100.0)
            prices[idx]["price"] = round(max(prices[idx]["price"] * multiplier, 0.01), 4)
            save_data("prices", prices)
            return {"status": f"Zmieniono cenę {data.symbol}"}
        return {"error": "Brak aktywa"}

@app.post("/api/admin/next-day")
def next_day():
    with data_lock:
        if game_state["current_day"] < 15:
            game_state["current_day"] += 1
            for p in prices:
                p["day_open_price"] = p["price"]
            save_data("prices", prices)
            save_data("gamestate", game_state)
            return {"status": f"Dzień {game_state['current_day']}"}
        return {"error": "Maksymalny dzień osiągnięty"}

@app.get("/api/messages")
def get_messages(): 
    with data_lock:
        return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    global messages
    with data_lock:
        messages.append({"player": msg.player, "text": msg.text})
        if len(messages) > 100: messages = messages[-100:] 
        save_data("messages", messages)
        return {"status": "ok"}

@app.get("/api/articles")
def get_articles(): 
    with data_lock:
        return articles

# ---- SYSTEM PŁYNNEGO SILNIKA RYNKOWEGO Z BOTAMI ----
def market_engine():
    tick_count = 0
    TICKS_PER_DAY = 86400.0 
    
    all_symbols = list(market_assets.keys())
    bot_active_assets = random.sample(all_symbols, 5)
    last_logged_day = game_state.get("current_day", 1)
    
    print(f"\n[⚙️ OK] Silnik gotowy. Aktywne aktywa botów na dzień {last_logged_day}: {bot_active_assets}", flush=True)
    
    while True:
        try:
            time.sleep(1)
            tick_count += 1
            
            with data_lock:
                day = game_state.get("current_day", 1)
                
                if day != last_logged_day:
                    bot_active_assets = random.sample(all_symbols, 5)
                    last_logged_day = day
                    print(f"[🤖 BOTY] Nowy dzień {day}! Boty zmieniają pozycje na: {bot_active_assets}", flush=True)
                
                current_day_trends = MARKET_TRENDS.get(day, MARKET_TRENDS[15])
                
                now = datetime.datetime.now()
                t_5m = now.strftime("%H:%M")
                t_1h = now.strftime("%H:00")
                t_1d = f"Dzień {day}"
                
                for p in prices:
                    sym = p["symbol"]
                    open_p = p["price"] 
                    
                    history_trend = current_day_trends.get(sym, 0.0)
                    tick_history_change = history_trend / TICKS_PER_DAY
                    
                    player_impulse = game_state.get("player_trend_impulse", {}).get(sym, 0.0)
                    tick_player_change = player_impulse / 600.0
                    
                    tick_bot_change = 0.0
                    if sym in bot_active_assets:
                        bot_direction = random.choice([-1, 1])
                        tick_bot_change = bot_direction * (0.03 / TICKS_PER_DAY)
                    
                    market_noise = random.uniform(-0.00001, 0.00001)
                    total_tick_change = tick_history_change + tick_player_change + tick_bot_change + market_noise
                    
                    if total_tick_change > 0.002: total_tick_change = 0.002
                    if total_tick_change < -0.002: total_tick_change = -0.002
                    
                    close_p = round(max(open_p * (1 + total_tick_change), 0.01), 4)
                    p["price"] = close_p
                    
                    day_open = p.get("day_open_price", open_p)
                    if day_open <= 0: day_open = 0.01 
                    p["daily_change"] = round(((close_p - day_open) / day_open) * 100, 2)
                    
                    if sym in game_state.get("player_trend_impulse", {}):
                        game_state["player_trend_impulse"][sym] *= 0.995
                    
                    high_p = round(max(open_p, close_p) + random.uniform(0.0005, close_p * 0.0002), 2)
                    low_p = round(max(min(open_p, close_p) - random.uniform(0.0005, close_p * 0.0002), 0.01), 2)

                    for tf, label, interval in [("5m", t_5m, 300), ("1h", t_1h, 3600), ("1d", t_1d, 86400)]:
                        hist = candles_history[sym][tf]
                        if tick_count % interval == 0 or len(hist) == 0:
                            hist.append([label, round(open_p, 2), high_p, low_p, round(close_p, 2)])
                        else:
                            last = hist[-1]
                            last[0] = label
                            last[2] = max(last[2], high_p)
                            last[3] = min(last[3], low_p)
                            last[4] = round(close_p, 2)
                        if len(hist) > 20: candles_history[sym][tf] = hist[-20:]

                # ---- SYSTEM MARGIN CALLS ----
                for username, player in list(players.items()):
                    if username == "admin": continue
                    
                    for sym, positions in list(player.get("portfolio_long", {}).items()):
                        current_price = next((p["price"] for p in prices if p["symbol"] == sym), None)
                        if current_price is None: continue
                        for pos in list(positions):
                            loss = (pos["buy_price"] - current_price) * pos["amount"] * pos["leverage"]
                            if loss >= pos["margin_allocated"]:
                                positions.remove(pos)
                                messages.append({"player": "SYSTEM", "text": f"🚨 MARGIN CALL! Pozycja LONG na {sym} gracza {username} zlikwidowana."})
                    
                    for sym, positions in list(player.get("portfolio_short", {}).items()):
                        current_price = next((p["price"] for p in prices if p["symbol"] == sym), None)
                        if current_price is None: continue
                        for pos in list(positions):
                            loss = (current_price - pos["entry_price"]) * pos["amount"] * pos["leverage"]
                            if loss >= pos["margin_allocated"]:
                                positions.remove(pos)
                                messages.append({"player": "SYSTEM", "text": f"🚨 MARGIN CALL! Pozycja SHORT na {sym} gracza {username} zlikwidowana."})

                # Zapis i log do konsoli co 5 sekund
                if tick_count % 5 == 0:
                    test_usd = next((p["price"] for p in prices if p["symbol"] == "USD"), 0.0)
                    print(f"[⚙️ DB LIVE] Tick: {tick_count} | USD: {test_usd} | Boty grają na: {bot_active_assets}", flush=True)
                    
                    save_data_batch({
                        "prices": prices,
                        "candles": candles_history,
                        "messages": messages,
                        "gamestate": game_state,
                        "players": players
                    })
                    
        except Exception as e:
            print(f"⚠️ [BLOKADA CRASH] Silnik przechwycił błąd i żyje dalej: {e}", flush=True)

threading.Thread(target=market_engine, daemon=True).start()