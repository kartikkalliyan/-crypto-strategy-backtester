import pandas as pd


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"

    buy_condition = df["close"] < df["BB_lower"]
    sell_condition = df["close"] > df["BB_upper"]

    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[sell_condition, "signal"] = "SELL"

    return df