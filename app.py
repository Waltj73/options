import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="The Strat Scanner", layout="wide")

# --- THE STRAT ENGINE ---
def get_scenario(df):
    """Determines if the current candle is a 1, 2U, 2D, or 3."""
    if len(df) < 2: return "0", "N/A"
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Inside Bar (1)
    if curr['High'] <= prev['High'] and curr['Low'] >= prev['Low']:
        return "1", "Inside (Consolidation)"
    # Outside Bar (3)
    elif curr['High'] > prev['High'] and curr['Low'] < prev['Low']:
        return "3", "Outside (Broadening)"
    # 2 Up
    elif curr['High'] > prev['High']:
        return "2U", "Up (Bullish)"
    # 2 Down
    elif curr['Low'] < prev['Low']:
        return "2D", "Down (Bearish)"
    return "2", "Directional"

def get_strat_data(ticker):
    try:
        # Download different timeframes to check Continuity
        # Note: auto_adjust=True is critical for Strat accuracy
        d_df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        w_df = yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True)
        m_df = yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True)

        if d_df.empty or w_df.empty: return None

        # Continuity: Is the current price above the OPEN of that candle?
        # This is the 'Green' vs 'Red' on the higher timeframes
        d_dir = "UP" if d_df['Close'].iloc[-1] > d_df['Open'].iloc[-1] else "DOWN"
        w_dir = "UP" if w_df['Close'].iloc[-1] > w_df['Open'].iloc[-1] else "DOWN"
        m_dir = "UP" if m_df['Close'].iloc[-1] > m_df['Open'].iloc[-1] else "DOWN"

        # Full Timeframe Continuity (FTFC)
        if d_dir == "UP" and w_dir == "UP" and m_dir == "UP":
            ftfc = "✅ FULL UP"
        elif d_dir == "DOWN" and w_dir == "DOWN" and m_dir == "DOWN":
            ftfc = "🛑 FULL DOWN"
        else:
            ftfc = "Mixed"

        scenario, desc = get_scenario(d_df)

        return {
            "Ticker": ticker,
            "Price": round(float(d_df['Close'].iloc[-1]), 2),
            "Scenario": scenario,
            "Continuity": ftfc,
            "D/W/M": f"{d_dir}/{w_dir}/{m_dir}",
            "Note": desc
        }
    except:
        return None

# --- UI ---
st.title("🎯 The Strat Continuity Scanner")
st.write("Looking for Scenario 1-2 reversals and Full Timeframe Continuity.")

# Your high-volume list
TICKERS = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "META", "AMZN", "PLTR", "PYPL", "MARA", "COIN", "SOFI", "RIOT", "HOOD"]

if st.button("🚀 Scan for Strat Setups"):
    results = []
    bar = st.progress(0)
    
    for i, t in enumerate(TICKERS):
        data = get_strat_data(t)
        if data:
            results.append(data)
        bar.progress((i+1)/len(TICKERS))

    if results:
        df = pd.DataFrame(results)
        
        # Highlight Logic for Strat
        def highlight_ftfc(val):
            if "FULL UP" in val: return 'background-color: #064e3b; color: white'
            if "FULL DOWN" in val: return 'background-color: #7f1d1d; color: white'
            return ''

        st.table(df.style.applymap(highlight_ftfc, subset=['Continuity']))
    else:
        st.error("Connection error or no data found.")
