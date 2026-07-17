"""
PHASE 5: Backtesting.

This answers the real question: if you had followed every BUY/SELL
signal exactly, with real money and real trading fees, would you have
ended up ahead or behind -- compared to simply buying BTC once and
holding it the whole time?

No live trading, no predictions -- just an honest historical check.
"""

import pandas as pd


def backtest(df, starting_cash=1000.0, fee_rate=0.001, stop_loss_pct=None):
    """
    starting_cash : hypothetical starting capital (e.g. $1000)
    fee_rate      : trading fee per transaction (0.001 = 0.1%, Binance's real spot rate)
    stop_loss_pct : if set (e.g. 0.10 for 10%), force-sell immediately if
                    price drops this much from the entry price, regardless
                    of what the strategy's own SELL signal says. None = no stop-loss.
    """
    cash = starting_cash
    btc_held = 0.0
    in_position = False
    entry_price = None

    trade_log = []

    for _, row in df.iterrows():
        price = row["close"]
        signal = row["signal"]

        # --- Stop-loss check happens FIRST, before the normal signal logic ---
        if in_position and stop_loss_pct is not None:
            drop_from_entry = (entry_price - price) / entry_price
            if drop_from_entry >= stop_loss_pct:
                cash = (btc_held * price) * (1 - fee_rate)
                btc_held = 0.0
                in_position = False
                entry_price = None
                trade_log.append({
                    "date": row["timestamp"], "action": "STOP_LOSS_SELL",
                    "price": price, "btc_held": btc_held, "cash": cash
                })
                continue

        if signal == "BUY" and not in_position:
            btc_bought = (cash * (1 - fee_rate)) / price
            btc_held = btc_bought
            cash = 0.0
            in_position = True
            entry_price = price
            trade_log.append({
                "date": row["timestamp"], "action": "BUY",
                "price": price, "btc_held": btc_held, "cash": cash
            })

        elif signal == "SELL" and in_position:
            cash = (btc_held * price) * (1 - fee_rate)
            btc_held = 0.0
            in_position = False
            entry_price = None
            trade_log.append({
                "date": row["timestamp"], "action": "SELL",
                "price": price, "btc_held": btc_held, "cash": cash
            })

    final_price = df.iloc[-1]["close"]
    final_value = cash + (btc_held * final_price)

    first_price = df.iloc[0]["close"]
    buy_hold_btc = (starting_cash * (1 - fee_rate)) / first_price
    buy_hold_value = buy_hold_btc * final_price

    return {
        "starting_cash": starting_cash,
        "final_value_strategy": final_value,
        "final_value_buy_hold": buy_hold_value,
        "strategy_return_pct": (final_value / starting_cash - 1) * 100,
        "buy_hold_return_pct": (buy_hold_value / starting_cash - 1) * 100,
        "num_trades": len(trade_log),
        "trade_log": trade_log
    }


def print_report(results):
    print("=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    print(f"Starting capital:        ${results['starting_cash']:.2f}")
    print(f"Strategy final value:    ${results['final_value_strategy']:.2f}")
    print(f"Buy & hold final value:  ${results['final_value_buy_hold']:.2f}")
    print(f"Strategy return:         {results['strategy_return_pct']:.2f}%")
    print(f"Buy & hold return:       {results['buy_hold_return_pct']:.2f}%")
    print(f"Number of trades:        {results['num_trades']}")
    print("=" * 50)

    if results["strategy_return_pct"] > results["buy_hold_return_pct"]:
        print("Strategy BEAT buy-and-hold.")
    else:
        print("Strategy UNDERPERFORMED buy-and-hold.")
        print("(This is a very common, honest result -- most simple")
        print(" rule-based strategies don't beat just holding.)")


if __name__ == "__main__":
    df = pd.read_csv("btc_with_filtered_ma_signals.csv", parse_dates=["timestamp"])  
    results = backtest(df, starting_cash=1000.0, fee_rate=0.001, stop_loss_pct=0.10)
    print_report(results)

    trade_df = pd.DataFrame(results["trade_log"])
    trade_df.to_csv("backtest_trade_log.csv", index=False)
    print("\nFull trade log saved to backtest_trade_log.csv")