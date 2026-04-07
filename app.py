import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Nasdaq-100 Strat Sniper", layout="wide")

# --- THE NASDAQ-100 COMPONENTS (Updated for April 2026) ---
NDX_100 = [
    "ADBE", "AMD", "ABNB", "ALNY", "GOOGL", "GOOG", "AMZN", "AEP", "AMGN", "ADI",
    "AAPL", "AMAT", "APP", "ARM", "ASML", "TEAM", "ADSK", "ADP", "AXON", "BKR",
    "BKNG", "AVGO", "CDNS", "CHTR", "CTAS", "CSCO", "CCEP", "CTSH", "CMCSA", "CEG",
    "CPRT", "CSGP", "COST", "CRWD", "CSX", "DDOG", "DXCM", "FANG", "DASH", "EA",
    "EXC", "FAST", "FER", "FTNT", "GEHC", "GILD", "HON", "IDXX", "INSM", "INTC",
    "INTU", "ISRG", "KDP", "KLAC", "KHC", "LRCX", "LIN", "MAR", "MRVL", "MELI",
    "META", "MCHP", "MU", "MSFT", "MDLZ", "MPWR", "MNST", "NFLX", "NVDA", "NXPI",
    "ORLY", "ODFL", "PCAR", "PLTR", "PANW", "PAYX", "PYPL", "PDD", "PEP", "QCOM",
    "REGN", "ROP", "ROST", "STX", "SHOP", "SBUX", "MSTR", "SNPS", "TMUS", "TTWO",
    "TSLA", "TXN", "TRI", "VRSK", "VRTX", "WMT", "WDC", "WDAY", "WBD", "XEL", "ZS"
]

def get_strat_type(curr, prev):
    if curr['High'] <= prev['High'] and curr['Low'] >= prev['Low']: return "1"
    if curr['High'] > prev['High'] and curr['Low'] < prev['Low']: return "3"
    if curr['High'] > prev['High']: return "2U"
    if curr['Low'] < prev['Low']: return "2D"
    return "2"

def get_h1_signal(df_h1):
    if len(df_h1) < 3: return "None", "Neutral"
    c, p, pp = df_h1.iloc[-1], df_h1.iloc[-2], df_h1.iloc[-3]
    t_c, t_p = get_strat_type(c, p), get_strat_type(p, pp)
    
    if t_p == "2D" and t_c == "2U": return "🚀 2-2 Rev Up", "Bullish"
    if t_p == "2U" and t_c == "2D": return "🩸 2-2 Rev Down", "Bearish"
    if t_p == "1" and t_c == "2U": return "🎯 1-2 Up", "Bullish"
    if t_p == "1" and t_c == "2D": return "⚠️ 1-2 Down", "Bearish"
    return f"H1: {t_c}", "Neutral"

def scan_strat(ticker):
    try:
        # Batch download for timeframes to keep speed up
        d = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        w = yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True)
        m = yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True)
        h1 = yf.download(ticker, period="5d", interval="1h", progress=False, auto_adjust=True)

        if any(x.empty for x in [d, w, m, h1]): return None

        price = h1['Close'].iloc[-1]
        m_dir = "UP" if price > m['Open'].iloc[-1] else "DOWN"
        w_dir = "UP" if price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if price > d['Open'].iloc[-1] else "DOWN"
        
        ftfc = "✅ FULL UP" if (m_dir == "UP" and w_dir == "UP" and d_dir == "UP") else \
               "🛑 FULL DOWN" if (m_dir == "DOWN" and w_dir == "DOWN" and d_dir == "DOWN") else "Mixed"

        signal, bias = get_h1_signal(h1)

        return {
            "Ticker": ticker,
            "Price": round(float(price), 2),
            "FTFC": ftfc,
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}",
            "H1 Trigger": signal,
            "Bias": bias
        }
    except: return None

# --- UI ---
st.title("🎯 Nasdaq-100 Strat Sniper")
st.subheader("Swing Trading Dashboard: M/W/D Continuity + 1H Action")

if st.button("🚀 Run Full NDX-100 Scan"):
    results = []
    progress_bar = st.progress(0)
    status_msg = st.empty()

    for i, ticker in enumerate(NDX_100):
        status_msg.text(f"Analyzing {ticker}...")
        res = scan_strat(ticker)
        if res: results.append(res)
        progress_bar.progress((i + 1) / len(NDX_100))

    status_msg.empty()

    if results:
        df = pd.DataFrame(results)
        
        # Priority Filter: Only show setups with high-probability alignment
        high_prob = df[(df['FTFC'].str.contains("FULL")) & (df['Bias'] != "Neutral")]
        
        st.write("### 🔥 Actionable Setups (FTFC Aligned)")
        if not high_prob.empty:
            st.table(high_prob)
        else:
            st.info("No 1-hour triggers currently align with M/W/D continuity.")

        st.write("### 📊 All Scanned Tickers")
        st.dataframe(df)
    else:
        st.error("No data retrieved. Verify API connection.")
