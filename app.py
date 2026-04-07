import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Strat Grade Master", layout="wide")

SECTORS = {
    "Market Pillars & Metals": ["SPY", "QQQ", "GLD", "SLV", "PAAS"],
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Consumer/Growth": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "SBUX", "ABNB", "SHOP", "DKNG", "MARA"],
    "Energy & Materials": ["XOM", "CVX", "SLB", "COP", "MPC", "LIN", "APD", "FCX", "NEM", "VMC"],
    "Industrials": ["GE", "CAT", "RTX", "HON", "UNP", "LMT", "UPS", "BA", "DE", "GEHC"],
    "Defensives (Staples/Utils)": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "SO", "DUK", "CEG", "EXC"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "AMGN", "ISRG", "PFE", "GILD"]
}

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def get_grade(m_dir, w_dir, d_dir, is_m_2d):
    # A+ Logic
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP" and is_m_2d:
        return "A+", "🔥 Failed 2D Monthly - Sniper Entry"
    # A Logic
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP":
        return "A", "✅ Full Continuity - Ride the Trend"
    # B Logic
    if w_dir == "UP" and d_dir == "UP" and m_dir == "DOWN":
        return "B", "⚠️ Potential Trap - Watching M-Open"
    # D Logic
    if m_dir == "DOWN" and w_dir == "DOWN" and d_dir == "DOWN":
        return "D", "🩸 Full Bearish - Avoid Longs"
    # C Logic
    return "C", "🔄 Mixed - Conflict/Consolidation"

def scan_strat(ticker, sector):
    try:
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True))
        w = flatten_df(yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True))
        
        if m.empty or w.empty or d.empty: return None

        curr_price = float(d['Close'].iloc[-1])
        m_open = float(m['Open'].iloc[-1])
        m_prev_low = float(m['Low'].iloc[-2])
        m_prev_high = float(m['High'].iloc[-2])
        
        is_m_2d = float(m['Low'].iloc[-1]) < m_prev_low
        m_dir = "UP" if curr_price > m_open else "DOWN"
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"

        grade, summary = get_grade(m_dir, w_dir, d_dir, is_m_2d)
        
        room = ((m_prev_high - curr_price) / curr_price) * 100

        return {
            "Grade": grade,
            "Ticker": ticker,
            "FTC": "✅" if (m_dir == "UP" and w_dir == "UP" and d_dir == "UP") else "❌",
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}",
            "Summary": summary,
            "Room (%)": round(room, 2),
            "Sector": sector
        }
    except: return None

# --- UI ---
st.title("🎯 The Strat: Grade Master")

if st.button("🚀 Run Full Graded Scan"):
    results = []
    bar = st.progress(0)
    
    total = sum(len(v) for v in SECTORS.values())
    count = 0
    for s, tickers in SECTORS.items():
        for t in tickers:
            res = scan_strat(t, s)
            if res: results.append(res)
            count += 1
            bar.progress(count/total)
    
    if results:
        df = pd.DataFrame(results)
        
        # Display A+ and A separately as the "Hot List"
        hot_list = df[df['Grade'].isin(['A+', 'A'])]
        st.subheader("🔥 Top Tier Opportunities (A+ & A)")
        st.table(hot_list.sort_values(by="Grade"))

        # Expandable tiers for everything else
        with st.expander("📝 View Tier B (The Hooks)", expanded=False):
            st.table(df[df['Grade'] == "B"])
        
        with st.expander("🔄 View Tier C (The Battles)", expanded=False):
            st.table(df[df['Grade'] == "C"])
            
        with st.expander("🩸 View Tier D (The Bears)", expanded=False):
            st.table(df[df['Grade'] == "D"])
