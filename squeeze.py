import yfinance as yf
import pandas as pd

def calculate_ttm_squeeze(ticker):
    try:
        # Download Daily Data
        df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if df.empty: return None
        
        # Flatten columns if MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        length = 20
        # Bollinger Bands
        m_avg = df['Close'].rolling(window=length).mean()
        m_std = df['Close'].rolling(window=length).std()
        df['bb_u'] = m_avg + (2.0 * m_std)
        df['bb_l'] = m_avg - (2.0 * m_std)

        # Keltner Channels
        tr = pd.concat([df['High'] - df['Low'], 
                        abs(df['High'] - df['Close'].shift()), 
                        abs(df['Low'] - df['Close'].shift())], axis=1).max(axis=1)
        atr = tr.rolling(window=length).mean()
        df['kc_u'] = m_avg + (1.5 * atr)
        df['kc_l'] = m_avg - (1.5 * atr)

        # Squeeze State
        df['sq_on'] = (df['bb_u'] < df['kc_u']) & (df['bb_l'] > df['kc_l'])

        # Momentum (TTM Style)
        highest_high = df['High'].rolling(window=length).max()
        lowest_low = df['Low'].rolling(window=length).min()
        hlo = (highest_high + lowest_low + m_avg) / 3
        df['mom'] = (df['Close'] - hlo).rolling(window=length).mean()

        last = df.iloc[-1]
        return {
            "squeeze_on": last['sq_on'],
            "momentum": last['mom']
        }
    except:
        return None
