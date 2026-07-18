import pandas as pd

VOLUME_MULTIPLIER = 1.5


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"

    breakout_up = (df["close"] > df["High20"]) & (df["volume"] > VOLUME_MULTIPLIER * df["Vol_MA20"])
    breakdown = df["close"] < df["Low20"]

    df.loc[breakout_up, "signal"] = "BUY"
    df.loc[breakdown, "signal"] = "SELL"

    return df