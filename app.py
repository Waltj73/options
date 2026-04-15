import streamlit as st
import yfinance as yf
import pandas as pd
from squeeze import calculate_dual_squeeze

# --- GLOBAL CONFIG ---
st.set_page_config(page_title="Strat Sniper v6", layout="wide")

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

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- TAB 1: STRAT LOGIC ---
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
        curr = float(d['Close'].iloc[-1])
        is_m_2d = float(m['Low'].iloc[-1]) < float(m['Low'].iloc[-2])
        m_dir = "UP" if curr > float(m['Open'].iloc[-1]) else "DOWN"
        w_dir = "UP" if curr > float(w['Open'].iloc[-1]) else "DOWN"
        d_dir = "UP" if curr > float(d['Open'].iloc[-1]) else "DOWN"
        grade, summary = get_grade(m_dir, w_dir, d_dir, is_m_2d)
        room = ((float(m['High'].iloc[-2]) - curr) / curr) * 100
        return {"Grade": grade, "Ticker": ticker, "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}", 
                "Summary": summary, "Room (%)": round(room, 2), "Sector": sector}
    except: return None

# --- UI TABS ---
tab_sniper, tab_flow, tab_squeeze = st.tabs(["🎯 Strat Universal Sniper", "🌊 Sector Money Flow", "💥 Dual-Timeframe Squeeze"])

with tab_sniper:
    st.title("🎯 Strat Universal Sniper")
    if st.button("🚀 Execute Strat Scan"):
        results = []
        bar = st.progress(0)
        tickers = [(s, t) for s, ts in SECTORS.items() for t in ts]
        for i, (s, t) in enumerate(tickers):
            res = scan_strat(t, s)
            if res: results.append(res)
            bar.progress((i + 1) / len(tickers))
        if results:
            df = pd.DataFrame(results)
            st.write("## 💎 A+ SNIPER SETUPS")
            st.table(df[df['Grade'] == "A+"].sort_values(by="Room (%)", ascending=False))
            with st.expander("Show All Grades"): st.dataframe(df)

with tab_flow:
    st.title("🌊 Sector Money Flow")
    if st.button("🔍 Analyze RS Flow"):
        etfs = {"XLK": "Tech", "XLF": "Fin", "XLE": "Energy", "XLV": "Health", "XLY": "Consum", "XLI": "Indus", "XLC": "Comm", "XLP": "Staples", "XLB": "Mat", "XLRE": "RealEstate", "XLU": "Util"}
        data = flatten_df(yf.download(list(etfs.keys()) + ["SPY"], period="7mo", progress=False, auto_adjust=True)['Close'])
        rs = data[list(etfs.keys())].div(data['SPY'], axis=0)
        f1, f3 = rs.pct_change(21).iloc[-1]*100, rs.pct_change(63).iloc[-1]*100
        res = [{"Ticker": k, "Sector": v, "1M Flow": round(f1[k], 2), "3M Flow": round(f3[k], 2), "Status": "🚀 ACCEL" if f1[k]>f3[k] else "🐢 SLOW"} for k,v in etfs.items()]
        st.dataframe(pd.DataFrame(res).sort_values("1M Flow", ascending=False), use_container_width=True)

with tab_squeeze:
    st.title("💥 Dual-Timeframe Squeeze Sniper")
    st.info("High Conviction = Daily Squeeze + 4H Trigger + Price/EMA Alignment.")
    if st.button("🔍 Scan Dual Timeframes"):
        results = []
        bar = st.progress(0)
        all_tickers = [t for sublist in SECTORS.values() for t in sublist]
        for i, t in enumerate(all_tickers):
            res = calculate_dual_squeeze(t)
            if res:
                trigger = "Waiting"
                if res['d_squeeze'] and not res['h4_squeeze']: trigger = "🚀 TRIGGERING (4H Fired)"
                elif res['d_squeeze'] and res['h4_squeeze']: trigger = "⏳ COILING (Both)"
                results.append({
                    "Ticker": t, "1D Squeeze": "🔴 ON" if res['d_squeeze'] else "🟢 FIRED",
                    "4H Squeeze": "🔴 ON" if res['h4_squeeze'] else "🟢 FIRED",
                    "Trigger": trigger, "Direction": res['direction'], 
                    "1D Mom": round(res['d_momentum'], 2), "4H Mom": round(res['h4_momentum'], 2)
                })
            bar.progress((i + 1) / len(all_tickers))
        if results:
            df = pd.DataFrame(results)
            st.subheader("🎯 High Conviction Alignment")
            conviction = df[(df['Direction'] != "Neutral") & (df['1D Squeeze'] == "🔴 ON")]
            st.table(conviction.sort_values("Trigger", ascending=False))
            with st.expander("Full Market Results"): st.dataframe(df)
