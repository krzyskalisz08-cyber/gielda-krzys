from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
import threading
import time
import os
import json

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

# ---- STATYCZNA BAZA AKTYWÓW ----
market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "desc": "Kompleks portowy zlokalizowany nad Zatoką Gdańską. Budowa rozpoczęta na mocy ustawy z dnia 23 września 1922 roku."},
    "MAGI": {"name": "Magistrala Śląsk-Gdynia", "base_price": 80.0, "desc": "Magistrala kolejowa Herby Nowe – Gdynia, oznaczona jako linia numer 201. Całkowita długość wynosi dokładnie 452 km."},
    "COP": {"name": "Centralny Okręg Przemysłowy", "base_price": 150.0, "desc": "Okręg przemysłu ciężkiego o powierzchni niemal 60 000 kilometrów kwadratowych, zlokalizowany w widłach Wisły i Sanu."},
    "AZOT": {"name": "Zakłady Azotowe Tarnów", "base_price": 60.0, "desc": "Państwowa Fabryka Związków Azotowych w Mościcach pod Tarnowem, wybudowana na obszarze 620 hektarów."},
    "STAL": {"name": "Stalowa Wola", "base_price": 100.0, "desc": "Zakłady Południowe zlokalizowane w nowo powstającym mieście Stalowa Wola w województwie lwowskim."},
    "KOLEJ": {"name": "Spółki Kolejowe i Transportowe", "base_price": 120.0, "desc": "Ogólnokrajowa infrastruktura Polskich Kolei Państwowych (PKP) zarządzająca sieciam ponad 17 000 km linii."},
    "AUTO": {"name": "Państwowe Zakłady Inżynierii", "base_price": 70.0, "desc": "Państwowe Zakłady Inżynierii (PZInż) z siedzibą przy ulicy Terespolskiej w Warszawie."},
    "ZLOTO": {"name": "Złoto", "base_price": 45.0, "desc": "Kruszec lokacyjny stanowiący oficjalną bazę rezerw Banku Polskiego. Powiązany z reformą Grabskiego."},
    "MIEDZ": {"name": "Miedź", "base_price": 20.0, "desc": "Metal przemysłowy o wysokiej przewodności, sprowadzany głównie drogą morską ze względu na zapotrzebowanie elektryfikacji."},
    "SREBRO": {"name": "Srebro", "base_price": 25.0, "desc": "Kruszec o podwójnym zastosowaniu rynkowym. Wykorzystywany jako surowiec menniczy przez Mennicę Państwową."},
    "USD": {"name": "Dolar Amerykański", "base_price": 5.20, "desc": "Główna waluta rezerwowa i rozliczeniowa Stanów Zjednoczonych Ameryki, oparta na parytecie złota."}
}

# ---- FUNKCJE ZAPISU I ODCZYTU Z PLIKÓW JSON ----
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

# ---- INICJALIZACJA ZMIENNYCH GLOBALNYCH Z PLIKÓW (LUB DOMYŚLNYCH) ----
players = load_json("players.json", {})
prices = load_json("prices.json", [])
candles_history = load_json("candles.json", {})
messages = load_json("messages.json", [])
articles = load_json("articles.json", [
    {"title": "Otwarcie Rynku II RP", "content": "Wiadomość Centrali: Terminale maklerskie zostały zsynchronizowane. Wprowadzono twarde limity salda oraz automatyczny mechanizm Margin Call chroniący przed debetami."}
])
game_state = load_json("gamestate.json", {"current_day": 1, "player_trend_impulse": {}})

def init_game():
    global players, prices, candles_history, game_state
    
    # Jeśli plik graczy był pusty, stwórz domyślnych
    if not players:
        players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio_long": {}, "portfolio_short": {}}
        players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio_long": {}, "portfolio_short": {}}
        save_json("players.json", players)
        
    # Jeśli stan rynku był pusty, wygeneruj go od zera
    if not prices or not candles_history or "player_trend_impulse" not in game_state or not game_state["player_trend_impulse"]:
        prices = []
        candles_history = {}
        game_state["player_trend_impulse"] = {}
        
        for symbol, data in market_assets.items():
            prices.append({"symbol": symbol, "name": data["name"], "price": data["base_price"], "desc": data["desc"], "daily_change": 0.0})
            game_state["player_trend_impulse"][symbol] = 0.0
            bp = data["base_price"]
            
            candles_history[symbol] = {
                "5m": [["12:00", bp, bp+0.5, bp-0.5, bp]],
                "1h": [["12:00", bp, bp+1, bp-1, bp]],
                "1d": [["Dzień 1", bp, bp+2, bp-2, bp]]
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
    if dp.username == "admin":
        return {"error": "Nie można usunąć konta głównego administratora!"}
    if dp.username in players:
        del players[dp.username]
        save_json("players.json", players)
        return {"status": f"Pomyślnie usunięto patrol/gracza: {dp.username}"}
    return {"error": "Nie znaleziono podanego gracza."}

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    if tx.username not in players: 
        return {"error": "Brak gracza"}
    player = players[tx.username]
    
    if "portfolio_long" not in player: player["portfolio_long"] = {}
    if "portfolio_short" not in player: player["portfolio_short"] = {}

    idx = next((i for i, p in enumerate(prices) if p["symbol"] == tx.symbol), None)
    if idx is None: 
        return {"error": "Brak aktywa"}
    
    asset_price = prices[idx]["price"]
    market_cap_reference = 500000.0 
    trade_value = tx.amount * asset_price
    
    # ---- 1. KUPNO POZYCJI DŁUGIEJ (LONG) ----
    if tx.type == "buy_long":
        margin = trade_value / tx.leverage
        if player["balance"] < margin: 
            return {"error": f"Brak środków! Wymagany depozyt: {margin:.2f} zł, a Twoje saldo to: {player['balance']:.2f} zł."}
        player["balance"] -= margin
        player["portfolio_long"][tx.symbol] = player["portfolio_long"].get(tx.symbol, [])
        player["portfolio_long"][tx.symbol].append({"amount": tx.amount, "buy_price": asset_price, "leverage": tx.leverage, "margin_allocated": margin})
        
        impact = (trade_value / market_cap_reference) * 0.10
        game_state["player_trend_impulse"][tx.symbol] = min(game_state["player_trend_impulse"][tx.symbol] + impact, 0.10)
        
    # ---- 2. ZAMKNIĘCIE POZYCJI DŁUGIEJ (SELL LONG) ----
    elif tx.type == "sell_long":
        positions = player["portfolio_long"].get(tx.symbol, [])
        if sum(pos["amount"] for pos in positions) < tx.amount: 
            return {"error": "Brak wymaganej liczby jednostek LONG!"}
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
        
        impact = (trade_value / market_cap_reference) * 0.10
        game_state["player_trend_impulse"][tx.symbol] = max(game_state["player_trend_impulse"][tx.symbol] - impact, -0.10)

    # ---- 3. OTWARCIE POZYCJI KRÓTKIEJ (OPEN SHORT) ----
    elif tx.type == "open_short":
        margin = trade_value / tx.leverage
        if player["balance"] < margin: 
            return {"error": f"Brak środków! Wymagany depozyt: {margin:.2f} zł, a Twoje saldo to: {player['balance']:.2f} zł."}
        player["balance"] -= margin
        player["portfolio_short"][tx.symbol] = player["portfolio_short"].get(tx.symbol, [])
        player["portfolio_short"][tx.symbol].append({"amount": tx.amount, "entry_price": asset_price, "leverage": tx.leverage, "margin_allocated": margin})
        
        impact = (trade_value / market_cap_reference) * 0.10
        game_state["player_trend_impulse"][tx.symbol] = max(game_state["player_trend_impulse"][tx.symbol] - impact, -0.10)

    # ---- 4. ZAMKNIĘCIE POZYCJI KRÓTKIEJ (CLOSE SHORT) ----
    elif tx.type == "close_short":
        positions = player["portfolio_short"].get(tx.symbol, [])
        if sum(pos["amount"] for pos in positions) < tx.amount: 
            return {"error": "Brak wymaganej liczby jednostek SHORT do zamknięcia!"}
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
        
        impact = (trade_value / market_cap_reference) * 0.10
        game_state["player_trend_impulse"][tx.symbol] = min(game_state["player_trend_impulse"][tx.symbol] + impact, 0.10)
        
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
        save_json("gamestate.json", game_state)
        return {"status": f"Dzień {game_state['current_day']}"}
    return {"error": "Maksymalny dzień osiągnięty"}

@app.get("/api/messages")
def get_messages(): 
    return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    messages.append({"player": msg.player, "text": msg.text})
    save_json("messages.json", messages)
    return {"status": "ok"}

@app.get("/api/articles")
def get_articles(): 
    return articles

def market_engine():
    tick_count = 15
    while True:
        time.sleep(4)
        tick_count += 1
        day = game_state["current_day"]
        
        for p in prices:
            sym = p["symbol"]
            open_p = p["price"]
            history_trend = 0.0
            
            if day <= 4:
                if sym == "USD": history_trend = 0.024
                if sym in ["COP", "STAL", "AZOT"]: history_trend = -0.005
                if sym == "PORT": history_trend = 0.006
            elif day == 5:
                if sym == "USD": history_trend = -0.06
                if sym in ["PORT", "KOLEJ"]: history_trend = 0.018
            elif day == 6:
                if sym == "USD": history_trend = 0.03
                if sym == "MIEDZ": history_trend = 0.014
            elif day in [7, 8, 9]:
                if sym in ["PORT", "MAGI", "KOLEJ"]: history_trend = 0.016
                if sym == "AUTO": history_trend = 0.018
                if sym == "AZOT": history_trend = 0.014
                if sym in ["MIEDZ", "SREBRO"]: history_trend = 0.007
            elif day in [10, 11, 12]:
                if sym in ["SREBRO", "MIEDZ", "AUTO"]: history_trend = -0.035
                if sym == "ZLOTO": history_trend = 0.022
            elif day == 13:
                if sym in ["PORT", "MAGI", "KOLEJ"]: history_trend = 0.026
            elif day == 14:
                if sym == "ZLOTO": history_trend = 0.035
                if sym in ["MIEDZ", "AUTO"]: history_trend = 0.01
            elif day == 15:
                if sym in ["COP", "STAL"]: history_trend = 0.05
                if sym in ["MIEDZ", "KOLEJ", "AUTO"]: history_trend = 0.018

            market_noise = random.uniform(-0.003, 0.003)
            player_impulse = game_state["player_trend_impulse"].get(sym, 0.0)
            
            tick_history_change = history_trend / 40.0
            tick_player_change = player_impulse / 40.0
            
            total_tick_change = tick_history_change + tick_player_change + market_noise
            
            if total_tick_change > 0.005: total_tick_change = 0.005
            if total_tick_change < -0.005: total_tick_change = -0.005
            
            close_p = round(max(open_p * (1 + total_tick_change), 0.02), 2)
            p["price"] = close_p
            p["daily_change"] = round(((close_p - open_p)/open_p)*100, 2)
            
            game_state["player_trend_impulse"][sym] *= 0.95
            
            high_p = round(max(open_p, close_p) + random.uniform(0.01, close_p * 0.002), 2)
            low_p = round(max(min(open_p, close_p) - random.uniform(0.01, close_p * 0.002), 0.01), 2)
            
            t_5m = f"12:{(tick_count*5)%60:02d}"
            t_1h = f"{(12+tick_count)%24:02d}:00"
            t_1d = f"Dzień {day}"

            for tf, label in [("5m", t_5m), ("1h", t_1h), ("1d", t_1d)]:
                hist = candles_history[sym][tf]
                if tick_count % 4 == 0 or len(hist) == 0:
                    hist.append([label, open_p, high_p, low_p, close_p])
                else:
                    last = hist[-1]
                    last[0] = label
                    last[2] = max(last[2], high_p)
                    last[3] = min(last[3], low_p)
                    last[4] = close_p
                if len(hist) > 15: candles_history[sym][tf] = hist[-15:]

        # ---- MECHANIZM MARGIN CALL (LIKWIDACJA) ----
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

        # Zapis stanu giełdy i graczy po każdym ticku (co 4 sekundy)
        save_json("prices.json", prices)
        save_json("candles.json", candles_history)
        save_json("messages.json", messages)
        save_json("gamestate.json", game_state)
        save_json("players.json", players)

threading.Thread(target=market_engine, daemon=True).start()