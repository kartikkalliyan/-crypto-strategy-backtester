import pandas as pd
from regime_detector import add_regime


def generate_adaptive_signals(df):
    df = df.copy()
    df = add_regime(df)
    df["signal"] = "HOLD"
    df["active_strategy"] = None

    prev_rsi = df["RSI"].shift(1)
    prev_ma20 = df["MA_20"].shift(1)
    prev_ma50 = df["MA_50"].shift(1)

    golden_cross = (prev_ma20 <= prev_ma50) & (df["MA_20"] > df["MA_50"])
    death_cross = (prev_ma20 >= prev_ma50) & (df["MA_20"] < df["MA_50"])

    rsi_buy = (prev_rsi < 30) & (df["RSI"] >= 30)
    rsi_sell = (prev_rsi < 70) & (df["RSI"] >= 70)

    in_position = False
    active_strategy = None

    signals = []
    strategies = []

    for i in range(len(df)):
        row = df.iloc[i]
        signal = "HOLD"

        if not in_position:
            if row["regime"] == "TRENDING" and golden_cross.iloc[i]:
                signal = "BUY"
                active_strategy = "MA_CROSSOVER"
                in_position = True
            elif row["regime"] == "CHOPPY" and rsi_buy.iloc[i]:
                signal = "BUY"
                active_strategy = "RSI_MEAN_REVERSION"
                in_position = True
        else:
            if active_strategy == "MA_CROSSOVER" and death_cross.iloc[i]:
                signal = "SELL"
                in_position = False
                active_strategy = None
            elif active_strategy == "RSI_MEAN_REVERSION" and rsi_sell.iloc[i]:
                signal = "SELL"
                in_position = False
                active_strategy = None

        signals.append(signal)
        strategies.append(active_strategy)

    df["signal"] = signals
    df["active_strategy"] = strategies
    return df


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = generate_adaptive_signals(df)
    df.to_csv("btc_with_adaptive_signals.csv", index=False)

    trades = df[df["signal"] != "HOLD"]
    print(f"Total signals: {len(trades)}")
    print(trades[["timestamp", "close", "regime", "signal", "active_strategy"]].to_string(index=False))