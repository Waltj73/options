import numpy as np
import pandas as pd
import yfinance as yf


def calculate_ttm_squeeze(ticker, trading_days_ahead=30, vol_lookback=20):
    try:
        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        if df.empty or len(df) < 35:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        length = 20

        # 1. Bollinger Bands (20, 2.0)
        m_avg = df["Close"].rolling(window=length).mean()
        m_std = df["Close"].rolling(window=length).std()
        bb_u = m_avg + (2.0 * m_std)
        bb_l = m_avg - (2.0 * m_std)

        # 2. Keltner Channels (20, 1.5)
        tr = pd.concat(
            [
                df["High"] - df["Low"],
                (df["High"] - df["Close"].shift()).abs(),
                (df["Low"] - df["Close"].shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(window=length).mean()
        kc_u = m_avg + (1.5 * atr)
        kc_l = m_avg - (1.5 * atr)

        # Squeeze State
        df["sq_on"] = (bb_u < kc_u) & (bb_l > kc_l)

        # 3. True TTM Linear Regression Momentum (Matches TOS Inertia)
        highest_high = df["High"].rolling(window=length).max()
        lowest_low = df["Low"].rolling(window=length).min()
        donchian_mid = (highest_high + lowest_low) / 2.0
        delta = df["Close"] - ((donchian_mid + m_avg) / 2.0)

        x = np.arange(length)
        df["mom"] = delta.rolling(window=length).apply(
            lambda y: np.polyfit(x, y, 1)[0] * (length - 1)
            + np.polyfit(x, y, 1)[1],
            raw=True,
        )

        # 4. Trend & Structure Context (10 & 21 EMA)
        df["ema10"] = df["Close"].ewm(span=10, adjust=False).mean()
        df["ema21"] = df["Close"].ewm(span=21, adjust=False).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        spot = float(last["Close"])
        prev_close = float(prev["Close"])
        ema10 = float(last["ema10"])
        ema21 = float(last["ema21"])
        mom = float(last["mom"])
        prev_mom = float(prev["mom"])
        sq_on = bool(last["sq_on"])
        prev_sq_on = bool(prev["sq_on"])

        # Price Rising & EMA Alignment Checks
        price_rising = spot > prev_close and spot > float(df["Open"].iloc[-1])
        above_21ema = spot > ema21
        ema_stacked = spot > ema10 > ema21
        dist_21ema_pct = ((spot - ema21) / ema21) * 100

        # Momentum Histogram Color / Acceleration State
        mom_rising = mom > prev_mom
        if mom > 0 and mom_rising:
            mom_state = "Cyan (Bull Accel)"
        elif mom > 0 and not mom_rising:
            mom_state = "Dark Blue (Bull Decel)"
        elif mom <= 0 and mom_rising:
            mom_state = "Yellow (Bear Decel)"
        else:
            mom_state = "Red (Bear Accel)"

        # Squeeze Status Tag
        if sq_on:
            sq_status = "🔴 SQUEEZING"
        elif prev_sq_on and not sq_on:
            sq_status = "🚀 JUST FIRED"
        else:
            sq_status = "🟢 OPEN / FIRED"

        # 5. Forward-Projected 30D Probability Targets (Matches TOS `probs`)
        log_ret = np.log(df["Close"] / df["Close"].shift(1))
        sigma_daily = float(log_ret.tail(vol_lookback).std())
        sigma_annual = sigma_daily * np.sqrt(252)
        t_years = trading_days_ahead / 252.0
        horizon_sigma = sigma_annual * np.sqrt(t_years)

        tgt_80 = spot * np.exp(0.5 * horizon_sigma)  # Yellow Shelf
        tgt_50 = spot * np.exp(1.0 * horizon_sigma)  # Cyan Shelf
        floor_50 = spot * np.exp(-1.0 * horizon_sigma)  # Red Floor
        upside_80_pct = ((tgt_80 - spot) / spot) * 100

        # 6. A+ Setup Grading Logic
        # A+ Long: Stacked above 10/21 EMA, rising price, accelerating momentum (Cyan or Yellow hook), squeezing or recently fired
        if ema_stacked and price_rising and mom_rising and (mom > 0 or sq_on):
            setup_grade = "A+ LONG"
        elif (
            above_21ema
            and mom_rising
            and (sq_on or mom_state == "Yellow (Bear Decel)")
        ):
            setup_grade = "B WATCH (Coiling/Hook)"
        elif (
            spot < ema10 < ema21
            and not price_rising
            and not mom_rising
            and mom < 0
        ):
            setup_grade = "A+ SHORT"
        else:
            setup_grade = "C NEUTRAL"

        return {
            "Ticker": ticker,
            "Grade": setup_grade,
            "Spot": round(spot, 2),
            "Squeeze": sq_status,
            "Momentum": round(mom, 2),
            "Momo State": mom_state,
            "Above 21 EMA": "✅ Yes" if above_21ema else "❌ No",
            "Dist 21EMA (%)": round(dist_21ema_pct, 2),
            "Rising": "📈 Yes" if price_rising else "📉 No",
            "30D 80% Tgt": round(tgt_80, 2),
            "80% Room (%)": round(upside_80_pct, 2),
            "30D 50% Tgt": round(tgt_50, 2),
            "30D 50% Floor": round(floor_50, 2),
        }
    except Exception:
        return None
