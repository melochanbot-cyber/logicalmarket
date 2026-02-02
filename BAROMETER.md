# Risk Barometer Documentation

## Overview

The LogicalMarket dashboard now includes a **Crash Risk Barometer** that analyzes multi-signal crash detection for four major assets:

- 🥇 **Gold** — Precious metals crash signals
- 📈 **S&P 500** — Equity market systemic risk
- 💻 **Nasdaq** — Tech sector crash risk
- ₿ **Bitcoin** — Crypto market crash risk

## How It Works

Each barometer calculates a **composite risk score (0-100)** by analyzing 5 core signals:

### Gold Signals (100 points total)

1. **COT Positioning (30 pts)** — CFTC Commitment of Traders data proxy (price percentile)
2. **Real Yields Surge (25 pts)** — 10Y Treasury yield 4-week change >50bps
3. **MA Overextension (15 pts)** — Price >10% above 50-day moving average
4. **DXY Breakout (15 pts)** — USD Index above 200-day MA and rising
5. **Volatility Extreme (15 pts)** — 20-day price volatility >3%

### S&P 500 Signals (100 points total)

1. **VIX Elevated (30 pts)** — VIX >25 (fear/uncertainty)
2. **Yield Curve (25 pts)** — 10Y-2Y spread <0.2% (inverted or flat)
3. **MA Overextension (20 pts)** — Price >8% above 200-day MA
4. **Hedging Surge (15 pts)** — VIX week-over-week change >30%
5. **Market Breadth (10 pts)** — Nasdaq lagging S&P by >3%

### Nasdaq Signals (100 points total)

1. **VIX Elevated (30 pts)** — Same as S&P
2. **MA Overextension (25 pts)** — Price >12% above 200-day MA (higher threshold)
3. **Rate Surge (20 pts)** — 10Y yield 4-week change >40bps (rate-sensitive)
4. **Momentum Reversal (15 pts)** — Strong 60d momentum turns negative
5. **Volatility Spike (10 pts)** — 20-day volatility >2.5%

### Bitcoin Signals (100 points total)

1. **MA Overextension (30 pts)** — Price >25% above 200-day MA
2. **Volatility Extreme (25 pts)** — 30-day volatility >8%
3. **Momentum Exhaustion (20 pts)** — Strong gains slowing (60d >30%, 30d <10%)
4. **Risk-Off Correlation (15 pts)** — Both BTC and Nasdaq down >10% in 60d
5. **Drawdown from ATH (10 pts)** — Down >30% from all-time high

## Risk Levels

| Score | Level | Color | Recommendation |
|-------|-------|-------|----------------|
| 0-30 | 🟢 LOW | Green | Normal conditions. Maintain trend-following positions. |
| 31-50 | 🟡 CAUTION | Yellow | Elevated risk. Monitor closely, prepare hedges. |
| 51-70 | 🟠 WARNING | Orange | High risk. Consider reducing exposure by 25-50%. |
| 71-100 | 🔴 DANGER | Red | Extreme risk. Hedge aggressively or reduce to 25% position. |

## Data Sources

All data is fetched from **free, publicly available APIs**:

- **Yahoo Finance** — Price history, moving averages, volatility
- **10Y Treasury (^TNX)** — Yield data for real yields and rate sensitivity
- **VIX (^VIX)** — Market volatility/fear index
- **DXY (DX-Y.NYB)** — USD Index

**Note:** COT data proxy uses price percentile ranking as a substitute for actual CFTC COT reports (which are weekly and require scraping). The current implementation is stdlib-only (no external dependencies).

## Update Frequency

- **Market data** (prices, sparklines): Every 5 minutes during US market hours, every 30 minutes off-hours
- **Risk barometer**: Runs with every market data update (signals are slower-moving, so frequent updates are safe)

The barometer is calculated by GitHub Actions and served as a static JSON file (`data/risk-barometer.json`).

## Technical Implementation

### Python Script (`scripts/fetch_risk_barometer.py`)

- **Language:** Python 3.12 (stdlib only, no external dependencies)
- **Output:** `data/risk-barometer.json`
- **Execution:** GitHub Actions (ubuntu-latest runner)

### Dashboard UI

- **HTML/CSS/JS:** Vanilla, no build tools
- **Barometer cards:** Circular gauge visualization, signal breakdown, risk level badge
- **Responsive:** 4 columns desktop, 2 columns tablet, 1 column mobile
- **Integrated with:** Existing refresh flow, updates every 5-30 minutes

### GitHub Actions Workflow

`.github/workflows/update-market-data.yml` now runs both:

1. `python scripts/fetch_market_data.py` (prices)
2. `python scripts/fetch_risk_barometer.py` (barometer)

Both outputs are committed and pushed automatically.

## Based on Research

The barometer signals are derived from the research document:

`/Users/melobot/.openclaw/workspace/research/crash-detection-final.md`

Key insights:

- **COT positioning** (commercial net short >85th percentile) is the highest-weighted signal (30 points) due to proven historical accuracy
- **Real yields** (10Y TIPS) have a strong inverse correlation with gold (-15x rule of thumb)
- **Moving average deviation** captures mean reversion tendency
- **Multi-signal composite** improves accuracy over single indicators (expected 55-65% accuracy for crash within 30-45 days)

The research showed that the simplified **5-signal system captures ~85% of the value of a 19-signal system** with far less overfitting risk (5 signals vs. 19 = 25% of the overfitting risk).

## Future Enhancements

Potential improvements (not yet implemented):

1. **Real CFTC COT data scraping** — Parse weekly COT reports directly from CFTC.gov
2. **FRED API integration** — Direct TIPS yield data instead of TNX proxy
3. **DSI sentiment data** — Integrate Daily Sentiment Index (requires $240/yr subscription)
4. **Put/Call ratio** — Real-time options data (CBOE or broker API)
5. **Historical backtesting** — Validate signal accuracy against 2006-2026 crashes
6. **Alert system** — Email/Telegram notifications when barometer enters WARNING/DANGER

## Current Status (Live)

As of February 2, 2026:

- **Gold:** 60/100 (🟠 WARNING) — Price at 99th percentile (5yr), overextended +13.8% above 50-day MA, high volatility
- **S&P 500:** 45/100 (🟡 CAUTION) — Yield curve near inversion, 8% above 200-day MA
- **Nasdaq:** 0/100 (🟢 LOW) — All signals normal
- **Bitcoin:** 10/100 (🟢 LOW) — Only drawdown signal triggered (-37% from ATH)

Gold is showing elevated crash risk. S&P 500 has some warning signs but not extreme. Nasdaq and Bitcoin are in normal ranges.

---

**Live Dashboard:** https://melochanbot-cyber.github.io/logicalmarket/

**GitHub Repo:** https://github.com/melochanbot-cyber/logicalmarket
