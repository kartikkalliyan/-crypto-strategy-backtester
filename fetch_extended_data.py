import time
import requests
import pandas as pd
from datetime import datetime


def fetch_batch(symbol, interval, end_time_ms, limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
        "endTime": end_time_ms
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_extended_history(symbol="BTCUSDT", interval="1d", start_date="2020-01-01"):
    all_rows = []
    end_time_ms = int(datetime.now().timestamp() * 1000)
    start_ms = int(pd.Timestamp(start_date).timestamp() * 1000)

    print(f"Fetching {symbol} {interval} candles back to {start_date}...")

    while True:
        batch = fetch_batch(symbol, interval, end_time_ms)
        if not batch:
            break

        all_rows = batch + all_rows
        oldest_time = batch[0][0]

        print(f"  Fetched {len(batch)} candles, oldest so far: "
              f"{pd.to_datetime(oldest_time, unit='ms').date()}")

        if oldest_time <= start_ms:
            break

        end_time_ms = oldest_time - 1
        time.sleep(0.3)

    columns = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ]
    df = pd.DataFrame(all_rows, columns=columns)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "timestamp"})

    df = df[df["timestamp"] >= start_date].drop_duplicates(subset="timestamp")
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


if __name__ == "__main__":
    df = fetch_extended_history(symbol="BTCUSDT", interval="1d", start_date="2020-01-01")
    df.to_csv("btc_extended_history.csv", index=False)
    print(f"\nSaved {len(df)} rows spanning {df['timestamp'].min().date()} "
          f"to {df['timestamp'].max().date()}")
    print(df.head())
    print(df.tail())