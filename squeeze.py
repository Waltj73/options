import yfinance as yf
import pandas as pd
import numpy as np

def calculate_ttm_squeeze(ticker):
    try:
        # Pull 1D and 1H (1H is used to build the 4H timeframe)
        d_data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        h1_data = yf.download(ticker, period="1mo", interval="1h", progress=False, auto_adjust=True)
        
        if d_data.empty or h1_data.empty: return None

        # Fix MultiIndex columns if present
        for d in [d_data, h1_data]:
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)

        # Build 4H Data from 1H
        h4_data = h1_data.resample('4H').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
        }).dropna()

        def get_sq_metrics(df):
            if len(df) < 21: return None
            length = 20
            # 21 EMA for Trend Filtering
            df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
            
            # Bollinger Bands
            m_avg = df['Close'].rolling(window=length).mean()
            m_std = df['Close'].rolling(window=length).std()
            df['bb_u'], df['bb_l'] = m_avg + (2.0 * m_std), m_avg - (2.0 * m_std)
            
            # Keltner Channels (using ATR)
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            atr = tr.rolling(window=length).mean()
            df['kc_u'], df['kc_l'] = m_avg + (1.5 * atr), m_avg - (1.5 * atr)
            
            # Squeeze State: BB inside KC
            df['sq_on'] = (df['bb_u'] < df['kc_u']) & (df['bb_l'] > df['kc_l'])
            
            # TTM Momentum Histogram
            hlo = (df['High'].rolling(length).max() + df['Low'].rolling(length).min() + m_avg) / 3
            df['mom'] = (df['Close'] - hlo).rolling(window=length).mean()
            return df.iloc[-1]

        d_met = get_sq_metrics(d_data)
        h4_met = get_sq_metrics(h4_data)

        if d_met is None or h4_met is None: return None

        return {
            "squeeze_on": d_met['sq_on'],
            "h4_squeeze": h4_met['sq_on'],
            "momentum": d_met['mom'],
            "price": d_met['Close'],
            "ema21": d_met['ema21']
        }
    except Exception as e:
        return None
