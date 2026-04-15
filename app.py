import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

# --- DATA HELPERS ---
def get_clean_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

# --- TAB 1: STRAT SNIPER ---
def scan_strat(ticker):
    try:
        m = get_clean_data(ticker, "6mo", "1mo")
        d = get_clean_data(ticker, "1mo", "1d")
        curr = d['Close'].iloc[-1]
        m_o = m['Open'].iloc[-1]
        m_l2 = m['Low'].iloc[-2]
        # Strat logic: Monthly trend + "2-Down" failure check
        m_up = curr > m_o
        is_2d = m['Low'].iloc[-1] < m_l2
        grade = "A+" if m_up and is_2d else "A" if m_up else "C"
        return {"Ticker": ticker, "Grade": grade, "Price": round(curr, 2), "Trend": "UP" if m_up else "DN"}
    except: return None

# --- TAB 3: SQUEEZE ENGINE ---
def get_squeeze(ticker):
    try:
        df = get_clean_data(ticker, "6mo", "1d")
        length = 20
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        m_avg = df['Close'].rolling(window=length).mean()
        m_std = df['Close'].rolling(window=length).std()
        # Bollinger vs Keltner
        bb_u = m_avg + (2.0 * m_std)
        bb_l = m_avg - (2.0 * m_std)
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        atr = tr.rolling(window=length).mean()
        kc_u, kc_l = m_avg + (1.5 * atr), m_avg - (1.5 * atr)
        
        sq_on = (bb_u < kc_u) and (bb_l > kc_l)
        last = df.iloc[-1]
        direction = "Bullish" if last['Close'] > last['ema21'] else "Bearish"
        
        return {"Ticker": ticker, "Status": "🔴 SQUEEZE" if sq_on else "🟢 FIRE", "Dir": direction, "Price": round(last['Close'], 2)}
    except: return None

# --- UI SECTIONS ---
t1, t2, t3 = st.tabs(["🎯 Strat Sniper", "🌊 Sector Flow", "💥 Squeeze Scanner"])

SECTORS = {"Tech": ["NVDA", "AAPL", "MSFT", "AMD"], "Fin": ["JPM", "V", "MA", "PYPL"], "Def": ["PG", "KO", "AMGN", "LLY"]}

with t1:
    if st.button("Run Strat"):
        res = [scan_strat(t) for t in [tk for s in SECTORS.values() for tk in s]]
        st.table(pd.DataFrame([r for r in res if r]))

with t2:
    if st.button("Run Flow"):
        data = yf.download(["XLK", "XLF", "XLY", "SPY"], period="6mo", progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        rs = data.div(data['SPY'], axis=0).pct_change(21).iloc[-1] * 100
        st.table(rs)

with t3:
    if st.button("Run Squeeze"):
        res = [get_squeeze(t) for t in [tk for s in SECTORS.values() for tk in s]]
        st.table(pd.DataFrame([r for r in res if r]))
