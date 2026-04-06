import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Strat Sniper 2026", layout="wide")

def get_strat_type(curr, prev):
    """Classifies a candle as 1, 2U, 2D, or 3."""
    if curr['High'] <= prev['High'] and curr['Low'] >= prev['Low']: return "1"
    if curr['High'] > prev['High'] and curr['Low'] < prev['Low']: return "3"
    if curr['High'] > prev['High']: return "2U"
    if curr['Low'] < prev['Low']: return "2D"
    return "2"

def get_actionable_signal(df_h1):
    """Detects 2-2 Reversals, 1-2 Breakouts, and 3-2 Reversals on H1."""
    if len(df_h1) < 3: return "None", "Neutral"
    
    c = df_h1.iloc[-1]   # Current Candle
    p = df_h1.iloc[-2]   # Previous Candle
    pp = df_h1.iloc[-3]  # Candle before previous
    
    t_c = get_strat_type(c, p)
    t_p = get_strat_type(p, pp)
    
    # 1. The 2-2 Reversal (Bullish: 2D then 2U)
    if t_p == "2D" and t_c == "2U": return "🚀 2-2 Rev Up", "Bullish"
    if t_p == "2U" and t_c == "2D": return "🩸 2-2 Rev Down", "Bearish"
    
    # 2. The 1-2 Breakout (The 'Coil' Release)
    if t_p == "1" and t_c == "2U": return "🎯 1-2 Up", "Bullish"
    if t_p == "1" and t_c == "2D": return "⚠️ 1-2 Down", "Bearish"
    
    # 3. The 3-2 Reversal (Broadening into Trend)
    if t_p == "3" and t_c == "2U": return "🔥 3-2 Up", "Bullish"
    if t_p == "3" and t_c == "2D": return "🌊 3-2 Down", "Bearish"

    return f"H1: {t_c}", "Neutral"

def scan_strat(ticker):
    try:
        # Fetching Data
        m = yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True)
        w = yf.download(ticker, period="3mo", interval="1wk", progress=False, auto_adjust=True)
        d = yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True)
        h1 = yf.download(ticker, period="5d", interval="1h", progress=False, auto_adjust=True)

        if m.empty or w.empty or d.empty or h1.empty: return None

        # FTC Check (Current Price vs Open)
        price = h1['Close'].iloc[-1]
        m_dir = "UP" if price > m['Open'].iloc[-1] else "DOWN"
        w_dir = "UP" if price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if price > d['Open'].iloc[-1] else "DOWN"
        
        ftfc = "✅ FULL UP" if (m_dir == "UP" and w_dir == "UP" and d_dir == "UP") else \
               "🛑 FULL DOWN" if (m_dir == "DOWN" and w_dir == "DOWN" and d_dir == "DOWN") else "Mixed"

        signal, bias = get_actionable_signal(h1)

        return {
            "Ticker": ticker,
            "Price": round(float(price), 2),
            "FTFC": ftfc,
            "M/W/D": f"{m_dir}/{w_dir}/{d_dir}",
            "H1 Signal": signal,
            "Bias": bias
        }
    except: return None

# --- UI ---
st.title("🎯 Strat Sniper: FTC + H1 Triggers")
st.write("Full Continuity on Month/Week/Day with actionable triggers on the 1-Hour chart.")

WATCHLIST = ["NVDA", "AAPL", "TSLA", "AMD", "MSFT", "META", "AMZN", "PLTR", "PYPL", "MARA", "COIN", "SOFI", "BTC-USD"]

if st.button("🔍 Scan for Actionable Signals"):
    results = []
    bar = st.progress(0)
    for i, t in enumerate(WATCHLIST):
        data = scan_strat(t)
        if data: results.append(data)
        bar.progress((i+1)/len(WATCHLIST))

    if results:
        df = pd.DataFrame(results)
        
        # Color Logic: Only Highlight if H1 Signal matches FTFC
        def highlight_trades(row):
            is_bullish_trade = (row['FTFC'] == "✅ FULL UP" and row['Bias'] == "Bullish")
            is_bearish_trade = (row['FTFC'] == "🛑 FULL DOWN" and row['Bias'] == "Bearish")
            
            if is_bullish_trade: return ['background-color: #064e3b; color: white'] * len(row)
            if is_bearish_trade: return ['background-color: #7f1d1d; color: white'] * len(row)
            return [''] * len(row)

        st.table(df.style.apply(highlight_trades, axis=1))
    else:
        st.info("No data returned. Markets may be closed or tickers invalid.")
