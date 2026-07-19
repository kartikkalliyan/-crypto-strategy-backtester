"""
LIVE TRADING ADVISOR - Streamlit UI

Lets you pick an asset (or type a custom one) from a dropdown, choose
a strategy and risk style, fetches live price data, and shows a clear
BUY/SELL/HOLD recommendation with reasoning and a historical track
record for that exact combination.

This is a DECISION-SUPPORT tool. It never places trades or touches
real money -- you decide whether to act on any recommendation shown.

Run with:
    pip install streamlit streamlit-autorefresh plotly
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from indicators import add_all_indicators
from regime_detector import add_regime
from strategy_v4_filtered_ma import generate_signals as ma_crossover_signals
from candlestick_strategy import generate_candlestick_signals
from strategy import generate_signals as rsi_signals
from strategy_bollinger import generate_signals as bollinger_signals
from strategy_macd import generate_signals as macd_signals
from strategy_breakout import generate_signals as breakout_signals
from strategy_buyhold import generate_signals as buyhold_signals
from backtest import backtest

st.set_page_config(page_title="Live Trading Advisor", layout="wide")

ASSET_OPTIONS = {
    "Bitcoin (BTC)": "BTCUSDT",
    "Ethereum (ETH)": "ETHUSDT",
    "Solana (SOL)": "SOLUSDT",
    "Binance Coin (BNB)": "BNBUSDT",
    "PAX Gold (PAXG)": "PAXGUSDT",
}

STRATEGY_FUNCS = {
    "MA Crossover (regime-filtered)": ma_crossover_signals,
    "Candlestick + Trend Filter": generate_candlestick_signals,
    "RSI Mean-Reversion": rsi_signals,
    "Bollinger Bands": bollinger_signals,
    "MACD Crossover": macd_signals,
    "Volume-Confirmed Breakout": breakout_signals,
    "Buy & Hold (baseline)": buyhold_signals,
}

RISK_STYLES = {
    "No stop-loss": {},
    "Fixed 10% stop-loss": {"stop_loss_pct": 0.10},
    "Trailing 10% stop": {"trailing_stop_pct": 0.10},
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


@st.cache_data(ttl=300)
def fetch_data_paginated(symbol, days, interval="1d"):
    all_rows = []
    end_time_ms = int(datetime.now().timestamp() * 1000)
    earliest_needed = datetime.now().timestamp() - (days * 86400)

    while True:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": 1000, "endTime": end_time_ms}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break

        all_rows = batch + all_rows
        oldest_time = batch[0][0]
        if (oldest_time / 1000) <= earliest_needed:
            break
        end_time_ms = oldest_time - 1

    columns = ["open_time", "open", "high", "low", "close", "volume",
               "close_time", "quote_asset_volume", "num_trades",
               "taker_buy_base", "taker_buy_quote", "ignore"]
    df = pd.DataFrame(all_rows, columns=columns)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    df = df.rename(columns={"open_time": "timestamp"})
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    df = df.iloc[:-1].reset_index(drop=True)
    return df


def find_data_for_trade_target(symbol, strategy_func, target_trades, max_days=3000):
    days = 300
    while True:
        df = fetch_data_paginated(symbol, days)
        prepped = prep_data(df.copy())
        signal_df = strategy_func(prepped)
        num_trades = len(signal_df[signal_df["signal"] != "HOLD"])

        ran_out_of_history = len(df) < days * 0.9
        if num_trades >= target_trades or days >= max_days or ran_out_of_history:
            return signal_df, num_trades, days

        days = min(days * 2, max_days)


def prep_data(df):
    df = add_all_indicators(df)
    df = add_regime(df)
    return df


def reason_for_signal(recommendation):
    if recommendation == "BUY":
        return "The selected strategy's entry conditions were met on the most recent closed candle."
    elif recommendation == "SELL":
        return "The selected strategy's exit conditions were met on the most recent closed candle."
    else:
        return "No new entry/exit condition triggered on the most recent closed candle."


def get_recommendation(df, strategy_func):
    signal_df = strategy_func(df.copy())
    latest = signal_df.iloc[-1]
    recommendation = latest["signal"]
    reason = reason_for_signal(recommendation)
    return recommendation, reason, latest, signal_df


def run_track_record(signal_df, risk_kwargs):
    results = backtest(signal_df, starting_cash=1000.0, fee_rate=0.001, **risk_kwargs)
    return results


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
    default_func = STRATEGY_FUNCS["MA Crossover (regime-filtered)"]
    for label, sym in ASSET_OPTIONS.items():
        try:
            df = fetch_data(sym)
            df = prep_data(df)
            rec, reason, latest, _ = get_recommendation(df, default_func)
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


def make_candlestick_chart(df, title=""):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["MA_20"], name="MA20",
        line=dict(color="#ffa726", width=1.5)
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["MA_50"], name="MA50",
        line=dict(color="#42a5f5", width=1.5)
    ))
    fig.update_layout(
        title=title, template="plotly_dark", height=450,
        xaxis_rangeslider_visible=True,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig


def badge(text, kind):
    colors = {
        "BUY": ("#0f5132", "#75dd9a"), "SELL": ("#5c1a1a", "#f28b8b"),
        "HOLD": ("#3a3a3a", "#bbbbbb"),
        "TRENDING": ("#0f5132", "#75dd9a"), "CHOPPY": ("#4a3b0f", "#e0c060"),
    }
    bg, fg = colors.get(kind, ("#3a3a3a", "#bbbbbb"))
    return (f'<span style="background-color:{bg}; color:{fg}; padding:4px 12px; '
            f'border-radius:12px; font-weight:600; font-size:0.9em;">{text}</span>')


st.title("Live Trading Advisor")
st.caption("Decision-support only. This tool never places trades -- you decide.")

with st.expander("What this strategy is actually good at (read before trusting it)"):
    st.markdown("""
    The default combo (regime-filtered MA crossover with a 10% trailing stop)
    was tested across 5 assets and multiple market periods, including a
    proper train/test split and a dedicated crash-period test:

    - **Strength:** during the 2022 crash, it lost only ~10% while simply
      holding lost 65% -- a strong, real downside-protection edge.
    - **Strength:** on BTC and ETH specifically, it meaningfully beat the
      fixed-stop version, and on ETH it even beat buy-and-hold outright.
    - **Known limitation:** on more volatile assets (SOL, BNB), the 10%
      trailing stop tends to get triggered by normal volatility, exiting
      trades too early.
    - You now have 7 strategies, 3 risk styles, and 2 ways to size the
      backtest window (by days or by target trade count) to mix and
      match per asset -- use the Track Record section below to compare
      combos honestly before trusting any recommendation.
    """)

refresh_minutes = st.sidebar.selectbox(
    "Auto-refresh every:", [5, 15, 30, 60], index=1
)
st_autorefresh(interval=refresh_minutes * 60 * 1000, key="auto_refresh")

st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
           f"(auto-refreshing every {refresh_minutes} min)")

st.markdown("### All assets at a glance")
st.caption("Uses the default combo (MA Crossover + Trailing stop). Customize per asset below.")
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

asset_label = st.selectbox("Choose an asset:", list(ASSET_OPTIONS.keys()) + ["Custom (type any symbol)"])

if asset_label == "Custom (type any symbol)":
    custom_input = st.text_input(
        "Enter a Binance trading pair symbol:",
        placeholder="e.g. DOGE, ADA, XRP, MATIC, LINK...",
        help="Just the coin name is fine -- USDT will be added automatically if you leave it off."
    )
    if not custom_input:
        st.info("Type a symbol above to continue (e.g. DOGE, ADA, XRP).")
        st.stop()

    symbol = custom_input.strip().upper().replace(" ", "")
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"
    asset_label = symbol

    try:
        _test_df = fetch_data(symbol, limit=5)
        if len(_test_df) == 0:
            st.error(f"'{symbol}' returned no data. Check the symbol is correct (e.g. DOGE, not DOGECOIN).")
            st.stop()
    except Exception as e:
        st.error(f"Couldn't find '{symbol}' on Binance. Check the spelling -- e.g. try 'DOGE' or 'ADA'. "
                  f"(Error: {e})")
        st.stop()
else:
    symbol = ASSET_OPTIONS[asset_label]

if symbol in ["SOLUSDT", "BNBUSDT"]:
    st.warning(f"Known limitation: the default trailing-stop MA crossover has tested "
               f"noticeably worse on {asset_label} historically due to its higher "
               f"volatility. Consider trying a different strategy/risk combo below, "
               f"or treat recommendations here with extra caution.")

scol1, scol2 = st.columns(2)
strategy_choice = scol1.selectbox(
    "Core strategy:", list(STRATEGY_FUNCS.keys()), key=f"strategy_{symbol}"
)
risk_choice = scol2.selectbox(
    "Risk style:", list(RISK_STYLES.keys()), index=2, key=f"risk_{symbol}"
)
strategy_func = STRATEGY_FUNCS[strategy_choice]
risk_kwargs = RISK_STYLES[risk_choice]

mode = st.radio(
    "Backtest window:", ["By number of days", "By number of trades"],
    horizontal=True, key=f"mode_{symbol}"
)

if mode == "By number of days":
    lookback_days = st.slider(
        "Number of days to analyze/backtest:", min_value=60, max_value=1000, value=200, step=10,
        key=f"lookback_{symbol}"
    )
    with st.spinner(f"Fetching live data for {symbol}..."):
        df = fetch_data(symbol, limit=lookback_days)
        df = prep_data(df)
        recommendation, reason, latest, signal_df = get_recommendation(df, strategy_func)
    window_label = f"last {lookback_days} days"
else:
    target_trades = st.number_input(
        "Target number of trades to test:", min_value=5, max_value=500, value=20, step=5,
        key=f"target_trades_{symbol}",
        help="The app will keep pulling further back in history until this many "
             "BUY/SELL trades have occurred for the selected strategy."
    )
    with st.spinner(f"Searching history for {target_trades} trades... this may take a moment"):
        signal_df, achieved_trades, days_used = find_data_for_trade_target(
            symbol, strategy_func, target_trades
        )
        latest = signal_df.iloc[-1]
        recommendation = latest["signal"]
        reason = reason_for_signal(recommendation)
        df = signal_df

    if achieved_trades < target_trades:
        st.info(f"Only found {achieved_trades} trades in {days_used} days of available "
                f"history (couldn't reach {target_trades} -- this asset may not have that "
                f"much history, or this strategy trades rarely).")
    else:
        st.caption(f"Found {achieved_trades} trades within {days_used} days of history.")
    window_label = f"{achieved_trades} trades ({days_used} days of history)"

st.markdown(f"## {badge(recommendation, recommendation)}", unsafe_allow_html=True)
st.write(reason)
st.caption(f"Using: **{strategy_choice}** with **{risk_choice}**")

col1, col2, col3 = st.columns(3)
col1.metric("Price", f"${latest['close']:.2f}")
col2.metric("MA20", f"${latest['MA_20']:.2f}")
col3.metric("MA50", f"${latest['MA_50']:.2f}")

st.markdown(f"**Regime:** {badge(latest['regime'], latest['regime'])}  |  **RSI:** {latest['RSI']:.1f}",
            unsafe_allow_html=True)
st.caption(f"Based on most recent closed candle: {latest['timestamp'].date()}")

if recommendation == "HOLD" and latest["regime"] == "CHOPPY":
    st.caption("Context: markets are choppy about 80% of the time historically -- "
               "many strategies are designed to sit out these periods rather than "
               "guess, which may be intentional rather than a malfunction.")

st.plotly_chart(make_candlestick_chart(df.tail(300), title=f"{asset_label} - Price with MA20/MA50"),
                use_container_width=True)
st.caption("Chart shows up to the last 300 candles for readability. "
           "The backtest below uses the full window you selected above.")

st.markdown(f"### Track record ({window_label})")
st.caption(f"How **{strategy_choice}** with **{risk_choice}** would have performed "
           f"historically on this asset -- so you can judge the recommendation with "
           f"real context, not just trust it blindly.")

track_results = run_track_record(signal_df, risk_kwargs)
tcol1, tcol2, tcol3 = st.columns(3)
tcol1.metric("Strategy return", f"{track_results['strategy_return_pct']:.2f}%")
tcol2.metric("Buy & hold return", f"{track_results['buy_hold_return_pct']:.2f}%")
tcol3.metric("Number of trades", track_results['num_trades'])

if track_results['strategy_return_pct'] > track_results['buy_hold_return_pct']:
    st.success("This combo beat buy-and-hold over this period.")
else:
    st.warning("This combo underperformed buy-and-hold over this period. "
               "Try a different strategy/risk combo above to compare.")

st.markdown("### Recent signal history")
st.caption(f"The actual BUY/SELL signals **{strategy_choice}** generated for this asset recently.")
history = get_signal_history(signal_df, n=10)
if len(history) > 0:
    st.dataframe(history, use_container_width=True, hide_index=True)
else:
    st.write("No BUY/SELL signals in the recent history window.")

st.markdown("---")
st.caption("Pick a strategy, risk style, and backtest window above for each asset -- "
           "your choices are remembered per asset as you switch between them. "
           "Past performance does not guarantee future results.")