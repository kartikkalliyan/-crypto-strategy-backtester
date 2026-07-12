"""
PHASE 4 (v3): Trend-following strategy -- Moving Average Crossover.

Unlike the RSI/MACD mean-reversion approach (which tries to catch
tops/bottoms and often exits trends too early), this strategy just
rides the trend:

    BUY  -> 20-day MA crosses ABOVE the 50-day MA   ("golden cross")
    SELL -> 20-day MA crosses BELOW the 50-day MA   ("death cross")
    HOLD -> otherwise

This tends to perform much better during strong sustained trends
(like the BTC bull run in our data), because it stays in the trade
the whole time instead of taking profits early. Its weakness is
choppy/sideways markets, where it "whipsaws" (frequent false signals).
"""

import pandas as pd


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"

    prev_ma20 = df["MA_20"].shift(1)
    prev_ma50 = df["MA_50"].shift(1)

    golden_cross = (prev_ma20 <= prev_ma50) & (df["MA_20"] > df["MA_50"])
    death_cross = (prev_ma20 >= prev_ma50) & (df["MA_20"] < df["MA_50"])

    df.loc[golden_cross, "signal"] = "BUY"
    df.loc[death_cross, "signal"] = "SELL"

    return df


def show_signal_log(df):
    signals = df[df["signal"] != "HOLD"]
    print(f"\nTotal signals generated: {len(signals)}")
    print(signals[["timestamp", "close", "MA_20", "MA_50", "signal"]]
          .to_string(index=False))


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = generate_signals(df)
    df.to_csv("btc_with_signals.csv", index=False)
    show_signal_log(df)
