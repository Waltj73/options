import streamlit as st
import yfinance as yf
import pandas as pd
import time
from squeeze import calculate_dual_squeeze

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

SECTORS = {
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Consumer/Growth": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "SBUX", "ABNB", "SHOP", "DKNG", "MARA"],
    "Energy & Materials": ["XOM", "CVX", "SLB", "COP", "MPC", "LIN", "APD", "FCX", "NEM", "PAAS"],
    "Industrials": ["GE", "CAT", "RTX", "HON", "UNP", "LMT", "UPS", "BA", "DE", "GEHC"],
    "Defensives": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "SO", "DUK", "CEG", "EXC"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "AMGN", "ISRG", "PFE", "GILD"]
}

def flatten(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

t1, t2, t3 = st.tabs(["🎯 Strat Sniper", "🌊 Sector Flow", "💥 Dual Squeeze"])

with t1:
    st.title("🎯 Strat Sniper (Failed 2-Down Logic)")
    if st.button("🚀 Run Full Sector Scan"):
        results = []
        all_t = [t for sub in SECTORS.values() for t in sub]
        bar = st.progress(0)
        for i, t in enumerate(all_t):
            try:
                m = flatten(yf.download(t, period="1y", interval="1mo", progress=False))
                w = flatten(yf.download(t, period="3mo", interval="1wk", progress=False))
                d = flatten(yf.download(t, period="1mo", interval="1d", progress=False))
                curr = d['Close'].iloc[-1]
                # Failed 2-Down Check: Monthly low was lower than previous, but price is back above Open
                is_m_2d = m['Low'].iloc[-1] < m['Low'].iloc[-2]
                m_up = curr > m['Open'].iloc[-1]
                w_up = curr > w['Open'].iloc[-1]
                d_up = curr > d['Open'].iloc[-1]
                
                grade = "A+" if m_up and w_up and d_up and is_2d else "A" if m_up and w_up and d_up else "C"
                results.append({"Ticker": t, "Grade": grade, "Setup": "Failed 2D" if is_m_2d else "Trend", "Price": round(curr, 2)})
            except: pass
            bar.progress((i+1)/len(all_t))
        if results: st.table(pd.DataFrame(results).sort_values("Grade"))

with t2:
    st.title("🌊 Sector Money Flow (RS)")
    if st.button("🔍 Analyze Rotation"):
        etfs = {"XLK":"Tech","XLF":"Fin","XLE":"Energy","XLV":"Health","XLY":"Disc","XLI":"Indus","XLC":"Comm","XLP":"Staples"}
        data = flatten(yf.download(list(etfs.keys())+["SPY"], period="7mo", progress=False)['Close'])
        rs = data[list(etfs.keys())].div(data['SPY'], axis=0).pct_change(21).iloc[-1]*100
        st.table(pd.DataFrame([{"Sector": etfs[k], "1M RS Flow": round(v, 2)} for k,v in rs.items()]).sort_values("1M RS Flow", ascending=False))

with t3:
    st.title("💥 Dual Squeeze Sniper")
    if st.button("🔍 Scan for Triggers"):
        results = []
        all_t = [t for sub in SECTORS.values() for t in sub]
        bar = st.progress(0)
        status = st.empty()
        for i, t in enumerate(all_t):
            status.text(f"Scanning {t}...")
            res = calculate_dual_squeeze(t)
            if res:
                trig = "🚀 TRIGGERING" if res['d_sq'] and not res['h4_sq'] else "⏳ COILING" if res['d_sq'] and res['h4_sq'] else "🟢 FIRED"
                results.append({"Ticker": t, "Status": trig, "Dir": res['dir'], "D_Sq": "ON" if res['d_sq'] else "OFF", "4H_Sq": "ON" if res['h4_sq'] else "OFF", "Mom": round(res['d_mom'], 2)})
            bar.progress((i+1)/len(all_t))
            time.sleep(0.05)
        status.text("Scan Complete!")
        if results: st.table(pd.DataFrame(results).sort_values("Status"))
