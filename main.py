import json
import requests

# --- CONFIGURATION ---
SYMBOL = "ETHUSDT"
INTERVAL = "1D"  
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
    if len(prices) < period: 
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def run_strategy():
    print(f"Executing daily strategy check for {SYMBOL}...")
    
    # Switched to api.bytick.com to bypass Railway data center IP restrictions
    url = f"https://api.bytick.com/v5/market/kline?category={MARKET_TYPE}&symbol={SYMBOL}&interval={INTERVAL}&limit=50"
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"Bybit server returned a bad status code: {response.status_code}")
            print(f"Raw response: {response.text}")
            return
            
        try:
            data = response.json()
        except Exception as json_err:
            print(f"JSON Parsing failed. Raw response data was: {response.text}")
            print(f"Parsing error: {json_err}")
            return

        if data.get("retCode") != 0:
            print(f"Bybit API Error: {data.get('retMsg')}")
            return
            
        klines = data["result"]["list"][::-1] 
        closes = [float(k[4]) for k in klines]
        
        last_closed_candle = klines[-1]
        open_price = float(last_closed_candle[1])
        close_price = float(last_closed_candle[4])
        
        color = "green" if close_price >= open_price else "red"
        
        ema5 = calculate_ema(closes, 5)
        ema20 = calculate_ema(closes, 20)
        
        print(f"Daily Close: {close_price} | Color: {color.upper()} | EMA5: {ema5:.2f} | EMA20: {ema20:.2f}")
        
        if color == "green" and ema5 > ema20:
            print("EMA Bullish: Sending Long to WunderTrading...")
            res = requests.post(WT_URL, json=LONG_PAYLOAD, timeout=10)
            print(f"WunderTrading Response: {res.status_code}")
        elif color == "red" and ema5 < ema20:
            print("EMA Bearish: Sending Short to WunderTrading...")
            res = requests.post(WT_URL, json=SHORT_PAYLOAD, timeout=10)
            print(f"WunderTrading Response: {res.status_code}")
        else:
            print("Conditions not met for a trade. Exiting.")
            
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    run_strategy()
