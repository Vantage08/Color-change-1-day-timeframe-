import json
import requests

# --- CONFIGURATION ---
# CoinGecko uses lowercase IDs (ethereum) rather than ticker symbols
COINGECKO_ID = "ethereum" 
VS_CURRENCY = "usd"

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
    print(f"Executing daily strategy check for ETH via CoinGecko Public API...")
    
    # Fetch 30 days of daily OHLC candles (Format: [timestamp, open, high, low, close])
    url = f"https://api.coingecko.com/api/v3/coins/{COINGECKO_ID}/ohlc?vs_currency={VS_CURRENCY}&days=30"
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"Aggregator server returned a bad status code: {response.status_code}")
            print(f"Raw response: {response.text}")
            return
            
        try:
            ohlc_data = response.json()
        except Exception as json_err:
            print(f"JSON Parsing failed: {json_err}")
            return

        if not ohlc_data or not isinstance(ohlc_data, list):
            print("Invalid or empty data format received.")
            return

        # Extract closing prices up to the last completed candle (excluding the live candle)
        closes = [float(candle[4]) for candle in ohlc_data[:-1]]
        
        # FIX: Look at index -2 to analyze the completely closed historical daily candle, 
        # ignoring the live candle at index -1 that just opened at midnight UTC.
        completed_candle = ohlc_data[-2]
        open_price = float(completed_candle[1])
        close_price = float(completed_candle[4])
        
        color = "green" if close_price >= open_price else "red"
        
        # Calculate EMAs strictly based on completed historical closing data
        ema5 = calculate_ema(closes, 5)
        ema20 = calculate_ema(closes, 20)
        
        print(f"Yesterday's Closed Daily Candle -> Close: {close_price} | Color: {color.upper()} | EMA5: {ema5:.2f} | EMA20: {ema20:.2f}")
        
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
