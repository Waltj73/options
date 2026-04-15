import streamlit as st
import yfinance as yf
import pandas as pd
import time
from squeeze import calculate_dual_squeeze

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

SECTORS = {
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Growth/Energy": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "XOM", "CVX", "SLB", "SHOP", "PAAS"],
    "Defensives": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "LLY", "UNH", "ABBV", "AMGN"]
}

def flatten(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

# --- UI ---
t1, t2, t3 = st.tabs(["🎯 Strat Sniper", "🌊 Sector Flow", "💥 Dual Squeeze"])

with t1:
    st.title("🎯 Strat Universal Sniper")
    if st.button("🚀 Run Strat Scan"):
        results = []
        bar = st.progress(0)
        all_t = [t for sub in SECTORS.values() for t in sub]
        for i, t in enumerate(all_t):
            try:
                m = flatten(yf.download(t, period="6mo", interval="1mo", progress=False))
                w = flatten(yf.download(t, period="1mo", interval="1wk", progress=False))
                d = flatten(yf.download(t, period="1mo", interval="1d", progress=False))
                if not m.empty and not w.empty and not d.empty:
                    curr, m_o = float(d['Close'].iloc[-1]), float(m['Open'].iloc[-1])
                    m_l2 = float(m['Low'].iloc[-2])
                    is_2d = float(m['Low'].iloc[-1]) < m_l2
                    m_up, w_up, d_up = curr > m_o, curr > float(w['Open'].iloc[-1]), curr > float(d['Open'].iloc[-1])
                    
                    grade = "A+" if m_up and w_up and d_up and is_2d else "A" if m_up and w_up and d_up else "B" if w_up and d_up and not m_up else "C"
                    results.append({"Ticker": t, "Grade": grade, "M/W/D": f"{m_up}/{w_up}/{d_up}", "Price": round(curr, 2)})
            except: pass
            bar.progress((i+1)/len(all_t))
        if results: st.table(pd.DataFrame(results).sort_values("Grade"))

with t2:
    st.title("🌊 Sector Money Flow")
    if st.button("🔍 Run Rotation Scan"):
        etfs = {"XLK":"Tech","XLF":"Fin","XLE":"Energy","XLV":"Health","XLY":"Disc","XLI":"Indus","XLC":"Comm","XLP":"Staples","XLB":"Mat","XLRE":"RE","XLU":"Util"}
        data = flatten(yf.download(list(etfs.keys())+["SPY"], period="7mo", progress=False)['Close'])
        rs = data[list(etfs.keys())].div(data['SPY'], axis=0)
        f1 = rs.pct_change(21).iloc[-1]*100
        res = [{"Ticker": k, "Sector": v, "1M Flow %": round(f1[k], 2)} for k,v in etfs.items()]
        st.table(pd.DataFrame(res).sort_values("1M Flow %", ascending=False))

with t3:
    st.title("💥 Dual-Timeframe Squeeze")
    if st.button("🔍 Scan Squeezes"):
        results = []
        bar = st.progress(0)
        all_t = [t for sub in SECTORS.values() for t in sub]
        for i, t in enumerate(all_t):
            res = calculate_dual_squeeze(t)
            if res:
                trig = "🚀 TRIGGER" if res['d_sq'] and not res['h4_sq'] else "⏳ COIL" if res['d_sq'] and res['h4_sq'] else "🟢 FIRED"
                results.append({"Ticker": t, "Trigger": trig, "Dir": res['dir'], "1D Sq": res['d_sq'], "4H Sq": res['h4_sq'], "Mom": round(res['d_mom'], 2)})
            time.sleep(0.1) # Small delay to prevent API lockout
            bar.progress((i+1)/len(all_t))
        if results: 
            df = pd.DataFrame(results)
            st.subheader("🔥 High Conviction (1D Squeeze + Trend)")
            st.table(df[(df['1D Sq'] == True) & (df['Dir'] != "Neutral")])
            st.subheader("Full Watchlist")
            st.dataframe(df)
