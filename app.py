import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. CONFIGURATION & UI ---
st.set_page_config(page_title="Nasdaq 50 Squeeze Pro", layout="wide")

# The "Big 50" - Hand-picked for liquidity and volatility
NASDAQ_50 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "PEP", 
    "ASML", "COST", "ADBE", "AZN", "LIN", "AMD", "TXN", "INTC", "TMUS", "AMAT", 
    "QCOM", "AMGN", "ISRG", "HON", "VRTX", "BKNG", "SBUX", "PANW", "MDLZ", "INTU", 
    "REGN", "GILD", "ADI", "LRCX", "MU", "MELI", "SNPS", "CDNS", "KLAC", "CSX", 
    "MAR", "PYPL", "ORLY", "MNST", "ASML", "ADSK", "ANSS", "CPRT", "KDP", "MCHP"
]

# --- 2. THE LOGIC ENGINE ---
def get_squeeze_data(ticker):
    try:
        # Fetch 6 months of data (Optimal for 21 EMA & Squeeze calculation speed)
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        h4_data = yf.download(ticker, period="1mo", interval="1h", progress=False) # 4h equivalent
        
        if data.empty or h4_data.empty: return None

        # --- Daily Analysis ---
        sqz = data.ta.squeeze(lazy_limit=True)
        ema21 = ta.ema(data['Close'], length=21)
        
        # Calculate Dot Count (How many consecutive red dots?)
        # We reverse the series and count until the first '0' (no squeeze)
        sqz_series = sqz['SQZ_ON'].iloc[::-1]
        dot_count = 0
        for val in sqz_series:
            if val == 1: dot_count += 1
            else: break
            
        last_d = data.iloc[-1]
        last_sqz = sqz.iloc[-1]
        
        # --- 4-Hour Analysis ---
        # Note: yfinance 1h data used to simulate 4h (last 4 bars)
        h4_sqz = h4_data.ta.squeeze(lazy_limit=True).iloc[-1]

        return {
            "Ticker": ticker,
            "Price": round(float(last_d['Close']), 2),
            "Trend": "Bullish" if last_d['Close'] > ema21.iloc[-1] else "Bearish",
            "Daily_Sqz": bool(last_sqz['SQZ_ON'] == 1),
            "Dot_Count": dot_count,
            "4H_Sqz": bool(h4_sqz['SQZ_ON'] == 1),
            "Fired": bool(sqz.iloc[-2]['SQZ_ON'] == 1 and last_sqz['SQZ_ON'] == 0),
            "Hist": round(float(last_sqz['SQZ_INC']), 3)
        }
    except:
        return None

# --- 3. MAIN INTERFACE ---
st.title("⚡ Nasdaq 50 Squeeze Dash")
st.caption("Scanning the top 50 Nasdaq names for compression setups and trend alignment.")

if st.button("🚀 Run Nasdaq Scan"):
    results = []
    bar = st.progress(0)
    
    for i, ticker in enumerate(NASDAQ_50):
        status = get_squeeze_data(ticker)
        if status:
            # Filtering for "Actionable" logic
            # We want: Current Squeezes OR Just Fired
            if status['Daily_Sqz'] or status['Fired']:
                
                # Determine Setup Type
                setup = "Building"
                if status['Fired'] and status['Trend'] == "Bullish": setup = "🚀 FIRE (LONG)"
                elif status['Daily_Sqz'] and status['4H_Sqz']: setup = "⭐ STACKED"
                elif status['Daily_Sqz']: setup = f"⏳ {status['Dot_Count']} Dots"
                
                results.append({
                    "Ticker": status['Ticker'],
                    "Price": status['Price'],
                    "Setup": setup,
                    "Trend": "✅" if status['Trend'] == "Bullish" else "❌",
                    "Dots": status['Dot_Count'],
                    "4H": "RED" if status['4H_Sqz'] else "OFF",
                    "Energy": status['Hist']
                })
        bar.progress((i + 1) / len(NASDAQ_50))

    if results:
        df = pd.DataFrame(results).sort_values(by="Dots", ascending=False)
        
        # UI Styling
        def highlight_rows(row):
            if "⭐" in str(row.Setup): return ['background-color: #1b4332'] * len(row)
            if "🚀" in str(row.Setup): return ['background-color: #0d47a1'] * len(row)
            return [''] * len(row)

        st.subheader("Active Setups Found")
        st.dataframe(df.style.apply(highlight_rows, axis=1), use_container_width=True)
        
        # Insight Column
        st.info("**Strategy Tip:** Focus on tickers with 5+ Dots that are also Bullish (✅). These are high-probability 'Coiled Springs'.")
    else:
        st.success("No active squeezes in the Nasdaq 50 right now. Markets might be in an extended 'Expansion' phase.")

else:
    st.info("Click the button above to analyze the Nasdaq 50.")
