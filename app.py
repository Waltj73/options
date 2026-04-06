import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Nasdaq 50 Master", layout="wide")

# --- 1. THE LIST ---
FULL_SCAN_LIST = [
    "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX", 
    "AMD", "ADBE", "CRM", "QCOM", "TXN", "MU", "INTC", "AMAT", "LRCX", "ADI", 
    "PANW", "SNPS", "CDNS", "KLAC", "MAR", "PYPL", "ORLY", "MNST", "ADSK", "ANSS", 
    "MARA", "PLTR", "SOFI", "RIOT", "COIN", "HOOD", "AFRM", "UPST", "RKLB", "NIO",
    "SQ", "SHOP", "RBLX", "TSM", "DKNG", "PATH", "U", "AI", "GME", "AMC"
]

def get_clean_data(ticker):
    try:
        # Download data
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        h4 = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=True)
        
        # FIX: Flatten Multi-Index if it exists
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if isinstance(h4.columns, pd.MultiIndex):
            h4.columns = h4.columns.get_level_values(0)

        if df.empty or len(df) < 21: return None

        # TTM Squeeze math
        sqz = df.ta.squeeze(lazy_limit=True)
        ema21 = ta.ema(df['Close'], length=21).iloc[-1]
        
        # Dot Count
        sqz_series = sqz['SQZ_ON'].iloc[::-1]
        dots = 0
        for val in sqz_series:
            if val == 1: dots += 1
            else: break

        return {
            "Ticker": ticker,
            "Price": round(float(df['Close'].iloc[-1]), 2),
            "Trend": "Bullish" if df['Close'].iloc[-1] > ema21 else "Bearish",
            "Daily_Sqz": bool(sqz['SQZ_ON'].iloc[-1] == 1),
            "4H_Sqz": bool(h4.ta.squeeze(lazy_limit=True)['SQZ_ON'].iloc[-1] == 1),
            "Dot_Count": dots,
            "Fired": bool(sqz['SQZ_ON'].iloc[-2] == 1 and sqz['SQZ_ON'].iloc[-1] == 0)
        }
    except: return None

# --- 2. UI ---
st.title("⚡ Nasdaq 50 Squeeze Master")

if st.button("🚀 Start Scan"):
    results = []
    status_text = st.empty() # Real-time update slot
    bar = st.progress(0)
    
    for i, t in enumerate(FULL_SCAN_LIST):
        status_text.text(f"Analyzing {t}...") # Shows you it's actually moving
        raw = get_clean_data(t)
        if raw:
            # We show everything with ANY squeeze or a recent FIRE
            if raw['Daily_Sqz'] or raw['4H_Sqz'] or raw['Fired']:
                grade = "C"
                if raw['Trend'] == "Bullish":
                    grade = "A+" if raw['Daily_Sqz'] and raw['4H_Sqz'] else "A"
                
                results.append({
                    "Grade": grade,
                    "Ticker": t,
                    "Price": raw['Price'],
                    "Trend": "✅ Bull" if raw['Trend'] == "Bullish" else "❌ Bear",
                    "Dots": raw['Dot_Count'],
                    "4H Sqz": "RED" if raw['4H_Sqz'] else "OFF",
                    "Status": "Squeezing" if raw['Daily_Sqz'] else "Fired"
                })
        bar.progress((i+1)/len(FULL_SCAN_LIST))

    status_text.empty() # Clear the progress text

    if results:
        df = pd.DataFrame(results).sort_values(by=["Grade", "Dots"], ascending=[True, False])
        st.table(df)
    else:
        st.warning("Scan Complete. Math is working, but 0 stocks meet the 'Squeeze' criteria right now.")
