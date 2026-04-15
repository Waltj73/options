import streamlit as st
import pandas as pd
import time
from squeeze import scan_ticker

st.set_page_config(page_title="EMA Radar v1", layout="wide")

SECTORS = {
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Growth/Energy": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "XOM", "CVX", "SLB", "SHOP", "PAAS"],
    "Defensives": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "LLY", "UNH", "ABBV", "AMGN"]
}

st.title("📡 Institutional Trend Radar")
st.write("Checking if Price is **ABOVE** or **BELOW** the 21 EMA (Daily & 4H).")

if st.button("🚀 Start Trend Scan"):
    all_results = []
    all_tickers = [t for sub in SECTORS.values() for t in sub]
    bar = st.progress(0)
    status = st.empty()
    
    for i, t in enumerate(all_tickers):
        status.text(f"Checking {t}...")
        res = scan_ticker(t)
        if res:
            all_results.append(res)
        bar.progress((i + 1) / len(all_tickers))
        time.sleep(0.05) # Prevent API Lockout
        
    status.text("Scan Complete!")
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Show High-Probability Alignment (Both D and 4H same direction)
        st.subheader("🎯 Dual-Timeframe Alignment")
        aligned = df[df['D_Trend'] == df['4H_Trend']]
        st.table(aligned.sort_values(by="D_Trend"))
        
        # Show All Results for Manual Review
        st.subheader("📋 Full Watchlist Review")
        st.dataframe(df, use_container_width=True)
