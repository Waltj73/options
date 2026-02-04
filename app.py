import math
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from scipy.stats import norm


# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Put Credit Spread Selector (V1)", layout="wide")

RISK_FREE_RATE_DEFAULT = 0.045  # V1 constant; you can later pull from FRED/UST
TRADING_DAYS = 252


# =========================
# MATH / GREEKS
# =========================
def _safe_float(x, default=np.nan):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def bs_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
    # Guardrails
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return np.nan, np.nan
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_put_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    d1, _ = bs_d1_d2(S, K, T, r, sigma)
    if np.isnan(d1):
        return np.nan
    # European put delta
    return norm.cdf(d1) - 1.0


def prob_finish_above(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    P(S_T >= K) under lognormal/BSM assumptions.
    This equals N(d2) for strike K.
    """
    _, d2 = bs_d1_d2(S, K, T, r, sigma)
    if np.isnan(d2):
        return np.nan
    return float(norm.cdf(d2))


# =========================
# DATA
# =========================
@st.cache_data(ttl=60 * 15, show_spinner=False)
def get_underlying_and_hist(ticker: str, lookback_days: int = 365) -> Tuple[float, pd.Series]:
    t = yf.Ticker(ticker)
    hist = t.history(period=f"{lookback_days}d")
    if hist.empty:
        return np.nan, pd.Series(dtype=float)
    close = hist["Close"].dropna()
    S = float(close.iloc[-1])
    return S, close


def historical_vol(close: pd.Series, window: int = 20) -> float:
    if close is None or close.empty or len(close) < window + 2:
        return np.nan
    rets = np.log(close / close.shift(1)).dropna()
    hv = rets.rolling(window).std().iloc[-1] * math.sqrt(TRADING_DAYS)
    return float(hv)


@st.cache_data(ttl=60 * 15, show_spinner=False)
def get_expirations(ticker: str) -> List[str]:
    t = yf.Ticker(ticker)
    return list(t.options)


@st.cache_data(ttl=60 * 15, show_spinner=False)
def get_option_chain(ticker: str, expiry: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    t = yf.Ticker(ticker)
    chain = t.option_chain(expiry)
    calls = chain.calls.copy()
    puts = chain.puts.copy()
    return calls, puts


def parse_expiry(exp: str) -> date:
    return datetime.strptime(exp, "%Y-%m-%d").date()


def dte(exp: date) -> int:
    return (exp - date.today()).days


# =========================
# SPREAD BUILDER
# =========================
@dataclass
class Filters:
    dte_min: int
    dte_max: int
    short_delta_min: float  # absolute value (e.g., 0.10)
    short_delta_max: float  # absolute value (e.g., 0.20)
    min_oi: int
    min_vol: int
    max_spread_pct: float   # e.g. 0.15 = 15%


def mid_price(bid: float, ask: float, last: float) -> float:
    bid = _safe_float(bid, np.nan)
    ask = _safe_float(ask, np.nan)
    last = _safe_float(last, np.nan)
    if not np.isnan(bid) and not np.isnan(ask) and ask >= bid and (ask + bid) > 0:
        return float((bid + ask) / 2.0)
    return float(last) if not np.isnan(last) else np.nan


def spread_pct(bid: float, ask: float) -> float:
    bid = _safe_float(bid, np.nan)
    ask = _safe_float(ask, np.nan)
    m = mid_price(bid, ask, np.nan)
    if np.isnan(m) or m <= 0 or np.isnan(bid) or np.isnan(ask):
        return np.nan
    return float((ask - bid) / m)


def enrich_puts(
    puts: pd.DataFrame,
    S: float,
    T: float,
    r: float,
    sigma_fallback: float
) -> pd.DataFrame:
    df = puts.copy()

    # yfinance often provides "impliedVolatility" but it can be NaN.
    df["iv"] = df.get("impliedVolatility", np.nan).apply(lambda x: _safe_float(x, np.nan))
    df["iv_used"] = df["iv"].copy()
    df.loc[df["iv_used"].isna() | (df["iv_used"] <= 0), "iv_used"] = sigma_fallback

    df["mid"] = df.apply(lambda row: mid_price(row.get("bid"), row.get("ask"), row.get("lastPrice")), axis=1)
    df["spr_pct"] = df.apply(lambda row: spread_pct(row.get("bid"), row.get("ask")), axis=1)

    # Greeks/probabilities
    df["delta"] = df.apply(lambda row: bs_put_delta(S, row["strike"], T, r, row["iv_used"]), axis=1)
    df["abs_delta"] = df["delta"].abs()
    df["p_finish_above_strike"] = df.apply(lambda row: prob_finish_above(S, row["strike"], T, r, row["iv_used"]), axis=1)

    # Normalized liquidity helpers
    df["oi"] = df.get("openInterest", 0).fillna(0).astype(int)
    df["vol"] = df.get("volume", 0).fillna(0).astype(int)

    return df


def build_put_credit_spreads(
    puts_enriched: pd.DataFrame,
    S: float,
    risk_cap_dollars: float,
    width_choices: List[float],
    f: Filters
) -> pd.DataFrame:
    """
    Build PCS: sell higher strike put, buy lower strike put.
    """
    df = puts_enriched.copy()

    # Only OTM short puts (strike < S) for PCS
    df = df[df["strike"] < S].copy()

    # Filter liquidity basics
    df["pass_oi"] = df["oi"] >= f.min_oi
    df["pass_vol"] = df["vol"] >= f.min_vol
    df["pass_spread"] = (df["spr_pct"].notna()) & (df["spr_pct"] <= f.max_spread_pct)

    # Delta range filter (short leg)
    df["pass_delta"] = (df["abs_delta"] >= f.short_delta_min) & (df["abs_delta"] <= f.short_delta_max)

    shorts = df[df["pass_oi"] & df["pass_vol"] & df["pass_spread"] & df["pass_delta"]].copy()
    if shorts.empty:
        return pd.DataFrame()

    # index by strike for quick lookup
    by_strike = df.set_index("strike", drop=False)

    spreads = []
    for _, sh in shorts.iterrows():
        short_strike = float(sh["strike"])
        short_mid = float(sh["mid"]) if not np.isnan(sh["mid"]) else np.nan
        if np.isnan(short_mid) or short_mid <= 0:
            continue

        for w in width_choices:
            long_strike = short_strike - w
            if long_strike <= 0:
                continue

            if long_strike not in by_strike.index:
                continue

            lg = by_strike.loc[long_strike]
            long_mid = float(lg["mid"]) if not np.isnan(lg["mid"]) else np.nan
            if np.isnan(long_mid) or long_mid <= 0:
                continue

            credit = short_mid - long_mid
            if credit <= 0:
                continue

            width = short_strike - long_strike
            max_loss = (width * 100.0) - (credit * 100.0)
            if max_loss <= 0:
                continue
            if max_loss > risk_cap_dollars:
                continue

            breakeven = short_strike - credit
            # POP proxy: P(finish above short strike)
            pop = float(sh["p_finish_above_strike"])

            # Liquidity score (lower spread pct better; higher oi/vol better)
            sh_spr = float(sh["spr_pct"]) if not np.isnan(sh["spr_pct"]) else 999
            lg_spr = float(lg["spr_pct"]) if not np.isnan(lg["spr_pct"]) else 999
            liquidity = (
                (1.0 / (1.0 + sh_spr)) * 0.5 +
                (1.0 / (1.0 + lg_spr)) * 0.5
            )
            liquidity *= (math.log1p(int(sh["oi"])) + math.log1p(int(lg["oi"]))) / 2.0
            liquidity *= (math.log1p(int(sh["vol"])) + math.log1p(int(lg["vol"]))) / 2.0

            # Efficiency score
            credit_per_risk = (credit * 100.0) / max_loss

            spreads.append({
                "Short Strike": short_strike,
                "Long Strike": long_strike,
                "Width": width,
                "Short Mid": short_mid,
                "Long Mid": long_mid,
                "Credit": credit,
                "Max Loss ($)": max_loss,
                "Breakeven": breakeven,
                "Short Δ": float(sh["delta"]),
                "|Δ|": float(sh["abs_delta"]),
                "POP (P>=Short)": pop,
                "Short OI": int(sh["oi"]),
                "Short Vol": int(sh["vol"]),
                "Short Spr%": float(sh["spr_pct"]),
                "Long OI": int(lg["oi"]),
                "Long Vol": int(lg["vol"]),
                "Long Spr%": float(lg["spr_pct"]),
                "Credit/Risk": credit_per_risk,
                "Liquidity": liquidity,
            })

    out = pd.DataFrame(spreads)
    if out.empty:
        return out

    # Rank: prioritize liquidity + credit efficiency + higher POP
    out["Score"] = (
        0.45 * rank01(out["Liquidity"]) +
        0.35 * rank01(out["Credit/Risk"]) +
        0.20 * rank01(out["POP (P>=Short)"])
    )
    out = out.sort_values(["Score", "Liquidity", "Credit/Risk"], ascending=False).reset_index(drop=True)
    return out


def rank01(s: pd.Series) -> pd.Series:
    s = s.replace([np.inf, -np.inf], np.nan)
    if s.dropna().empty:
        return pd.Series([0.0] * len(s), index=s.index)
    lo = float(s.min(skipna=True))
    hi = float(s.max(skipna=True))
    if hi - lo < 1e-12:
        return pd.Series([0.5] * len(s), index=s.index)
    return (s - lo) / (hi - lo)


# =========================
# UI HELPERS
# =========================
def green_check(v: bool) -> str:
    return "✅" if bool(v) else ""


def style_checks(df: pd.DataFrame, check_cols: List[str]) -> pd.io.formats.style.Styler:
    def _style_cell(val):
        if val == "✅":
            return "color: #16a34a; font-weight: 700;"  # green-600
        return ""
    sty = df.style
    for c in check_cols:
        if c in df.columns:
            sty = sty.applymap(_style_cell, subset=[c])
    return sty


# =========================
# APP
# =========================
st.title("Put Credit Spread Selector — V1 (yfinance + Black–Scholes)")

with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Ticker", value="SPY").upper().strip()
    risk_cap = st.number_input("Max risk per trade ($)", min_value=50, max_value=5000, value=200, step=25)

    st.subheader("DTE")
    dte_min = st.slider("Min DTE", 1, 120, 30)
    dte_max = st.slider("Max DTE", 1, 180, 45)
    if dte_max < dte_min:
        dte_min, dte_max = dte_max, dte_min

    st.subheader("Short delta target (absolute)")
    delta_min = st.slider("Min |delta|", 0.01, 0.50, 0.10, step=0.01)
    delta_max = st.slider("Max |delta|", 0.01, 0.60, 0.20, step=0.01)
    if delta_max < delta_min:
        delta_min, delta_max = delta_max, delta_min

    st.subheader("Liquidity filters")
    min_oi = st.number_input("Min Open Interest", min_value=0, max_value=500000, value=200, step=50)
    min_vol = st.number_input("Min Volume", min_value=0, max_value=500000, value=50, step=10)
    max_spr = st.slider("Max bid/ask spread % (mid-based)", 0.01, 1.00, 0.15, step=0.01)

    st.subheader("Spread widths")
    widths = st.multiselect("Width choices ($)", options=[0.5, 1, 2, 3, 5, 10, 20], default=[1, 2, 3, 5])

    st.subheader("Model")
    r = st.number_input("Risk-free rate (r)", min_value=0.0, max_value=0.10, value=RISK_FREE_RATE_DEFAULT, step=0.005)
    hv_window = st.slider("HV window (days) for IV fallback", 10, 60, 20)

    top_n = st.slider("Show top N spreads", 5, 200, 50)

    run = st.button("Run Scan", type="primary")


if not run:
    st.info("Set your filters on the left, then click **Run Scan**.")
    st.stop()

# Underlying
with st.spinner("Loading underlying + history..."):
    S, close = get_underlying_and_hist(ticker, lookback_days=365)

if np.isnan(S) or close.empty:
    st.error("Could not load price/history. Check the ticker symbol.")
    st.stop()

hv = historical_vol(close, window=hv_window)

st.caption(f"Underlying **{ticker}** last price: **{S:.2f}** | HV({hv_window}) fallback: **{hv:.2%}**")

# Expirations in DTE range
exps = get_expirations(ticker)
if not exps:
    st.error("No expirations found.")
    st.stop()

exp_rows = []
for e in exps:
    ed = parse_expiry(e)
    days = dte(ed)
    if dte_min <= days <= dte_max:
        exp_rows.append((e, days))

if not exp_rows:
    st.warning("No expirations match your DTE range. Try widening DTE min/max.")
    st.stop()

exp_df = pd.DataFrame(exp_rows, columns=["Expiration", "DTE"]).sort_values("DTE")
st.write("### Matching expirations")
st.dataframe(exp_df, hide_index=True, use_container_width=True)

filters = Filters(
    dte_min=dte_min,
    dte_max=dte_max,
    short_delta_min=delta_min,
    short_delta_max=delta_max,
    min_oi=int(min_oi),
    min_vol=int(min_vol),
    max_spread_pct=float(max_spr),
)

# Build spreads across expirations
all_spreads = []
detail_blocks = []

for exp_str, days in exp_rows:
    T = max(days, 1) / 365.0

    with st.spinner(f"Loading chain for {exp_str}..."):
        _, puts = get_option_chain(ticker, exp_str)

    if puts is None or puts.empty:
        continue

    sigma_fallback = hv if not np.isnan(hv) and hv > 0 else 0.30  # last-resort fallback
    puts_enriched = enrich_puts(puts, S=S, T=T, r=r, sigma_fallback=sigma_fallback)

    # Add pass/fail columns with checks
    puts_enriched["Pass OI"] = puts_enriched["oi"].ge(filters.min_oi).apply(green_check)
    puts_enriched["Pass Vol"] = puts_enriched["vol"].ge(filters.min_vol).apply(green_check)
    puts_enriched["Pass Spr"] = puts_enriched["spr_pct"].le(filters.max_spread_pct).fillna(False).apply(green_check)
    puts_enriched["Pass |Δ|"] = puts_enriched["abs_delta"].between(filters.short_delta_min, filters.short_delta_max).fillna(False).apply(green_check)
    puts_enriched["OTM"] = (puts_enriched["strike"] < S).apply(green_check)

    # Spreads
    spreads = build_put_credit_spreads(
        puts_enriched=puts_enriched,
        S=S,
        risk_cap_dollars=float(risk_cap),
        width_choices=sorted([float(w) for w in widths]),
        f=filters
    )

    if spreads.empty:
        continue

    spreads.insert(0, "Expiration", exp_str)
    spreads.insert(1, "DTE", days)
    all_spreads.append(spreads)

    # Keep a small per-expiry detail view
    detail_blocks.append((exp_str, days, puts_enriched))

if not all_spreads:
    st.warning("No spreads found that match your filters + risk cap. Try: higher risk cap, wider delta range, looser liquidity, or more widths.")
    # show a helpful detail table for the first matching expiry
    exp_str, days = exp_rows[0]
    _, puts = get_option_chain(ticker, exp_str)
    T = max(days, 1) / 365.0
    sigma_fallback = hv if not np.isnan(hv) and hv > 0 else 0.30
    puts_enriched = enrich_puts(puts, S=S, T=T, r=r, sigma_fallback=sigma_fallback)
    st.write("### Debug view (puts chain sample)")
    sample = puts_enriched[["strike","bid","ask","mid","spr_pct","oi","vol","iv","iv_used","delta","abs_delta"]].sort_values("strike")
    st.dataframe(sample.tail(40), use_container_width=True, hide_index=True)
    st.stop()

final = pd.concat(all_spreads, ignore_index=True)

# Keep it readable
show_cols = [
    "Expiration","DTE",
    "Short Strike","Long Strike","Width",
    "Credit","Max Loss ($)","Breakeven",
    "Short Δ","|Δ|","POP (P>=Short)",
    "Short Spr%","Short OI","Short Vol",
    "Long Spr%","Long OI","Long Vol",
    "Credit/Risk","Score"
]
final = final[show_cols].copy()

# Format
final["Credit"] = final["Credit"].map(lambda x: round(x, 3))
final["Max Loss ($)"] = final["Max Loss ($)"].map(lambda x: round(x, 2))
final["Breakeven"] = final["Breakeven"].map(lambda x: round(x, 2))
final["Short Δ"] = final["Short Δ"].map(lambda x: round(x, 3))
final["|Δ|"] = final["|Δ|"].map(lambda x: round(x, 3))
final["POP (P>=Short)"] = final["POP (P>=Short)"].map(lambda x: round(x, 3))
final["Short Spr%"] = final["Short Spr%"].map(lambda x: round(x, 3))
final["Long Spr%"] = final["Long Spr%"].map(lambda x: round(x, 3))
final["Credit/Risk"] = final["Credit/Risk"].map(lambda x: round(x, 3))
final["Score"] = final["Score"].map(lambda x: round(x, 3))

st.write("## Top Put Credit Spreads (ranked)")
st.dataframe(final.head(top_n), use_container_width=True, hide_index=True)

with st.expander("Why these are ranked high (V1 scoring)"):
    st.markdown(
        """
- **Liquidity**: tight spreads + higher OI/volume on both legs  
- **Credit/Risk**: better premium efficiency  
- **POP proxy**: higher probability of finishing above the short strike (Black–Scholes lognormal assumption)  
        """.strip()
    )

st.write("## Chain detail (green check = passes filter)")
# Show one detail table for the best expiry from results
best_exp = final.iloc[0]["Expiration"]
best_block = None
for exp_str, days, pe in detail_blocks:
    if exp_str == best_exp:
        best_block = (exp_str, days, pe)
        break

if best_block:
    exp_str, days, pe = best_block
    st.caption(f"Detail for expiration **{exp_str}** (DTE={days}) — checks are based on your filters.")
    view = pe[[
        "contractSymbol","strike","bid","ask","mid","spr_pct","oi","vol",
        "iv","iv_used","delta","abs_delta","p_finish_above_strike",
        "OTM","Pass |Δ|","Pass OI","Pass Vol","Pass Spr"
    ]].sort_values("strike", ascending=False)

    # Convert to checkmarks for display columns already created
    check_cols = ["OTM","Pass |Δ|","Pass OI","Pass Vol","Pass Spr"]
    sty = style_checks(view.head(80), check_cols)

    st.dataframe(sty, use_container_width=True, hide_index=True)

st.warning(
    "V1 note: This uses yfinance chain data (can be delayed/incomplete) + Black–Scholes assumptions. "
    "For production-grade options selection, swap data source (Tradier/Polygon/ORATS/etc.) when you're ready."
)
