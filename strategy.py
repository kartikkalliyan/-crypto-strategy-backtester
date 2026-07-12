import pandas as pd


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"

    prev_rsi = df["RSI"].shift(1)
    prev_macd = df["MACD"].shift(1)
    prev_macd_signal = df["MACD_signal"].shift(1)

    rsi_cross_up_30 = (prev_rsi < 30) & (df["RSI"] >= 30)
    above_trend = df["close"] > df["MA_50"]
    buy_condition = rsi_cross_up_30 & above_trend

    rsi_cross_up_70 = (prev_rsi < 70) & (df["RSI"] >= 70)
    macd_cross_down = (prev_macd > prev_macd_signal) & (df["MACD"] <= df["MACD_signal"])
    sell_condition = rsi_cross_up_70 | macd_cross_down

    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[sell_condition, "signal"] = "SELL"

    return df


def show_signal_log(df):
    signals = df[df["signal"] != "HOLD"]
    print(f"\nTotal signals generated: {len(signals)}")
    print(signals[["timestamp", "close", "RSI", "MACD", "MACD_signal", "signal"]]
          .to_string(index=False))


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = generate_signals(df)
    df.to_csv("btc_with_signals.csv", index=False)
    show_signal_log(df)