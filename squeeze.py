import yfinance as yf
import pandas as pd
import numpy as np

def get_squeeze_data(df):
    if df.empty or len(df) < 25: return None
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    m_avg = df['Close'].rolling(window=20).mean()
    m_std = df['Close'].rolling(window=20).std()
    df['bb_u'], df['bb_l'] = m_avg + (2.0 * m_std), m_avg - (2.0 * m_std)
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=20).mean()
    df['kc_u'], df['kc_l'] = m_avg + (1.5 * atr), m_avg - (1.5 * atr)
    df['sq_on'] = (df['bb_u'] < df['kc_u']) & (df['bb_l'] > df['kc_l'])
    hlo_avg = (df['High'].rolling(20).max() + df['Low'].rolling(20).min() + m_avg) / 3
    df['momentum'] = (df['Close'] - hlo_avg).rolling(window=20).mean()
    return df.iloc[-1]

def calculate_dual_squeeze(ticker):
    try:
        d_data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        h1_data = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)
        if d_data.empty or h1_data.empty: return None
        for d in [d_data, h1_data]:
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        h4_data = h1_data.resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        d_res, h4_res = get_squeeze_data(d_data), get_squeeze_data(h4_data)
        if d_res is None or h4_res is None: return None
        price, ema = float(d_res['Close']), float(d_res['ema21'])
        direction = "Bullish" if price > ema and d_res['momentum'] > 0 else "Bearish" if price < ema and d_res['momentum'] < 0 else "Neutral"
        return {"ticker": ticker, "d_sq": d_res['sq_on'], "h4_sq": h4_res['sq_on'], "dir": direction, "price": price, "d_mom": d_res['momentum']}
    except: return None
