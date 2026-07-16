import pandas as pd


def add_candlestick_patterns(df, doji_threshold=0.001, wick_ratio=2.0):
    df = df.copy()

    body = (df["close"] - df["open"]).abs()
    candle_range = df["high"] - df["low"]
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]

    is_bullish = df["close"] > df["open"]
    is_bearish = df["close"] < df["open"]

    prev_open = df["open"].shift(1)
    prev_close = df["close"].shift(1)
    prev_bullish = prev_close > prev_open
    prev_bearish = prev_close < prev_open

    bullish_engulfing = (
        is_bullish & prev_bearish &
        (df["open"] <= prev_close) & (df["close"] >= prev_open)
    )
    bearish_engulfing = (
        is_bearish & prev_bullish &
        (df["open"] >= prev_close) & (df["close"] <= prev_open)
    )

    safe_body = body.replace(0, 0.0001)

    hammer = (
        (lower_wick >= wick_ratio * safe_body) &
        (upper_wick <= safe_body * 0.5)
    )
    shooting_star = (
        (upper_wick >= wick_ratio * safe_body) &
        (lower_wick <= safe_body * 0.5)
    )

    doji = (body / candle_range.replace(0, 0.0001)) <= doji_threshold

    df["pattern"] = "NONE"
    df.loc[doji, "pattern"] = "DOJI"
    df.loc[hammer, "pattern"] = "HAMMER"
    df.loc[shooting_star, "pattern"] = "SHOOTING_STAR"
    df.loc[bullish_engulfing, "pattern"] = "BULLISH_ENGULFING"
    df.loc[bearish_engulfing, "pattern"] = "BEARISH_ENGULFING"

    return df


if __name__ == "__main__":
    df = pd.read_csv("btc_daily.csv", parse_dates=["timestamp"])
    df = add_candlestick_patterns(df)

    found = df[df["pattern"] != "NONE"]
    print(f"Total patterns found: {len(found)}")
    print(found["pattern"].value_counts())
    print("\nMost recent patterns:")
    print(found[["timestamp", "open", "high", "low", "close", "pattern"]].tail(15).to_string(index=False))