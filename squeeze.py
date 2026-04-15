import yfinance as yf
import pandas as pd
import numpy as np

def calculate_ttm_squeeze(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if data.empty or len(data) < 20: return None

        length = 20
        mult_bb = 2.0
        mult_kc = 1.5

        # Bollinger Bands
        m_avg = data['Close'].rolling(window=length).mean()
        m_std = data['Close'].rolling(window=length).std()
        data['bb_upper'] = m_avg + (mult_bb * m_std)
        data['bb_lower'] = m_avg - (mult_bb * m_std)

        # Keltner Channels
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(window=length).mean()
        
        data['kc_upper'] = m_avg + (mult_kc * atr)
        data['kc_lower'] = m_avg - (mult_kc * atr)

        # Squeeze Logic
        data['squeeze_on'] = (data['bb_upper'] < data['kc_upper']) & (data['bb_lower'] > data['kc_lower'])
        
        # Momentum Histogram
        avg_h_l_m = (data['High'].rolling(length).max() + data['Low'].rolling(length).min() + m_avg) / 3
        data['momentum'] = (data['Close'] - avg_h_l_m).rolling(window=length).mean()

        return data.iloc[-1]
    except:
        return None
