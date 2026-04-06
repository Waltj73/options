import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. SETTINGS & CONFIG ---
st.set_page_config(page_title="Ultimate Squeeze Scanner", layout="wide")

# --- 2. HELPERS: DATA FETCHING & LOGIC ---
@st.cache_data(ttl=3600) # Caches ticker lists for 1 hour
def get_index_tickers(index_name):
    try:
        if index_name == "S&P 500":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            return pd.read_html(url)[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        elif index_name == "Nasdaq 100":
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            return pd.read_html(url)[4]['Ticker'].tolist()
    except Exception:
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMD"] # Fallback
    return []

def get_squeeze_status(ticker, interval):
    try:
        # Download data (2y for Daily, 60d for Intraday to keep it fast)
        period = "2y" if "d" in interval else "60d"
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        
        if data.empty or len(data) < 30:
            return None

        # TTM Squeeze Calculation
        # Returns: SQZ_ON (Red Dot), SQZ_OFF (Green Dot), SQZ_INC (Histogram)
        sqz = data.ta.squeeze(lazy_limit=True)
        
        # Trend Filter (21 EMA)
        ema21 = ta.ema(data['Close'], length=21)
        
        df = pd.concat([data['Close'], sqz, ema21], axis=1)
        df.columns = ['Close', 'SQZ_ON', 'SQZ_OFF', 'SQZ_NO', 'SQZ_INC', 'SQZ_DEC', 'EMA21']
        
        last = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "in_squeeze": bool(last['SQZ_ON'] == 1),
            "fired_long": bool(prev['SQZ_ON'] == 1 and last['SQZ_ON'] == 0 and last['SQZ_INC'] > 0),
            "bullish": bool(last['Close'] > last['EMA21']),
            "hist": last['SQZ_INC']
        }
    except:
        return None

# --- 3. SIDEBAR UI ---
st.sidebar.title("Configuration")
mode = st.sidebar.radio("Ticker Source", ["Index Auto-Load", "Manual Entry"])

if mode == "Index Auto-Load":
    idx_choice = st.sidebar.selectbox("Select Index", ["S&P 500", "Nasdaq 100"])
    all_tickers = get_index_tickers(idx_choice)
    tickers = st.sidebar.multiselect("Select Tickers to Scan", all_tickers, default=all_tickers[:20])
    st.sidebar.info(f"Scanning {len(tickers)} symbols.")
else:
    manual_input = st.sidebar.text_area("Enter Tickers (Comma Separated)", "AAPL, TSLA, NVDA, COIN, BTC-USD")
    tickers = [t.strip().upper() for t in manual_input.split(",") if t.strip()]

run_button = st.sidebar.button("🚀 Start Scan")

# --- 4. MAIN DASHBOARD ---
st.title("📈 Pro-Squeeze Swing Dashboard")
st.markdown("""
This system identifies **Energy Compression** (Squeezes) aligning across multiple timeframes.
- **Stacked**: Squeeze active on both Daily & 4-Hour charts.
- **Trend**: Only highlights setups where Price is above the 21 EMA.
""")

if run_button:
    results = []
    bar = st.progress(0)
    
    for i, symbol in enumerate(tickers):
        d_data = get_squeeze_status(symbol, "1d")
        h4_data = get_squeeze_status(symbol, "4h")
        
        if d_data and h4_data:
            # Logic Synthesis
            is_stacked = d_data['in_squeeze'] and h4_data['in_squeeze']
            trend_label = "✅ Bullish" if d_data['bullish'] else "❌ Bearish"
            
            setup_label = "Scanning..."
            if d_data['bullish']:
                if is_stacked: setup_label = "⭐ STACKED SQUEEZE"
                elif d_data['fired_long']: setup_label = "🚀 DAILY FIRE"
                elif h4_data['fired_long']: setup_label = "🔥 4H FIRE"
                elif d_data['in_squeeze']: setup_label = "⏳ Daily Building"
                else: setup_label = "Searching..."
            
            # We only want to see actionable setups or active squeezes
            if setup_label != "Searching...":
                results.append({
                    "Ticker": symbol,
                    "Setup Type": setup_label,
                    "Daily Trend": trend_label,
                    "Daily Sqz": "RED" if d_data['in_squeeze'] else "OFF",
                    "4H Sqz": "RED" if h4_data['in_squeeze'] else "OFF",
                    "Momentum": round(d_data['hist'], 3)
                })
        
        bar.progress((i + 1) / len(tickers))

    # --- 5. RESULTS DISPLAY ---
    if results:
        final_df = pd.DataFrame(results)
        
        # Color coding logic
        def color_map(val):
            if "⭐" in str(val): return 'background-color: #004d00; color: white' # Emerald
            if "🚀" in str(val) or "🔥" in str(val): return 'background-color: #003366; color: white' # Navy
            return ''

        st.subheader(f"Found {len(results)} Potential Setups")
        st.dataframe(final_df.style.applymap(color_map, subset=['Setup Type']), use_container_width=True)
        
        # Display actionable metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Stacked Squeezes", len(final_df[final_df['Setup Type'].str.contains("⭐")]))
        c2.metric("New Fires", len(final_df[final_df['Setup Type'].str.contains("🚀|🔥")]))
        c3.metric("Trend Alignment", f"{int((len(final_df)/len(tickers))*100)}%")
    else:
        st.warning("No active Squeezes or Fires found for these tickers.")
else:
    st.info("Configure your tickers in the sidebar and hit **Start Scan** to begin.")

# --- FOOTER ---
st.markdown("---")
st.caption("v1.0 | Integrated TTM Squeeze + Trend Filter Dashboard")
