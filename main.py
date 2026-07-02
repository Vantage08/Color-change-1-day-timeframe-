import json
import time
import threading
import requests
import websocket

# --- CONFIGURATION ---
SYMBOL = "ETHUSDT"       # Switched to ETH Futures (uppercase)
INTERVAL = "1"           # Timeframe in minutes ("1", "5", "15", "60")
MARKET_TYPE = "linear"   # "linear" handles USDT Perpetuals/Futures

# Your MacroDroid Webhook Configuration
MACRODROID_DEVICE_ID = "5fb875be-984c-4dda-afaf-d0f88d3c7ed6" 
MACRODROID_IDENTIFIER = "candle_alert"
MACRODROID_URL = f"https://trigger.macrodroid.com/{MACRODROID_DEVICE_ID}/{MACRODROID_IDENTIFIER}"

SOCKET_URL = f"wss://stream.bybit.com/v5/public/{MARKET_TYPE}"

def send_ping(ws):
    """Keeps the connection to Bybit alive (Required every 20s)."""
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
        
        # True only when the candle officially closes
        is_candle_closed = candle_data.get("confirm", False)
        
        if is_candle_closed:
            open_price = float(candle_data["open"])
            close_price = float(candle_data["close"])
            color = "green" if close_price >= open_price else "red"
            
            print(f"[{SYMBOL}] Candle Closed {color.upper()}. Sending Webhook...")
            
            # Instantly forward the data to MacroDroid
            try:
                response = requests.get(
                    MACRODROID_URL, 
                    params={"color": color, "price": close_price}, 
                    timeout=5
                )
                print(f"MacroDroid response status: {response.status_code}")
            except Exception as e:
                print(f"Failed to hit MacroDroid Webhook: {e}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### Connection lost. Reconnecting in 2s... ###")
    time.sleep(2)
    start_socket()

def on_open(ws):
    print(f"### Connected to Bybit V5 Futures Stream ###")
    threading.Thread(target=send_ping, args=(ws,), daemon=True).start()
    
    subscribe_payload = {
        "op": "subscribe",
        "args": [f"kline.{INTERVAL}.{SYMBOL}"]
    }
    ws.send(json.dumps(subscribe_payload))
    print(f"Subscribed to kline.{INTERVAL}.{SYMBOL}")

def start_socket():
    ws = websocket.WebSocketApp(
        SOCKET_URL, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close
    )
    ws.run_forever()

if __name__ == "__main__":
    start_socket()
