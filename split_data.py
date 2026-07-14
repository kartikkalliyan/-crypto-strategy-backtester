import pandas as pd
from indicators import add_all_indicators

TRAIN_END = "2023-12-31"
TEST_START = "2024-01-01"


if __name__ == "__main__":
    df = pd.read_csv("btc_extended_history.csv", parse_dates=["timestamp"])
    df = add_all_indicators(df)

    train_df = df[df["timestamp"] <= TRAIN_END].reset_index(drop=True)
    test_df = df[df["timestamp"] >= TEST_START].reset_index(drop=True)

    train_df.to_csv("btc_train.csv", index=False)
    test_df.to_csv("btc_test.csv", index=False)

    print(f"TRAIN set: {len(train_df)} rows, "
          f"{train_df['timestamp'].min().date()} to {train_df['timestamp'].max().date()}")
    print(f"TEST set:  {len(test_df)} rows, "
          f"{test_df['timestamp'].min().date()} to {test_df['timestamp'].max().date()}")