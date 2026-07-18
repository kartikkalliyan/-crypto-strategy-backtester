import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from indicators import add_all_indicators
from regime_detector import add_regime
from strategy_v4_filtered_ma import generate_signals
from backtest import backtest

st.set_page_config(page_title="Live Trading Advisor", layout="centered")

ASSET_OPTIONS = {
    "Bitcoin (BTC)": "BTCUSDT",
    "Ethereum (ETH)": "ETHUSDT",
    "Solana (SOL)": "SOLUSDT",
    "Binance Coin (BNB)": "BNBUSDT",
    "PAX Gold (PAXG)": "PAXGUSDT",
}


@st.cache_data(ttl=300)
def fetch_data(symbol, interval="1d", limit=200):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    columns = ["open_time", "open", "high", "low", "close", "volume",
               "close_time", "quote_asset_volume", "num_trades",
               "taker_buy_base", "taker_buy_quote", "ignore"]
    df = pd.DataFrame(raw, columns=columns)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "timestamp"})

    df = df.iloc[:-1].reset_index(drop=True)
    return df


def get_recommendation(df):
    df = add_all_indicators(df)
    df = add_regime(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    golden_cross = (prev["MA_20"] <= prev["MA_50"]) and (latest["MA_20"] > latest["MA_50"])
    death_cross = (prev["MA_20"] >= prev["MA_50"]) and (latest["MA_20"] < latest["MA_50"])
    is_trending = latest["regime"] == "TRENDING"

    if golden_cross and is_trending:
        recommendation = "BUY"
        reason = "A golden cross (MA20 crossed above MA50) just occurred during a confirmed TRENDING period."
    elif death_cross and is_trending:
        recommendation = "SELL"
        reason = "A death cross (MA20 crossed below MA50) just occurred during a confirmed TRENDING period."
    else:
        recommendation = "HOLD"
        if not is_trending:
            reason = "Market is currently CHOPPY -- no confirmed trend, so no signal is trusted right now."
        else:
            reason = "No new crossover has occurred on the most recent candle."

    return recommendation, reason, latest


def run_track_record(df):
    signal_df = generate_signals(df)
    results = backtest(signal_df, starting_cash=1000.0, fee_rate=0.001, stop_loss_pct=0.10)
    return results, signal_df


def get_signal_history(signal_df, n=10):
    history = signal_df[signal_df["signal"] != "HOLD"].copy()
    history = history[["timestamp", "close", "regime", "signal"]].tail(n)
    history = history.rename(columns={
        "timestamp": "Date", "close": "Price", "regime": "Regime", "signal": "Signal"
    })
    history["Date"] = history["Date"].dt.date
    history["Price"] = history["Price"].round(2)
    return history.iloc[::-1]


@st.cache_data(ttl=300)
def get_all_recommendations():
    rows = []
    for label, sym in ASSET_OPTIONS.items():
        try:
            df = fetch_data(sym)
            rec, reason, latest = get_recommendation(df)
            rows.append({
                "Asset": label,
                "Price": f"${latest['close']:.2f}",
                "Regime": latest["regime"],
                "Recommendation": rec,
            })
        except Exception as e:
            rows.append({
                "Asset": label, "Price": "N/A", "Regime": "N/A",
                "Recommendation": f"Error: {e}"
            })
    return pd.DataFrame(rows)


st.title("Live Trading Advisor")
st.caption("Decision-support only. This tool never places trades -- you decide.")

with st.expander("What this strategy is actually good at (read before trusting it)"):
    st.markdown("""
    This strategy (regime-filtered MA crossover) was tested across 5 assets
    and multiple market periods, including a proper train/test split and a
    dedicated crash-period test. Here's what was actually found:

    - **Strength:** during the 2022 crash, it lost 47% while simply holding
      lost 65% -- a real, meaningful downside-protection edge.
    - **Weakness:** during strong sustained bull runs (which crypto has had
      a lot of), it consistently underperforms simply buying and holding,
      because it exits and re-enters, missing some of the upside.
    - **Overall:** it trades some upside for downside protection. It is
      *not* designed to beat a strong bull market -- it's designed to
      avoid the worst of a crash. Treat any BUY/SELL signal with that
      trade-off in mind, not as a promise of outperformance.
    """)

refresh_minutes = st.sidebar.selectbox(
    "Auto-refresh every:", [5, 15, 30, 60], index=1
)
st_autorefresh(interval=refresh_minutes * 60 * 1000, key="auto_refresh")

st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
           f"(auto-refreshing every {refresh_minutes} min)")

st.markdown("### All assets at a glance")
with st.spinner("Checking all assets..."):
    overview_df = get_all_recommendations()


def highlight_recommendation(val):
    if val == "BUY":
        return "color: green; font-weight: bold"
    elif val == "SELL":
        return "color: red; font-weight: bold"
    elif val == "HOLD":
        return "color: gray"
    return ""


st.dataframe(
    overview_df.style.map(highlight_recommendation, subset=["Recommendation"]),
    use_container_width=True, hide_index=True
)

st.markdown("---")
st.markdown("### Asset detail")

asset_label = st.selectbox("Choose an asset:", list(ASSET_OPTIONS.keys()))
symbol = ASSET_OPTIONS[asset_label]

with st.spinner(f"Fetching live data for {symbol}..."):
    df = fetch_data(symbol)
    recommendation, reason, latest = get_recommendation(df)

color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}[recommendation]
st.markdown(f"## :{color}[{recommendation}]")
st.write(reason)

col1, col2, col3 = st.columns(3)
col1.metric("Price", f"${latest['close']:.2f}")
col2.metric("MA20", f"${latest['MA_20']:.2f}")
col3.metric("MA50", f"${latest['MA_50']:.2f}")

st.write(f"**Regime:** {latest['regime']}  |  **RSI:** {latest['RSI']:.1f}")
st.caption(f"Based on most recent closed candle: {latest['timestamp'].date()}")

if recommendation == "HOLD" and latest["regime"] == "CHOPPY":
    st.caption("Context: markets are choppy about 80% of the time historically -- "
               "this strategy is designed to sit out these periods rather than "
               "guess, which is intentional, not a malfunction.")
elif recommendation == "BUY":
    st.caption("Context: this signal fires on a confirmed trend start. Historically, "
               "trend-following signals like this capture real moves but can also "
               "occasionally be a false start in a young trend.")
elif recommendation == "SELL":
    st.caption("Context: this signal is where the strategy has shown its clearest "
               "value historically -- exiting before a real reversal, which mattered "
               "most during the 2022 crash.")

st.line_chart(df.set_index("timestamp")[["close", "MA_20", "MA_50"]].tail(100))

st.markdown("### Track record (last ~200 days)")
st.caption("How this exact strategy would have performed historically on this asset -- "
           "so you can judge the recommendation with real context, not just trust it blindly.")

track_results, signal_df = run_track_record(df)
tcol1, tcol2, tcol3 = st.columns(3)
tcol1.metric("Strategy return", f"{track_results['strategy_return_pct']:.2f}%")
tcol2.metric("Buy & hold return", f"{track_results['buy_hold_return_pct']:.2f}%")
tcol3.metric("Number of trades", track_results['num_trades'])

if track_results['strategy_return_pct'] > track_results['buy_hold_return_pct']:
    st.success("Strategy beat buy-and-hold over this period.")
else:
    st.warning("Strategy underperformed buy-and-hold over this period. "
               "This strategy is designed for downside protection during crashes, "
               "not necessarily for beating a strong bull run.")

st.markdown("### Recent signal history")
st.caption("The actual BUY/SELL signals this strategy generated for this asset recently.")
history = get_signal_history(signal_df, n=10)
if len(history) > 0:
    st.dataframe(history, use_container_width=True, hide_index=True)
else:
    st.write("No BUY/SELL signals in the recent history window.")

st.markdown("---")
st.caption("Strategy: regime-filtered MA crossover (validated via train/test split, "
           "2022 crash test). Past performance does not guarantee future results.")