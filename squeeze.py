import yfinance as yf
import pandas as pd

def get_trend_data(df):
    if df is None or len(df) < 22: return None
    try:
        # Calculate 21 EMA
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # Keep Squeeze logic so you still see the "coiling" state
        m_avg = df['Close'].rolling(window=20).mean()
        m_std = df['Close'].rolling(window=20).std()
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        atr = tr.rolling(window=20).mean()
        
        bb_u, bb_l = m_avg + (2.0 * m_std), m_avg - (2.0 * m_std)
        kc_u, kc_l = m_avg + (1.5 * atr), m_avg - (1.5 * atr)
        
        squeeze = (bb_u < kc_u) and (bb_l > kc_l)
        last = df.iloc[-1]
        
        return {
            "price": round(float(last['Close']), 2),
            "ema": round(float(last['ema21']), 2),
            "squeeze": squeeze,
            "position": "ABOVE" if last['Close'] > last['ema21'] else "BELOW"
        }
    except: return None

def scan_ticker(ticker):
    try:
        d_data = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        h1_data = yf.download(ticker, period="15d", interval="1h", progress=False, auto_adjust=True)
        
        if d_data.empty or h1_data.empty: return None
        
        # Clean MultiIndex
        if isinstance(d_data.columns, pd.MultiIndex): d_data.columns = d_data.columns.get_level_values(0)
        if isinstance(h1_data.columns, pd.MultiIndex): h1_data.columns = h1_data.columns.get_level_values(0)
        
        h4_data = h1_data.resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        
        d_res = get_trend_data(d_data)
        h4_res = get_trend_data(h4_data)
        
        if not d_res or not h4_res: return None
        
        return {
            "Ticker": ticker,
            "D_Price": d_res['price'],
            "D_EMA": d_res['ema'],
            "D_Trend": d_res['position'],
            "D_Sq": "🔴" if d_res['squeeze'] else "🟢",
            "4H_Trend": h4_res['position'],
            "4H_Sq": "🔴" if h4_res['squeeze'] else "🟢"
        }
    except: return None
