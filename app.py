import streamlit as st
import pandas as pd
from squeeze import calculate_dual_squeeze

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

# --- TICKER LIST ---
SECTORS = {
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Consumer/Energy": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "XOM", "CVX", "SLB"],
    "Defensives/Health": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "LLY", "UNH", "ABBV", "AMGN"]
}

st.title("💥 Dual-Timeframe Squeeze Sniper")

if st.button("🔍 Scan All Sectors"):
    results = []
    all_tickers = [t for sub in SECTORS.values() for t in sub]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(all_tickers):
        status_text.text(f"Scanning {t}...")
        res = calculate_dual_squeeze(t)
        if res:
            trigger = "Waiting"
            if res['d_squeeze'] and not res['h4_squeeze']:
                trigger = "🚀 TRIGGERING (4H Fired)"
            elif res['d_squeeze'] and res['h4_squeeze']:
                trigger = "⏳ COILING (Both Squeezing)"
            elif not res['d_squeeze'] and not res['h4_squeeze']:
                trigger = "🟢 FIRED (Both)"

            results.append({
                "Ticker": t,
                "Status": trigger,
                "1D Sq": "ON" if res['d_squeeze'] else "OFF",
                "4H Sq": "ON" if res['h4_squeeze'] else "OFF",
                "Direction": res['direction'],
                "1D Mom": round(res['d_momentum'], 2),
                "Price": round(res['price'], 2)
            })
        progress_bar.progress((i + 1) / len(all_tickers))

    if results:
        df = pd.DataFrame(results)
        
        # 🎯 SECTION 1: THE BEST TRADES (Daily Squeeze + Trend Match)
        st.subheader("🔥 High Conviction Squeezes (Daily Squeezing)")
        high_conviction = df[(df['1D Sq'] == "ON") & (df['Direction'] != "Neutral")]
        if not high_conviction.empty:
            st.table(high_conviction.sort_values(by="1D Mom", ascending=False))
        else:
            st.info("No active Daily squeezes with trend alignment found.")

        # 📊 SECTION 2: EVERYTHING ELSE
        st.subheader("📋 All Watchlist Results")
        st.dataframe(df, use_container_width=True)
    else:
        st.error("Scanner returned zero results. Check your internet connection or ticker list.")
