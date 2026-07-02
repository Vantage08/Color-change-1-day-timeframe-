import json
import time
import threading
import requests
import websocket

# --- CONFIGURATION ---
SYMBOL = "ETHUSDT"       
INTERVAL = "D"           # Daily Timeframe
MARKET_TYPE = "linear"   

# Your MacroDroid Webhook Configuration
MACRODROID_DEVICE_ID = "5fb875be-984c-4dda-afaf-d0f88d3c7ed6" 
MACRODROID_IDENTIFIER = "candle_alert"
MACRODROID_URL = f"https://trigger.macrodroid.com/{MACRODROID_DEVICE_ID}/{MACRODROID_IDENTIFIER}"

def calculate_ema(prices, period):
    """Calculates Exponential Moving Average (EMA) for a list of close prices."""
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period  # Simple Moving Average as the seed
    for price in prices[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def fetch_historical_closes():
    """Fetches the last 50 daily close prices from Bybit to calculate accurate EMAs."""
    url = f"https://api.bybit.com/v5/market/kline?category={MARKET_TYPE}&symbol={SYMBOL}&interval={INTERVAL}&limit=50"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("retCode") == 0:
            # Bybit returns newest first, so reverse it to chronological order
            klines = data["result"]["list"][::-1]
            closes = [float(k[4]) for k in klines]  # Index 4 is the close price
            return closes
    except Exception as e:
        print(f"Failed to fetch historical data for EMA calculation: {e}")
    return []

def send_ping(ws):
    while True:
        time.sleep(20)
        if ws.sock and ws.sock.connected:
            ws.send(json.dumps({"op": "ping"}))

def on_message(ws, message):
    payload = json.loads(message)
    if "op" in payload and payload["op"] == "pong":
        return

    if "topic" in payload and "data" in payload:
        candle_data = payload["data"][0]
        is_candle_closed = candle_data.get("confirm", False)
        
        if is_candle_closed:
            open_price = float(candle_data["open"])
            close_price = float(candle_data["close"])
            color = "green" if close_price >= open_price else "red"
            
            # Fetch history to compute EMAs
            closes = fetch_historical_closes()
            if not closes:
                print("Skipping processing due to historical data fetch failure.")
                return
                
            # Append the current closing candle if it's not already in history
            if closes[-1] != close_price:
                closes.append(close_price)
                
            ema5 = calculate_ema(closes, 5)
            ema20 = calculate_ema(closes, 20)
            
            if ema5 is None or ema20 is None:
                print("Not enough history to compute EMAs.")
                return
                
            print(f"[{SYMBOL}] Close: {close_price} | EMA5: {ema5:.2f} | EMA20: {ema20:.2f}")
            
            # Evaluate EMA conditions
            trend_match = "no"
            if color == "green" and ema5 > ema20:
                trend_match = "yes"
            elif color == "red" and ema5 < ema20:
                trend_match = "yes"
                
            print(f"[{SYMBOL}] Daily Close {color.upper()}. Trend Match: {trend_match.upper()}. Sending Webhook...")
            
            try:
                response = requests.get(
                    MACRODROID_URL, 
                    params={"color": color, "price": close_price, "trend_match": trend_match}, 
                    timeout=5
                )
                print(f"MacroDroid response status: {response.status_code}")
            except Exception as e:
                print(f"Failed to hit MacroDroid Webhook: {e}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    time.sleep(2)
    start_socket()

def on_open(ws):
    threading.Thread(target=send_ping, args=(ws,), daemon=True).start()
    subscribe_payload = {"op": "subscribe", "args": [f"kline.{INTERVAL}.{SYMBOL}"]}
    ws.send(json.dumps(subscribe_payload))

def start_socket():
    SOCKET_URL = f"wss://stream.bybit.com/v5/public/{MARKET_TYPE}"
    ws = websocket.WebSocketApp(SOCKET_URL, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever()

if __name__ == "__main__":
    start_socket()
