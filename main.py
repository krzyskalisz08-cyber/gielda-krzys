from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
import threading
import time
import os

app = FastAPI(title="Giełda II RP - Realna Symulacja Chronologiczna")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

market_assets = {
    "PORT": {
        "name": "Port w Gdyni", 
        "base_price": 100.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Kompleks portowy zlokalizowany nad Zatoką Gdańską. Budowa rozpoczęta na mocy ustawy z dnia 23 września 1922 roku. Infrastruktura obejmuje tzw. Port Tymczasowy (wzniesiony kosztem około 25 milionów marek polskich), a docelowy projekt przewiduje baseny o głębokości do 10 metrów, nabrzeża przeładunkowe (m.in. Indyjskie, Rotterdamskie), falochron osłonowy o długości ponad 2 kilometrów oraz nowoczesną łuszczarnię ryżu i chłodnię składową. Roczne zdolności przeładunkowe w pierwszym etapie oszacowano na 2,5 miliona ton towarów, głównie węgla kamiennego i drewna."
    },
    "MAGI": {
        "name": "Magistrala Śląsk-Gdynia", 
        "base_price": 80.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Magistrala kolejowa Herby Nowe – Gdynia, oznaczona jako linia numer 201. Całkowita długość trasy wynosi dokładnie 452 kilometry. Państwowy projekt budowlany mający na celu bezpośrednie ominięcie terytorium Wolnego Miasta Gdańska. Prowadzi ruch towarowy przez stacje węzłowe Zduńska Wola Karsznice oraz Inowrocław. Koszt położenia jednego kilometra torowiska w trudnym terenie kaszubskim wyniósł średnio 220 000 złotych. Trasa jest w pełni przystosowana to obsługi ciężkich składów węglowych o masie brutto do 1800 ton, ciągniętych przez parowozy serii Ty23."
    },
    "COP": {
        "name": "Centralny Okręg Przemysłowy", 
        "base_price": 150.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Okręg przemysłu ciężkiego o powierzchni niemal 60 000 kilometrów kwadratowych, zlokalizowany w widłach Wisły i Sanu, obejmujący powiaty województw kieleckiego, lubelskiego, krakowskiego i lwowskiego. Całkowity budżet inwestycyjny rozpisany przez Departament Budżetowy Ministerstwa Skarbu wynosi 1 miliard złotych. Struktura podzielona jest na trzy regiony: surowcowy (kielecki), wytwórczy (sandomierski) oraz konsumpcyjny (lubelski). W skład zasobów wchodzą m.in. elektrownia wodna w Rożnowie oraz liczne zakłady przetwórstwa metali."
    },
    "AZOT": {
        "name": "Zakłady Azotowe Tarnów", 
        "base_price": 60.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Państwowa Fabryka Związków Azotowych w Mościcach pod Tarnowem, wybudowana na obszarze 620 hektarów zakupionym od rodziny Sanguszków. Koszt całej inwestycji infrastrukturalnej zamknął się w kwocie 64 milionów złotych rządu II RP. Kompleks posiada własną elektrociepłownię o mocy 30 MW, rozbudowany węzeł gazowy oraz instalacje do syntezy amoniaku według metody Fausera. Nominalna zdolność produkcyjna zakładu wynosi około 60 000 ton saletrzaku, siarczanu amonu oraz kwasu azotowego rocznie, przeznaczonych na rynek wewnętrzny."
    },
    "STAL": {
        "name": "Stalowa Wola", 
        "base_price": 100.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Zakłady Południowe zlokalizowane w nowo powstającym mieście Stalowa Wola w województwie lwowskim. Powierzchnia hal fabrycznych i hutniczych wynosi 120 hektarów. Inwestycja finansowana jest z kredytów Funduszu Obrony Narodowej. Park maszynowy składa się z nowoczesnych tokarek importowanych z Francji oraz własnego wydziału metalurgicznego wyposażonego w piece martenowskie o pojemności 50 ton. Profil produkcyjny obejmuje odlewy staliwne, lufy artylejryjskie, blachy pancerne oraz płyty walcowane na zimno."
    },
    "KOLEJ": {
        "name": "Spółki Kolejowe i Transportowe", 
        "base_price": 120.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Ogólnokrajowa infrastruktura Polskich Kolei Państwowych (PKP) zarządzająca sieciam ponad 17 000 kilometrów linii normalnotorowych. Tabor państwowy składa się z 5100 parowozów, 11 500 wagonów pasażerskich oraz około 150 000 wagonów towarowych (głównie węglarek i platform). Główny węzeł rozrządowy zlokalizowany jest w Warszawie (stacja Warszawa Główna). Oficjalna taryfa przewozowa za tonokilometr ładunku masowego wynosi średnio 0,04 złotego, a roczny wolumen przewozów towarowych oscyluje w granicach 60 milionów ton."
    },
    "AUTO": {
        "name": "Państwowe Zakłady Inżynierii", 
        "base_price": 70.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Państwowe Zakłady Inżynierii (PZInż) z siedzibą przy ulicy Terespolskiej w Warszawie, skupiające m.in. Fabrykę Samochodów Osobowych i Półciężarowych oraz Fabrykę Silników i Armatury w Ursusie. Zakłady posiadają wyłączne licencje na produkcję pojazdów ciężarowych i podwozi marki Fiat (modele 621 i 508), motocykli Sokół 1000 i 600 oraz ciągników gąsienicowych C7P. Zatrudnienie przekracza 6000 robotników i inżynierów. Moce montażowe linii produkcyjnej wynoszą do 3500 podwozi kołowych w skali roku."
    },
    "ZLOTO": {
        "name": "Złoto", 
        "base_price": 45.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Kruszec lokacyjny stanowiący oficjalną bazę rezerw Banku Polskiego. Jeden kilogram czystego złota o próbie 900 odpowiada parytetowi określonemu w statucie banku. Zgodnie z reformą Władysława Grabskiego z kwietnia 1924 roku, parytet polskiego złotego został powiązany bezpośrednio z wartością 0,168792 grama czystego kruszcu. Zasoby fizyczne Banku Polskiego przechowywane są w skarbcach w Warszawie, a część rezerw zdeponowana jest w bankach centralnych we Francji, Wielkiej Brytanii oraz w Federal Reserve Bank w Nowym Jorku."
    },
    "MIEDZ": {
        "name": "Miedź", 
        "base_price": 20.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Metal przemysłowy o wysokiej przewodności, sprowadzany głównie drogą morską z kopalń w Chile oraz drogą kolejową z Katangi. Standardowa giełdowa jednostka rozliczeniowa to 1 tona katod miedziowych na giełdzie w Londynie (LME). W kraju surowiec przetwarzany jest przez walcownie Dziedzice oraz zakłady w Szopienicach. Cena rynkowa ustalana jest w oparciu o cenniki międzynarodowe przeliczane na złote dewizowe. Średnie zużycie krajowe na cele elektryfikacyjne wynosi około 12 000 ton rocznie."
    },
    "SREBRO": {
        "name": "Srebro", 
        "base_price": 25.0, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Kruszec o podwójnym zastosowaniu rynkowym. Wykorzystywany jako surowiec menniczy przez Mennicę Państwową w Warszawie do bicia monet obiegowych (o nominałach 2, 5 i 10 złotych z wizerunkiem Polonii lub Józefa Piłsudskiego, o próbie srebra 750). Skup i rozliczenia realizowane są w uncjach trojańskich. Krajowe zapasy pochodzą częściowo z odzysku metalurgicznego na Górnym Śląsku oraz z importu surowego srebra rafinowanego z rafinerii w Hamburgu i Londynie."
    },
    "USD": {
        "name": "Dolar Amerykański", 
        "base_price": 5.20, 
        "desc": "Oficjalne memorandum wywiadu gospodarczego: Główna waluta rezerwowa i rozliczeniowa Stanów Zjednoczonych Ameryki, oparta na parytecie złota (zgodnie z ustawą Gold Standard Act). Przed reformą Grabskiego kurs dolara na wolnym rynku w Warszawie osiągał miliony marek polskich. Po wprowadzeniu złotego oficjalny kurs parytetowy ustalono na poziomie 5,18 złotego za 1 dolara amerykańskiego. Waluta ta służy w II RP do zabezpieczania transakcji zagranicznych oraz jako prywatny środek tezauryzacji (gromadzenia kapitału) przez obywateli."
    }
}

prices = []
candles_history = {} 
players = {}  
messages = []
articles = [
    {"title": "Otwarcie Rynku II RP", "content": "Wiadomość Centrali: Terminale maklerskie zostały zsynchronizowane. Rozpoczynamy symulację handlową opartą o uwarunkowania geopolityczne i gospodarcze państwa."}
]
game_state = {"current_day": 1, "player_impact": {}}

def init_game():
    players["admin"] = {"password": "druh", "balance": 9999999.0, "portfolio": {}}
    players["krzys"] = {"password": "dh1", "balance": 5000.0, "portfolio": {}}
    
    for symbol, data in market_assets.items():
        # Dodane pole daily_change do śledzenia procentów
        prices.append({"symbol": symbol, "name": data["name"], "price": data["base_price"], "desc": data["desc"], "daily_change": 0.0})
        game_state["player_impact"][symbol] = 1.0
        bp = data["base_price"]
        
        # Inicjalizacja świeczek ze znacznikami czasu w formacie string
        candles_history[symbol] = {
            "5m": [["12:00", bp, bp+0.5, bp-0.5, bp]],
            "1h": [["12:00", bp, bp+1, bp-1, bp]],
            "1d": [["Dzień 1", bp, bp+2, bp-2, bp]]
        }
        # Wygenerowanie przykładowej historii wstecznej
        for i in range(1, 15):
            t_5m = f"12:{i*5:02d}" if i*5 < 60 else f"13:{i*5-60:02d}"
            candles_history[symbol]["5m"].append([t_5m, bp, bp+random.uniform(-1,1), bp+random.uniform(-1,1), bp])
            candles_history[symbol]["1h"].append([f"{12+i}:00", bp, bp+random.uniform(-2,2), bp+random.uniform(-2,2), bp])
            candles_history[symbol]["1d"].append([f"Dzień {i}", bp, bp+random.uniform(-5,5), bp+random.uniform(-5,5), bp])

init_game()

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
    players[cp.username] = {"password": cp.password, "balance": 5000.0, "portfolio": {}}
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
        "portfolio": players[username]["portfolio"], 
        "current_day": game_state["current_day"]
    }

@app.get("/api/ranking")
def get_ranking():
    ranking_list = [{"name": u, "balance": d["balance"]} for u, d in players.items() if u != "admin"]
    return sorted(ranking_list, key=lambda x: x["balance"], reverse=True)

@app.post("/api/transactions")
def process_transaction(tx: Transaction):
    if tx.username not in players: 
        return {"error": "Brak gracza"}
    player = players[tx.username]
    idx = next((i for i, p in enumerate(prices) if p["symbol"] == tx.symbol), None)
    if idx is None: 
        return {"error": "Brak aktywa"}
    
    asset_price = prices[idx]["price"]
    if tx.type == "buy":
        margin = (asset_price * tx.amount) / tx.leverage
        if player["balance"] < margin: 
            return {"error": "Brak wolnych środków!"}
        player["balance"] -= margin
        player["portfolio"][tx.symbol] = player["portfolio"].get(tx.symbol, [])
        player["portfolio"][tx.symbol].append({"amount": tx.amount, "buy_price": asset_price, "leverage": tx.leverage})
        game_state["player_impact"][tx.symbol] = min(game_state["player_impact"][tx.symbol] + (tx.amount * 0.001), 1.15)
        
    elif tx.type == "sell":
        positions = player["portfolio"].get(tx.symbol, [])
        if sum(pos["amount"] for pos in positions) < tx.amount: 
            return {"error": "Brak wymaganej liczby jednostek!"}
        amt_to_rem = tx.amount
        refund = 0
        for pos in list(positions):
            if amt_to_rem <= 0: 
                break
            if pos["amount"] <= amt_to_rem:
                profit = ((asset_price - pos["buy_price"]) * pos["amount"]) * pos["leverage"]
                refund += ((pos["buy_price"] * pos["amount"]) / pos["leverage"] + profit)
                amt_to_rem -= pos["amount"]
                positions.remove(pos)
            else:
                profit = ((asset_price - pos["buy_price"]) * amt_to_rem) * pos["leverage"]
                refund += ((pos["buy_price"] * amt_to_rem) / pos["leverage"] + profit)
                pos["amount"] -= amt_to_rem
                amt_to_rem = 0
        player["balance"] += max(refund, 0.0)
        player["portfolio"][tx.symbol] = positions
        game_state["player_impact"][tx.symbol] = max(game_state["player_impact"][tx.symbol] - (tx.amount * 0.001), 0.85)
    return {"status": "ok"}

@app.post("/api/admin/money")
def admin_add_money(data: AddMoney):
    if data.username in players:
        players[data.username]["balance"] += data.amount
        return {"status": f"Przyznano {data.amount} zł"}
    return {"error": "Brak gracza"}

@app.post("/api/admin/change-percent")
def admin_change_percent(data: SetPercentChange):
    idx = next((i for i, p in enumerate(prices) if p["symbol"] == data.symbol), None)
    if idx is not None:
        multiplier = 1 + (data.percent / 100.0)
        prices[idx]["price"] = round(max(prices[idx]["price"] * multiplier, 0.01), 2)
        return {"status": f"Zmieniono cenę {data.symbol} o {data.percent}%"}
    return {"error": "Brak aktywa"}

@app.post("/api/admin/article")
def admin_add_article(art: Article):
    articles.append({"title": art.title, "content": art.content})
    return {"status": "Artykuł opublikowany"}

@app.post("/api/admin/next-day")
def next_day():
    if game_state["current_day"] < 15:
        game_state["current_day"] += 1
        return {"status": f"Dzień {game_state['current_day']}"}
    return {"error": "Maksymalny dzień osiągnięty"}

@app.get("/api/messages")
def get_messages(): 
    return messages[-30:]

@app.post("/api/messages")
def add_message(msg: Message):
    messages.append(msg)
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
                if sym == "USD": history_trend = -0.001
            elif day in [10, 11, 12]:
                if sym in ["SREBRO", "MIEDZ", "AUTO"]: history_trend = -0.035
                if sym == "ZLOTO": history_trend = 0.022
                if sym in ["PORT", "MAGI"]: history_trend = 0.004
            elif day == 13:
                if sym in ["PORT", "MAGI", "KOLEJ"]: history_trend = 0.026
                if sym == "ZLOTO": history_trend = -0.012
            elif day == 14:
                if sym == "ZLOTO": history_trend = 0.035
                if sym in ["MIEDZ", "AUTO"]: history_trend = 0.01
            elif day == 15:
                if sym in ["COP", "STAL"]: history_trend = 0.05
                if sym in ["MIEDZ", "KOLEJ", "AUTO"]: history_trend = 0.018

            market_noise = random.uniform(-0.01, 0.01)
            total_change = (history_trend * 0.6) + (market_noise * 0.4)
            total_change += (game_state["player_impact"][sym] - 1.0) * 0.05
            
            if total_change > 0.10: total_change = 0.10
            if total_change < -0.10: total_change = -0.10
            
            close_p = round(max(open_p * (1 + total_change), 0.02), 2)
            p["price"] = close_p
            # Wyliczenie procentowej zmiany dla front-endu
            p["daily_change"] = round(total_change * 100, 2)
            
            high_p = round(max(open_p, close_p) + random.uniform(0.01, close_p * 0.01), 2)
            low_p = round(max(min(open_p, close_p) - random.uniform(0.01, close_p * 0.01), 0.01), 2)
            
            # Znaczniki osi czasu
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
                if len(hist) > 15: 
                    candles_history[sym][tf] = hist[-15:]

threading.Thread(target=market_engine, daemon=True).start()