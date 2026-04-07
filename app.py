import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="NDX-100 Trap Sniper", layout="wide")

# --- OFFICIAL NDX-100 TICKER LIST (Updated April 2026) ---
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
    "TSLA", "TXN", "TRI", "VRSK", "VRTX", "WMT", "WDC", "WDAY", "WBD", "XEL"
]

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def scan_trap(ticker):
    try:
        # Standardize data fetching
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True))
        w = flatten_df(yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True))
        
        if m.empty or w.empty or d.empty: return None

        curr_price = float(d['Close'].iloc[-1])
        m_open = float(m['Open'].iloc[-1])
        m_prev_low = float(m['Low'].iloc[-2])
        m_prev_high = float(m['High'].iloc[-2])
        
        # Monthly State
        m_curr_low = float(m['Low'].iloc[-1])
        is_m_2d = m_curr_low < m_prev_low
        
        # Continuity Check
        m_dir = "UP" if curr_price > m_open else "DOWN"
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"

        # FTC & Trap Logic
        is_ftc_up = (m_dir == "UP" and w_dir == "UP" and d_dir == "UP")
        ftc_signal = "✅" if is_ftc_up else "❌"
        is_trap = is_m_2d and w_dir == "UP" and d_dir == "UP"

        # Room to Run
        distance_to_target = m_prev_high - curr_price
        pct_to_target = (distance_to_target / curr_price) * 100

        setup = "Trend"
        if is_trap and m_dir == "UP":
            setup = "🔥 FAILED 2-DOWN"
        elif is_trap:
            setup = "⚠️ POTENTIAL TRAP"

        return {
            "FTC": ftc_signal,
            "Ticker": ticker,
            "Price": round(curr_price, 2),
            "Setup": setup,
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}",
            "Target (PMH)": round(m_prev_high, 2),
            "Room to Run (%)": round(pct_to_target, 2)
        }
    except: return None

# --- UI ---
st.title("🎯 Nasdaq-100 Trap Sniper")
st.write(f"Searching {len(NDX_100)} names for Monthly Failed 2-Downs.")

if st.button("🚀 Start Full 100-Stock Scan"):
    results = []
    bar = st.progress(0)
    status = st.empty()
    
    for i, t in enumerate(NDX_100):
        status.text(f"Scanning {t}...")
        res = scan_trap(t)
        if res: results.append(res)
        # Small sleep to keep the API connection stable
        if i % 15 == 0: time.sleep(0.1)
        bar.progress((i+1)/len(NDX_100))
    
    status.empty()
    
    if results:
        df = pd.DataFrame(results)
        aplus = df[(df['FTC'] == "✅") & (df['Setup'] == "🔥 FAILED 2-DOWN")]
        
        st.write("### 💎 A+ Setup List (FTC UP + Monthly Failure)")
        if not aplus.empty:
            st.table(aplus.sort_values(by="Room to Run (%)", ascending=False))
        else:
            st.info("No current A+ setups. Check back at the next 1-hour candle close.")
            
        st.write("### 📊 Market-Wide Scan Data")
        st.dataframe(df.sort_values(by="FTC", ascending=False))
