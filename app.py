import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Strat Trap Sniper v3", layout="wide")

# --- THE NASDAQ-100 LIST ---
NDX_100 = [
    "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX", 
    "AMD", "ADBE", "CRM", "QCOM", "TXN", "MU", "INTC", "AMAT", "LRCX", "ADI", 
    "PANW", "SNPS", "CDNS", "KLAC", "MAR", "PYPL", "ORLY", "MNST", "ADSK", "ANSS", 
    "MARA", "PLTR", "SOFI", "RIOT", "COIN", "HOOD", "AFRM", "UPST", "RKLB", "NIO",
    "SQ", "SHOP", "RBLX", "TSM", "DKNG", "PATH", "U", "AI", "GME", "AMC"
]

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def scan_trap(ticker):
    try:
        # Fetching Monthly, Weekly, Daily
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True))
        w = flatten_df(yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True))
        
        if m.empty or w.empty or d.empty: return None

        curr_price = float(d['Close'].iloc[-1])
        m_open = float(m['Open'].iloc[-1])
        m_prev_low = float(m['Low'].iloc[-2])
        m_prev_high = float(m['High'].iloc[-2])
        
        # 1. Monthly State (Did it go 2-Down?)
        m_curr_low = float(m['Low'].iloc[-1])
        is_m_2d = m_curr_low < m_prev_low
        
        # 2. Continuity Directions
        m_dir = "UP" if curr_price > m_open else "DOWN"
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"

        # 3. FTC Check (The Visual Signal)
        is_ftc_up = (m_dir == "UP" and w_dir == "UP" and d_dir == "UP")
        ftc_signal = "✅" if is_ftc_up else "❌"

        # 4. Trap Logic: Failed 2-Down
        is_trap = is_m_2d and w_dir == "UP" and d_dir == "UP"

        # 5. Room to Run (%)
        distance_to_target = m_prev_high - curr_price
        pct_to_target = (distance_to_target / curr_price) * 100

        setup = "Trend"
        if is_trap and m_dir == "UP":
            setup = "🔥 FAILED 2-DOWN"
        elif is_trap:
            setup = "⚠️ POTENTIAL TRAP"

        return {
            "FTC": ftc_signal,
            "Ticker": ticker,
            "Price": round(curr_price, 2),
            "Setup": setup,
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}",
            "Target (PMH)": round(m_prev_high, 2),
            "Room to Run (%)": round(pct_to_target, 2)
        }
    except: return None

# --- UI ---
st.title("🎯 Strat Trap Sniper v3")
st.write("Targeting Monthly 'Failed 2-Downs' with Full Timeframe Continuity (FTC) Checkmarks.")

if st.button("🚀 Run Full Advanced Scan"):
    results = []
    bar = st.progress(0)
    status = st.empty()
    
    for i, t in enumerate(NDX_100):
        status.text(f"Analyzing {t}...")
        res = scan_trap(t)
        if res: results.append(res)
        bar.progress((i+1)/len(NDX_100))
    
    status.empty()
    
    if results:
        df = pd.DataFrame(results)
        
        # Logic: Filter for "A+" setups (FTC is UP AND it's a Failed 2-Down)
        aplus_setups = df[(df['FTC'] == "✅") & (df['Setup'] == "🔥 FAILED 2-DOWN")].sort_values(by="Room to Run (%)", ascending=False)
        
        st.write("### 💎 A+ Setups (FTC ✅ + Failed 2D Monthly 🔥)")
        if not aplus_setups.empty:
            st.table(aplus_setups)
        else:
            st.info("No A+ setups found where FTC is currently green on a Failed 2-Down Monthly.")
            
        st.write("### 📊 Market Context (All Scanned Tickers)")
        # Make the full list searchable
        st.dataframe(df.sort_values(by="FTC", ascending=False))
    else:
        st.error("No data retrieved. Verify your internet connection and ticker list.")
