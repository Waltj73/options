import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# --- STREAMLIT UI CONFIG ---
st.set_page_config(page_title="Pro-Squeeze Scanner", layout="wide")
st.title("🚀 Multi-Timeframe Squeeze Scanner")
st.markdown("""
This scanner looks for **Energy Compression** (TTM Squeeze) combined with **Trend Direction** (21 EMA).
* **Stacked Squeeze**: Active squeeze on both Daily and 4H timeframes.
* **Trend Filter**: Price must be above the 21 EMA for Bullish setups.
""")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Scanner Settings")
ticker_input = st.sidebar.text_area("Enter Tickers (comma separated)", 
                                   "AAPL, TSLA, MSFT, NVDA, AMD, GOOGL, AMZN, META, COIN, MARA, RIOT, SPY, QQQ")
tickers = [t.strip().upper() for t in ticker_input.split(",")]

# --- CORE LOGIC ---
def get_squeeze_status(ticker, interval):
    try:
        # Fetch slightly more data to ensure EMA and Squeeze stabilize
        data = yf.download(ticker, period="1y", interval=interval, progress=False)
        if data.empty or len(data) < 30: 
            return None

        # 1. TTM Squeeze via Pandas_TA
        # Returns columns: SQZ_ON (Red Dot), SQZ_OFF (Green Dot), SQZ_INC (Histogram)
        sqz = data.ta.squeeze(lazy_limit=True)
        
        # 2. Trend Filter (21 EMA)
        ema21 = ta.ema(data['Close'], length=21)
        
        df = pd.concat([data['Close'], sqz, ema21], axis=1)
        df.columns = ['Close', 'SQZ_ON', 'SQZ_OFF', 'SQZ_NO', 'SQZ_INC', 'SQZ_DEC', 'EMA21']
        
        last = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "in_squeeze": bool(last['SQZ_ON'] == 1),
            "fired_long": bool(prev['SQZ_ON'] == 1 and last['SQZ_ON'] == 0 and last['SQZ_INC'] > 0),
            "bullish": bool(last['Close'] > last['EMA21']),
            "hist": last['SQZ_INC']
        }
    except Exception as e:
        return None

# --- SCANNER EXECUTION ---
if st.sidebar.button("Run Scanner"):
    results = []
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(tickers):
        daily = get_squeeze_status(symbol, "1d")
        four_h = get_squeeze_status(symbol, "4h")
        
        if daily and four_h:
            # Determine Status
            is_stacked = daily['in_squeeze'] and four_h['in_squeeze']
            
            # Trend Check (Using Daily as the primary anchor)
            trend_status = "✅ Bullish" if daily['bullish'] else "❌ Bearish"
            
            # Labeling the "Trade Idea"
            trade_idea = "Neutral"
            if daily['bullish']:
                if is_stacked: trade_idea = "⭐ STACKED SQUEEZE"
                elif daily['fired_long']: trade_idea = "🚀 DAILY FIRE"
                elif four_h['fired_long']: trade_idea = "🔥 4H FIRE"
                elif daily['in_squeeze']: trade_idea = "⏳ Daily Squeezing"

            results.append({
                "Ticker": symbol,
                "Setup": trade_idea,
                "Trend (21 EMA)": trend_status,
                "Daily Sqz": "RED" if daily['in_squeeze'] else "OFF",
                "4H Sqz": "RED" if four_h['in_squeeze'] else "OFF",
                "Daily Hist": round(daily['hist'], 2)
            })
        
        progress_bar.progress((i + 1) / len(tickers))

    # --- DISPLAY RESULTS ---
    if results:
        df = pd.DataFrame(results)
        
        # Style the dataframe
        def highlight_setups(s):
            if "⭐" in s: return 'background-color: #155724; color: white' # Dark Green
            if "🚀" in s or "🔥" in s: return 'background-color: #1e3a8a; color: white' # Blue
            return ''

        styled_df = df.style.applymap(highlight_setups, subset=['Setup'])
        
        st.subheader("Scan Results")
        st.dataframe(styled_df, use_container_width=True)
        
        # Summary Stats
        col1, col2 = st.columns(2)
        col1.metric("Stacked Squeezes Found", len(df[df['Setup'] == "⭐ STACKED SQUEEZE"]))
        col2.metric("Total Bullish Setups", len(df[df['Trend (21 EMA)'] == "✅ Bullish"]))
    else:
        st.error("No data found or scan returned zero results.")

else:
    st.info("Click 'Run Scanner' in the sidebar to begin.")

# --- FOOTER ---
st.markdown("---")
st.caption("Data provided by Yahoo Finance. This tool is for educational purposes and does not constitute financial advice.")
