import streamlit as st
import pandas as pd
from squeeze import scan_ticker

SECTORS = {
    "Tech": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL"],
    "Fin": ["JPM", "V", "MA", "BAC", "GS", "PYPL"],
    "Def": ["PG", "COST", "PEP", "KO", "WMT", "AMGN", "LLY"]
}

st.title("🎯 Trend Sniper (EMA)")

if st.button("Run Scan"):
    results = []
    all_t = [t for sub in SECTORS.values() for t in sub]
    bar = st.progress(0)
    for i, t in enumerate(all_t):
        res = scan_ticker(t)
        if res: results.append(res)
        bar.progress((i+1)/len(all_t))
    
    if results:
        st.table(pd.DataFrame(results))
