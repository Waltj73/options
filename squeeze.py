import yfinance as yf
import pandas as pd
import numpy as np

def get_squeeze_data(df):
    if df is None or len(df) < 25: return None
    
    length = 20
    # 21 EMA
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # Bollinger & Keltner
    m_avg = df['Close'].rolling(window=length).mean()
    m_std = df['Close'].rolling(window=length).std()
    df['bb_upper'] = m_avg + (2.0 * m_std)
    df['bb_lower'] = m_avg - (2.0 * m_std)
    
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=length).mean()
    df['kc_upper'] = m_avg + (1.5 * atr)
    df['kc_lower'] = m_avg - (1.5 * atr)
    
    # Squeeze & Momentum
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    avg_hlo = (df['High'].rolling(length).max() + df['Low'].rolling(length).min() + m_avg) / 3
    df['momentum'] = (df['Close'] - avg_hlo).rolling(window=length).mean()
    
    return df.iloc[-1]

def calculate_dual_squeeze(ticker):
    try:
        # Standardize data pull
        d_data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        h1_data = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if d_data.empty or h1_data.empty: return None

        for d in [d_data, h1_data]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)

        h4_data = h1_data.resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

        d_res = get_squeeze_data(d_data)
        h4_res = get_squeeze_data(h4_data)

        if d_res is None or h4_res is None: return None

        price, ema, mom = float(d_res['Close']), float(d_res['ema21']), float(d_res['momentum'])
        direction = "Bullish" if price > ema and mom > 0 else "Bearish" if price < ema and mom < 0 else "Neutral"

        return {
            "ticker": ticker, "d_sq": d_res['squeeze_on'], "h4_sq": h4_res['squeeze_on'],
            "d_mom": mom, "h4_mom": h4_res['momentum'], "dir": direction, "price": price
        }
    except: return None
