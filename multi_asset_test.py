import time
import requests
import pandas as pd
from datetime import datetime

from indicators import add_all_indicators
from strategy_v3_ma_crossover import generate_signals
from backtest import backtest

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "PAXGUSDT"]
START_DATE = "2021-01-01"


def fetch_batch(symbol, interval, end_time_ms, limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit, "endTime": end_time_ms}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_history(symbol, interval="1d", start_date=START_DATE):
    all_rows = []
    end_time_ms = int(datetime.now().timestamp() * 1000)
    start_ms = int(pd.Timestamp(start_date).timestamp() * 1000)

    while True:
        batch = fetch_batch(symbol, interval, end_time_ms)
        if not batch:
            break
        all_rows = batch + all_rows
        oldest_time = batch[0][0]
        if oldest_time <= start_ms:
            break
        end_time_ms = oldest_time - 1
        time.sleep(0.3)

    columns = ["open_time", "open", "high", "low", "close", "volume",
               "close_time", "quote_asset_volume", "num_trades",
               "taker_buy_base", "taker_buy_quote", "ignore"]
    df = pd.DataFrame(all_rows, columns=columns)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "timestamp"})
    df = df[df["timestamp"] >= start_date].drop_duplicates(subset="timestamp")
    return df.sort_values("timestamp").reset_index(drop=True)


def test_asset(symbol):
    print(f"Fetching {symbol}...")
    try:
        df = fetch_history(symbol)
        if len(df) < 100:
            return {"symbol": symbol, "error": "Not enough data"}

        df = add_all_indicators(df)
        df = generate_signals(df)
        results = backtest(df, starting_cash=1000.0, fee_rate=0.001)

        return {
            "symbol": symbol,
            "strategy_return": results["strategy_return_pct"],
            "buy_hold_return": results["buy_hold_return_pct"],
            "num_trades": results["num_trades"],
            "beat_buy_hold": results["strategy_return_pct"] > results["buy_hold_return_pct"]
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


if __name__ == "__main__":
    all_results = []
    for symbol in ASSETS:
        result = test_asset(symbol)
        all_results.append(result)

    print("\n" + "=" * 70)
    print(f"{'Asset':<10}{'Strategy':>12}{'Buy&Hold':>12}{'Trades':>10}{'Beat B&H?':>14}")
    print("=" * 70)
    for r in all_results:
        if "error" in r:
            print(f"{r['symbol']:<10}  ERROR: {r['error']}")
        else:
            beat = "YES" if r["beat_buy_hold"] else "no"
            print(f"{r['symbol']:<10}{r['strategy_return']:>11.2f}%"
                  f"{r['buy_hold_return']:>11.2f}%{r['num_trades']:>10}{beat:>14}")

    pd.DataFrame(all_results).to_csv("multi_asset_results.csv", index=False)
    print("\nSaved full results to multi_asset_results.csv")