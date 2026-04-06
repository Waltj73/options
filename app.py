import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Pro-Squeeze Grader", layout="wide")

# --- 1. DATASETS ---
MARKET_CAP_50 = ["NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX", "AMD", "ADBE", "CRM", "QCOM", "TXN"]
VOLUME_LEADERS_50 = ["PLTR", "SOFI", "MARA", "RIOT", "COIN", "HOOD", "AFRM", "UPST", "RKLB", "NIO", "TSLA", "NVDA", "AMD", "INTC", "GME"]

# --- 2. THE GRADING ENGINE ---
def grade_setup(data):
    ticker = data['Ticker']
    is_bullish = data['Trend'] == "Bullish"
    d_sqz = data['Daily_Sqz']
    h4_sqz = data['4H_Sqz']
    dots = data['Dot_Count']
    fired = data['Fired']

    if is_bullish and d_sqz and h4_sqz:
        return "A+", f"The Holy Grail. {ticker} is trending higher and compressed on two timeframes. Explosive potential."
    elif is_bullish and d_sqz and dots >= 5:
        return "A", f"Strong Bullish Coil. {ticker} has {dots} days of energy built up above the trend line."
    elif is_bullish and d_sqz:
        return "B", f"Early Bullish Squeeze. Trend is right, but the squeeze is still in the early 'coiling' phase."
    elif is_bullish and fired:
        return "A (Fired)", f"Momentum Release. The squeeze just fired long. Watch for follow-through."
    elif not is_bullish and d_sqz:
        return "C", f"Bearish Squeeze. {ticker} is coiling but remains below the 21 EMA. High risk of a breakdown."
    return "D", "No significant squeeze activity or trend alignment."

def get_data(ticker):
    try:
        d = yf.download(ticker, period="6mo", interval="1d", progress=False)
        h4 = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if d.empty or h4.empty: return None
        
        sqz = d.ta.squeeze(lazy_limit=True)
        ema21 = ta.ema(d['Close'], length=21).iloc[-1]
        
        # Dot counting logic
        sqz_series = sqz['SQZ_ON'].iloc[::-1]
        dots = 0
        for val in sqz_series:
            if val == 1: dots += 1
            else: break

        return {
            "Ticker": ticker,
            "Price": round(float(d['Close'].iloc[-1]), 2),
            "Trend": "Bullish" if d['Close'].iloc[-1] > ema21 else "Bearish",
            "Daily_Sqz": bool(sqz['SQZ_ON'].iloc[-1] == 1),
            "4H_Sqz": bool(h4.ta.squeeze(lazy_limit=True)['SQZ_ON'].iloc[-1] == 1),
            "Dot_Count": dots,
            "Fired": bool(sqz['SQZ_ON'].iloc[-2] == 1 and sqz['SQZ_ON'].iloc[-1] == 0),
            "Hist": round(float(sqz['SQZ_INC'].iloc[-1]), 3)
        }
    except: return None

# --- 3. UI ---
st.title("🎓 Pro-Squeeze Setup Grader")
scan_mode = st.sidebar.radio("Universe", ["Market Cap Titans", "Volume Movers"])
tickers = MARKET_CAP_50 if "Titans" in scan_mode else VOLUME_LEADERS_50

if st.sidebar.button("🔍 Scan & Grade"):
    results = []
    bar = st.progress(0)
    for i, t in enumerate(tickers):
        raw = get_data(t)
        if raw:
            grade, summary = grade_setup(raw)
            if True: # Loosened: Shows everything except "No Setup"
                results.append({
                    "Grade": grade, "Ticker": t, "Price": raw['Price'], 
                    "Trend": "✅" if raw['Trend'] == "Bullish" else "❌",
                    "Sqz (D/4H)": f"{raw['Daily_Sqz']}/{raw['4H_Sqz']}",
                    "Summary": summary
                })
        bar.progress((i+1)/len(tickers))

    if results:
        df = pd.DataFrame(results).sort_values(by="Grade")
        def color_grade(val):
            color = '#1e3a8a' if 'A' in val else '#374151'
            if val == 'A+': color = '#064e3b'
            return f'background-color: {color}; color: white'

        st.table(df.style.applymap(color_grade, subset=['Grade']))
    else:
        st.info("No Squeezes found in this list.")
