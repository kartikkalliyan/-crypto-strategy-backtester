import time
import os
import pandas as pd
import requests
from datetime import datetime

SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LOOKBACK = 200
CHECK_INTERVAL_MINUTES = 15
LOG_FILE = "live_signals_log.csv"


def fetch_latest_candles():
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": LOOKBACK}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    columns = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]
    df = pd.DataFrame(raw, columns=columns)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "timestamp"})
    df = df.iloc[:-1].reset_index(drop=True)
    return df


def compute_signal(df):
    df["MA_20"] = df["close"].rolling(window=20).mean()
    df["MA_50"] = df["close"].rolling(window=50).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    golden_cross = (prev["MA_20"] <= prev["MA_50"]) and (latest["MA_20"] > latest["MA_50"])
    death_cross = (prev["MA_20"] >= prev["MA_50"]) and (latest["MA_20"] < latest["MA_50"])

    if golden_cross:
        return "BUY", latest
    elif death_cross:
        return "SELL", latest
    else:
        return "HOLD", latest


def log_signal(signal, row):
    file_exists = os.path.isfile(LOG_FILE)
    entry = pd.DataFrame([{
        "checked_at": datetime.now(),
        "candle_time": row["timestamp"],
        "close_price": row["close"],
        "MA_20": row["MA_20"],
        "MA_50": row["MA_50"],
        "signal": signal
    }])
    entry.to_csv(LOG_FILE, mode="a", header=not file_exists, index=False)


def run_bot():
    print(f"Starting live monitor for {SYMBOL} ({INTERVAL} candles).")
    print(f"Checking every {CHECK_INTERVAL_MINUTES} minutes. Press Ctrl+C to stop.\n")

    while True:
        try:
            df = fetch_latest_candles()
            signal, latest_row = compute_signal(df)
            log_signal(signal, latest_row)

            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp_str}] Latest closed candle: {latest_row['timestamp']} "
                  f"| Price: {latest_row['close']:.2f} "
                  f"| MA20: {latest_row['MA_20']:.2f} | MA50: {latest_row['MA_50']:.2f} "
                  f"-> SUGGESTION: {signal}")

            if signal != "HOLD":
                print(f"  >>> New {signal} signal detected. Check live_signals_log.csv <<<")

        except Exception as e:
            print(f"Error during check: {e}. Will retry next cycle.")

        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run_bot()