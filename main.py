from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import random
import threading
import time
import os

app = FastAPI(title="Giełda II RP - Obóz Harcerski")

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
    leverage: int # 1, 2, 3, 4, 5

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
    trend: float # -0.1 do 0.1 (modyfikator ręczny admina)

# ---------------- STRUKTURA DANYCH II RP ----------------
# Gra symuluje 15 dni (każdy dzień to skok w historii o ponad rok, aby zamknąć 20 lat II RP)
game_state = {
    "current_day": 1,
    "admin_trends": {} # Ręczne manipulacje admina na wykresach
}

# Memorandum i baza spółek + surowców
market_assets = {
    "PORT": {"name": "Port w Gdyni", "base_price": 100.0, "risk": "medium", "type": "company", "desc": "Budowa przynosi 40-60 mln zł rocznie. Koszt: 300 mln. Ryzyko średnie przez sytuację międzynarodową. Stabilny wzrost w długiej perspektywie."},
    "MAGI": {"name": "Magistrala Śląsk-Gdynia", "base_price": 80.0, "risk": "low", "type": "company", "desc": "Transport węgla. Przychody 30-50 mln zł rocznie. Koszt: 250 mln. Niskie ryzyko, stabilny popyt na węgiel."},
    "COP": {"name": "Centralny Okręg Przemysłowy", "base_price": 250.0, "risk": "high", "type": "company", "desc": "Strategiczny projekt państwowy. Koszt >3 mld zł. Początkowe straty, ale gigantyczny potencjał długoterminowy i zyski rzędu 100-150 mln zł."},
    "AZOT": {"name": "Zakłady Azotowe Tarnów", "base_price": 50.0, "risk": "medium", "type": "company", "desc": "Produkcja nawozów dla rolnictwa. Koszt: 100 mln. Zysk netto 5-8 mln rocznie. Stabilny popyt, ryzyko umiarkowane (ceny surowców)."},
    "STAL": {"name": "Stalowa Wola", "base_price": 120.0, "risk": "high", "type": "company", "desc": "Przemysł ciężki i wojskowy. Koszt: 200 mln. Przychody 50-80 mln rocznie. Zależne od zamówień rządowych i obronnych."},
    "KOLEJ": {"name": "Spółka Kolejowa (PKP)", "base_price": 150.0, "risk": "low", "type": "company", "desc": "Modernizacja sieci. Koszt: 500 mln. Przychody 100-150 mln rocznie. Podstawa transportu kraju, bardzo bezpieczna lokata."},
    "AUTO": {"name": "Fabryka Samochodów", "base_price": 70.0, "risk": "high", "type": "company", "desc": "Budowa pod Warszawą. Koszt: 150 mln. Rynek dopiero startuje, wysoka niepewność popytu, ale szansa na dynamiczny skok technologiczny."},
    "ZLOTO": {"name": "Złoto (PZBP)", "base_price": 45.0, "type": "resource", "desc": "Kruszec lokacyjny, bezpieczna przystań w czasach niepewności geopolitycznej II RP."},
    "MIEDZ": {"name": "Miedź", "base_price": 15.0, "type": "resource", "desc": "Surowiec strategiczny dla rozbudowy elektryczności i przemysłu zbrojeniowego COP."},
    "SREBRO": {"name": "Srebro", "base_price": 22.0, "type": "resource", "desc": "Wykorzystywane w przemyśle oraz do bicia monet obiegowych w II RP."},
    "USD": {"name": "Dolar Amerykański", "base_price": 5.30, "type": "resource", "desc": "Twarda waluta zagraniczna. Kurs zależny od stabilizacji złotego i sytuacji na świecie."}
}

prices = []
players = {}  # username -> {password, balance, portfolio: {symbol: {amount, buy_price, leverage}}}
messages = []

# Inicjalizacja domyślnych graczy i cen
def init_game():
    # Konto admina
    players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio": {}}
    # Pierwszy gracz testowy
    players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio": {}}
    
    for symbol, data in market_assets.items():
        prices.append({
            "symbol": symbol,
            "name": data["name"],
            "price": data["base_price"],
            "type": data["type"],
            "desc": data["desc"]
        })

init_game()

# ---- SERWOWANIE FRONTENDU ----
@app.get("/", response_class=HTMLResponse)
def get_frontend():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Błąd: Serwer działa, ale nie znaleziono pliku index.html</h1>"

# ---------------- ENDPOINTY GRACZY & ADMINA ----------------
@app.post("/api/register")
def register_player(cp: CreatePlayer):
    if cp.username in players:
        return {"error": "Ta nazwa użytkownika jest zajęta!"}
    players[cp.username] = {
        "password": cp.password,
        "balance": 5000.0, # Początkowy żołd na obozie
        "portfolio": {}
    }
    return {"status": "Zarejestrowano pomyślnie"}

@app.get("/api/prices")
def get_prices():
    return prices

@app.get("/api/player/{username}/{password}")
def get_player_data(username: str, password: str):
    if username not in players or players[username]["password"] != password:
        return {"error": "Błędny login lub hasło"}
    return {
        "balance": players[username]["balance"],
        "portfolio": players[username]["portfolio"],
        "current_day": game_state["current_day"]
    }

@app.get("/api/ranking")
def get_ranking():
    ranking_list = []
    for user, data in players.items():
        if user == "admin": continue
        ranking_list.append({"name": user, "balance": data["balance"]})
    return sorted(ranking_list, key=lambda x: x["balance"], reverse=True)

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    if tx.username not in players:
        return {"error": "Użytkownik nie istnieje"}
    
    player = players[tx.username]
    asset_price = next((p["price"] for p in prices if p["symbol"] == tx.symbol), None)
    
    if not asset_price:
        return {"error": "Nie znaleziono aktywów"}
        
    if tx.type == "buy":
        # Koszt zakupu przy uwzględnieniu dźwigni finansowej (leverage)
        # Przy dźwigni 5x, gracz płaci tylko 1/5 ceny jako depozyt
        required_margin = (asset_price * tx.amount) / tx.leverage
        if player["balance"] < required_margin:
            return {"error": "Masz za mało pieniędzy (brak depozytu zabezpieczającego)!"}
            
        player["balance"] -= required_margin
        
        if tx.symbol not in player["portfolio"]:
            player["portfolio"][tx.symbol] = []
            
        player["portfolio"][tx.symbol].append({
            "amount": tx.amount,
            "buy_price": asset_price,
            "leverage": tx.leverage
        })
        
    elif tx.type == "sell":
        positions = player["portfolio"].get(tx.symbol, [])
        if not positions:
            return {"error": "Nie posiadasz tego aktywa!"}
            
        # Zamykamy pierwszą otwartą pozycję (FIFO) pasującą ilością
        total_owned = sum(pos["amount"] for pos in positions)
        if total_owned < tx.amount:
            return {"error": "Chcesz sprzedać więcej niż posiadasz!"}
            
        # Prosta mechanika zamknięcia całości dla uproszczenia mobilnego handlu
        amount_to_remove = tx.amount
        refund = 0
        
        for pos in list(positions):
            if amount_to_remove <= 0: break
            if pos["amount"] <= amount_to_remove:
                # Obliczanie zysku/straty z dźwignią
                price_diff = asset_price - pos["buy_price"]
                position_profit = (price_diff * pos["amount"]) * pos["leverage"]
                initial_margin = (pos["buy_price"] * pos["amount"]) / pos["leverage"]
                
                refund += (initial_margin + position_profit)
                amount_to_remove -= pos["amount"]
                positions.remove(pos)
            else:
                # Częściowe zamknięcie pozycji
                fraction = amount_to_remove / pos["amount"]
                price_diff = asset_price - pos["buy_price"]
                position_profit = (price_diff * amount_to_remove) * pos["leverage"]
                initial_margin = (pos["buy_price"] * amount_to_remove) / pos["leverage"]
                
                refund += (initial_margin + position_profit)
                pos["amount"] -= amount_to_remove
                amount_to_remove = 0
                
        player["balance"] += max(refund, 0.0) # Zapobiega ujemnemu zwrotowi ponad depozyt
        player["portfolio"][tx.symbol] = positions

    return {"status": "ok"}

# ---------------- PANEL ADMINISTRATORA ----------------
@app.post("/api/admin/money")
def admin_add_money(data: AddMoney):
    if data.username in players:
        players[data.username]["balance"] += data.amount
        return {"status": f"Dodano {data.amount} zł użytkownikowi {data.username}"}
    return {"error": "Brak gracza"}

@app.post("/api/admin/trend")
def admin_set_trend(data: SetTrend):
    game_state["admin_trends"][data.symbol] = data.trend
    return {"status": f"Ustawiono trend dla {data.symbol}"}

@app.post("/api/admin/next-day")
def next_day():
    if game_state["current_day"] < 15:
        game_state["current_day"] += 1
        return {"status": f"Nastał dzień {game_state['current_day']} (Kolejny rok rozwoju II RP)"}
    return {"error": "Osiągnięto już 15 dzień obozu (koniec symulacji 20-lecia)!"}

@app.get("/api/messages")
def get_messages():
    return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    messages.append(msg)
    return {"status": "ok"}

# ---------------- SILNIK SYMULACJI GOSPODARCZEJ II RP ----------------
def market_engine():
    while True:
        time.sleep(4) # Ceny aktualizują się płynnie w tle co 4 sekundy
        for p in prices:
            symbol = p["symbol"]
            # Podstawowy losowy ruch rynkowy
            change_percent = random.uniform(-0.02, 0.02)
            
            # Wpływ roku / dnia obozowego na konkretne gałęzie gospodarki II RP
            day = game_state["current_day"]
            if symbol == "PORT" and day > 3: change_percent += 0.005 # Port w Gdyni rusza na pełne obroty
            if symbol == "COP" and day < 6: change_percent -= 0.008 # Budowa COP pochłania gigantyczne koszty (początkowe spadki)
            if symbol == "COP" and day >= 6: change_percent += 0.012 # Po 6 dniu COP generuje potężne zyski
            if symbol == "STAL" and day > 8: change_percent += 0.007 # Produkcja zbrojeniowa Stalowej Woli rośnie przed 1939 r.
            if symbol == "AUTO" and day > 10: change_percent += random.uniform(-0.04, 0.05) # Wysokie ryzyko fabryki aut
            
            # Wpływ ingerencji dh. Administratora
            if symbol in game_state["admin_trends"]:
                change_percent += game_state["admin_trends"][symbol]
                
            # Wyliczenie nowej ceny
            p["price"] = round(max(p["price"] * (1 + change_percent), 0.1), 2)

threading.Thread(target=market_engine, daemon=True).start()