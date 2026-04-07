import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Strat Trap Sniper", layout="wide")

NDX_100 = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "META", "AMZN", "PLTR", "PYPL", "MARA", "COIN", "MSTR", "APP"] # Add more as needed

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def scan_trap(ticker):
    try:
        # Pull Monthly, Weekly, Daily
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True))
        w = flatten_df(yf.download(ticker, period="3mo", interval="1wk", progress=False, auto_adjust=True))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True))
        
        if m.empty or w.empty or d.empty: return None

        curr_price = d['Close'].iloc[-1]
        
        # Monthly Logic
        m_curr = m.iloc[-1]
        m_prev = m.iloc[-2]
        
        # Check if it IS a 2-Down Monthly
        is_m_2d = curr_price < m_prev['Low'] or m_curr['Low'] < m_prev['Low']
        
        # Continuity Check
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"
        m_dir = "UP" if curr_price > m['Open'].iloc[-1] else "DOWN"

        # The Trap Definition: Monthly is/was 2D, but Weekly/Daily are UP
        is_trap = is_m_2d and w_dir == "UP" and d_dir == "UP"

        status = "Normal"
        if is_trap and m_dir == "UP":
            status = "🔥 FAILED 2-DOWN (MTF Up)"
        elif is_trap:
            status = "⚠️ POTENTIAL TRAP (M-Open Pivot)"

        return {
            "Ticker": ticker,
            "Price": round(float(curr_price), 2),
            "Monthly State": "2-Down" if is_m_2d else "Other",
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}",
            "Target (PMH)": round(float(m_prev['High']), 2),
            "Setup": status
        }
    except: return None

# --- UI ---
st.title("🎯 Strat Trap Sniper: Monthly Failed 2-Down")
st.write("Hunting for Monthly 'Traps' where price is hooking back into Daily/Weekly Continuity.")

if st.button("🔍 Scan for Monthly Traps"):
    results = []
    bar = st.progress(0)
    for i, t in enumerate(NDX_100):
        res = scan_trap(t)
        if res: results.append(res)
        bar.progress((i+1)/len(NDX_100))
    
    if results:
        df = pd.DataFrame(results)
        traps = df[df['Setup'] != "Normal"]
        
        st.write("### 🚨 Active Monthly Reversal Setups")
        if not traps.empty:
            st.table(traps)
        else:
            st.info("No Monthly Failed 2-Down setups found right now.")
            
        st.write("### 📊 Full List")
        st.dataframe(df)
