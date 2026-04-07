import yfinance as yf
import pandas as pd

def professional_scanner(tickers):
    results = []
    
    # Check Market Regime first (Don't swim against the tide)
    spy = yf.download("SPY", period="5d", progress=False)
    market_trend = "Bullish" if spy['Close'].iloc[-1].values[0] > spy['Close'].iloc[-5].values[0] else "Caution"
    
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if df.empty or len(df) < 50: continue

            # Flatten columns (yfinance sometimes returns multi-index)
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

            # Indicators
            df['8EMA'] = df['Close'].ewm(span=8, adjust=False).mean()
            df['21EMA'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['50SMA'] = df['Close'].rolling(window=50).mean()
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
            
            last_close = float(df['Close'].iloc[-1])
            ema21 = float(df['21EMA'].iloc[-1])
            sma50 = float(df['50SMA'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Vol_Avg'].iloc[-1])

            # Logic
            is_uptrend = last_close > sma50
            near_21ema = abs(last_close - ema21) / ema21 < 0.03 # 3% cushion
            vol_dry_up = curr_vol < (avg_vol * 1.1) # Within 10% of average or lower

            if is_uptrend and near_21ema:
                score = 6 # Base Score
                if vol_dry_up: score += 2
                if market_trend == "Bullish": score += 2
                
                results.append({
                    "Ticker": ticker,
                    "Price": round(last_close, 2),
                    "Score": score,
                    "Trend": market_trend,
                    "Stop": round(ema21 * 0.97, 2)
                })
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")
            continue
            
    if not results:
        return pd.DataFrame(columns=["Ticker", "Price", "Score", "Trend", "Stop"])
        
    return pd.DataFrame(results).sort_values(by="Score", ascending=False)

# Broaden your watchlist to ensure the scanner finds liquidity
watchlist = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOGL", "AMZN", "META", "NFLX", "AVGO"]
report = professional_scanner(watchlist)

if report.empty:
    print("--- SCAN COMPLETE: NO QUALIFIED SETUPS ---")
else:
    print("--- TOP DESK PICKS ---")
    print(report)
