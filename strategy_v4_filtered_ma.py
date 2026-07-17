import pandas as pd
from regime_detector import add_regime


def generate_signals(df):
    df = df.copy()
    df = add_regime(df)
    df["signal"] = "HOLD"

    prev_ma20 = df["MA_20"].shift(1)
    prev_ma50 = df["MA_50"].shift(1)

    golden_cross = (prev_ma20 <= prev_ma50) & (df["MA_20"] > df["MA_50"])
    death_cross = (prev_ma20 >= prev_ma50) & (df["MA_20"] < df["MA_50"])

    is_trending = df["regime"] == "TRENDING"

    buy_condition = golden_cross & is_trending
    sell_condition = death_cross & is_trending

    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[sell_condition, "signal"] = "SELL"

    return df


def show_signal_log(df):
    signals = df[df["signal"] != "HOLD"]
    print(f"\nTotal signals generated: {len(signals)}")
    print(signals[["timestamp", "close", "MA_20", "MA_50", "regime", "signal"]]
          .to_string(index=False))


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = generate_signals(df)
    df.to_csv("btc_with_filtered_ma_signals.csv", index=False)
    show_signal_log(df)