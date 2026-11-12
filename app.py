from datetime import datetime
import time
import pandas as pd
from squeeze import calculate_ttm_squeeze
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Strat Sniper v7", layout="wide")


def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


SECTORS = {
    "Market Pillars & Metals": ["SPY", "QQQ", "GLD", "SLV", "PAAS"],
    "Technology": [
        "NVDA",
        "AAPL",
        "MSFT",
        "AMD",
        "AVGO",
        "ORCL",
        "CRM",
        "QCOM",
        "MU",
        "PLTR",
    ],
    "Financials": [
        "JPM",
        "V",
        "MA",
        "BAC",
        "GS",
        "MS",
        "AXP",
        "PYPL",
        "COIN",
        "HOOD",
    ],
    "Consumer/Growth": [
        "AMZN",
        "TSLA",
        "META",
        "GOOGL",
        "NFLX",
        "SBUX",
        "ABNB",
        "SHOP",
        "DKNG",
        "MARA",
    ],
    "Energy & Materials": [
        "XOM",
        "CVX",
        "SLB",
        "COP",
        "MPC",
        "LIN",
        "APD",
        "FCX",
        "NEM",
        "VMC",
    ],
    "Industrials": [
        "GE",
        "CAT",
        "RTX",
        "HON",
        "UNP",
        "LMT",
        "UPS",
        "BA",
        "DE",
        "GEHC",
    ],
    "Defensives": [
        "PG",
        "COST",
        "PEP",
        "KO",
        "WMT",
        "NEE",
        "SO",
        "DUK",
        "CEG",
        "EXC",
    ],
    "Healthcare": [
        "LLY",
        "UNH",
        "JNJ",
        "ABBV",
        "MRK",
        "TMO",
        "AMGN",
        "ISRG",
        "PFE",
        "GILD",
    ],
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
        m = flatten_df(
            yf.download(
                ticker,
                period="6mo",
                interval="1mo",
                progress=False,
                auto_adjust=True,
            )
        )
        w = flatten_df(
            yf.download(
                ticker,
                period="1mo",
                interval="1wk",
                progress=False,
                auto_adjust=True,
            )
        )
        d = flatten_df(
            yf.download(
                ticker,
                period="1mo",
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
        )
        if m.empty or w.empty or d.empty:
            return None

        curr_price = float(d["Close"].iloc[-1])
        m_open = float(m["Open"].iloc[-1])
        m_prev_low = float(m["Low"].iloc[-2])
        m_prev_high = float(m["High"].iloc[-2])
        is_m_2d = float(m["Low"].iloc[-1]) < m_prev_low

        m_dir = "UP" if curr_price > m_open else "DOWN"
        w_dir = "UP" if curr_price > w["Open"].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d["Open"].iloc[-1] else "DOWN"

        grade, summary = get_grade(m_dir, w_dir, d_dir, is_m_2d)
        room = ((m_prev_high - curr_price) / curr_price) * 100

        return {
            "Grade": grade,
            "Ticker": ticker,
            "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}",
            "Summary": summary,
            "Room (%)": round(room, 2),
            "Sector": sector,
        }
    except Exception:
        return None


def scan_unusual_options(
    ticker,
    min_vol=500,
    min_vol_oi=2.0,
    min_dte=15,
    max_dte=60,
    max_moneyness_pct=15.0,
):
    try:
        tk = yf.Ticker(ticker)

        # Get live or latest underlying price
        fast_info = tk.fast_info
        underlying_price = float(
            fast_info.last_price
            if hasattr(fast_info, "last_price") and fast_info.last_price
            else 0
        )
        if underlying_price == 0:
            hist = tk.history(period="1d")
            if not hist.empty:
                underlying_price = float(hist["Close"].iloc[-1])
        if underlying_price == 0:
            return []

        all_expirations = tk.options
        if not all_expirations:
            return []

        today = datetime.now().date()
        valid_expirations = []
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
                df["volume"] = df["volume"].fillna(0).astype(int)
                df["openInterest"] = df["openInterest"].fillna(0).astype(int)
                df["bid"] = df.get("bid", 0.0).fillna(0.0).astype(float)
                df["ask"] = df.get("ask", 0.0).fillna(0.0).astype(float)
                df["lastPrice"] = (
                    df.get("lastPrice", 0.0).fillna(0.0).astype(float)
                )
                df["impliedVolatility"] = (
                    df.get("impliedVolatility", 0.0).fillna(0.0).astype(float)
                )

                # Minimum volume floor
                active = df[df["volume"] >= min_vol].copy()
                if active.empty:
                    continue

                for _, r in active.iterrows():
                    strike = float(r["strike"])
                    pct_from_money = (
                        (strike - underlying_price) / underlying_price
                    ) * 100

                    # Discard deep ITM/OTM noise
                    if abs(pct_from_money) > max_moneyness_pct:
                        continue

                    # Eliminate dead IV misprints
                    iv = round(r["impliedVolatility"] * 100, 2)
                    if iv < 10.0:
                        continue

                    vol = int(r["volume"])
                    oi = int(r["openInterest"])
                    vol_oi = (
                        round(vol / oi, 2) if oi > 0 else round(float(vol), 2)
                    )

                    if vol_oi < min_vol_oi:
                        continue

                    last = r["lastPrice"]
                    bid = r["bid"]
                    ask = r["ask"]

                    # Determine initiation side based on NBBO execution
                    if ask > 0 and last >= ask:
                        side = "BUY (At/Above Ask)"
                        bias = "BULLISH" if opt_type == "CALL" else "BEARISH"
                    elif bid > 0 and last <= bid:
                        side = "SELL (At/Below Bid)"
                        bias = "BEARISH" if opt_type == "CALL" else "BULLISH"
                    else:
                        side = "MID / SPREAD"
                        bias = "NEUTRAL"

                    # Moneyness tag
                    if opt_type == "CALL":
                        m_state = "OTM" if strike > underlying_price else "ITM"
                    else:
                        m_state = "OTM" if strike < underlying_price else "ITM"

                    rows.append({
                        "Ticker": ticker,
                        "Type": opt_type,
                        "Strike": strike,
                        "Stock Price": round(underlying_price, 2),
                        "Moneyness": f"{m_state} ({abs(pct_from_money):.1f}%)",
                        "Side": side,
                        "Directional Bias": bias,
                        "Expiry": exp,
                        "DTE": dte,
                        "Volume": vol,
                        "Open Int": oi,
                        "Vol / OI": vol_oi,
                        "Est Flow ($)": round(vol * last * 100, 2),
                        "IV (%)": iv,
                    })
        return rows
    except Exception:
        return []


tab_sniper, tab_flow, tab_squeeze, tab_options = st.tabs([
    "🎯 Strat Universal Sniper",
    "🌊 Sector Money Flow",
    "💥 TTM Squeeze & Probs",
    "⚡ Unusual Options",
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
            aplus = df[df["Grade"] == "A+"]
            if not aplus.empty:
                st.table(aplus.sort_values(by="Room (%)", ascending=False))
            else:
                st.info("No A+ Failed 2D Monthly setups detected right now.")
            with st.expander("📈 Tier A (Clean Trends)", expanded=True):
                st.table(
                    df[df["Grade"] == "A"].sort_values(
                        by="Room (%)", ascending=False
                    )
                )

# --- TAB 2: SECTOR FLOW & ROTATION ---
with tab_flow:
    st.title("🌊 Institutional Sector Rotation & Money Flow")
    st.caption(
        "Tracks Relative Strength (RS) vs. SPY across 1W, 1M, and 3M horizons to spot early capital rotation."
    )

    if st.button("🔍 Analyze Sector Rotation"):
        sector_etfs = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLE": "Energy",
            "XLV": "Healthcare",
            "XLY": "Consumer Disc",
            "XLI": "Industrials",
            "XLC": "Communications",
            "XLP": "Consumer Staples",
            "XLB": "Materials",
            "XLRE": "Real Estate",
            "XLU": "Utilities",
        }

        tickers_to_pull = list(sector_etfs.keys()) + ["SPY"]
        raw = yf.download(
            tickers_to_pull, period="7mo", progress=False, auto_adjust=True
        )["Close"]
        data = flatten_df(raw)

        # Calculate RS Ratio (Sector / SPY)
        rs_ratios = data[list(sector_etfs.keys())].div(data["SPY"], axis=0)

        flow_1w = (rs_ratios.pct_change(5).iloc[-1]) * 100
        flow_1m = (rs_ratios.pct_change(21).iloc[-1]) * 100
        flow_3m = (rs_ratios.pct_change(63).iloc[-1]) * 100

        # 21 EMA check on each Sector ETF
        ema21 = data[list(sector_etfs.keys())].ewm(span=21, adjust=False).mean()

        flow_results = []
        for t, name in sector_etfs.items():
            w_val = float(flow_1w[t])
            m_val = float(flow_1m[t])
            q_val = float(flow_3m[t])
            spot_etf = float(data[t].iloc[-1])
            ema_val = float(ema21[t].iloc[-1])
            above_21 = spot_etf > ema_val

            # Rotation Stage Classification
            if m_val > 0 and w_val > 0:
                stage = "🟢 LEADING (Inflow)"
            elif m_val <= 0 and w_val > 0:
                stage = "🚀 IMPROVING (Early Turn)"
            elif m_val > 0 and w_val <= 0:
                stage = "🟡 WEAKENING (Profit Taking)"
            else:
                stage = "🔴 LAGGING (Outflow)"

            flow_results.append({
                "Ticker": t,
                "Sector": name,
                "Rotation Stage": stage,
                "Spot": round(spot_etf, 2),
                "Above 21 EMA": "✅ Yes" if above_21 else "❌ No",
                "1W RS (%)": round(w_val, 2),
                "1M RS (%)": round(m_val, 2),
                "3M RS (%)": round(q_val, 2),
                "RS Accel (1W vs 1M)": round(w_val - (m_val / 4.0), 2),
            })

        flow_df = pd.DataFrame(flow_results).sort_values(
            by="1M RS (%)", ascending=False
        )

        # Top Highlight Metrics
        top_leader = flow_df.iloc[0]
        fastest_turn = flow_df.sort_values(by="1W RS (%)", ascending=False).iloc[
            0
        ]

        m1, m2, m3 = st.columns(3)
        m1.metric(
            "🏆 #1 Monthly Leader",
            f"{top_leader['Ticker']} ({top_leader['Sector']})",
            f"{top_leader['1M RS (%)']:+.2f}% vs SPY",
        )
        m2.metric(
            "⚡ #1 Weekly Surge",
            f"{fastest_turn['Ticker']} ({fastest_turn['Sector']})",
            f"{fastest_turn['1W RS (%)']:+.2f}% (1W RS)",
        )
        m3.metric(
            "📊 Sectors Above 21 EMA",
            f"{(flow_df['Above 21 EMA'] == '✅ Yes').sum()} / {len(flow_df)}",
            "Broad Market Breadth",
        )

        # RRG-Style Scatter Chart (1M RS vs 1W RS Momentum)
        st.subheader("🧭 Relative Rotation Map (1M Trend vs. 1W Momentum)")
        st.scatter_chart(
            flow_df,
            x="1M RS (%)",
            y="1W RS (%)",
            color="Rotation Stage",
            size=120,
            use_container_width=True,
        )

        # Detailed Data Table
        st.subheader("📋 Full Sector Breakdown")
        st.dataframe(
            flow_df.style.format({
                "Spot": "${:.2f}",
                "1W RS (%)": "{:+.2f}%",
                "1M RS (%)": "{:+.2f}%",
                "3M RS (%)": "{:+.2f}%",
                "RS Accel (1W vs 1M)": "{:+.2f}%",
            }),
            width="stretch",
            hide_index=True,
        )

# --- TAB 3: TTM SQUEEZE & PROBABILITIES ---
with tab_squeeze:
    st.title("💥 TTM Squeeze & 30D Probability Scanner")
    st.caption(
        "Combines 10/21 EMA trend structure, TTM Linear Regression acceleration, and forward 80%/50% probability target shelves."
    )

    sq_col1, sq_col2 = st.columns([1, 2])
    with sq_col1:
        horizon_days = st.selectbox(
            "Probability Horizon (Trading Days)", [15, 30, 45], index=1
        )
    with sq_col2:
        sq_universe = st.selectbox(
            "Sector Universe",
            ["All Watchlist"] + list(SECTORS.keys()),
            index=0,
        )

    if st.button("🔍 Scan for A+ Squeeze Setups"):
        results = []
        if sq_universe == "All Watchlist":
            scan_tickers = [t for sublist in SECTORS.values() for t in sublist]
        else:
            scan_tickers = SECTORS[sq_universe]

        bar = st.progress(0)
        for i, t in enumerate(scan_tickers):
            row = calculate_ttm_squeeze(t, trading_days_ahead=horizon_days)
            if row is not None:
                results.append(row)
            bar.progress((i + 1) / len(scan_tickers))

        if results:
            sq_df = pd.DataFrame(results)

            # Rename target columns dynamically to match selected trading-day horizon
            col_80 = f"{horizon_days}D 80% Tgt"
            col_50 = f"{horizon_days}D 50% Tgt"
            col_fl = f"{horizon_days}D 50% Floor"
            sq_df = sq_df.rename(
                columns={
                    "30D 80% Tgt": col_80,
                    "30D 50% Tgt": col_50,
                    "30D 50% Floor": col_fl,
                }
            )

            fmt_dict = {
                "Spot": "${:.2f}",
                "Momentum": "{:.2f}",
                col_80: "${:.2f}",
                col_50: "${:.2f}",
                col_fl: "${:.2f}",
                "Dist 21EMA (%)": "{:+.2f}%",
                "80% Room (%)": "+{:.2f}%",
            }

            # 1. A+ Setups (Confirmed Alignment)
            aplus_sq = sq_df[
                sq_df["Grade"].isin(["A+ LONG", "A+ SHORT"])
            ].sort_values(by="80% Room (%)", ascending=False)
            st.subheader("💎 A+ Confirmed Setups (Aligned Structure + Momentum)")
            if not aplus_sq.empty:
                st.dataframe(
                    aplus_sq.style.format(fmt_dict),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info(
                    "No fully aligned A+ setups firing in this universe right now."
                )

            # 2. B Watchlist (Coiling / Yellow Hook Anticipation Setups)
            b_watch = sq_df[
                sq_df["Grade"] == "B WATCH (Coiling/Hook)"
            ].sort_values(by="80% Room (%)", ascending=False)
            st.subheader(
                "⚡ B-Tier Watchlist (Above 21 EMA + Coiling or Momentum Hook)"
            )
            if not b_watch.empty:
                st.dataframe(
                    b_watch.style.format(fmt_dict),
                    width="stretch",
                    hide_index=True,
                )

            # 3. Full Table
            with st.expander("View All Scanned Symbols"):
                st.dataframe(
                    sq_df.style.format(fmt_dict),
                    width="stretch",
                    hide_index=True,
                )

# --- TAB 4: UNUSUAL OPTIONS ACTIVITY ---
with tab_options:
    st.title("⚡ Directional Options Flow")
    st.caption(
        "Filters for buyer/seller aggression, moneyness within ±15%, and positive IV."
    )

    col1, col2 = st.columns(2)
    with col1:
        dte_range = st.slider(
            "Expiration Window (DTE)", min_value=7, max_value=90, value=(15, 45)
        )
    with col2:
        target_group = st.selectbox(
            "Universe to Scan",
            [
                "Technology",
                "Market Pillars & Metals",
                "Consumer/Growth",
                "Financials",
                "Energy & Materials",
                "Industrials",
                "Defensives",
                "Healthcare",
                "All Watchlist",
            ],
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        min_contracts = st.number_input(
            "Min Volume (Contracts)", min_value=100, value=500, step=100
        )
    with col4:
        vol_oi_threshold = st.number_input(
            "Min Vol / OI Ratio", min_value=1.0, value=2.0, step=0.5
        )
    with col5:
        min_dollar_flow = st.number_input(
            "Min Estimated Flow ($)", min_value=0, value=50000, step=25000
        )

    if st.button("🔥 Scan Directional Flow"):
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
                max_dte=dte_range[1],
                max_moneyness_pct=15.0,
            )
            if hits:
                opt_results.extend(hits)
            bar.progress((idx + 1) / len(scan_list))
            time.sleep(0.05)

        if opt_results:
            flow_df = pd.DataFrame(opt_results)
            flow_df = flow_df[
                flow_df["Est Flow ($)"] >= min_dollar_flow
            ].sort_values(by="Est Flow ($)", ascending=False)

            if not flow_df.empty:
                bullish = flow_df[flow_df["Directional Bias"] == "BULLISH"]
                bearish = flow_df[flow_df["Directional Bias"] == "BEARISH"]
                neutral = flow_df[flow_df["Directional Bias"] == "NEUTRAL"]

                st.write(
                    "### 🚀 High-Conviction Bullish Flow (Bought Calls or Sold Puts)"
                )
                if not bullish.empty:
                    st.dataframe(
                        bullish.style.format({
                            "Est Flow ($)": "${:,.0f}",
                            "Strike": "${:.2f}",
                            "Stock Price": "${:.2f}",
                        }),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info("No aggressive bullish flow detected.")

                st.write(
                    "### 🩸 High-Conviction Bearish Flow (Bought Puts or Sold Calls)"
                )
                if not bearish.empty:
                    st.dataframe(
                        bearish.style.format({
                            "Est Flow ($)": "${:,.0f}",
                            "Strike": "${:.2f}",
                            "Stock Price": "${:.2f}",
                        }),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info("No aggressive bearish flow detected.")

                with st.expander("Midpoint / Spread Flow (Uncertain Direction)"):
                    if not neutral.empty:
                        st.dataframe(
                            neutral.style.format({
                                "Est Flow ($)": "${:,.0f}",
                                "Strike": "${:.2f}",
                                "Stock Price": "${:.2f}",
                            }),
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.write("No midpoint flow recorded.")
            else:
                st.warning(
                    "Found contracts with elevated Vol/OI, but none met your Minimum Flow ($) threshold within ±15% of spot price."
                )
        else:
            st.warning("No contracts met the criteria in this expiration range.")
