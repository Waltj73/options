import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from squeeze import calculate_ttm_squeeze 

st.set_page_config(page_title="Strat Sniper v6", layout="wide")

def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

SECTORS = {
    "Market Pillars & Metals": ["SPY", "QQQ", "GLD", "SLV", "PAAS"],
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Consumer/Growth": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "SBUX", "ABNB", "SHOP", "DKNG", "MARA"],
    "Energy & Materials": ["XOM", "CVX", "SLB", "COP", "MPC", "LIN", "APD", "FCX", "NEM", "VMC"],
    "Industrials": ["GE", "CAT", "RTX", "HON", "UNP", "LMT", "UPS", "BA", "DE", "GEHC"],
    "Defensives": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "SO", "DUK", "CEG", "EXC"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "AMGN", "ISRG", "PFE", "GILD"]
}

def get_grade(m_dir, w_dir, d_dir, is_m_2d):
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP" and is_m_2d:
        return "A+", "🔥 SNIPER: Failed 2D Monthly + FTC Up"
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP":
        return "A", "✅ TREND: Full Continuity Up"
    if w_dir == "UP" and d_dir == "UP" and m_dir == "DOWN":
        return "B", "⚠️ HOOK: Monthly Trap In-Progress"
    if m_dir == "DOWN" and w_dir == "DOWN" and d_dir == "DOWN":
        return "D", "🩸 BEAR: Avoid Longs"
    return "C", "🔄 BATTLE: Mixed Continuity"

def scan_strat(ticker, sector):
    try:
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True))
        w = flatten_df(yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True))
        if m.empty or w.empty or d.empty: 
            return None
        curr_price = float(d['Close'].iloc[-1])
        m_open = float(m['Open'].iloc[-1])
        m_prev_low = float(m['Low'].iloc[-2])
        m_prev_high = float(m['High'].iloc[-2])
        is_m_2d = float(m['Low'].iloc[-1]) < m_prev_low
        m_dir = "UP" if curr_price > m_open else "DOWN"
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"
        grade, summary = get_grade(m_dir, w_dir, d_dir, is_m_2d)
        room = ((m_prev_high - curr_price) / curr_price) * 100
        return {
            "Grade": grade, 
            "Ticker": ticker, 
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}", 
            "Summary": summary, 
            "Room (%)": round(room, 2), 
            "Sector": sector
        }
    except Exception: 
        return None

def scan_unusual_options(ticker, min_vol=500, min_vol_oi=2.0, min_dte=15, max_dte=60):
    try:
        tk = yf.Ticker(ticker)
        all_expirations = tk.options
        if not all_expirations:
            return []

        today = datetime.now().date()
        valid_expirations = []
        
        # Filter expirations strictly by the user's DTE target window
        for exp_str in all_expirations:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if min_dte <= dte <= max_dte:
                valid_expirations.append((exp_str, dte))

        if not valid_expirations:
            return []

        rows = []
        for exp, dte in valid_expirations:
            chain = tk.option_chain(exp)
            for opt_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                if df.empty:
                    continue
                
                df = df.copy()
                df['volume'] = df['volume'].fillna(0).astype(int)
                df['openInterest'] = df['openInterest'].fillna(0).astype(int)
                
                active = df[df['volume'] >= min_vol].copy()
                if active.empty:
                    continue
                
                active['vol_oi'] = active.apply(
                    lambda r: round(r['volume'] / r['openInterest'], 2) if r['openInterest'] > 0 else round(float(r['volume']), 2),
                    axis=1
                )
                
                unusual = active[active['vol_oi'] >= min_vol_oi]
                for _, r in unusual.iterrows():
                    last_price = float(r.get('lastPrice', 0.0))
                    volume = int(r['volume'])
                    est_premium = round(volume * last_price * 100, 2)
                    
                    rows.append({
                        "Ticker": ticker,
                        "Type": opt_type,
                        "Expiry": exp,
                        "DTE": dte,
                        "Strike": r['strike'],
                        "Last": last_price,
                        "Volume": volume,
                        "Open Int": int(r['openInterest']),
                        "Vol / OI": r['vol_oi'],
                        "Est Flow ($)": est_premium,
                        "IV (%)": round(r.get('impliedVolatility', 0) * 100, 2)
                    })
        return rows
    except Exception:
        return []

tab_sniper, tab_flow, tab_squeeze, tab_options = st.tabs([
    "🎯 Strat Universal Sniper", 
    "🌊 Sector Money Flow", 
    "💥 TTM Squeeze",
    "⚡ Unusual Options"
])

# --- TAB 1: STRAT SNIPER ---
with tab_sniper:
    st.title("🎯 Strat Universal Sniper")
    if st.button("🚀 Execute Full Market Scan"):
        results = []
        bar = st.progress(0)
        total = sum(len(v) for v in SECTORS.values())
        count = 0
        for s, tickers in SECTORS.items():
            for t in tickers:
                res = scan_strat(t, s)
                if res: 
                    results.append(res)
                count += 1
                bar.progress(count / total)
        if results:
            df = pd.DataFrame(results)
            st.write("## 💎 THE KILL ZONE: A+ SNIPER SETUPS")
            aplus = df[df['Grade'] == "A+"]
            if not aplus.empty: 
                st.table(aplus.sort_values(by="Room (%)", ascending=False))
            with st.expander("📈 Tier A (Clean Trends)", expanded=True):
                st.table(df[df['Grade'] == "A"].sort_values(by="Room (%)", ascending=False))

# --- TAB 2: SECTOR FLOW ---
with tab_flow:
    st.title("🌊 Sector Money Flow")
    if st.button("🔍 Analyze Relative Strength"):
        sector_etfs = {
            "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", 
            "XLV": "Healthcare", "XLY": "Consumer Disc", "XLI": "Industrials", 
            "XLC": "Communications", "XLP": "Consumer Staples", "XLB": "Materials", 
            "XLRE": "Real Estate", "XLU": "Utilities"
        }
        data = flatten_df(yf.download(list(sector_etfs.keys()) + ["SPY"], period="7mo", progress=False, auto_adjust=True)['Close'])
        rs_ratios = data[list(sector_etfs.keys())].div(data['SPY'], axis=0)
        flow_1m = (rs_ratios.pct_change(21).iloc[-1]) * 100
        flow_results = [{"Ticker": t, "Sector": n, "1M RS Flow (%)": round(flow_1m[t], 2)} for t, n in sector_etfs.items()]
        st.dataframe(pd.DataFrame(flow_results).sort_values(by="1M RS Flow (%)", ascending=False))

# --- TAB 3: TTM SQUEEZE ---
with tab_squeeze:
    st.title("💥 TTM Squeeze Scanner")
    if st.button("🔍 Scan for Squeezes"):
        results = []
        all_tickers = [t for sublist in SECTORS.values() for t in sublist]
        bar = st.progress(0)
        for i, t in enumerate(all_tickers):
            row = calculate_ttm_squeeze(t)
            if row is not None:
                results.append({
                    "Ticker": t,
                    "Status": "🔴 SQUEEZING" if row['squeeze_on'] else "🟢 FIRED",
                    "Momentum": round(row['momentum'], 4),
                    "Direction": "Bullish" if row['momentum'] > 0 else "Bearish"
                })
            bar.progress((i + 1) / len(all_tickers))
        if results:
            sq_df = pd.DataFrame(results)
            active = sq_df[sq_df['Status'] == "🔴 SQUEEZING"].sort_values(by="Momentum", ascending=False)
            st.subheader("Active Volatility Squeezes")
            if not active.empty: 
                st.table(active)
            with st.expander("View All Symbols"): 
                st.dataframe(sq_df, use_container_width=True)

# --- TAB 4: UNUSUAL OPTIONS ACTIVITY ---
with tab_options:
    st.title("⚡ Unusual Options Activity")
    st.caption("Filters for aggressive positioning across tactical expiration cycles.")
    
    col1, col2 = st.columns(2)
    with col1:
        dte_range = st.slider("Expiration Window (DTE)", min_value=7, max_value=90, value=(15, 60))
    with col2:
        target_group = st.selectbox(
            "Universe to Scan", 
            ["Technology", "Market Pillars & Metals", "Consumer/Growth", "Financials", "Energy & Materials", "Industrials", "Defensives", "Healthcare", "All Watchlist"]
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        min_contracts = st.number_input("Min Volume (Contracts)", min_value=100, value=500, step=100)
    with col4:
        vol_oi_threshold = st.number_input("Min Vol / OI Ratio", min_value=1.0, value=2.0, step=0.5)
    with col5:
        min_dollar_flow = st.number_input("Min Estimated Premium ($)", min_value=0, value=50000, step=25000)

    if st.button("🔥 Scan Flow"):
        if target_group == "All Watchlist":
            scan_list = [t for sublist in SECTORS.values() for t in sublist]
        else:
            scan_list = SECTORS[target_group]
            
        opt_results = []
        bar = st.progress(0)
        
        for idx, sym in enumerate(scan_list):
            hits = scan_unusual_options(
                sym, 
                min_vol=min_contracts, 
                min_vol_oi=vol_oi_threshold,
                min_dte=dte_range[0],
                max_dte=dte_range[1]
            )
            if hits:
                opt_results.extend(hits)
            bar.progress((idx + 1) / len(scan_list))
            time.sleep(0.05)
            
        if opt_results:
            flow_df = pd.DataFrame(opt_results)
            # Filter by total dollar premium committed
            flow_df = flow_df[flow_df['Est Flow ($)'] >= min_dollar_flow].sort_values(by="Est Flow ($)", ascending=False)
            
            if not flow_df.empty:
                calls = flow_df[flow_df['Type'] == "CALL"]
                puts = flow_df[flow_df['Type'] == "PUT"]
                
                st.write(f"### 🚀 Bullish Flow (Calls | {dte_range[0]}–{dte_range[1]} DTE)")
                if not calls.empty:
                    st.dataframe(
                        calls.style.format({"Est Flow ($)": "${:,.0", "Last": "${:.2f}", "Strike": "${:.2f}"}),
                        use_container_width=True
                    )
                else:
                    st.info("No calls matched your volume and premium filters.")
                    
                st.write(f"### 🩸 Bearish Flow (Puts | {dte_range[0]}–{dte_range[1]} DTE)")
                if not puts.empty:
                    st.dataframe(
                        puts.style.format({"Est Flow ($)": "${:,.0f}", "Last": "${:.2f}", "Strike": "${:.2f}"}),
                        use_container_width=True
                    )
                else:
                    st.info("No puts matched your volume and premium filters.")
            else:
                st.warning("Found contracts with high Vol/OI, but none met your Minimum Dollar Flow threshold.")
        else:
            st.warning("No contracts met the criteria in this expiration range.")
