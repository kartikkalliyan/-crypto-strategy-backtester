import pandas as pd
from candlestick_patterns import add_candlestick_patterns


def generate_candlestick_signals(df):
    df = df.copy()
    df = add_candlestick_patterns(df)
    df["signal"] = "HOLD"

    below_trend = df["close"] < df["MA_50"]
    above_trend = df["close"] > df["MA_50"]

    bullish_pattern = df["pattern"].isin(["BULLISH_ENGULFING", "HAMMER"])
    bearish_pattern = df["pattern"].isin(["BEARISH_ENGULFING", "SHOOTING_STAR"])

    buy_condition = bullish_pattern & below_trend
    sell_condition = bearish_pattern & above_trend

    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[sell_condition, "signal"] = "SELL"

    return df


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = generate_candlestick_signals(df)
    df.to_csv("btc_with_candlestick_signals.csv", index=False)

    trades = df[df["signal"] != "HOLD"]
    print(f"Total signals: {len(trades)}")
    print(trades[["timestamp", "close", "MA_50", "pattern", "signal"]].to_string(index=False))