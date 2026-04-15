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

t1, t2, t3 = st.tabs(["🎯 Strat Sniper", "🌊 Sector Flow", "💥 Dual Squeeze"])

with t1:
    st.title("🎯 Strat Sniper")
    if st.button("🚀 Run Strat Scan"):
        results = []
        all_t = [t for sub in SECTORS.values() for t in sub]
        bar = st.progress(0)
        for i, t in enumerate(all_t):
            try:
                d = flatten(yf.download(t, period="3mo", interval="1d", progress=False))
                m = flatten(yf.download(t, period="6mo", interval="1mo", progress=False))
                if not d.empty and not m.empty:
                    curr = float(d['Close'].iloc[-1])
                    m_up = curr > float(m['Open'].iloc[-1])
                    results.append({"Ticker": t, "Price": round(curr, 2), "M_Trend": "UP" if m_up else "DN"})
            except: pass
            bar.progress((i+1)/len(all_t))
        st.table(pd.DataFrame(results))

with t2:
    st.title("🌊 Sector Flow")
    if st.button("🔍 Run Rotation Scan"):
        etfs = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLI", "XLC", "XLP", "XLB", "XLRE", "XLU", "SPY"]
        data = flatten(yf.download(etfs, period="6mo", progress=False)['Close'])
        rs = data.div(data['SPY'], axis=0).pct_change(21).iloc[-1] * 100
        st.table(pd.DataFrame(rs).rename(columns={0: "1M RS Flow %"}))

with t3:
    st.title("💥 Dual Squeeze Sniper")
    if st.button("🔍 Execute Scan"):
        results = []
        all_t = [t for sub in SECTORS.values() for t in sub]
        bar = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(all_t):
            status.text(f"Scanning: {t}...")
            res = calculate_dual_squeeze(t)
            if res:
                trig = "🚀 TRIGGER" if res['d_sq'] and not res['h4_sq'] else "⏳ COIL" if res['d_sq'] and res['h4_sq'] else "🟢 FIRED"
                results.append({"Ticker": t, "Trigger": trig, "Dir": res['dir'], "1D Sq": res['d_sq'], "4H Sq": res['h4_sq'], "Mom": round(res['d_mom'], 2)})
            bar.progress((i+1)/len(all_t))
            time.sleep(0.05)
        
        status.text("Scan Complete!")
        if results:
            df = pd.DataFrame(results)
            st.subheader("🔥 High Conviction (1D Squeeze + Trend)")
            st.table(df[(df['1D Sq'] == True) & (df['Dir'] != "Neutral")])
            st.dataframe(df)
