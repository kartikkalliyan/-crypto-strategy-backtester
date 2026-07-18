import pandas as pd
from strategy_v4_filtered_ma import generate_signals
from backtest import backtest


def run_and_report(filepath, label):
    df = pd.read_csv(filepath, parse_dates=["timestamp"])
    df = generate_signals(df)
    results = backtest(df, starting_cash=1000.0, fee_rate=0.001, trailing_stop_pct=0.10)

    print(f"\n{'=' * 55}")
    print(f"{label}  ({df['timestamp'].min().date()} to {df['timestamp'].max().date()})")
    print(f"{'=' * 55}")
    print(f"Strategy return:   {results['strategy_return_pct']:.2f}%")
    print(f"Buy & hold return: {results['buy_hold_return_pct']:.2f}%")
    print(f"Number of trades:  {results['num_trades']}")

    return results


if __name__ == "__main__":
    train_results = run_and_report("btc_train.csv", "TRAIN SET RESULTS")
    test_results = run_and_report("btc_test.csv", "TEST SET RESULTS (unseen data)")

    print(f"\n{'=' * 55}")
    print("SUMMARY")
    print(f"{'=' * 55}")
    print(f"TRAIN strategy return: {train_results['strategy_return_pct']:.2f}%  "
          f"(buy&hold: {train_results['buy_hold_return_pct']:.2f}%)")
    print(f"TEST  strategy return: {test_results['strategy_return_pct']:.2f}%  "
          f"(buy&hold: {test_results['buy_hold_return_pct']:.2f}%)")