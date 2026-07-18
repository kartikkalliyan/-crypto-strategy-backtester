import pandas as pd


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"

    prev_macd = df["MACD"].shift(1)
    prev_signal = df["MACD_signal"].shift(1)

    macd_cross_up = (prev_macd <= prev_signal) & (df["MACD"] > df["MACD_signal"])
    macd_cross_down = (prev_macd >= prev_signal) & (df["MACD"] < df["MACD_signal"])

    df.loc[macd_cross_up, "signal"] = "BUY"
    df.loc[macd_cross_down, "signal"] = "SELL"

    return df