#!/usr/bin/env python3
"""
Risk Barometer - Multi-Asset Crash Detection
Generates crash risk scores for Gold, S&P 500, Nasdaq, and Bitcoin.
Uses only stdlib - no external dependencies.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from statistics import mean, stdev

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


def fetch_json(url: str, timeout: int = 15) -> dict:
    """Fetch JSON from URL with error handling."""
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_yahoo_history(symbol: str, range_str: str = '1y') -> list:
    """Fetch historical price data from Yahoo Finance."""
    url = (
        f'https://query1.finance.yahoo.com/v8/finance/chart/'
        f'{urllib.request.quote(symbol, safe="")}?range={range_str}&interval=1d'
    )
    data = fetch_json(url)
    result = data['chart']['result'][0]
    
    timestamps = result['timestamp']
    quotes = result['indicators']['quote'][0]
    closes = quotes.get('close', [])
    
    # Filter out None values and zip with timestamps
    history = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
    return history


def calculate_ma(history: list, period: int) -> float:
    """Calculate moving average from history [(timestamp, price)]."""
    if len(history) < period:
        return None
    recent_prices = [price for _, price in history[-period:]]
    return mean(recent_prices)


def percentile_rank(value: float, historical_values: list) -> float:
    """Calculate percentile rank of value in historical_values (0-100)."""
    if not historical_values or value is None:
        return None
    sorted_vals = sorted(historical_values)
    count_below = sum(1 for v in sorted_vals if v < value)
    return (count_below / len(sorted_vals)) * 100


# ═══════════════════════════════════════════════════
# GOLD BAROMETER
# ═══════════════════════════════════════════════════

def fetch_gold_barometer() -> dict:
    """Generate crash barometer for Gold."""
    signals = []
    score = 0
    
    # Fetch gold price history
    try:
        gold_history = fetch_yahoo_history('GC=F', '1y')
        current_price = gold_history[-1][1]
    except Exception as e:
        return {'error': f'Failed to fetch gold data: {e}'}
    
    # Signal 1: COT Commercial Positioning (30 points)
    # CFTC COT data is weekly, published Tuesday evenings (Friday data)
    # For now, we'll use a proxy: check if gold has had extreme positioning
    # Real implementation would scrape CFTC.gov, but that's complex for stdlib-only
    # Using MA deviation as proxy for now
    try:
        # Fetch 5 years of weekly data to calculate percentile
        gold_5y = fetch_yahoo_history('GC=F', '5y')
        weekly_prices = [price for _, price in gold_5y[::7]]  # Sample weekly
        
        # COT proxy: When price is in upper percentile AND sentiment extreme
        price_percentile = percentile_rank(current_price, weekly_prices)
        
        cot_triggered = price_percentile and price_percentile > 85
        cot_points = 30 if cot_triggered else 0
        score += cot_points
        
        signals.append({
            'name': 'COT Positioning (Proxy)',
            'triggered': cot_triggered,
            'points': cot_points,
            'maxPoints': 30,
            'detail': f'Price at {price_percentile:.0f}th percentile (5yr)' if price_percentile else 'Unavailable'
        })
    except Exception as e:
        signals.append({
            'name': 'COT Positioning',
            'triggered': False,
            'points': 0,
            'maxPoints': 30,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 2: Real Yields - 10Y TIPS (25 points)
    try:
        # Fetch 10Y Treasury yield from Yahoo Finance (^TNX is 10-year yield * 10)
        tnx_history = fetch_yahoo_history('^TNX', '3mo')
        
        if len(tnx_history) >= 28:
            current_yield = tnx_history[-1][1] / 10  # TNX is in tens (e.g., 45.0 = 4.5%)
            month_ago_yield = tnx_history[-28][1] / 10
            yield_change = (current_yield - month_ago_yield) * 100  # Change in bps
            
            # Trigger: 4-week change >50bps (0.50%)
            real_yields_triggered = yield_change > 50
            real_yields_points = 25 if real_yields_triggered else 0
            score += real_yields_points
            
            signals.append({
                'name': 'Real Yields Surge',
                'triggered': real_yields_triggered,
                'points': real_yields_points,
                'maxPoints': 25,
                'detail': f'4-week change: {yield_change:+.0f}bps (current: {current_yield:.2f}%)'
            })
        else:
            raise ValueError('Insufficient yield data')
    except Exception as e:
        signals.append({
            'name': 'Real Yields',
            'triggered': False,
            'points': 0,
            'maxPoints': 25,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 3: Moving Average Deviation (15 points)
    try:
        ma_50 = calculate_ma(gold_history, 50)
        
        if ma_50:
            deviation_pct = ((current_price - ma_50) / ma_50) * 100
            
            # Trigger: Price >10% above 50-day MA
            ma_triggered = deviation_pct > 10
            ma_points = 15 if ma_triggered else 0
            score += ma_points
            
            signals.append({
                'name': 'MA Overextension',
                'triggered': ma_triggered,
                'points': ma_points,
                'maxPoints': 15,
                'detail': f'{deviation_pct:+.1f}% above 50-day MA'
            })
        else:
            raise ValueError('Insufficient history for MA')
    except Exception as e:
        signals.append({
            'name': 'MA Deviation',
            'triggered': False,
            'points': 0,
            'maxPoints': 15,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 4: DXY Breakout (15 points)
    try:
        dxy_history = fetch_yahoo_history('DX-Y.NYB', '1y')
        current_dxy = dxy_history[-1][1]
        ma_200 = calculate_ma(dxy_history, 200)
        
        if ma_200:
            # Check if DXY is above 200-day MA and rising
            week_ago_dxy = dxy_history[-7][1] if len(dxy_history) >= 7 else current_dxy
            is_rising = current_dxy > week_ago_dxy
            above_ma = current_dxy > ma_200
            
            dxy_triggered = above_ma and is_rising
            dxy_points = 15 if dxy_triggered else 0
            score += dxy_points
            
            ma_diff_pct = ((current_dxy - ma_200) / ma_200) * 100
            signals.append({
                'name': 'DXY Breakout',
                'triggered': dxy_triggered,
                'points': dxy_points,
                'maxPoints': 15,
                'detail': f'{ma_diff_pct:+.1f}% vs 200-MA, {"rising" if is_rising else "falling"}'
            })
        else:
            raise ValueError('Insufficient DXY history')
    except Exception as e:
        signals.append({
            'name': 'DXY Breakout',
            'triggered': False,
            'points': 0,
            'maxPoints': 15,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 5: Sentiment / Put-Call Ratio (15 points)
    # Using volatility as proxy (VIX equivalent for gold = GVZ)
    try:
        # For gold, we'll use price volatility as sentiment proxy
        recent_prices = [price for _, price in gold_history[-20:]]
        if len(recent_prices) >= 20:
            volatility = stdev(recent_prices) / mean(recent_prices) * 100
            
            # High volatility can indicate extreme sentiment
            # Arbitrary threshold: >3% daily volatility = extreme
            sentiment_triggered = volatility > 3.0
            sentiment_points = 15 if sentiment_triggered else 0
            score += sentiment_points
            
            signals.append({
                'name': 'Volatility Extreme',
                'triggered': sentiment_triggered,
                'points': sentiment_points,
                'maxPoints': 15,
                'detail': f'20-day volatility: {volatility:.2f}%'
            })
        else:
            raise ValueError('Insufficient data')
    except Exception as e:
        signals.append({
            'name': 'Sentiment',
            'triggered': False,
            'points': 0,
            'maxPoints': 15,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Determine risk level and recommendation
    if score <= 30:
        level = 'LOW'
        recommendation = 'Normal conditions. Maintain trend-following positions.'
    elif score <= 50:
        level = 'CAUTION'
        recommendation = 'Elevated risk. Monitor closely, prepare hedges.'
    elif score <= 70:
        level = 'WARNING'
        recommendation = 'High risk. Consider reducing exposure by 25-50%.'
    else:
        level = 'DANGER'
        recommendation = 'Extreme risk. Hedge aggressively or reduce to 25% position.'
    
    return {
        'score': score,
        'level': level,
        'signals': signals,
        'recommendation': recommendation
    }


# ═══════════════════════════════════════════════════
# S&P 500 BAROMETER
# ═══════════════════════════════════════════════════

def fetch_sp500_barometer() -> dict:
    """Generate crash barometer for S&P 500."""
    signals = []
    score = 0
    
    try:
        sp_history = fetch_yahoo_history('^GSPC', '1y')
        current_price = sp_history[-1][1]
    except Exception as e:
        return {'error': f'Failed to fetch S&P 500 data: {e}'}
    
    # Signal 1: VIX Level (30 points)
    try:
        vix_history = fetch_yahoo_history('^VIX', '3mo')
        current_vix = vix_history[-1][1]
        
        # Trigger: VIX >25 (elevated fear)
        vix_triggered = current_vix > 25
        vix_points = 30 if vix_triggered else 0
        score += vix_points
        
        signals.append({
            'name': 'VIX Elevated',
            'triggered': vix_triggered,
            'points': vix_points,
            'maxPoints': 30,
            'detail': f'VIX at {current_vix:.1f} (threshold: 25)'
        })
    except Exception as e:
        signals.append({
            'name': 'VIX Level',
            'triggered': False,
            'points': 0,
            'maxPoints': 30,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 2: Yield Curve (25 points)
    try:
        # Fetch 10Y and 2Y yields
        tnx_10y = fetch_yahoo_history('^TNX', '1mo')[-1][1] / 10
        # ^IRX is 13-week T-bill, use as proxy for short end
        irx_short = fetch_yahoo_history('^IRX', '1mo')[-1][1] / 10
        
        yield_spread = tnx_10y - irx_short
        
        # Trigger: Inverted or flat yield curve (<0.2%)
        curve_triggered = yield_spread < 0.2
        curve_points = 25 if curve_triggered else 0
        score += curve_points
        
        signals.append({
            'name': 'Yield Curve',
            'triggered': curve_triggered,
            'points': curve_points,
            'maxPoints': 25,
            'detail': f'10Y-2Y spread: {yield_spread:.2f}% {"(inverted)" if yield_spread < 0 else ""}'
        })
    except Exception as e:
        signals.append({
            'name': 'Yield Curve',
            'triggered': False,
            'points': 0,
            'maxPoints': 25,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 3: 200-day MA Deviation (20 points)
    try:
        ma_200 = calculate_ma(sp_history, 200)
        
        if ma_200:
            deviation_pct = ((current_price - ma_200) / ma_200) * 100
            
            # Trigger: >8% above 200-day MA
            ma_triggered = deviation_pct > 8
            ma_points = 20 if ma_triggered else 0
            score += ma_points
            
            signals.append({
                'name': 'MA Overextension',
                'triggered': ma_triggered,
                'points': ma_points,
                'maxPoints': 20,
                'detail': f'{deviation_pct:+.1f}% vs 200-day MA'
            })
        else:
            raise ValueError('Insufficient history')
    except Exception as e:
        signals.append({
            'name': 'MA Deviation',
            'triggered': False,
            'points': 0,
            'maxPoints': 20,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 4: Put/Call Ratio Extreme (15 points)
    try:
        # Using VIX term structure as proxy (VIX vs VIX3M)
        vix_current = fetch_yahoo_history('^VIX', '1mo')[-1][1]
        # Can't get VIX3M easily, so use volatility change instead
        vix_week_ago = fetch_yahoo_history('^VIX', '1mo')[-7][1] if len(fetch_yahoo_history('^VIX', '1mo')) >= 7 else vix_current
        
        vix_change_pct = ((vix_current - vix_week_ago) / vix_week_ago) * 100
        
        # Trigger: VIX jumped >30% in a week (panic hedging)
        pc_triggered = vix_change_pct > 30
        pc_points = 15 if pc_triggered else 0
        score += pc_points
        
        signals.append({
            'name': 'Hedging Surge',
            'triggered': pc_triggered,
            'points': pc_points,
            'maxPoints': 15,
            'detail': f'VIX 1-week change: {vix_change_pct:+.1f}%'
        })
    except Exception as e:
        signals.append({
            'name': 'Put/Call Ratio',
            'triggered': False,
            'points': 0,
            'maxPoints': 15,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 5: Market Breadth (10 points)
    try:
        # Use Nasdaq vs S&P divergence as breadth proxy
        nasdaq_history = fetch_yahoo_history('^IXIC', '1mo')
        nasdaq_change_1m = ((nasdaq_history[-1][1] - nasdaq_history[0][1]) / nasdaq_history[0][1]) * 100
        sp_change_1m = ((sp_history[-1][1] - sp_history[-30][1]) / sp_history[-30][1]) * 100 if len(sp_history) >= 30 else 0
        
        divergence = nasdaq_change_1m - sp_change_1m
        
        # Trigger: Nasdaq lagging S&P by >3% (narrowing leadership)
        breadth_triggered = divergence < -3
        breadth_points = 10 if breadth_triggered else 0
        score += breadth_points
        
        signals.append({
            'name': 'Market Breadth',
            'triggered': breadth_triggered,
            'points': breadth_points,
            'maxPoints': 10,
            'detail': f'NDX-SPX divergence: {divergence:+.1f}%'
        })
    except Exception as e:
        signals.append({
            'name': 'Market Breadth',
            'triggered': False,
            'points': 0,
            'maxPoints': 10,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Determine level
    if score <= 30:
        level = 'LOW'
        recommendation = 'Normal market conditions. Continue systematic strategies.'
    elif score <= 50:
        level = 'CAUTION'
        recommendation = 'Elevated risk. Consider tightening stops.'
    elif score <= 70:
        level = 'WARNING'
        recommendation = 'High risk environment. Reduce equity exposure.'
    else:
        level = 'DANGER'
        recommendation = 'Extreme risk. Consider significant hedging.'
    
    return {
        'score': score,
        'level': level,
        'signals': signals,
        'recommendation': recommendation
    }


# ═══════════════════════════════════════════════════
# NASDAQ BAROMETER
# ═══════════════════════════════════════════════════

def fetch_nasdaq_barometer() -> dict:
    """Generate crash barometer for Nasdaq (similar to S&P but higher beta)."""
    signals = []
    score = 0
    
    try:
        nasdaq_history = fetch_yahoo_history('^IXIC', '1y')
        current_price = nasdaq_history[-1][1]
    except Exception as e:
        return {'error': f'Failed to fetch Nasdaq data: {e}'}
    
    # Signal 1: VIX Level (30 points) - same as S&P
    try:
        vix_history = fetch_yahoo_history('^VIX', '3mo')
        current_vix = vix_history[-1][1]
        
        vix_triggered = current_vix > 25
        vix_points = 30 if vix_triggered else 0
        score += vix_points
        
        signals.append({
            'name': 'VIX Elevated',
            'triggered': vix_triggered,
            'points': vix_points,
            'maxPoints': 30,
            'detail': f'VIX at {current_vix:.1f}'
        })
    except Exception as e:
        signals.append({
            'name': 'VIX Level',
            'triggered': False,
            'points': 0,
            'maxPoints': 30,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 2: Tech Sector Concentration (25 points)
    try:
        # Use QQQ options skew or just higher MA threshold
        ma_200 = calculate_ma(nasdaq_history, 200)
        
        if ma_200:
            deviation_pct = ((current_price - ma_200) / ma_200) * 100
            
            # Trigger: >12% above 200-day MA (higher threshold than S&P)
            ma_triggered = deviation_pct > 12
            ma_points = 25 if ma_triggered else 0
            score += ma_points
            
            signals.append({
                'name': 'MA Overextension',
                'triggered': ma_triggered,
                'points': ma_points,
                'maxPoints': 25,
                'detail': f'{deviation_pct:+.1f}% vs 200-day MA'
            })
        else:
            raise ValueError('Insufficient history')
    except Exception as e:
        signals.append({
            'name': 'MA Deviation',
            'triggered': False,
            'points': 0,
            'maxPoints': 25,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 3: Rate Sensitivity (20 points)
    try:
        tnx_history = fetch_yahoo_history('^TNX', '3mo')
        current_yield = tnx_history[-1][1] / 10
        month_ago_yield = tnx_history[-28][1] / 10 if len(tnx_history) >= 28 else current_yield
        
        yield_change = (current_yield - month_ago_yield) * 100
        
        # Nasdaq is more rate-sensitive: trigger at 40bps
        rate_triggered = yield_change > 40
        rate_points = 20 if rate_triggered else 0
        score += rate_points
        
        signals.append({
            'name': 'Rate Surge',
            'triggered': rate_triggered,
            'points': rate_points,
            'maxPoints': 20,
            'detail': f'4-week yield change: {yield_change:+.0f}bps'
        })
    except Exception as e:
        signals.append({
            'name': 'Rate Sensitivity',
            'triggered': False,
            'points': 0,
            'maxPoints': 20,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 4: Momentum Reversal (15 points)
    try:
        if len(nasdaq_history) >= 60:
            price_60d_ago = nasdaq_history[-60][1]
            price_30d_ago = nasdaq_history[-30][1]
            
            momentum_60d = ((price_30d_ago - price_60d_ago) / price_60d_ago) * 100
            momentum_recent = ((current_price - price_30d_ago) / price_30d_ago) * 100
            
            # Trigger: Momentum reversal (was strong, now weak)
            reversal_triggered = momentum_60d > 5 and momentum_recent < -2
            reversal_points = 15 if reversal_triggered else 0
            score += reversal_points
            
            signals.append({
                'name': 'Momentum Reversal',
                'triggered': reversal_triggered,
                'points': reversal_points,
                'maxPoints': 15,
                'detail': f'60d: {momentum_60d:+.1f}%, 30d: {momentum_recent:+.1f}%'
            })
        else:
            raise ValueError('Insufficient history')
    except Exception as e:
        signals.append({
            'name': 'Momentum',
            'triggered': False,
            'points': 0,
            'maxPoints': 15,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 5: Volatility Spike (10 points)
    try:
        recent_prices = [price for _, price in nasdaq_history[-20:]]
        volatility = stdev(recent_prices) / mean(recent_prices) * 100
        
        vol_triggered = volatility > 2.5
        vol_points = 10 if vol_triggered else 0
        score += vol_points
        
        signals.append({
            'name': 'Volatility Spike',
            'triggered': vol_triggered,
            'points': vol_points,
            'maxPoints': 10,
            'detail': f'20-day vol: {volatility:.2f}%'
        })
    except Exception as e:
        signals.append({
            'name': 'Volatility',
            'triggered': False,
            'points': 0,
            'maxPoints': 10,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Determine level
    if score <= 30:
        level = 'LOW'
        recommendation = 'Normal conditions for growth/tech.'
    elif score <= 50:
        level = 'CAUTION'
        recommendation = 'Elevated risk. Monitor rate-sensitive positions.'
    elif score <= 70:
        level = 'WARNING'
        recommendation = 'High risk. Consider rotating to defensive sectors.'
    else:
        level = 'DANGER'
        recommendation = 'Extreme risk for tech. Reduce exposure significantly.'
    
    return {
        'score': score,
        'level': level,
        'signals': signals,
        'recommendation': recommendation
    }


# ═══════════════════════════════════════════════════
# BITCOIN BAROMETER
# ═══════════════════════════════════════════════════

def fetch_bitcoin_barometer() -> dict:
    """Generate crash barometer for Bitcoin."""
    signals = []
    score = 0
    
    try:
        btc_history = fetch_yahoo_history('BTC-USD', '1y')
        current_price = btc_history[-1][1]
    except Exception as e:
        return {'error': f'Failed to fetch Bitcoin data: {e}'}
    
    # Signal 1: 200-day MA Deviation (30 points)
    try:
        ma_200 = calculate_ma(btc_history, 200)
        
        if ma_200:
            deviation_pct = ((current_price - ma_200) / ma_200) * 100
            
            # Trigger: >25% above 200-day MA (crypto is more volatile)
            ma_triggered = deviation_pct > 25
            ma_points = 30 if ma_triggered else 0
            score += ma_points
            
            signals.append({
                'name': 'MA Overextension',
                'triggered': ma_triggered,
                'points': ma_points,
                'maxPoints': 30,
                'detail': f'{deviation_pct:+.1f}% vs 200-day MA'
            })
        else:
            raise ValueError('Insufficient history')
    except Exception as e:
        signals.append({
            'name': 'MA Deviation',
            'triggered': False,
            'points': 0,
            'maxPoints': 30,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 2: Volatility Extreme (25 points)
    try:
        recent_prices = [price for _, price in btc_history[-30:]]
        volatility = stdev(recent_prices) / mean(recent_prices) * 100
        
        # High volatility for Bitcoin: >8%
        vol_triggered = volatility > 8
        vol_points = 25 if vol_triggered else 0
        score += vol_points
        
        signals.append({
            'name': 'Volatility Extreme',
            'triggered': vol_triggered,
            'points': vol_points,
            'maxPoints': 25,
            'detail': f'30-day volatility: {volatility:.2f}%'
        })
    except Exception as e:
        signals.append({
            'name': 'Volatility',
            'triggered': False,
            'points': 0,
            'maxPoints': 25,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 3: Momentum Exhaustion (20 points)
    try:
        if len(btc_history) >= 90:
            price_90d_ago = btc_history[-90][1]
            price_30d_ago = btc_history[-30][1]
            
            gain_first_60d = ((price_30d_ago - price_90d_ago) / price_90d_ago) * 100
            gain_last_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
            
            # Trigger: Strong gains slowing (first period >30%, recent <10%)
            momentum_triggered = gain_first_60d > 30 and gain_last_30d < 10
            momentum_points = 20 if momentum_triggered else 0
            score += momentum_points
            
            signals.append({
                'name': 'Momentum Exhaustion',
                'triggered': momentum_triggered,
                'points': momentum_points,
                'maxPoints': 20,
                'detail': f'60d gain: {gain_first_60d:+.1f}%, 30d: {gain_last_30d:+.1f}%'
            })
        else:
            raise ValueError('Insufficient history')
    except Exception as e:
        signals.append({
            'name': 'Momentum',
            'triggered': False,
            'points': 0,
            'maxPoints': 20,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 4: Correlation with Risk Assets (15 points)
    try:
        # Check if Bitcoin is moving with Nasdaq (risk-on)
        nasdaq_history = fetch_yahoo_history('^IXIC', '3mo')
        
        # Get overlapping period
        btc_recent = [price for _, price in btc_history[-60:]]
        nasdaq_recent = [price for _, price in nasdaq_history[-60:]]
        
        if len(btc_recent) >= 60 and len(nasdaq_recent) >= 60:
            # Simple correlation check: both falling or both very extended
            btc_change = ((btc_recent[-1] - btc_recent[0]) / btc_recent[0]) * 100
            ndx_change = ((nasdaq_recent[-1] - nasdaq_recent[0]) / nasdaq_recent[0]) * 100
            
            # Trigger: Both down >10% in 60d (risk-off)
            corr_triggered = btc_change < -10 and ndx_change < -10
            corr_points = 15 if corr_triggered else 0
            score += corr_points
            
            signals.append({
                'name': 'Risk-Off Correlation',
                'triggered': corr_triggered,
                'points': corr_points,
                'maxPoints': 15,
                'detail': f'BTC: {btc_change:+.1f}%, NDX: {ndx_change:+.1f}%'
            })
        else:
            raise ValueError('Insufficient data')
    except Exception as e:
        signals.append({
            'name': 'Correlation',
            'triggered': False,
            'points': 0,
            'maxPoints': 15,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Signal 5: Price Drawdown from ATH (10 points)
    try:
        all_time_high = max(price for _, price in btc_history)
        drawdown_pct = ((current_price - all_time_high) / all_time_high) * 100
        
        # Trigger: Down >30% from ATH
        dd_triggered = drawdown_pct < -30
        dd_points = 10 if dd_triggered else 0
        score += dd_points
        
        signals.append({
            'name': 'Drawdown from ATH',
            'triggered': dd_triggered,
            'points': dd_points,
            'maxPoints': 10,
            'detail': f'{drawdown_pct:.1f}% from all-time high'
        })
    except Exception as e:
        signals.append({
            'name': 'Drawdown',
            'triggered': False,
            'points': 0,
            'maxPoints': 10,
            'detail': f'Data unavailable: {str(e)[:50]}'
        })
    
    # Determine level
    if score <= 30:
        level = 'LOW'
        recommendation = 'Normal crypto conditions. Maintain positions.'
    elif score <= 50:
        level = 'CAUTION'
        recommendation = 'Elevated risk. Consider taking profits on leveraged positions.'
    elif score <= 70:
        level = 'WARNING'
        recommendation = 'High risk. Reduce exposure, avoid leverage.'
    else:
        level = 'DANGER'
        recommendation = 'Extreme risk. Significant correction likely.'
    
    return {
        'score': score,
        'level': level,
        'signals': signals,
        'recommendation': recommendation
    }


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    """Generate risk barometer data for all assets."""
    print('🔍 Generating risk barometers...\n')
    
    barometers = {}
    
    # Fetch each barometer
    for name, func in [
        ('gold', fetch_gold_barometer),
        ('sp500', fetch_sp500_barometer),
        ('nasdaq', fetch_nasdaq_barometer),
        ('bitcoin', fetch_bitcoin_barometer),
    ]:
        try:
            print(f'  Analyzing {name.upper()}...')
            barometer = func()
            
            if 'error' in barometer:
                print(f'    ✗ Error: {barometer["error"]}')
                barometers[name] = barometer
            else:
                barometers[name] = barometer
                score = barometer['score']
                level = barometer['level']
                triggered_count = sum(1 for s in barometer['signals'] if s['triggered'])
                print(f'    ✓ Score: {score}/100 | Level: {level} | Signals: {triggered_count}/5')
        except Exception as e:
            print(f'    ✗ Failed: {e}')
            barometers[name] = {'error': str(e)}
    
    output = {
        'updatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'barometers': barometers
    }
    
    # Ensure data/ directory exists
    os.makedirs('data', exist_ok=True)
    
    # Write to file
    with open('data/risk-barometer.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f'\n✓ Risk barometer data written to data/risk-barometer.json')
    
    # Show summary
    print('\n📊 Summary:')
    for name, data in barometers.items():
        if 'score' in data:
            emoji = {'LOW': '🟢', 'CAUTION': '🟡', 'WARNING': '🟠', 'DANGER': '🔴'}[data['level']]
            print(f'  {emoji} {name.upper()}: {data["score"]}/100 ({data["level"]})')
        else:
            print(f'  ❌ {name.upper()}: Error')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n⚠ Interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ Fatal error: {e}', file=sys.stderr)
        sys.exit(1)
