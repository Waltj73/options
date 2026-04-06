import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Nasdaq Squeeze Pro", layout="wide")

# DATASETS (Updated for 2026 Market Leaders)
MARKET_CAP_50 = [
    "NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "TSM", "AVGO", "META", "TSLA", "WMT",
    "LLY", "JPM", "XOM", "JNJ", "V", "ASML", "COST", "MA", "ORCL", "NFLX",
    "MU", "CVX", "ABBV", "AMD", "BAC", "PLTR", "CAT", "PG", "KO", "HD",
    "AZN", "CSCO", "MRK", "NVS", "INTC", "UNH", "WFC", "PM", "GEV", "LIN",
    "IBM", "RY", "TMUS", "MCD", "PEP", "VZ", "ADBE", "QCOM", "TXN", "AMGN"
]

VOLUME_LEADERS_50 = [
    "NVDA", "TSLA", "PLTR", "AMD", "INTC", "MARA", "SOFI", "RIOT", "COIN", "AAPL",
    "AMZN", "MSFT", "GOOGL", "META", "BABA", "NIO", "LCID", "F", "BAC", "T",
    "MU", "SQ", "SHOP", "RKLB", "HOOD", "AFRM", "UPST", "DKNG", "OPEN", "PLUG",
    "U", "AI", "CLSK", "WULF", "GME", "AMC", "PYPL", "SNAP", "NKE", "VALE",
    "PFE", "XOM", "CCL", "AAL", "ABNB", "DASH", "PATH", "RIVN", "SMCI", "MSTR"
]

# --- 2. LOGIC ENGINE ---
def get_squeeze_data(ticker):
    try:
        # 6-month lookback is ideal for 21 EMA and Squeeze stability
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        h4_data = yf.download(ticker, period="1mo", interval="1h", progress=False) 
        
        if data.empty or h4_data.empty: return None

        # Daily Indicators
        sqz = data.ta.squeeze(lazy_limit=True)
        ema21 = ta.ema(data['Close'], length=21)
        
        # Calculate Consecutive Red Dots
        sqz_series = sqz['SQZ_ON'].iloc[::-1]
        dot_count = 0
        for val in sqz_series:
            if val == 1: dot_count += 1
            else: break
            
        last_d = data.iloc[-1]
        last_sqz = sqz.iloc[-1]
        
        # 4-Hour Squeeze (Simulated via 1h data)
        h4_sqz = h4_data.ta.squeeze(lazy_limit=True).iloc[-1]

        return {
            "Ticker": ticker,
            "Price": round(float(last_d['Close']), 2),
            "Trend": "Bullish" if last_d['Close'] > ema21.iloc[-1] else "Bearish",
            "Daily_Sqz": bool(last_sqz['SQZ_ON'] == 1),
            "Dot_Count": dot_count,
            "4H_Sqz": bool(h4_sqz['SQZ_ON'] == 1),
            "Fired": bool(sqz.iloc[-2]['SQZ_ON'] == 1 and last_sqz['SQZ_ON'] == 0),
            "Hist": round(float(last_sqz['SQZ_INC']), 3)
        }
    except:
        return None

# --- 3. MAIN UI ---
st.title("⚡ Nasdaq Dual-Mode Squeeze Dash")
st.sidebar.header("Scanner Controls")

# THE TOGGLE
scan_mode = st.sidebar.radio("Select Scan Universe", ["Top 50 Market Cap", "Top 50 Volume"])
selected_list = MARKET_CAP_50 if scan_mode == "Top 50 Market Cap" else VOLUME_LEADERS_50

if st.sidebar.button("🚀 Run Active Scan"):
    results = []
    bar = st.progress(0)
    
    for i, ticker in enumerate(selected_list):
        status = get_squeeze_data(ticker)
        if status:
            # Show if Squeezing or Just Fired
            if status['Daily_Sqz'] or status['Fired']:
                setup = "Building"
                if status['Fired'] and status['Trend'] == "Bullish": setup = "🚀 FIRE (LONG)"
                elif status['Daily_Sqz'] and status['4H_Sqz']: setup = "⭐ STACKED"
                elif status['Daily_Sqz']: setup = f"⏳ {status['Dot_Count']} Dots"
                
                results.append({
                    "Ticker": status['Ticker'],
                    "Price": status['Price'],
                    "Setup": setup,
                    "Trend": "✅" if status['Trend'] == "Bullish" else "❌",
                    "Dots": status['Dot_Count'],
                    "4H Sqz": "RED" if status['4H_Sqz'] else "OFF",
                    "Momentum": status['Hist']
                })
        bar.progress((i + 1) / len(selected_list))

    if results:
        df = pd.DataFrame(results).sort_values(by="Dots", ascending=False)
        
        def highlight_rows(row):
            if "⭐" in str(row.Setup): return ['background-color: #064e3b; color: white'] * len(row)
            if "🚀" in str(row.Setup): return ['background-color: #1e3a8a; color: white'] * len(row)
            return [''] * len(row)

        st.subheader(f"Results: {scan_mode}")
        st.dataframe(df.style.apply(highlight_rows, axis=1), use_container_width=True)
    else:
        st.info(f"No active squeezes in {scan_mode} right now.")
else:
    st.info(f"Pick a mode and click **Run Active Scan**.")
