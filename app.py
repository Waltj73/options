# app.py
import math
import streamlit as st

st.set_page_config(page_title="Trading Calculator", layout="centered")

st.title("📈 Trading Calculator (Basic)")
st.caption("Enter entry, stop, and risk to calculate size, total cost, and risk metrics.")

# --- Inputs ---
col1, col2 = st.columns(2)

with col1:
    side = st.selectbox("Side", ["Long", "Short"])
    entry = st.number_input("Entry Price", min_value=0.0, value=100.00, step=0.01, format="%.2f")
    stop = st.number_input("Stop Price", min_value=0.0, value=98.00, step=0.01, format="%.2f")

with col2:
    risk_dollars = st.number_input("Max Risk ($)", min_value=0.0, value=200.00, step=10.0, format="%.2f")
    target = st.number_input("Target Price (optional)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    round_down = st.checkbox("Round size down to whole shares", value=True)

st.divider()

# --- Calculations ---
def calc_risk_per_share(side: str, entry: float, stop: float) -> float:
    if side == "Long":
        return entry - stop
    else:
        return stop - entry

risk_per_share = calc_risk_per_share(side, entry, stop)

# Validate
if entry <= 0:
    st.error("Entry price must be greater than 0.")
    st.stop()

if stop <= 0:
    st.error("Stop price must be greater than 0.")
    st.stop()

if risk_dollars <= 0:
    st.error("Max Risk ($) must be greater than 0.")
    st.stop()

if risk_per_share <= 0:
    st.error(
        "Stop is on the wrong side of entry for the selected direction.\n\n"
        "For Long: stop must be below entry.\n"
        "For Short: stop must be above entry."
    )
    st.stop()

raw_size = risk_dollars / risk_per_share
size = math.floor(raw_size) if round_down else raw_size

total_cost = size * entry  # for shares; for short it's still notional value
total_risk = size * risk_per_share

# Target math
profit_per_share = None
r_multiple = None
expected_profit = None

if target and target > 0:
    if side == "Long":
        profit_per_share = target - entry
    else:
        profit_per_share = entry - target

    if profit_per_share is not None and profit_per_share > 0:
        expected_profit = profit_per_share * size
        r_multiple = profit_per_share / risk_per_share

# --- Output ---
c1, c2, c3 = st.columns(3)
c1.metric("Risk / Share", f"${risk_per_share:,.2f}")
c2.metric("Position Size", f"{size:,.0f}" if round_down else f"{size:,.2f}")
c3.metric("Total Risk", f"${total_risk:,.2f}")

c4, c5 = st.columns(2)
c4.metric("Total Cost (Notional)", f"${total_cost:,.2f}")
c5.metric("Entry → Stop Move", f"{(risk_per_share / entry) * 100:,.2f}%")

st.divider()

if target and target > 0:
    if profit_per_share is None or profit_per_share <= 0:
        st.warning("Target is not in the profitable direction for the selected side.")
    else:
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Profit / Share", f"${profit_per_share:,.2f}")
        cc2.metric("R Multiple", f"{r_multiple:,.2f}R")
        cc3.metric("Profit at Target", f"${expected_profit:,.2f}")

st.caption("Note: For options/futures, you can adapt size to contract multipliers and margin rules.")

st.divider()
st.subheader("Trade Quality Check")

# Minimum acceptable R
min_r_required = st.number_input(
    "Minimum R Required",
    value=2.0,
    step=0.25
)

good_trade = True
reasons = []

# R multiple check
if r_multiple is not None:
    if r_multiple < min_r_required:
        good_trade = False
        reasons.append("Reward is too small vs risk.")
else:
    good_trade = False
    reasons.append("No valid profit target set.")

# Position size sanity check
if size <= 0:
    good_trade = False
    reasons.append("Position size invalid.")

# Stop distance %
stop_pct = (risk_per_share / entry) * 100
if stop_pct < 0.2:
    reasons.append("Stop may be too tight.")
if stop_pct > 10:
    reasons.append("Stop distance very large.")

# Final decision
if good_trade:
    st.success("✅ Trade meets your minimum criteria.")
else:
    st.error("❌ Trade does NOT meet criteria.")

if reasons:
    st.write("Notes:")
    for r in reasons:
        st.write("-", r)

