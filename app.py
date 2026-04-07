import yfinance as yf
import pandas as pd
import numpy as np
import warnings

# Clean console output
warnings.filterwarnings('ignore')

def get_master_desk_report(watchlist):
    """
    MASTER INSTITUTIONAL RE-ENTRY SYSTEM
    Core Logic: Price > 50SMA > 200SMA | Pullback to 21EMA | Volume Dry-up
    """
    results = []
    
    print(f"--- INITIALIZING MASTER SCANNER | {len(watchlist)} ASSETS ---")

    for ticker in watchlist:
        try:
            # Download 1 year of daily data
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            if df.empty or len(df) < 200:
                continue

            # --- DATA REPAIR & FLATTENING ---
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index)

            # --- TECHNICAL CORE ---
            # Exponential Averages (Fast Momentum)
            df['8EMA'] = df['Close'].ewm(span=8, adjust=False).mean()
            df['21EMA'] = df['Close'].ewm(span=21, adjust=False).mean()
            
            # Simple Moving Averages (Institutional Baseline)
            df['50SMA'] = df['Close'].rolling(window=50).mean()
            df['200SMA'] = df['Close'].rolling(window=200).mean()
            
            # Volume Analysis
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()

            # --- DATA EXTRACTION (CURRENT vs PREVIOUS) ---
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = float(curr['Close'])
            ema21 = float(curr['21EMA'])
            sma50 = float(curr['50SMA'])
            sma200 = float(curr['200SMA'])
            curr_vol = float(curr['Volume'])
            avg_vol = float(curr['Vol_Avg'])

            # --- PROFESSIONAL LOGIC GATES ---
            # 1. Structural Integrity: Stock must be in a verified Stage 2 Uptrend
            is_uptrend = price > sma50 and sma50 > sma200
            
            # 2. Value Zone: Price is pulling back to the 21EMA 'Safety Net'
            # We look for price within 3% of the 21EMA
            near_21ema = abs(price - ema21) / ema21 < 0.03
            
            # 3. Strat Trigger: Checking for an "Inside Day" (Scenario 1)
            is_inside_day = (curr['High'] < prev['High']) and (curr['Low'] > prev['Low'])
            
            # 4. Volume Exhaustion: Sellers are getting tired
            low_vol = curr_vol < (avg_vol * 1.05)

            # --- THE SCORING ENGINE ---
            if is_uptrend and near_21ema:
                score = 5 # Baseline for Trend + Value
                
                if low_vol: score += 2        # Evidence of institutional holding
                if is_inside_day: score += 2  # The Strat 'Scenario 1' setup
                if price > curr['8EMA']: score += 1 # Recapturing short-term momentum
                
                # Risk/Reward Calculation
                stop = round(ema21 * 0.97, 2) # 3% cushion below the EMA floor
                risk = price - stop
                target = round(price + (risk * 2), 2) # 2:1 Reward to Risk ratio

                results.append({
                    "TICKER": ticker,
                    "PRICE": round(price, 2),
                    "SCORE": score,
                    "RATING": "A+" if score >= 9 else "B" if score >= 7 else "C",
                    "SETUP": "Inside Day" if is_inside_day else "Pullback",
                    "STOP": stop,
                    "TARGET_2R": target,
                    "VOL_STATUS": "Dry" if low_vol else "High"
                })

        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values(by="SCORE", ascending=False)

# --- WORKSTATION EXECUTION ---
# This list contains "Institutional Leaders" - stocks big money loves to defend at the 21EMA.
master_watchlist = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOGL", "AMZN", "META", 
    "NFLX", "AVGO", "ORCL", "COST", "SMCI", "UBER", "PANW", "QCOM", "PLTR"
]

report = get_master_desk_report(master_watchlist)

if report.empty:
    print("\n[REPORT] Market Condition: Overextended or Bearish. No Low-Risk entries found.")
    print("Action: Preserve Capital. Wait for the pullback to the 21-day EMA.")
else:
    print("\n--- MASTER INSTITUTIONAL RE-ENTRY REPORT ---")
    print(report.to_string(index=False))
    
    # Position Sizing Logic for the Top Pick
    top = report.iloc[0]
    print(f"\n--- EXECUTION GUIDE (TOP PICK: {top['TICKER']}) ---")
    print(f"Risking $500 on this trade? Buy {int(500 / (top['PRICE'] - top['STOP']))} shares.")
