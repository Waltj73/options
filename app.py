import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Universal Strat Sniper", layout="wide")

# --- ORGANIZED SECTOR LIST ---
SECTORS = {
    "Market Pillars & Metals": ["SPY", "QQQ", "GLD", "SLV", "PAAS"],
    "Technology": ["MSFT", "AAPL", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "QCOM", "INTU"],
    "Financials": ["JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "BLK", "SPGI"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "AMGN", "ISRG", "PFE", "GILD"],
    "Consumer Disc": ["AMZN", "TSLA", "HD", "MCD", "NKE", "BKNG", "LOW", "SBUX", "TJX", "CMG"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "HES", "HAL", "PSX"],
    "Industrials": ["GE", "CAT", "RTX", "HON", "UNP", "LMT", "UPS", "BA", "DE", "GEHC"],
    "Communication": ["META", "GOOGL", "NFLX", "DIS", "TMUS", "VZ", "T", "CHTR", "CMCSA", "EA"]
}

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def scan_trap(ticker, sector):
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
        
        # Monthly State
        m_curr_low = float(m['Low'].iloc[-1])
        is_m_2d = m_curr_low < m_prev_low
        
        # Continuity Directions
        m_dir = "UP" if curr_price > m_open else "DOWN"
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"

        # FTC & Trap Logic
        is_ftc_up = (m_dir == "UP" and w_dir == "UP" and d_dir == "UP")
        ftc_signal = "✅" if is_ftc_up else "❌"
        is_trap = is_m_2d and w_dir == "UP" and d_dir == "UP"

        # Room to Run (%)
        distance_to_target = m_prev_high - curr_price
        pct_to_target = (distance_to_target / curr_price) * 100

        setup = "Trend"
        if is_trap and m_dir == "UP":
            setup = "🔥 FAILED 2-DOWN"
        elif is_trap:
            setup = "⚠️ POTENTIAL TRAP"

        return {
            "Sector": sector,
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
st.title("🎯 Universal Strat Sniper")
st.write("Cross-Sector Analysis: Metals, Indices, and Market Leaders.")

if st.button("🚀 Run Sector-Wide Scan"):
    results = []
    total_tickers = sum(len(ticks) for ticks in SECTORS.values())
    bar = st.progress(0)
    status = st.empty()
    
    count = 0
    for sector, tickers in SECTORS.items():
        for t in tickers:
            status.text(f"Scanning {sector}: {t}...")
            res = scan_trap(t, sector)
            if res: results.append(res)
            count += 1
            bar.progress(count / total_tickers)
            if count % 15 == 0: time.sleep(0.1)
    
    status.empty()
    
    if results:
        df = pd.DataFrame(results)
        
        # High Priority Section
        st.write("### 💎 A+ Sector Setups (FTC ✅ + Failed 2D Monthly 🔥)")
        aplus = df[(df['FTC'] == "✅") & (df['Setup'] == "🔥 FAILED 2-DOWN")]
        if not aplus.empty:
            st.table(aplus.sort_values(by="Room to Run (%)", ascending=False))
        else:
            st.info("No A+ setups currently meet all criteria across sectors.")

        # Full Sector Breakdown
        st.write("### 📊 Full Sector Results")
        for sector in SECTORS.keys():
            with st.expander(f"View {sector}", expanded=True):
                sector_df = df[df['Sector'] == sector]
                st.table(sector_df.sort_values(by="FTC", ascending=False))
    else:
        st.error("No data retrieved. Please check your connection.")
