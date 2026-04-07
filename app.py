import yfinance as yf
import pandas as pd
import numpy as np

def get_desk_report(watchlist):
    """
    Professional Swing Trading Scanner
    Strategy: Institutional Re-entry (Pullback to 21EMA in Uptrend)
    """
    results = []
    
    print(f"--- Scanning {len(watchlist)} Tickers for Desk Setups ---")

    for ticker in watchlist:
        try:
            # Fetch 7 months to ensure 200-day SMA stability
            df = yf.download(ticker, period="7mo", interval="1d", progress=False)
            
            if df.empty or len(df) < 50:
                continue

            # Fix for yfinance Multi-Index columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- Technical Indicators ---
            df['8EMA'] = df['Close'].ewm(span=8, adjust=False).mean()
            df['21EMA'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['50SMA'] = df['Close'].rolling(window=50).mean()
            df['200SMA'] = df['Close'].rolling(window=200).mean()
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()

            # Current Data Points
            price = float(df['Close'].iloc[-1])
            ema8 = float(df['8EMA'].iloc[-1])
            ema21 = float(df['21EMA'].iloc[-1])
            sma50 = float(df['50SMA'].iloc[-1])
            sma200 = float(df['200SMA'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Vol_Avg'].iloc[-1])

            # --- Professional Logic Gates ---
            # 1. Trend Quality: Price > 50SMA > 200SMA
            is_uptrend = price > sma50 and sma50 > sma200
            
            # 2. Mean Reversion Zone: Price is within 2.5% of the 21EMA
            in_buy_zone = abs(price - ema21) / ema21 < 0.025
            
            # 3. Volume Exhaustion: Current volume is lower than 20-day average
            vol_dry_up = curr_vol < avg_vol

            if is_uptrend and in_buy_zone:
                # --- Scoring Engine (Rating 1-10) ---
                score = 5  # Base score for trend + pullback
                
                if vol_dry_up: score += 2
                if price > ema8: score += 2 # Recovering momentum
                if price > df['Close'].iloc[-2]: score += 1 # Positive day
                
                # Risk Metrics
                stop_loss = round(ema21 * 0.965, 2) # 3.5% buffer below EMA
                risk_per_share = price - stop_loss
                target_1 = round(price + (risk_per_share * 1.5), 2) # 1.5R Reward

                results.append({
                    "Ticker": ticker,
                    "Price": round(price, 2),
                    "Score": score,
                    "Rating": "A+" if score >= 9 else "B" if score >= 7 else "C",
                    "Stop_Loss": stop_loss,
                    "Target_1R": target_1,
                    "Volume_Status": "Dry" if vol_dry_up else "Elevated"
                })

        except Exception as e:
            print(f"Skipping {ticker}: Data Error")
            continue

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values(by="Score", ascending=False)

def calculate_position(price, stop, account_value=100000, risk_pct=0.01):
    """Calculates how many shares to buy based on 1% total account risk."""
    total_risk_dollars = account_value * risk_pct
    risk_per_share = price - stop
    if risk_per_share <= 0: return 0
    return int(total_risk_dollars / risk_per_share)

# --- EXECUTION ---
# Desk Watchlist (Focus on high-liquidity leaders)
watchlist = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOGL", "AMZN", "META", 
    "NFLX", "AVGO", "ORCL", "COST", "SMCI", "UBER", "PANW"
]

report = get_desk_report(watchlist)

if report.empty:
    print("\n[REPORT] No setups found. Market is likely overextended or in a correction. Stay in Cash.")
else:
    print("\n--- OFFICIAL DESK TRADING REPORT ---")
    print(report.to_string(index=False))
    
    print("\n--- SAMPLE POSITION SIZING (Risk 1% on $100k Account) ---")
    top_pick = report.iloc[0]
    shares = calculate_position(top_pick['Price'], top_pick['Stop_Loss'])
    print(f"Top Pick: {top_pick['Ticker']} | Suggested Size: {shares} shares")
