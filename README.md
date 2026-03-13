# 📊 LogicalMarket

A clean, modern static dashboard tracking prominent asset movements with real-time data.

**🌐 Live:** [https://melochanbot-cyber.github.io/logicalmarket/](https://melochanbot-cyber.github.io/logicalmarket/)

## Assets Tracked

| Asset | Symbol | Category |
|-------|--------|----------|
| Gold | GC=F | Commodity |
| Silver | SI=F | Commodity |
| Crude Oil | CL=F | Commodity |
| S&P 500 | ^GSPC | Index |
| Nasdaq | ^IXIC | Index |
| Dow Jones | ^DJI | Index |
| Bitcoin | BTC-USD | Crypto |
| Ethereum | ETH-USD | Crypto |
| USD Index | DX-Y.NYB | Currency |

## Features

- **Real-time prices** via Yahoo Finance API
- **Sparkline charts** for 5-day price history
- **Market movers** — sorted by daily change %
- **Crash Risk Barometer** — Multi-signal composite scoring for Gold, S&P 500, Nasdaq, Bitcoin
- **Risk Alerts** — Automated notifications when assets hit WARNING/DANGER levels
- **News feed** — categorized market headlines from Google News
- **Auto-refresh** every 5 minutes
- **Dark theme** with Bloomberg-inspired design
- **Mobile responsive**
- **Zero dependencies** — pure HTML/CSS/JS

## Tech Stack

- Vanilla HTML, CSS, JavaScript
- Yahoo Finance chart API (via CORS proxy fallback chain)
- Google News RSS (via CORS proxy)
- GitHub Pages hosting

## Development

Just open `index.html` in a browser. No build step required.

## Scripts

### Data Updates (Automated via GitHub Actions)

```bash
# Fetch latest market data
python scripts/fetch_market_data.py

# Calculate risk barometer scores
python scripts/fetch_risk_barometer.py
```

### Risk Alerts (Optional)

Monitor the risk barometer and send alerts when assets hit WARNING (51-70) or DANGER (71-100) levels:

```bash
# Dry run (check alerts without sending)
node scripts/risk-alert.mjs --dry-run

# Send alerts to Feishu
node scripts/risk-alert.mjs --feishu-chat-id=oc_xxxxx

# Via environment variable
FEISHU_CHAT_ID=oc_xxxxx node scripts/risk-alert.mjs
```

**Alert Logic:**
- 🔴 **DANGER (71-100):** Always alert
- 🟠 **WARNING (51-70):** Alert once per 24 hours per asset
- 🟡 **CAUTION (31-50):** No alert (monitor only)
- 🟢 **LOW (0-30):** No alert

State tracking in `data/alert-state.json` prevents spam.

**Setup as cron job:**
```bash
# Check every hour during market hours
0 9-16 * * 1-5 cd /path/to/logicalmarket && node scripts/risk-alert.mjs
```

## License

MIT
