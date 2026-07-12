"""
PHASE 1: Fetch real historical crypto price data from Binance.

Binance's kline (candlestick) endpoint is public — no API key needed
for historical data. This script pulls daily BTC/USDT candles and
saves them to a CSV.

Run this on YOUR machine (needs internet access):
    pip install requests pandas
    python fetch_data.py
"""

import requests
import pandas as pd

def fetch_binance_klines(symbol="BTCUSDT", interval="1d", limit=1000):
    """
    Fetch candlestick data from Binance public API.

    symbol   : trading pair, e.g. "BTCUSDT", "ETHUSDT"
    interval : "1m", "5m", "15m", "1h", "4h", "1d", "1w"
    limit    : number of candles to fetch (max 1000 per request)
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    raw_data = response.json()

    # Each row from Binance looks like:
    # [open_time, open, high, low, close, volume, close_time, ...]
    columns = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]
    df = pd.DataFrame(raw_data, columns=columns)

    # Convert types
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    # Keep just what we need
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "timestamp"})
    return df


if __name__ == "__main__":
    print("Fetching BTC/USDT daily candles from Binance...")
    df = fetch_binance_klines(symbol="BTCUSDT", interval="1d", limit=1000)
    df.to_csv("btc_daily.csv", index=False)
    print(f"Saved {len(df)} rows to btc_daily.csv")
    print(df.tail())
