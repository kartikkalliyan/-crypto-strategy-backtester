"""
PHASE 4: Rule-based trading strategy.

This turns indicators into actual BUY / SELL / HOLD signals.
It's intentionally simple to start with — the goal is to understand
the mechanism, then improve it once we see backtest results (Phase 5).

Strategy logic:
    BUY  -> RSI crosses UP through 30 (leaving oversold)
            AND price is above the 50-day moving average (uptrend filter)
    SELL -> RSI crosses UP through 70 (entering overbought)
            OR MACD crosses below its signal line (momentum turning down)
    HOLD -> anything else
"""

import pandas as pd


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"

    # Shifted values so we can detect "crossing" (comparing today vs yesterday)
    prev_rsi = df["RSI"].shift(1)
    prev_macd = df["MACD"].shift(1)
    prev_macd_signal = df["MACD_signal"].shift(1)

    # --- BUY condition ---
    rsi_cross_up_30 = (prev_rsi < 30) & (df["RSI"] >= 30)
    above_trend = df["close"] > df["MA_50"]
    buy_condition = rsi_cross_up_30 & above_trend

    # --- SELL condition ---
    # v2: removed the MACD-cross-down trigger -- it fired too often and
    # exited positions too early during strong uptrends (see v1 backtest).
    # Now we only sell on genuine overbought RSI, or if price breaks
    # below the 50-day trend line (a real trend-reversal signal).
    rsi_cross_up_70 = (prev_rsi < 70) & (df["RSI"] >= 70)
    trend_broken = (df["close"].shift(1) > df["MA_50"].shift(1)) & (df["close"] <= df["MA_50"])
    sell_condition = rsi_cross_up_70 | trend_broken

    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[sell_condition, "signal"] = "SELL"

    return df


def show_signal_log(df):
    """Print a readable list of every BUY/SELL signal generated."""
    signals = df[df["signal"] != "HOLD"]
    print(f"\nTotal signals generated: {len(signals)}")
    print(signals[["timestamp", "close", "RSI", "MACD", "MACD_signal", "signal"]]
          .to_string(index=False))


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = generate_signals(df)
    df.to_csv("btc_with_signals.csv", index=False)
    show_signal_log(df)
