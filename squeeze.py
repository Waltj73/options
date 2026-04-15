import yfinance as yf
import pandas as pd
import numpy as np

def get_squeeze_data(df):
    """Calculates TTM Squeeze, 21 EMA, and Momentum for a given dataframe."""
    if df.empty or len(df) < 22: return None
    
    length = 20
    mult_bb = 2.0
    mult_kc = 1.5

    # 1. EMA Calculation
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # 2. Bollinger Bands
    m_avg = df['Close'].rolling(window=length).mean()
    m_std = df['Close'].rolling(window=length).std()
    df['bb_upper'] = m_avg + (mult_bb * m_std)
    df['bb_lower'] = m_avg - (mult_bb * m_std)
    
    # 3. Keltner Channels (using ATR)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window=length).mean()
    
    df['kc_upper'] = m_avg + (mult_kc * atr)
    df['kc_lower'] = m_avg - (mult_kc * atr)

    # 4. Squeeze Logic (BB inside KC)
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    
    # 5. Momentum Histogram (Simplified TTM Version)
    highest_high = df['High'].rolling(window=length).max()
    lowest_low = df['Low'].rolling(window=length).min()
    m_avg_hlo = (highest_high + lowest_low + m_avg) / 3
    df['momentum'] = (df['Close'] - m_avg_hlo).rolling(window=length).mean()
    
    return df.iloc[-1]

def calculate_dual_squeeze(ticker):
    """Fetches 1D and 4H data to identify multi-timeframe alignment."""
    try:
        # Download Daily (1D) and Hourly (to resample to 4H)
        d_data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        h1_data = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if isinstance(d_data.columns, pd.MultiIndex): d_data.columns = d_data.columns.get_level_values(0)
        if isinstance(h1_data.columns, pd.MultiIndex): h1_data.columns = h1_data.columns.get_level_values(0)

        # Resample 1h to 4h
        h4_data = h1_data.resample('4H').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
        }).dropna()

        d_res = get_squeeze_data(d_data)
        h4_res = get_squeeze_data(h4_data)

        if d_res is None or h4_res is None: return None

        # Price vs EMA and Momentum Direction
        price = float(d_res['Close'])
        ema = float(d_res['ema21'])
        direction = "Neutral"
        if price > ema and d_res['momentum'] > 0: direction = "Bullish"
        elif price < ema and d_res['momentum'] < 0: direction = "Bearish"

        return {
            "ticker": ticker,
            "d_squeeze": d_res['squeeze_on'],
            "h4_squeeze": h4_res['squeeze_on'],
            "d_momentum": d_res['momentum'],
            "h4_momentum": h4_res['momentum'],
            "direction": direction,
            "price": price
        }
    except:
        return None
