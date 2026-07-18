import pandas as pd


def generate_signals(df):
    df = df.copy()
    df["signal"] = "HOLD"
    df.iloc[0, df.columns.get_loc("signal")] = "BUY"
    return df