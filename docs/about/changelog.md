# Changelog

All notable changes to ArBot will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- Web-based interface for remote monitoring
- Advanced charting and technical analysis
- Machine learning-based opportunity prediction
- Multi-asset arbitrage (cross-chain)
- Advanced portfolio management
- Mobile app for monitoring
- Telegram/Discord notifications
- Cloud deployment templates

---

## [1.2.0] - 2024-01-15

### 🚀 Added
- **Trend-Based Arbitrage Filtering**: Only trade during favorable market trends
  - Configurable trend modes: uptrend_buy_low, downtrend_sell_high, both, disabled
  - Real-time trend indicators (↗↘→) in GUI
  - Trend confirmation threshold settings
- **Enhanced Moving Average System**: 30-second moving averages with configurable periods
- **Premium Detection**: Statistical analysis of exchange pricing patterns
- **Quote Currency Filtering**: Focus on specific quote currencies (USDT, BUSD, USDC, etc.)
- **Dynamic Symbol Management**: Auto-detect high-volume trading pairs (up to 200+ symbols)
- **Interactive Column Sorting**: Click column headers with visual indicators (↑↓)

### 🎨 Changed
- **GUI Price Display**: New format "Price(±Diff)" for cleaner visualization
- **Settings Panel Layout**: Row-based dynamic layout prevents overlapping
- **Symbol Monitoring**: Increased from 50 to 200+ symbols maximum
- **Column Structure**: Replaced Direction with Higher Exchange + trend indicators

### 🐛 Fixed
- Hard-coded 50-symbol limit in GUI components
- Settings panel row overlap issues
- Symbol filtering conflicts between USDT/USDC patterns
- Strategy not using dynamically detected symbols
- Quote currency detection edge cases

### 🔧 Technical
- Implemented MovingAverageManager class for trend analysis
- Added row_cnt variable management in all settings panels
- Improved quote currency detection with longest-first matching
- Enhanced arbitrage filtering with trend confirmation

---

## [1.1.0] - 2024-01-01

### 🚀 Added
- **Multi-Exchange Support**: Binance, Bybit, OKX, Bitget
- **Real-Time WebSocket Feeds**: Sub-second price updates
- **Risk Management Framework**: Stop-loss, drawdown protection, position sizing
- **Configuration System**: Flexible JSON-based configuration with environment overrides
- **Database Integration**: SQLite for historical data and trade records
- **Performance Monitoring**: Real-time metrics and analytics

### 🎨 Changed
- Complete GUI redesign with tkinter
- Modular exchange adapter architecture
- Improved error handling and reconnection logic

### 🐛 Fixed
- Memory leaks in WebSocket connections
- GUI freezing during high-frequency updates
- Database locking issues under concurrent access

---

## [1.0.0] - 2023-12-01

### 🚀 Initial Release

**Core Features:**
- **Arbitrage Detection**: Real-time spread monitoring between exchanges
- **Trading Modes**: Simulation, Live, and Backtest modes
- **GUI Interface**: Modern tkinter-based user interface
- **Exchange Integration**: Initial support for Binance and Bybit
- **Configuration Management**: JSON-based configuration system
- **Risk Controls**: Basic position sizing and stop-loss functionality

**Exchange Support:**
- ✅ Binance (Spot trading)
- ✅ Bybit (Spot trading)
- 🔄 OKX (Planned)
- 🔄 Bitget (Planned)

**Trading Features:**
- Real-time price monitoring
- Arbitrage opportunity detection
- Simulated trading for testing
- Basic risk management
- Trade history tracking

**Technical Foundation:**
- Python 3.8+ compatibility
- Asynchronous WebSocket connections
- SQLite database for data persistence
- Modular architecture for easy extension
- Comprehensive logging system

---

## Version History Summary

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| **1.2.0** | 2024-01-15 | Trend filtering, dynamic symbols, enhanced GUI |
| **1.1.0** | 2024-01-01 | Multi-exchange, risk management, performance monitoring |
| **1.0.0** | 2023-12-01 | Initial release, basic arbitrage detection |

---

## Upgrade Guide

### From 1.1.0 to 1.2.0

**Configuration Changes:**
```json
{
  "arbitrage": {
    "max_symbols": 200,
    "enabled_quote_currencies": ["USDT"],
    "available_quote_currencies": ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"],
    "moving_average_periods": 30,
    "use_trend_filter": true,
    "trend_filter_mode": "uptrend_buy_low",
    "trend_confirmation_threshold": 0.001
  }
}
```

**Breaking Changes:**
- GUI column structure changed (Direction → Higher Exchange)
- Settings panel layout restructured
- New required configuration parameters for trend filtering

**Migration Steps:**
1. Update `config.json` with new parameters
2. Review and adjust `max_symbols` setting
3. Configure quote currency preferences
4. Test trend filtering in simulation mode

### From 1.0.0 to 1.1.0

**New Dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**Database Migration:**
- Automatic schema updates on first run
- Backup existing database before upgrade
- New tables for performance metrics

**API Changes:**
- Exchange adapter interface updated
- New risk management parameters required
- Configuration structure expanded

---

## Development Milestones

### 🎯 Current Focus (v1.2.x)
- Trend filtering optimization
- Enhanced GUI features
- Performance improvements
- Documentation expansion

### 🔮 Next Release (v1.3.0)
- Advanced charting integration
- Machine learning price prediction
- Enhanced backtesting engine
- Mobile-responsive interface

### 🚀 Future Vision (v2.0.0)
- Cross-chain arbitrage
- DeFi protocol integration
- Advanced portfolio management
- Cloud-native deployment

---

## Contributing to Changelog

When contributing to ArBot, please:

1. **Follow semantic versioning** for version numbers
2. **Categorize changes** using the sections above
3. **Write clear descriptions** of what changed and why
4. **Link to issues/PRs** where applicable
5. **Update upgrade guides** for breaking changes

### Change Categories

- **🚀 Added** - New features and functionality
- **🎨 Changed** - Modifications to existing features
- **🐛 Fixed** - Bug fixes and error corrections
- **🔧 Technical** - Internal improvements and refactoring
- **💔 Breaking** - Changes that break backward compatibility
- **🗑️ Removed** - Deprecated features removed
- **🔒 Security** - Security-related improvements

---

## Release Schedule

ArBot follows a regular release schedule:

- **Major releases** (x.0.0): Every 6 months with significant new features
- **Minor releases** (x.y.0): Every 2-3 months with new features and improvements
- **Patch releases** (x.y.z): As needed for bug fixes and security updates

### Release Process

1. **Feature freeze** 2 weeks before release
2. **Beta testing** with community feedback
3. **Documentation updates** and migration guides
4. **Final testing** across all supported platforms
5. **Release announcement** with detailed changelog

---

!!! tip "Stay Updated"
    - Watch the [GitHub repository](https://github.com/FinAI6/arbot) for release notifications
    - Join our community discussions for early access to features
    - Follow the [development roadmap](../development/contributing.md) for upcoming features

!!! info "Version Support"
    - **Current version**: Full support with new features and bug fixes
    - **Previous major version**: Security updates and critical bug fixes only
    - **Older versions**: Community support through GitHub issues