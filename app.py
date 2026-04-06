import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Nasdaq 50 Pro Grader", layout="wide")

# --- 1. THE FULL LIST (Back to 50) ---
FULL_SCAN_LIST = [
    "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX", 
    "AMD", "ADBE", "CRM", "QCOM", "TXN", "MU", "INTC", "AMAT", "LRCX", "ADI", 
    "PANW", "SNPS", "CDNS", "KLAC", "MAR", "PYPL", "ORLY", "MNST", "ADSK", "ANSS", 
    "MARA", "PLTR", "SOFI", "RIOT", "COIN", "HOOD", "AFRM", "UPST", "RKLB", "NIO",
    "SQ", "SHOP", "RBLX", "TSM", "DKNG", "PATH", "U", "AI", "GME", "AMC"
]

def get_clean_data(ticker):
    try:
        # One by one to avoid the Multi-Index bug
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        h4 = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)
        
        if df.empty or len(df) < 30: return None

        # TTM Squeeze Calculation
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
            "Fired": bool(sqz['SQZ_ON'].iloc[-2] == 1 and sqz['SQZ_ON'].iloc[-1] == 0),
            "Hist": round(float(sqz['SQZ_INC'].iloc[-1]), 3)
        }
    except: return None

# --- 2. UI ---
st.title("⚡ Nasdaq 50 Squeeze Master")
st.caption(f"Scanning {len(FULL_SCAN_LIST)} Momentum & Volume Leaders")

if st.button("🚀 Start Full 50-Stock Scan"):
    results = []
    total_scanned = 0
    bar = st.progress(0)
    
    for i, t in enumerate(FULL_SCAN_LIST):
        raw = get_clean_data(t)
        if raw:
            total_scanned += 1
            # Show if in Squeeze or just Fired
            if raw['Daily_Sqz'] or raw['4H_Sqz'] or raw['Fired']:
                # GRADING LOGIC
                if raw['Trend'] == "Bullish" and raw['Daily_Sqz'] and raw['4H_Sqz']: grade = "A+"
                elif raw['Trend'] == "Bullish" and raw['Daily_Sqz']: grade = "A"
                elif raw['Daily_Sqz']: grade = "C (Bearish)"
                else: grade = "Fired"

                results.append({
                    "Grade": grade,
                    "Ticker": t,
                    "Price": raw['Price'],
                    "Trend": "✅ Bull" if raw['Trend'] == "Bullish" else "❌ Bear",
                    "Dots": raw['Dot_Count'],
                    "4H Sqz": "RED" if raw['4H_Sqz'] else "OFF",
                    "Summary": f"Coiling above 21 EMA" if raw['Trend'] == "Bullish" else "Coiling BELOW trend"
                })
        bar.progress((i+1)/len(FULL_SCAN_LIST))

    if results:
        df = pd.DataFrame(results).sort_values(by="Grade")
        st.table(df)
    else:
        st.warning(f"Scan Complete. Scanned {total_scanned} stocks, but 0 are currently in a Squeeze.")
        st.info("Market Context: When the VIX is high, Bollinger Bands stay wide. No red dots = No compression.")
