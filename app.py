import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Pro-Squeeze Grader", layout="wide")

# --- 1. DATASETS ---
MARKET_CAP_50 = ["NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX", "AMD", "ADBE", "CRM", "QCOM", "TXN"]
VOLUME_LEADERS_50 = ["PLTR", "SOFI", "MARA", "RIOT", "COIN", "HOOD", "AFRM", "UPST", "RKLB", "NIO", "TSLA", "NVDA", "AMD", "INTC", "PYPL"]

# --- 2. THE GRADING ENGINE ---
def grade_setup(data):
    ticker = data['Ticker']
    is_bullish = data['Trend'] == "Bullish"
    d_sqz = data['Daily_Sqz']
    h4_sqz = data['4H_Sqz']
    dots = data['Dot_Count']

    # New Logic: Grade based on Trend + Compression
    if is_bullish and d_sqz and h4_sqz:
        return "A+", f"The Holy Grail. {ticker} is trending higher and compressed on two timeframes."
    elif is_bullish and d_sqz:
        return "A" if dots >= 5 else "B", f"Bullish coil. Above 21 EMA with {dots} dots."
    elif not is_bullish and d_sqz:
        return "C", f"Bearish Squeeze. {ticker} is coiling but remains BELOW the 21 EMA. Watch for a breakdown or a trend reversal."
    elif data['Fired']:
        return "Fired", "The squeeze just released momentum. Check the chart for the direction."
    return "D", "No active squeeze."

def get_data(ticker):
    try:
        # Use a slightly longer period for EMA stability
        d = yf.download(ticker, period="1y", interval="1d", progress=False)
        h4 = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if d.empty or h4.empty: return None
        
        sqz = d.ta.squeeze(lazy_limit=True)
        ema21 = ta.ema(d['Close'], length=21).iloc[-1]
        
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
st.title("🎓 Pro-Squeeze Grader (Unfiltered)")
scan_mode = st.sidebar.radio("Universe", ["Market Cap Titans", "Volume Movers"])
tickers = MARKET_CAP_50 if "Titans" in scan_mode else VOLUME_LEADERS_50

if st.sidebar.button("🔍 Scan Everything"):
    results = []
    bar = st.progress(0)
    for i, t in enumerate(tickers):
        raw = get_data(t)
        if raw:
            grade, summary = grade_setup(raw)
            # LOOSENED: We now show everything that has ANY squeeze or just fired
            if raw['Daily_Sqz'] or raw['4H_Sqz'] or raw['Fired']:
                results.append({
                    "Grade": grade, 
                    "Ticker": t, 
                    "Price": raw['Price'], 
                    "Trend": "✅ Bull" if raw['Trend'] == "Bullish" else "❌ Bear",
                    "Dots": raw['Dot_Count'],
                    "Summary": summary
                })
        bar.progress((i+1)/len(tickers))

    if results:
        df = pd.DataFrame(results).sort_values(by="Grade")
        st.table(df)
    else:
        st.info("No tickers are currently in a Squeeze. The market is likely in an 'Expansion' phase.")
