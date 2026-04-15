import yfinance as yf
import pandas as pd
import numpy as np

def get_squeeze_data(df):
    """Calculates TTM Squeeze, 21 EMA, and Momentum."""
    if df is None or len(df) < 25: return None # Ensure we have enough data
    
    length = 20
    # Calculations
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    m_avg = df['Close'].rolling(window=length).mean()
    m_std = df['Close'].rolling(window=length).std()
    
    df['bb_upper'] = m_avg + (2.0 * m_std)
    df['bb_lower'] = m_avg - (2.0 * m_std)
    
    true_range = pd.concat([
        df['High'] - df['Low'],
        np.abs(df['High'] - df['Close'].shift()),
        np.abs(df['Low'] - df['Close'].shift())
    ], axis=1).max(axis=1)
    atr = true_range.rolling(window=length).mean()
    
    df['kc_upper'] = m_avg + (1.5 * atr)
    df['kc_lower'] = m_avg - (1.5 * atr)
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    
    highest_h = df['High'].rolling(window=length).max()
    lowest_l = df['Low'].rolling(window=length).min()
    m_avg_hlo = (highest_h + lowest_l + m_avg) / 3
    df['momentum'] = (df['Close'] - m_avg_hlo).rolling(window=length).mean()
    
    return df.iloc[-1]

def calculate_dual_squeeze(ticker):
    try:
        # Pull 1D and 1H (to resample to 4H)
        d_data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        # We need at least 100 hours of data to get 25 reliable 4H bars
        h1_data = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if d_data.empty or h1_data.empty: return None

        # Standardize columns (handles MultiIndex if it exists)
        for d in [d_data, h1_data]:
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)

        # Resample 1h to 4h
        h4_data = h1_data.resample('4H').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
        }).dropna()

        d_res = get_squeeze_data(d_data)
        h4_res = get_squeeze_data(h4_data)

        if d_res is None or h4_res is None: return None

        price = float(d_res['Close'])
        direction = "Neutral"
        if price > d_res['ema21'] and d_res['momentum'] > 0: direction = "Bullish"
        elif price < d_res['ema21'] and d_res['momentum'] < 0: direction = "Bearish"

        return {
            "ticker": ticker,
            "d_squeeze": d_res['squeeze_on'],
            "h4_squeeze": h4_res['squeeze_on'],
            "d_momentum": d_res['momentum'],
            "h4_momentum": h4_res['momentum'],
            "direction": direction,
            "price": price
        }
    except Exception as e:
        print(f"Error scanning {ticker}: {e}")
        return None
