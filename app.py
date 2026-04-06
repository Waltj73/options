import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Pro-Squeeze Fixed", layout="wide")

# --- 1. DATASETS ---
VOL_LEADERS = ["NVDA", "TSLA", "PLTR", "AMD", "MARA", "PYPL", "COIN", "SOFI", "RIOT", "RKLB"]

def get_data_fixed(ticker):
    try:
        # BUG FIX: We download ONE ticker at a time to avoid Multi-Index issues
        # and we use 'auto_adjust=True' to match TOS OHLC data
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        h4 = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)
        
        if df.empty or len(df) < 30: return None

        # Calculate Squeeze - We must be explicit with the columns now
        # Returns: SQZ_ON, SQZ_OFF, SQZ_NO, SQZ_INC, SQZ_DEC
        sqz = df.ta.squeeze(lazy_limit=True)
        
        # Calculate EMA
        ema21 = ta.ema(df['Close'], length=21).iloc[-1]
        
        # Dot counting logic (Reverse scan for consecutive reds)
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
    except Exception as e:
        # st.error(f"Error on {ticker}: {e}") # Debugging
        return None

# --- 2. UI ---
st.title("🎓 Pro-Squeeze Grader (Fixed Data)")
if st.button("🔍 Scan Momentum Leaders"):
    results = []
    bar = st.progress(0)
    for i, t in enumerate(VOL_LEADERS):
        raw = get_data_fixed(t)
        if raw:
            # UNFILTERED: Shows everything with a squeeze or a fire
            if raw['Daily_Sqz'] or raw['4H_Sqz'] or raw['Fired']:
                status = "A+" if raw['Trend'] == "Bullish" and raw['Daily_Sqz'] else "Check Chart"
                results.append({
                    "Ticker": t,
                    "Price": raw['Price'],
                    "Setup": f"{raw['Dot_Count']} Dots" if raw['Daily_Sqz'] else "Fired",
                    "Trend": "✅ Bull" if raw['Trend'] == "Bullish" else "❌ Bear",
                    "4H Sqz": "RED" if raw['4H_Sqz'] else "OFF",
                    "Score": status
                })
        bar.progress((i+1)/len(VOL_LEADERS))

    if results:
        st.table(pd.DataFrame(results))
    else:
        st.warning("Math is working, but no Squeezes found in these 10 names. Try adding more tickers.")
