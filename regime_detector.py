import pandas as pd
import numpy as np


def add_regime(df, window=14, trend_threshold=0.5):
    df = df.copy()

    net_move = (df["close"] - df["close"].shift(window)).abs()
    total_move = df["close"].diff().abs().rolling(window=window).sum()

    trend_strength = net_move / total_move.replace(0, np.nan)
    df["trend_strength"] = trend_strength

    df["regime"] = np.where(
        df["trend_strength"] >= trend_threshold, "TRENDING", "CHOPPY"
    )
    df.loc[df["trend_strength"].isna(), "regime"] = "UNKNOWN"

    return df


if __name__ == "__main__":
    df = pd.read_csv("btc_daily_with_indicators.csv", parse_dates=["timestamp"])
    df = add_regime(df)

    print(df[["timestamp", "close", "trend_strength", "regime"]].tail(20).to_string(index=False))

    print("\nRegime breakdown (% of days):")
    print((df["regime"].value_counts(normalize=True) * 100).round(1))