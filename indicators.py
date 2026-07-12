"""
PHASE 3: Technical indicators, written from scratch with pandas.

Writing these yourself (instead of importing a black-box library)
means you actually understand what "RSI = 30" means, instead of
just trusting a number.
"""

import pandas as pd


def add_moving_averages(df, windows=(20, 50, 200)):
    """Simple moving averages over the close price."""
    for w in windows:
        df[f"MA_{w}"] = df["close"].rolling(window=w).mean()
    return df


def add_rsi(df, period=14):
    """
    RSI (Relative Strength Index): measures speed/magnitude of recent
    price changes. Ranges 0-100.
      RSI > 70  -> often considered "overbought"
      RSI < 30  -> often considered "oversold"
    """
    delta = df["close"].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df, fast=12, slow=26, signal=9):
    """
    MACD (Moving Average Convergence Divergence): difference between
    a fast and slow exponential moving average, plus a signal line.
    Common rule: MACD crossing above signal line = bullish momentum.
    """
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    return df


def add_all_indicators(df):
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)
    return df


if __name__ == "__main__":
    df = pd.read_csv("btc_daily.csv", parse_dates=["timestamp"])
    df = add_all_indicators(df)
    df.to_csv("btc_daily_with_indicators.csv", index=False)
    print(df.tail())
