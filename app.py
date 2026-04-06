import streamlit as st
import yfinance as yf
import pandas as pd

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="Squeeze Pro Stable", layout="wide")

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

# ---------------- CACHE ---------------- #
@st.cache_data(ttl=1800)
def get_data(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df = df.dropna()
        return df
    except:
        return None

# ---------------- EMA ---------------- #
def ema(series, length=21):
    return series.ewm(span=length, adjust=False).mean()

# ---------------- SQUEEZE (CUSTOM, NO pandas_ta) ---------------- #
def compute_squeeze(df):
    close = df['Close']
    high = df['High']
    low = df['Low']

    # Bollinger Bands
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    # Keltner Channels
    tr = (high - low)
    kc_mid = close.rolling(20).mean()
    kc_upper = kc_mid + 1.5 * tr.rolling(20).mean()
    kc_lower = kc_mid - 1.5 * tr.rolling(20).mean()

    # Squeeze ON
    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)

    # Momentum proxy
    momentum = close - close.rolling(20).mean()

    return squeeze_on, momentum

# ---------------- MARKET BIAS ---------------- #
def get_market_bias():
    spy = get_data("SPY", "6mo", "1d")
    if spy is None or len(spy) < 30:
        return "Neutral"

    close = spy['Close']
    ema21 = ema(close, 21)

    if ema21.isna().all():
        return "Neutral"

    return "Bullish" if close.iloc[-1] > ema21.iloc[-1] else "Bearish"

# ---------------- ANALYSIS ENGINE ---------------- #
def analyze_ticker(ticker):
    try:
        df = get_data(ticker, "6mo", "1d")
        h1 = get_data(ticker, "1mo", "1h")

        if df is None or h1 is None or len(df) < 50:
            return None

        # ---- FIX INDEX ---- #
        h1.index = pd.to_datetime(h1.index)
        h1 = h1.tz_localize(None)

        # ---- REAL 4H ---- #
        h4 = h1.resample('4H').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        if len(h4) < 20:
            return None

        # ---- INDICATORS ---- #
        sqz_on, momentum = compute_squeeze(df)
        h4_sqz_on, _ = compute_squeeze(h4)

        if len(sqz_on) < 2:
            return None

        close = df['Close']
        ema21 = ema(close, 21)

        last_price = close.iloc[-1]
        trend = "Bullish" if last_price > ema21.iloc[-1] else "Bearish"

        # ---- DOT COUNT ---- #
        dot_count = 0
        for val in sqz_on[::-1]:
            if val:
                dot_count += 1
            else:
                break

        daily_sqz = bool(sqz_on.iloc[-1])
        fired = bool(sqz_on.iloc[-2] and not sqz_on.iloc[-1])

        mom = momentum.iloc[-1]
        prev_mom = momentum.iloc[-2]

        momentum_state = "Rising" if mom > prev_mom else "Falling"
        direction = "Bullish" if mom > 0 else "Bearish"

        h4_state = bool(h4_sqz_on.iloc[-1])

        # ---- SCORING ---- #
        score = 0
        if daily_sqz: score += 2
        if h4_state: score += 2
        if fired and direction == "Bullish": score += 3
        if momentum_state == "Rising": score += 1
        if dot_count >= 5: score += 1
        if trend == "Bullish": score += 1

        return {
            "Ticker": ticker,
            "Price": round(float(last_price), 2),
            "Trend": trend,
            "Direction": direction,
            "Dots": dot_count,
            "Score": score
        }

    except Exception as e:
        print(f"{ticker} error: {e}")
        return None

# ---------------- UI ---------------- #
st.title("⚡ Squeeze Pro (Stable Build)")

st.sidebar.header("Controls")

mode = st.sidebar.radio("Universe", ["Market Cap", "Volume"])
tickers = MARKET_CAP_50 if mode == "Market Cap" else VOLUME_LEADERS_50

market_bias = get_market_bias()

if market_bias == "Neutral":
    st.sidebar.warning("Market Bias: Neutral")
else:
    st.sidebar.markdown(
        f"### Market Bias: {'🟢 Bullish' if market_bias == 'Bullish' else '🔴 Bearish'}"
    )

# ---------------- RUN SCAN ---------------- #
if st.sidebar.button("Run Scan"):

    results = []
    progress = st.progress(0)

    for i, t in enumerate(tickers):
        data = analyze_ticker(t)

        if data:
            if market_bias == "Bullish" and data["Direction"] == "Bearish":
                continue

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
        st.warning("No setups found.")

else:
    st.info("Click Run Scan")
