import yfinance as yf
import pandas as pd
import warnings

# Suppress annoying background warnings
warnings.filterwarnings('ignore')

def professional_scanner(watchlist):
    results = []
    print(f"--- ACCESSING Y-FINANCE TERMINAL | SCANNING {len(watchlist)} TICKERS ---")

    for ticker in watchlist:
        try:
            # Download 1 year of data for SMA stability
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            if df.empty:
                continue

            # --- CRITICAL REPAIR BLOCK ---
            # Recent yfinance updates return Multi-Index columns. This flattens them.
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Ensure the index is a DatetimeIndex
            df.index = pd.to_datetime(df.index)
            # -----------------------------

            # Technical Indicators
            df['8EMA'] = df['Close'].ewm(span=8, adjust=False).mean()
            df['21EMA'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['50SMA'] = df['Close'].rolling(window=50).mean()
            df['200SMA'] = df['Close'].rolling(window=200).mean()
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()

            # Current Values
            price = float(df['Close'].iloc[-1])
            ema21 = float(df['21EMA'].iloc[-1])
            sma50 = float(df['50SMA'].iloc[-1])
            sma200 = float(df['200SMA'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Vol_Avg'].iloc[-1])

            # Logic Check
            is_uptrend = price > sma50 and sma50 > sma200
            near_ema21 = abs(price - ema21) / ema21 < 0.04 # 4% range
            
            # If the stock is in a healthy uptrend and near the 21EMA support...
            if is_uptrend and near_ema21:
                score = 7 # Starting score for quality uptrend
                if curr_vol < avg_vol: score += 2 # Institutional dry-up
                if price > df['8EMA'].iloc[-1]: score += 1 # Gaining momentum
                
                results.append({
                    "TICKER": ticker,
                    "PRICE": f"${price:.2f}",
                    "SCORE": f"{score}/10",
                    "RATING": "A+" if score >= 9 else "B",
                    "STOP": f"${(ema21 * 0.97):.2f}",
                    "VOL": "Low/Dry" if curr_vol < avg_vol else "Elevated"
                })

        except Exception as e:
            # Silently skip errors to keep the terminal clean
            continue

    return pd.DataFrame(results)

# 1. RUN THE SCAN
# Using a broader list to guarantee we find setups in today's market
watchlist = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOGL", "AMZN", "META", "AVGO", "NFLX", "COST", "SMCI"]
report = professional_scanner(watchlist)

# 2. OUTPUT TO CONSOLE
if report.empty:
    print("\n[DESK ALERT] No qualified setups found. Market may be overextended.")
    print("Action: Stay in Cash. Do not chase.")
else:
    print("\n--- OFFICIAL TRADING DESK REPORT ---")
    # Sort by score manually since Score is now a string for display
    print(report.to_string(index=False))

print("\n--- SCAN COMPLETE ---")
