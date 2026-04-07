import yfinance as yf
import pandas as pd
import numpy as np

def professional_scanner(tickers):
    results = []
    
    for ticker in tickers:
        try:
            # Download 6 months of data for moving average stability
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if len(df) < 50: continue

            # 1. Technical Indicators
            df['8EMA'] = df['Close'].ewm(span=8, adjust=False).mean()
            df['21EMA'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['50SMA'] = df['Close'].rolling(window=50).mean()
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
            
            # 2. Logic Definitions
            last_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            ema21 = df['21EMA'].iloc[-1]
            sma50 = df['50SMA'].iloc[-1]
            curr_vol = df['Volume'].iloc[-1]
            avg_vol = df['Vol_Avg'].iloc[-1]

            # 3. The Setup Criteria (The "Desk" Filter)
            is_uptrend = last_close > sma50  # Long term trend is up
            is_near_ema21 = abs(last_close - ema21) / ema21 < 0.02 # Within 2% of 21EMA
            low_volume = curr_vol < avg_vol # Institutional "dry up"
            
            # Reversal Candle (Hammer or Inside Day)
            is_hammer = (df['High'].iloc[-1] - df['Low'].iloc[-1]) > 3 * abs(df['Open'].iloc[-1] - last_close)
            is_inside_day = (df['High'].iloc[-1] < df['High'].iloc[-2]) and (df['Low'].iloc[-1] > df['Low'].iloc[-2])

            if is_uptrend and is_near_ema21 and (is_hammer or is_inside_day):
                # Scoring System (0-10)
                score = 5 # Base score for meeting criteria
                if low_volume: score += 2
                if last_close > df['8EMA'].iloc[-1]: score += 2
                if is_inside_day and is_hammer: score += 1
                
                results.append({
                    "Ticker": ticker,
                    "Price": round(last_close, 2),
                    "Score": score,
                    "Setup": "Hammer" if is_hammer else "Inside Day",
                    "StopLoss": round(df['Low'].iloc[-1] * 0.99, 2),
                    "Target1": round(last_close + (last_close - (df['Low'].iloc[-1] * 0.99)), 2)
                })
        except Exception as e:
            continue
            
    return pd.DataFrame(results).sort_values(by="Score", ascending=False)

# Example Desk Watchlist
watchlist = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOGL", "AMZN", "META"]
scan_report = professional_scanner(watchlist)
print(scan_report)
