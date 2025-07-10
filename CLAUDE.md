# CLAUDE.md – Developer Guide for `arbot`

## Project Overview
`arbot` is a modular, real-time arbitrage trading bot that monitors and exploits price spreads between multiple centralized crypto exchanges (e.g., Binance, Bybit, OKX, Bitget). It supports both real-time trading and simulation modes and is controlled via a terminal-based UI using Textual.

---

## Goals
- Detect arbitrage opportunities using live price data via WebSocket feeds
- Support multiple exchanges with pluggable adapters
- Execute simultaneous trades (or simulations)
- Provide a backtest engine using historical price data
- Visualize everything in a modern terminal UI
- Ensure modularity, testability, and clean async design

---

## Architecture
```
arbot/
├── main.py # Orchestration and entrypoint
├── config.py # Global settings, API keys, thresholds
├── database.py # SQLite models and persistence
├── strategy.py # Arbitrage detection logic
├── trader.py # Live order placement logic
├── simulator.py # Simulated trader for testing
├── backtester.py # Historical simulation engine
├── ui.py # Textual UI implementation
└── exchanges/
  ├── base.py # BaseExchange (abstract class)
  ├── binance.py # Implements BaseExchange
  ├── bybit.py
  ├── bitget.py
  └── okx.py
```

---

## Development Instructions

### Exchange Module Guidelines
- Each exchange must implement `BaseExchange` defined in `exchanges/base.py`.
- Required methods:
  - `connect_ws()`: Subscribe to live ticker/orderbook
  - `get_orderbook()`: Return current bid/ask
  - `place_order()`: Submit order
  - `cancel_order()`: Cancel active order
  - `get_balance()`: Retrieve account balance

### Strategy
- Inputs: real-time prices from two or more exchanges
- Output: arbitrage signal if (ask_A + fee < bid_B - fee)
- Must account for:
  - Fees
  - Slippage
  - Minimum profit threshold

### Modes
- `Live mode`: Uses real API keys to place real orders
- `Sim mode`: Uses live prices but mocks orders and fills
- `Backtest mode`: Replays historical data from DB or CSV

### Textual UI
- Show:
  - Prices and spreads per exchange pair
  - Trade history
  - Account balances
  - Start/stop control
  - Strategy settings (editable)

---

## Rules & Constraints

- No testnet: Only live prices allowed (even in sim mode)
- All code must be async
- No hardcoded exchange logic in strategy/trader
- Use retry logic and reconnection handling in WebSocket clients
- Prioritize performance and modularity
- SQLite only (no external DB)
- Deployment target: PyInstaller or Docker

---

## How to Start
Begin by:
1. Implementing `BaseExchange` in `exchanges/base.py`
2. Stubbing out `binance/client.py` and `bybit/client.py`
3. Building `main.py` to orchestrate data collection and strategy loop
4. Creating a basic UI layout in `ui.py` using `Textual`
5. Testing in `simulator.py` first before live trading

---

## Naming Convention
- Project: `arbot`
- Python packages/modules: lowercase with underscores
- Class names: PascalCase
- Async functions: use `async def` and `await` best practices

---

## License
MIT 

---

## Contact
Lead Developer: Euiyun Kim  
GitHub: [https://github.com/FinAI6/arbot]  
Email: geniuskey@gmail.com
