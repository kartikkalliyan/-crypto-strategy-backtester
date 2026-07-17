import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from indicators import add_all_indicators
from regime_detector import add_regime

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


st.title("Live Trading Advisor")
st.caption("Decision-support only. This tool never places trades -- you decide.")

asset_label = st.selectbox("Choose an asset:", list(ASSET_OPTIONS.keys()))
symbol = ASSET_OPTIONS[asset_label]

if st.button("Check latest recommendation", type="primary"):
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

    st.line_chart(df.set_index("timestamp")[["close", "MA_20", "MA_50"]].tail(100))
else:
    st.info("Select an asset and click the button above to get a recommendation.")

st.markdown("---")
st.caption("Strategy: regime-filtered MA crossover (validated via train/test split, "
           "2022 crash test). Past performance does not guarantee future results.")