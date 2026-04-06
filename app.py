import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="Squeeze Pro V2", layout="wide")

MARKET_CAP_50 = [
    "NVDA","AAPL","GOOGL","MSFT","AMZN","TSM","AVGO","META","TSLA","WMT",
    "LLY","JPM","XOM","JNJ","V","ASML","COST","MA","ORCL","NFLX",
    "MU","CVX","ABBV","AMD","BAC","PLTR","CAT","PG","KO","HD",
    "AZN","CSCO","MRK","NVS","INTC","UNH","WFC","PM","GEV","LIN",
    "IBM","RY","TMUS","MCD","PEP","VZ","ADBE","QCOM","TXN","AMGN"
]

VOLUME_LEADERS_50 = [
    "NVDA","TSLA","PLTR","AMD","INTC","MARA","SOFI","RIOT","COIN","AAPL",
    "AMZN","MSFT","GOOGL","META","BABA","NIO","LCID","F","BAC","T",
    "MU","SQ","SHOP","RKLB","HOOD","AFRM","UPST","DKNG","OPEN","PLUG",
    "U","AI","CLSK","WULF","GME","AMC","PYPL","SNAP","NKE","VALE",
    "PFE","XOM","CCL","AAL","ABNB","DASH","PATH","RIVN","SMCI","MSTR"
]

# ---------------- DATA CACHE ---------------- #
@st.cache_data(ttl=1800)
def get_data(ticker, period, interval):
    return yf.download(ticker, period=period, interval=interval, progress=False)

# ---------------- MARKET FILTER ---------------- #
def get_market_bias():
    spy = get_data("SPY", "6mo", "1d")
    ema21 = ta.ema(spy['Close'], length=21)
    return "Bullish" if spy['Close'].iloc[-1] > ema21.iloc[-1] else "Bearish"

# ---------------- CORE ENGINE ---------------- #
def analyze_ticker(ticker):
    try:
        df = get_data(ticker, "6mo", "1d")
        h1 = get_data(ticker, "1mo", "1h")

        if df.empty or h1.empty:
            return None

        # ----- REAL 4H RESAMPLE -----
        h4 = h1.resample('4H').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        # ----- INDICATORS -----
        sqz = df.ta.squeeze(lazy_limit=True)
        ema21 = ta.ema(df['Close'], length=21)

        h4_sqz = h4.ta.squeeze(lazy_limit=True)

        last = df.iloc[-1]
        last_sqz = sqz.iloc[-1]
        prev_sqz = sqz.iloc[-2]

        # ----- DOT COUNT -----
        dot_count = 0
        for val in sqz['SQZ_ON'].iloc[::-1]:
            if val == 1:
                dot_count += 1
            else:
                break

        # ----- TREND -----
        trend = "Bullish" if last['Close'] > ema21.iloc[-1] else "Bearish"

        # ----- SQUEEZE STATES -----
        daily_sqz = last_sqz['SQZ_ON'] == 1
        fired = prev_sqz['SQZ_ON'] == 1 and last_sqz['SQZ_ON'] == 0

        # ----- MOMENTUM -----
        momentum = last_sqz['SQZ_INC']
        prev_momentum = prev_sqz['SQZ_INC']

        momentum_state = "Rising" if momentum > prev_momentum else "Falling"
        direction = "Bullish" if momentum > 0 else "Bearish"

        # ----- 4H CONFIRMATION -----
        h4_state = h4_sqz.iloc[-1]['SQZ_ON'] == 1

        # ----- SCORING SYSTEM -----
        score = 0

        if daily_sqz:
            score += 2
        if h4_state:
            score += 2
        if fired and direction == "Bullish":
            score += 3
        if momentum_state == "Rising":
            score += 1
        if dot_count >= 5:
            score += 1
        if trend == "Bullish":
            score += 1

        return {
            "Ticker": ticker,
            "Price": round(float(last['Close']), 2),
            "Trend": trend,
            "Daily Sqz": daily_sqz,
            "4H Sqz": h4_state,
            "Fired": fired,
            "Direction": direction,
            "Momentum": round(momentum, 3),
            "Momentum State": momentum_state,
            "Dots": dot_count,
            "Score": score
        }

    except:
        return None

# ---------------- UI ---------------- #
st.title("⚡ Squeeze Pro V2")

st.sidebar.header("Controls")

mode = st.sidebar.radio("Universe", ["Market Cap", "Volume"])
tickers = MARKET_CAP_50 if mode == "Market Cap" else VOLUME_LEADERS_50

market_bias = get_market_bias()
st.sidebar.markdown(f"### Market Bias: {'🟢 Bullish' if market_bias == 'Bullish' else '🔴 Bearish'}")

if st.sidebar.button("Run Scan"):

    results = []
    progress = st.progress(0)

    for i, t in enumerate(tickers):
        data = analyze_ticker(t)

        if data:
            # MARKET FILTER
            if market_bias == "Bullish" and data["Direction"] == "Bearish":
                continue

            if data["Daily Sqz"] or data["Fired"]:
                results.append(data)

        progress.progress((i + 1) / len(tickers))

    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)

        def style_rows(row):
            if row["Score"] >= 6:
                return ['background-color: #064e3b; color: white'] * len(row)
            elif row["Score"] >= 4:
                return ['background-color: #1e3a8a; color: white'] * len(row)
            return [''] * len(row)

        st.subheader("Top Setups")
        st.dataframe(df.style.apply(style_rows, axis=1), use_container_width=True)

    else:
        st.warning("No valid setups found.")

else:
    st.info("Click Run Scan")
