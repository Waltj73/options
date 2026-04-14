import streamlit as st
import yfinance as yf
import pandas as pd
from squeeze import calculate_ttm_squeeze  # <--- NEW IMPORT

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

# ... (Keep your flatten_df and SECTORS here) ...

# --- NEW TAB ADDITION ---
tab_sniper, tab_flow, tab_squeeze = st.tabs(["🎯 Strat Universal Sniper", "🌊 Sector Money Flow", "💥 TTM Squeeze"])

# ... (Keep your tab_sniper and tab_flow logic here) ...

with tab_squeeze:
    st.title("💥 TTM Squeeze Scanner")
    st.write("Finding symbols in low-volatility 'Squeeze' phases, ready for a momentum explosion.")

    if st.button("🔍 Scan for Squeezes"):
        results = []
        with st.spinner("Analyzing volatility bands..."):
            # Flatten SECTORS to a single list for scanning
            all_tickers = [t for sublist in SECTORS.values() for t in sublist]
            
            for t in all_tickers:
                row = calculate_ttm_squeeze(t)
                if row is not None:
                    status = "🔴 SQUEEZING" if row['squeeze_on'] else "🟢 FIRED"
                    results.append({
                        "Ticker": t,
                        "Status": status,
                        "Momentum": round(row['momentum'], 4),
                        "Direction": "Bullish" if row['momentum'] > 0 else "Bearish"
                    })
        
        if results:
            sq_df = pd.DataFrame(results)
            
            # Show active squeezes first
            st.subheader("Active Volatility Squeezes")
            active = sq_df[sq_df['Status'] == "🔴 SQUEEZING"].sort_values(by="Momentum", ascending=False)
            if not active.empty:
                st.table(active)
            else:
                st.info("No active squeezes found in the current watchlist.")

            with st.expander("View All Symbols"):
                st.dataframe(sq_df, use_container_width=True)
