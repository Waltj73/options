import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

# --- DATA HELPERS ---
def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- TAB 1: STRAT SNIPER LOGIC ---
SECTORS = {
    "Market Pillars & Metals": ["SPY", "QQQ", "GLD", "SLV", "PAAS"],
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Consumer/Growth": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "SBUX", "ABNB", "SHOP", "DKNG", "MARA"],
    "Energy & Materials": ["XOM", "CVX", "SLB", "COP", "MPC", "LIN", "APD", "FCX", "NEM", "VMC"],
    "Industrials": ["GE", "CAT", "RTX", "HON", "UNP", "LMT", "UPS", "BA", "DE", "GEHC"],
    "Defensives": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "SO", "DUK", "CEG", "EXC"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "AMGN", "ISRG", "PFE", "GILD"]
}

def get_grade(m_dir, w_dir, d_dir, is_m_2d):
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP" and is_m_2d:
        return "A+", "🔥 SNIPER: Failed 2D Monthly + FTC Up"
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP":
        return "A", "✅ TREND: Full Continuity Up"
    if w_dir == "UP" and d_dir == "UP" and m_dir == "DOWN":
        return "B", "⚠️ HOOK: Monthly Trap In-Progress"
    if m_dir == "DOWN" and w_dir == "DOWN" and d_dir == "DOWN":
        return "D", "🩸 BEAR: Avoid Longs"
    return "C", "🔄 BATTLE: Mixed Continuity"

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
        return {"Grade": grade, "Ticker": ticker, "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}", 
                "Summary": summary, "Room (%)": round(room, 2), "Sector": sector}
    except: return None

# --- UI TABS ---
tab_sniper, tab_flow = st.tabs(["🎯 Strat Universal Sniper", "🌊 Sector Money Flow"])

with tab_sniper:
    st.title("🎯 Strat Universal Sniper")
    st.write("Grading 80+ tickers to find the absolute best Failed 2-Down Monthly setups.")

    if st.button("🚀 Execute Full Market Scan"):
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
            st.write("## 💎 THE KILL ZONE: A+ SNIPER SETUPS")
            aplus = df[df['Grade'] == "A+"]
            if not aplus.empty:
                st.table(aplus.sort_values(by="Room (%)", ascending=False))
            else:
                st.info("No A+ setups currently live.")

            with st.expander("📈 Tier A (Clean Trends)", expanded=True):
                st.table(df[df['Grade'] == "A"].sort_values(by="Room (%)", ascending=False))
            with st.expander("⚠️ Tier B (The Potential Hooks)", expanded=False):
                st.table(df[df['Grade'] == "B"])
            with st.expander("🩸 Tier D (Full Bearish)", expanded=False):
                st.table(df[df['Grade'] == "D"])

with tab_flow:
    st.title("🌊 Sector Money Flow")
    st.write("Determining institutional flow by comparing Sector ETFs against the S&P 500 ($SPY).")
    
    if st.button("🔍 Analyze Relative Strength"):
        with st.spinner("Calculating Sector Alpha..."):
            sector_etfs = {
                "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", 
                "XLV": "Healthcare", "XLY": "Consumer Disc", "XLI": "Industrials", 
                "XLC": "Communications", "XLP": "Consumer Staples", "XLB": "Materials", 
                "XLRE": "Real Estate", "XLU": "Utilities"
            }
            tickers = list(sector_etfs.keys()) + ["SPY"]
            # Get 6 months of data
            data = yf.download(tickers, period="7mo", interval="1d", progress=False, auto_adjust=True)
            data = flatten_df(data['Close'])
            
            # Calculate RS Ratio: (Sector / SPY)
            rs_ratios = data[list(sector_etfs.keys())].div(data['SPY'], axis=0)
            
            # Calculate 1-Month (21 days) and 3-Month (63 days) momentum of the ratio
            flow_1m = (rs_ratios.pct_change(21).iloc[-1]) * 100
            flow_3m = (rs_ratios.pct_change(63).iloc[-1]) * 100
            
            flow_results = []
            for ticker, name in sector_etfs.items():
                flow_results.append({
                    "Ticker": ticker,
                    "Sector": name,
                    "1M RS Flow (%)": round(flow_1m[ticker], 2),
                    "3M RS Flow (%)": round(flow_3m[ticker], 2),
                    "Status": "🚀 ACCELERATING" if flow_1m[ticker] > flow_3m[ticker] else "🐢 SLOWING"
                })
            
            flow_df = pd.DataFrame(flow_results).sort_values(by="1M RS Flow (%)", ascending=False)
            
            st.write("### Sector Leaderboard (vs SPY)")
            st.dataframe(flow_df.style.background_gradient(cmap='RdYlGn', subset=['1M RS Flow (%)', '3M RS Flow (%)']), use_container_width=True)
            
            st.info("💡 **Strategy:** Look for A+ Sniper setups in sectors where 1M Flow is positive and 'Accelerating'.")
