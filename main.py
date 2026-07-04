import json
import time
import threading
import requests
import websocket

# --- CONFIGURATION ---
SYMBOL = "ETHUSDT"
INTERVAL = "D"
MARKET_TYPE = "linear"

# WunderTrading Webhook Configuration
WT_URL = "https://wtalerts.com/bot/other"

LONG_PAYLOAD = {
    "code": "ENTER-LONG_Bybit_NONE_Eth short 15_15M_8e34479cfe49027eda195457",
    "amountPerTrade": "1.0",
    "amountPerTradeType": "percents"
}

SHORT_PAYLOAD = {
    "code": "ENTER-SHORT_Bybit_ETHUSDT_Eth short 15_15M_8e34479cfe49027eda195457",
    "amountPerTrade": "1.0",
    "amountPerTradeType": "percents"
}

def calculate_ema(prices, period):
    if len(prices) < period: return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def fetch_historical_closes():
    url = f"https://api.bybit.com/v5/market/kline?category={MARKET_TYPE}&symbol={SYMBOL}&interval={INTERVAL}&limit=50"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("retCode") == 0:
            klines = data["result"]["list"][::-1]
            return [float(k[4]) for k in klines]
    except Exception as e:
        print(f"Fetch error: {e}")
    return []

def send_wt_alert(payload):
    try:
        response = requests.post(WT_URL, json=payload, timeout=10)
        print(f"WunderTrading Response: {response.status_code}")
    except Exception as e:
        print(f"Failed to send to WT: {e}")

def on_message(ws, message):
    payload = json.loads(message)
    if "data" in payload and payload["data"][0].get("confirm"):
        candle_data = payload["data"][0]
        color = "green" if float(candle_data["close"]) >= float(candle_data["open"]) else "red"
        
        closes = fetch_historical_closes()
        if not closes: return
        
        ema5 = calculate_ema(closes, 5)
        ema20 = calculate_ema(closes, 20)
        
        if color == "green" and ema5 > ema20:
            print("EMA Bullish: Sending Long to WT")
            send_wt_alert(LONG_PAYLOAD)
        elif color == "red" and ema5 < ema20:
            print("EMA Bearish: Sending Short to WT")
            send_wt_alert(SHORT_PAYLOAD)

# ... [Keep your existing on_error, on_close, on_open, and start_socket functions]
