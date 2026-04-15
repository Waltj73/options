import yfinance as yf
import pandas as pd

def get_trend_data(df):
    if df is None or len(df) < 22: return None
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    last = df.iloc[-1]
    return {
        "price": round(float(last['Close']), 2),
        "ema": round(float(last['ema21']), 2),
        "trend": "ABOVE" if last['Close'] > last['ema21'] else "BELOW"
    }

def scan_ticker(ticker):
    try:
        d_data = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        h_data = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)
        if d_data.empty or h_data.empty: return None
        
        # Build 4H from 1H
        h4_data = h_data.resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        
        d_res = get_trend_data(d_data)
        h4_res = get_trend_data(h4_data)
        
        if not d_res or not h4_res: return None
        return {
            "Ticker": ticker,
            "Price": d_res['price'],
            "D_Trend": d_res['trend'],
            "4H_Trend": h4_res['trend']
        }
    except: return None
