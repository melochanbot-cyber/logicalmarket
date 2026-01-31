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

## License

MIT
