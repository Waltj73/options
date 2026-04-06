import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="The Strat Scanner", layout="wide")

# --- 1. THE STRAT LOGIC ---
def get_strat_scenario(df):
    if len(df) < 2: return "0", "Unknown"
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Identify Scenario
    if curr['High'] <= prev['High'] and curr['Low'] >= prev['Low']:
        return "1", "Inside (Consolidation)"
    elif curr['High'] > prev['High'] and curr['Low'] < prev['Low']:
        return "3", "Outside (Broadening)"
    elif curr['High'] > prev['High']:
        return "2U", "Up (Bullish)"
    elif curr['Low'] < prev['Low']:
        return "2D", "Down (Bearish)"
    return "2", "Directional"

def get_strat_data(ticker):
    try:
        # Fetch Month, Week, Day
        m_df = yf.download(ticker, period="3mo", interval="1mo", progress=False)
        w_df = yf.download(ticker, period="3mo", interval="1wk", progress=False)
        d_df = yf.download(ticker, period="1mo", interval="1d", progress=False)

        if m_df.empty or w_df.empty or d_df.empty: return None

        # Determine Continuity (Is Price > Open?)
        m_dir = "UP" if m_df['Close'].iloc[-1] > m_df['Open'].iloc[-1] else "DOWN"
        w_dir = "UP" if w_df['Close'].iloc[-1] > w_df['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if d_df['Close'].iloc[-1] > d_df['Open'].iloc[-1] else "DOWN"
        
        ftfc = "✅ FULL UP" if (m_dir == "UP" and w_dir == "UP" and d_dir == "UP") else \
               "🛑 FULL DOWN" if (m_dir == "DOWN" and w_dir == "DOWN" and d_dir == "DOWN") else "Partial"

        scenario, desc = get_strat_scenario(d_df)

        return {
            "Ticker": ticker,
            "Price": round(float(d_df['Close'].iloc[-1]), 2),
            "Scenario": scenario,
            "Continuity": ftfc,
            "M/W/D": f"{m_dir}/{w_dir}/{d_dir}"
        }
    except: return None

# --- 2. UI ---
st.title("🎯 The Strat: Continuity Scanner")
st.caption("Scans for Scenarios (1, 2, 3) and Full Timeframe Continuity (FTFC)")

TICKERS = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "META", "AMZN", "PLTR", "PYPL", "MARA", "COIN", "SOFI"]

if st.button("🚀 Run Strat Scan"):
    results = []
    bar = st.progress(0)
    for i, t in enumerate(TICKERS):
        data = get_strat_data(t)
        if data: results.append(data)
        bar.progress((i+1)/len(TICKERS))

    if results:
        df = pd.DataFrame(results)
        
        # Color coding for The Strat
        def highlight_strat(row):
            if "FULL UP" in row.Continuity: return ['background-color: #064e3b; color: white'] * len(row)
            if "FULL DOWN" in row.Continuity: return ['background-color: #7f1d1d; color: white'] * len(row)
            if row.Scenario == "1": return ['background-color: #3b82f6; color: white'] * len(row) # Blue for Inside Bars
            return [''] * len(row)

        st.table(df.style.apply(highlight_strat, axis=1))
    else:
        st.error("No data found. Check your ticker list.")
