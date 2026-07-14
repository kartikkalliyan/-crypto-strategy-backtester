import pandas as pd
from strategy_v3_ma_crossover import generate_signals
from backtest import backtest, print_report
from indicators import add_all_indicators

CRASH_START = "2022-01-01"
CRASH_END = "2022-12-31"

if __name__ == "__main__":
    df = pd.read_csv("btc_extended_history.csv", parse_dates=["timestamp"])
    df = add_all_indicators(df)

    crash_df = df[(df["timestamp"] >= CRASH_START) & (df["timestamp"] <= CRASH_END)].reset_index(drop=True)
    crash_df = generate_signals(crash_df)

    results = backtest(crash_df, starting_cash=1000.0, fee_rate=0.001)
    print_report(results)