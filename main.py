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

app = FastAPI(title="Giełda II RP - Realna Symulacja Chronologiczna")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- MODELE DANYCH (PYDANTIC) ----
class Transaction(BaseModel):
    username: str
    symbol: str
    type: str       # "buy_long", "sell_long", "open_short", "close_short"
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

# ---- MAPA TRENDÓW DOBOWYCH (Rozkładane na 24h) ----
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

# ---- POMOCNICZE FUNKCJE PERSYSTENCJI ----
def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Błąd zapisu pliku {filename}: {e}")

def load_json(filename, default_value):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Błąd odczytu pliku {filename}: {e}")
    return default_value

# ---- INICJALIZACJA STANU GRY ----
players = load_json("players.json", {})
prices = load_json("prices.json", [])
candles_history = load_json("candles.json", {})
messages = load_json("messages.json", [])
articles = load_json("articles.json", [
    {"title": "Otwarcie Realnego Rynku 24H", "content": "System zsynchronizowany. Silnik bije co 1 sekundę, a dobowe zmiany procentowe odnoszą się do ceny otwarcia dnia."}
])
game_state = load_json("gamestate.json", {"current_day": 1, "player_trend_impulse": {}})

def init_game():
    global players, prices, candles_history, game_state
    if not players:
        players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio_long": {}, "portfolio_short": {}}
        players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
        save_json("players.json", players)
        
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
            bp = data["base_price"]
            
            candles_history[symbol] = {
                "5m": [],
                "1h": [],
                "1d": []
            }
        save_json("prices.json", prices)
        save_json("candles.json", candles_history)
        save_json("gamestate.json", game_state)

init_game()

# ---- ENDPOINTY API ----
@app.get("/", response_class=HTMLResponse)
def get_frontend():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f: 
            return f.read()
    return "<h1>Status: Backend Giełdy II RP działa pomyślnie</h1>"

@app.post("/api/register")
def register_player(cp: CreatePlayer):
    if cp.username in players: 
        return {"error": "Ta nazwa jest zajęta!"}
    players[cp.username] = {"password": cp.password, "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
    save_json("players.json", players)
    return {"status": f"Pomyślnie utworzono profil: {cp.username}"}

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
        return {"error": "Błąd autoryzacji"}
    return {
        "balance": players[username]["balance"], 
        "portfolio_long": players[username].get("portfolio_long", {}), 
        "portfolio_short": players[username].get("portfolio_short", {}), 
        "current_day": game_state["current_day"]
    }

@app.get("/api/admin/players-list")
def admin_get_players():
    return [{"username": u, "password": d["password"], "balance": d["balance"]} for u, d in players.items()]

@app.post("/api/admin/delete-player")
def admin_delete_player(dp: DeletePlayer):
    if dp.username == "admin": return {"error": "Nie można usunąć administratora!"}
    if dp.username in players:
        del players[dp.username]
        save_json("players.json", players)
        return {"status": f"Usunięto gracza: {dp.username}"}
    return {"error": "Nie znaleziono gracza."}

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
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
        game_state["player_trend_impulse"][tx.symbol] = min(game_state["player_trend_impulse"][tx.symbol] + impact, 0.25)
        
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
        game_state["player_trend_impulse"][tx.symbol] = max(game_state["player_trend_impulse"][tx.symbol] - impact, -0.25)

    # ---- OTWARCIE SHORT ----
    elif tx.type == "open_short":
        margin = trade_value / tx.leverage
        if player["balance"] < margin: return {"error": "Brak środków na depozyt!"}
        player["balance"] -= margin
        player["portfolio_short"][tx.symbol] = player["portfolio_short"].get(tx.symbol, [])
        player["portfolio_short"][tx.symbol].append({"amount": tx.amount, "entry_price": asset_price, "leverage": tx.leverage, "margin_allocated": margin})
        
        impact = (trade_value / market_cap_reference) * 0.15
        game_state["player_trend_impulse"][tx.symbol] = max(game_state["player_trend_impulse"][tx.symbol] - impact, -0.25)

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
        game_state["player_trend_impulse"][tx.symbol] = min(game_state["player_trend_impulse"][tx.symbol] + impact, 0.25)
        
    save_json("players.json", players)
    save_json("gamestate.json", game_state)
    return {"status": "ok"}

@app.post("/api/admin/money")
def admin_add_money(data: AddMoney):
    if data.username in players:
        players[data.username]["balance"] += data.amount
        save_json("players.json", players)
        return {"status": f"Przyznano {data.amount} zł"}
    return {"error": "Brak gracza"}

@app.post("/api/admin/change-percent")
def admin_change_percent(data: SetPercentChange):
    idx = next((i for i, p in enumerate(prices) if p["symbol"] == data.symbol), None)
    if idx is not None:
        multiplier = 1 + (data.percent / 100.0)
        prices[idx]["price"] = round(max(prices[idx]["price"] * multiplier, 0.01), 2)
        save_json("prices.json", prices)
        return {"status": f"Zmieniono cenę {data.symbol} o {data.percent}%"}
    return {"error": "Brak aktywa"}

@app.post("/api/admin/article")
def admin_add_article(art: Article):
    articles.append({"title": art.title, "content": art.content})
    save_json("articles.json", articles)
    return {"status": "Artykuł opublikowany"}

@app.post("/api/admin/next-day")
def next_day():
    if game_state["current_day"] < 15:
        game_state["current_day"] += 1
        
        # Przy zmianie dnia zapisujemy AKTUALNĄ cenę jako nową bazę otwarcia kolejnego dnia
        for p in prices:
            p["day_open_price"] = p["price"]
            
        save_json("prices.json", prices)
        save_json("gamestate.json", game_state)
        return {"status": f"Dzień {game_state['current_day']}"}
    return {"error": "Maksymalny dzień osiągnięty"}

@app.get("/api/messages")
def get_messages(): return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    messages.append({"player": msg.player, "text": msg.text})
    save_json("messages.json", messages)
    return {"status": "ok"}

@app.get("/api/articles")
def get_articles(): return articles

@app.get("/api/admin/export-players")
def export_players(): return players

@app.post("/api/admin/import-players")
def import_players(raw_data: dict):
    global players
    players = raw_data
    save_json("players.json", players)
    return {"status": "Baza graczy przywrócona!"}

# ---- SILNIK RYNKOWY (ODŚWIEŻANIE 1s, SKALA DOBOWA 24H) ----
def market_engine():
    tick_count = 0
    
    # 24 godziny w sekundach – na tyle rozbijamy scenariusz trendu historycznego
    TICKS_PER_DAY = 86400.0 
    
    while True:
        # Pętla wykonuje się dokładnie co 1 sekundę w czasie rzeczywistym
        time.sleep(1)
        tick_count += 1
        
        day = game_state["current_day"]
        current_day_trends = MARKET_TRENDS.get(day, MARKET_TRENDS[15])
        
        # Pobranie prawdziwego czasu serwera do opisów osi czasu na frontendzie
        now = datetime.datetime.now()
        t_5m = now.strftime("%H:%M")
        t_1h = now.strftime("%H:00")
        t_1d = f"Dzień {day}"
        
        for p in prices:
            sym = p["symbol"]
            open_p = p["price"] 
            
            history_trend = current_day_trends.get(sym, 0.0)
            
            # Bezpieczny, mikro-szum sekundowy, aby cena żyła i drgała
            market_noise = random.uniform(-0.00002, 0.00002)
            
            player_impulse = game_state["player_trend_impulse"].get(sym, 0.0)
            
            # Dzielimy trend dobowy przez 86400 sekund
            tick_history_change = history_trend / TICKS_PER_DAY
            
            # Impuls zakupowy gracza rozkładamy na ok. 10 minut (600 sekund), aby wzrost był płynny
            tick_player_change = player_impulse / 600.0
            
            total_tick_change = tick_history_change + tick_player_change + market_noise
            
            # Zabezpieczenie przed nagłymi błędami (max 0.1% zmiany w 1 sekundę)
            if total_tick_change > 0.001: total_tick_change = 0.001
            if total_tick_change < -0.001: total_tick_change = -0.001
            
            close_p = round(max(open_p * (1 + total_tick_change), 0.02), 2)
            p["price"] = close_p
            
            # --- POPRAWKA PROCENTOWA ---
            # Pobieramy cenę otwarcia z początku DNIA i liczymy realny, skumulowany zysk/stratę z 24h
            day_open = p.get("day_open_price", open_p)
            if day_open <= 0: day_open = 0.01 
            p["daily_change"] = round(((close_p - day_open) / day_open) * 100, 2)
            
            # Powolne wygaszanie wpływu gracza sekunda po sekundzie
            game_state["player_trend_impulse"][sym] *= 0.995
            
            # Generowanie mikro-knotów dla świeczek
            high_p = round(max(open_p, close_p) + random.uniform(0.0005, close_p * 0.0002), 2)
            low_p = round(max(min(open_p, close_p) - random.uniform(0.0005, close_p * 0.0002), 0.01), 2)

            # Budowanie świec na bazie sekund i prawdziwego czasu
            for tf, label, interval in [("5m", t_5m, 300), ("1h", t_1h, 3600), ("1d", t_1d, 86400)]:
                hist = candles_history[sym][tf]
                
                # Tworzymy nową świecę po upływie interwału (np. 300s dla wykresu 5-minutowego)
                if tick_count % interval == 0 or len(hist) == 0:
                    hist.append([label, open_p, high_p, low_p, close_p])
                else:
                    last = hist[-1]
                    last[0] = label
                    last[2] = max(last[2], high_p)
                    last[3] = min(last[3], low_p)
                    last[4] = close_p
                if len(hist) > 20: candles_history[sym][tf] = hist[-20:]

        # ---- MECHANIZM MARGIN CALL ----
        for username, player in list(players.items()):
            if username == "admin": continue
            
            for sym, positions in list(player.get("portfolio_long", {}).items()):
                current_price = next((p["price"] for p in prices if p["symbol"] == sym), None)
                if current_price is None: continue
                for pos in list(positions):
                    loss = (pos["buy_price"] - current_price) * pos["amount"] * pos["leverage"]
                    if loss >= pos["margin_allocated"]:
                        positions.remove(pos)
                        messages.append({"player": "SYSTEM", "text": f"🚨 MARGIN CALL! Pozycja LONG na {sym} gracza {username} została zlikwidowana z powodu braku depozytu."})
            
            for sym, positions in list(player.get("portfolio_short", {}).items()):
                current_price = next((p["price"] for p in prices if p["symbol"] == sym), None)
                if current_price is None: continue
                for pos in list(positions):
                    loss = (current_price - pos["entry_price"]) * pos["amount"] * pos["leverage"]
                    if loss >= pos["margin_allocated"]:
                        positions.remove(pos)
                        messages.append({"player": "SYSTEM", "text": f"🚨 MARGIN CALL! Pozycja SHORT na {sym} gracza {username} została zlikwidowana z powodu braku depozytu."})

        # Optymalizacja zapisu (Zapis na dysk darmowego Rendera co 5 sekund, zamiast co sekundę)
        if tick_count % 5 == 0:
            save_json("prices.json", prices)
            save_json("candles.json", candles_history)
            save_json("messages.json", messages)
            save_json("gamestate.json", game_state)
            save_json("players.json", players)

threading.Thread(target=market_engine, daemon=True).start()