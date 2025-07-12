import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, DataTable, Button, Label, Input, 
    TabbedContent, TabPane, RichLog, Switch, Select, ProgressBar
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from .config import Config, TradingMode
from .database import Database
from .strategy import ArbitrageStrategy, ArbitrageSignal
from .trader import LiveTrader
from .simulator import TradingSimulator
from .backtester import Backtester
from .exchanges import BinanceExchange, BybitExchange

logger = logging.getLogger(__name__)


@dataclass
class UIState:
    trading_active: bool = False
    trading_mode: TradingMode = TradingMode.SIMULATION
    connected_exchanges: List[str] = None
    active_symbols: List[str] = None
    total_profit: float = 0.0
    total_trades: int = 0
    active_opportunities: int = 0
    last_update: float = 0.0


class StatusWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = UIState()
    
    def update_state(self, state: UIState):
        self.state = state
        self.refresh()
    
    def render(self) -> Panel:
        status_text = Text()
        
        # Trading status
        if self.state.trading_active:
            status_text.append("● RUNNING", style="bold green")
        else:
            status_text.append("● STOPPED", style="bold red")
        
        status_text.append(f" | Mode: {self.state.trading_mode.value.upper()}", style="cyan")
        
        # Exchanges
        if self.state.connected_exchanges:
            status_text.append(f" | Exchanges: {', '.join(self.state.connected_exchanges)}", style="blue")
        
        # Statistics
        status_text.append(f" | Profit: ${self.state.total_profit:.2f}", style="green" if self.state.total_profit >= 0 else "red")
        status_text.append(f" | Trades: {self.state.total_trades}", style="yellow")
        status_text.append(f" | Opportunities: {self.state.active_opportunities}", style="magenta")
        
        # Last update
        if self.state.last_update > 0:
            last_update_str = datetime.fromtimestamp(self.state.last_update).strftime('%H:%M:%S')
            status_text.append(f" | Updated: {last_update_str}", style="dim")
        
        return Panel(
            Align.center(status_text),
            title="System Status",
            border_style="blue"
        )


class PriceWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prices: Dict[str, Dict[str, float]] = {}
        self.spreads: Dict[str, float] = {}
    
    def update_prices(self, prices: Dict[str, Dict[str, float]], spreads: Dict[str, float]):
        self.prices = prices
        self.spreads = spreads
        self.refresh()
    
    def render(self) -> Panel:
        if not self.prices:
            return Panel("No price data available", title="Live Prices")
        
        table = Table(title="Live Prices & Spreads")
        table.add_column("Symbol", style="cyan")
        table.add_column("Exchange", style="blue")
        table.add_column("Bid", style="green")
        table.add_column("Ask", style="red")
        table.add_column("Spread", style="yellow")
        table.add_column("Best Arb", style="magenta")
        
        for symbol, exchange_prices in self.prices.items():
            for exchange, price_data in exchange_prices.items():
                bid = price_data.get('bid', 0)
                ask = price_data.get('ask', 0)
                spread = ((ask - bid) / bid * 100) if bid > 0 else 0
                best_arb = self.spreads.get(f"{symbol}_{exchange}", 0)
                
                table.add_row(
                    symbol,
                    exchange,
                    f"{bid:.6f}",
                    f"{ask:.6f}",
                    f"{spread:.3f}%",
                    f"{best_arb:.3f}%" if best_arb > 0 else "-"
                )
        
        return Panel(table, title="Live Prices & Spreads")


class TradesWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recent_trades: List[Dict] = []
    
    def update_trades(self, trades: List[Dict]):
        self.recent_trades = trades[-10:]  # Keep last 10 trades
        self.refresh()
    
    def render(self) -> Panel:
        if not self.recent_trades:
            return Panel("No recent trades", title="Recent Trades")
        
        table = Table(title="Recent Trades")
        table.add_column("Time", style="cyan")
        table.add_column("Symbol", style="blue")
        table.add_column("Type", style="yellow")
        table.add_column("Buy Exchange", style="green")
        table.add_column("Sell Exchange", style="red")
        table.add_column("Profit", style="magenta")
        table.add_column("Status", style="white")
        
        for trade in self.recent_trades:
            time_str = datetime.fromtimestamp(trade.get('timestamp', 0)).strftime('%H:%M:%S')
            profit = trade.get('profit', 0)
            profit_str = f"${profit:.2f}" if profit != 0 else "-"
            profit_style = "green" if profit > 0 else "red" if profit < 0 else "white"
            
            table.add_row(
                time_str,
                trade.get('symbol', ''),
                'ARB',
                trade.get('buy_exchange', ''),
                trade.get('sell_exchange', ''),
                Text(profit_str, style=profit_style),
                trade.get('status', '')
            )
        
        return Panel(table, title="Recent Trades")


class OpportunitiesWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.opportunities: List[ArbitrageSignal] = []
    
    def update_opportunities(self, opportunities: List[ArbitrageSignal]):
        self.opportunities = opportunities
        self.refresh()
    
    def render(self) -> Panel:
        if not self.opportunities:
            return Panel("No current opportunities", title="Arbitrage Opportunities")
        
        table = Table(title="Arbitrage Opportunities")
        table.add_column("Symbol", style="cyan")
        table.add_column("Buy Exchange", style="green")
        table.add_column("Sell Exchange", style="red")
        table.add_column("Buy Price", style="blue")
        table.add_column("Sell Price", style="blue")
        table.add_column("Profit %", style="magenta")
        table.add_column("Size", style="yellow")
        table.add_column("Age", style="dim")
        
        current_time = time.time()
        
        for opp in self.opportunities:
            age = int(current_time - opp.timestamp)
            size = min(opp.buy_size, opp.sell_size)
            
            table.add_row(
                opp.symbol,
                opp.buy_exchange,
                opp.sell_exchange,
                f"{opp.buy_price:.6f}",
                f"{opp.sell_price:.6f}",
                f"{opp.profit_percent:.3f}%",
                f"{size:.2f}",
                f"{age}s"
            )
        
        return Panel(table, title="Arbitrage Opportunities")


class BalanceWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.balances: Dict[str, Dict[str, float]] = {}
    
    def update_balances(self, balances: Dict[str, Dict[str, float]]):
        self.balances = balances
        self.refresh()
    
    def render(self) -> Panel:
        if not self.balances:
            return Panel("No balance data", title="Account Balances")
        
        table = Table(title="Account Balances")
        table.add_column("Exchange", style="cyan")
        table.add_column("Asset", style="blue")
        table.add_column("Free", style="green")
        table.add_column("Locked", style="yellow")
        table.add_column("Total", style="magenta")
        
        for exchange, assets in self.balances.items():
            for asset, balance in assets.items():
                if isinstance(balance, dict):
                    free = balance.get('free', 0)
                    locked = balance.get('locked', 0)
                    total = balance.get('total', 0)
                else:
                    free = balance
                    locked = 0
                    total = balance
                
                # Only show non-zero balances
                if total > 0.001:
                    table.add_row(
                        exchange,
                        asset,
                        f"{free:.6f}",
                        f"{locked:.6f}",
                        f"{total:.6f}"
                    )
        
        return Panel(table, title="Account Balances")


class ControlPanel(Container):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trading_active = False
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("Start", id="start_button", variant="success")
            yield Button("Stop", id="stop_button", variant="error")
            yield Button("Reset", id="reset_button", variant="warning")
        
        with Horizontal():
            yield Label("Trading Mode:")
            yield Select(
                [(mode.value.title(), mode.value) for mode in TradingMode],
                value=TradingMode.SIMULATION.value,
                id="mode_select"
            )
        
        with Horizontal():
            yield Label("Min Profit %:")
            yield Input(placeholder="0.1", id="min_profit_input")
        
        with Horizontal():
            yield Label("Trade Amount USD:")
            yield Input(placeholder="100", id="trade_amount_input")


class ArbitrageBotApp(App):
    """A Textual app for the Arbitrage Bot"""
    
    TITLE = "ArBot - Arbitrage Trading Bot"
    SUB_TITLE = "Real-time Cryptocurrency Arbitrage"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start_stop", "Start/Stop"),
        Binding("r", "reset", "Reset"),
        Binding("h", "help", "Help"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]
    
    def __init__(self, config: Config, database: Database, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.database = database
        self.exchanges = {}
        self.strategy = None
        self.trader = None
        self.simulator = None
        self.backtester = None
        
        # UI state
        self.ui_state = UIState()
        self.trading_active = False
        self.last_update = 0
        
        # Data for widgets
        self.recent_trades = []
        self.current_opportunities = []
        self.current_balances = {}
        self.current_prices = {}
        self.current_spreads = {}
        
        # Update task
        self.update_task = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        
        yield Header()
        
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                with Vertical():
                    yield StatusWidget(id="status_widget")
                    
                    with Horizontal():
                        yield PriceWidget(id="price_widget")
                        yield OpportunitiesWidget(id="opportunities_widget")
                    
                    with Horizontal():
                        yield TradesWidget(id="trades_widget")
                        yield BalanceWidget(id="balance_widget")
            
            with TabPane("Controls", id="controls"):
                yield ControlPanel(id="control_panel")
            
            with TabPane("Logs", id="logs"):
                yield RichLog(id="log_widget", auto_scroll=True)
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Called when app starts."""
        # Initialize components
        await self._initialize_components()
        
        # Start update task
        self.update_task = asyncio.create_task(self._update_loop())
        
        # Setup logging
        log_widget = self.query_one("#log_widget", RichLog)
        
        # Create a custom log handler to send logs to the UI
        class UILogHandler(logging.Handler):
            def __init__(self, log_widget):
                super().__init__()
                self.log_widget = log_widget
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.log_widget.write(msg)
                except Exception:
                    pass
        
        ui_handler = UILogHandler(log_widget)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add handler to root logger
        logging.getLogger().addHandler(ui_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        log_widget.write("ArBot UI started successfully!")
    
    async def _initialize_components(self):
        """Initialize trading components"""
        try:
            logger.info("Starting UI component initialization")
            
            # Initialize database
            logger.info("Initializing database")
            await self.database.initialize()
            logger.info("Database initialized successfully")
            
            # Initialize exchanges
            logger.info("Initializing exchanges")
            for exchange_name, exchange_config in self.config.exchanges.items():
                if not exchange_config.enabled:
                    continue
                
                if exchange_name == 'binance':
                    exchange = BinanceExchange(
                        exchange_config.api_key,
                        exchange_config.api_secret,
                        exchange_config.testnet
                    )
                elif exchange_name == 'bybit':
                    exchange = BybitExchange(
                        exchange_config.api_key,
                        exchange_config.api_secret,
                        exchange_config.testnet
                    )
                else:
                    continue
                
                self.exchanges[exchange_name] = exchange
                logger.info(f"Created exchange: {exchange_name}")
            
            logger.info(f"Created {len(self.exchanges)} exchanges")
            
            # Initialize strategy
            logger.info("Initializing arbitrage strategy")
            self.strategy = ArbitrageStrategy(self.config, self.database)
            await self.strategy.initialize(self.exchanges)
            self.strategy.add_signal_callback(self._on_arbitrage_signal)
            logger.info("Strategy initialized successfully")
            
            # Initialize trader/simulator based on mode
            logger.info(f"Initializing trader/simulator for mode: {self.config.trading_mode}")
            if self.config.trading_mode == TradingMode.LIVE:
                self.trader = LiveTrader(self.config, self.database)
                await self.trader.initialize(self.exchanges)
                logger.info("Live trader initialized successfully")
            else:
                self.simulator = TradingSimulator(self.config, self.database)
                logger.info("Simulator initialized successfully")
            
            # Initialize backtester
            logger.info("Initializing backtester")
            self.backtester = Backtester(self.config, self.database)
            logger.info("Backtester initialized successfully")
            
            # Update UI state
            logger.info("Updating UI state")
            self.ui_state.trading_mode = self.config.trading_mode
            self.ui_state.connected_exchanges = list(self.exchanges.keys())
            self.ui_state.active_symbols = self.config.arbitrage.symbols
            logger.info("UI component initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await self.action_quit()
    
    async def _update_loop(self):
        """Main update loop for the UI"""
        while True:
            try:
                await asyncio.sleep(self.config.ui.refresh_rate_ms / 1000.0)
                await self._update_ui_data()
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
    
    async def _update_ui_data(self):
        """Update UI data from components"""
        try:
            current_time = time.time()
            
            # Update strategy stats
            if self.strategy:
                strategy_stats = self.strategy.get_stats()
                self.current_opportunities = self.strategy.get_recent_signals(10)
                
                self.ui_state.active_opportunities = len(self.current_opportunities)
            
            # Update trader/simulator stats
            if self.trader and self.config.trading_mode == TradingMode.LIVE:
                trader_stats = self.trader.get_stats()
                self.ui_state.total_profit = trader_stats.get('total_profit', 0)
                self.ui_state.total_trades = trader_stats.get('total_trades', 0)
                
                # Get balances
                self.current_balances = self.trader.balances
                
                # Get recent trades
                active_trades = self.trader.get_active_trades()
                self.recent_trades = [
                    {
                        'timestamp': trade.start_time,
                        'symbol': trade.signal.symbol,
                        'buy_exchange': trade.signal.buy_exchange,
                        'sell_exchange': trade.signal.sell_exchange,
                        'profit': trade.actual_profit,
                        'status': trade.status.value
                    }
                    for trade in active_trades
                ]
            
            elif self.simulator:
                sim_stats = self.simulator.get_stats()
                self.ui_state.total_profit = sim_stats.get('net_profit', 0)
                self.ui_state.total_trades = sim_stats.get('total_trades', 0)
                
                # Get balances
                sim_balances = self.simulator.get_balances()
                self.current_balances = {
                    exchange: {
                        asset: {
                            'free': balance.free,
                            'locked': balance.locked,
                            'total': balance.total
                        }
                        for asset, balance in assets.items()
                    }
                    for exchange, assets in sim_balances.items()
                }
                
                # Get recent trades
                completed_trades = self.simulator.get_completed_trades()
                self.recent_trades = [
                    {
                        'timestamp': trade.start_time,
                        'symbol': trade.signal.symbol,
                        'buy_exchange': trade.signal.buy_exchange,
                        'sell_exchange': trade.signal.sell_exchange,
                        'profit': trade.actual_profit,
                        'status': trade.status
                    }
                    for trade in completed_trades[-10:]
                ]
            
            # Update UI state
            self.ui_state.trading_active = self.trading_active
            self.ui_state.last_update = current_time
            
            # Update widgets
            self._update_widgets()
            
        except Exception as e:
            logger.error(f"Error updating UI data: {e}")
    
    def _update_widgets(self):
        """Update all widgets with current data"""
        try:
            # Update status widget
            status_widget = self.query_one("#status_widget", StatusWidget)
            status_widget.update_state(self.ui_state)
            
            # Update price widget
            price_widget = self.query_one("#price_widget", PriceWidget)
            price_widget.update_prices(self.current_prices, self.current_spreads)
            
            # Update opportunities widget
            opportunities_widget = self.query_one("#opportunities_widget", OpportunitiesWidget)
            opportunities_widget.update_opportunities(self.current_opportunities)
            
            # Update trades widget
            trades_widget = self.query_one("#trades_widget", TradesWidget)
            trades_widget.update_trades(self.recent_trades)
            
            # Update balance widget
            balance_widget = self.query_one("#balance_widget", BalanceWidget)
            balance_widget.update_balances(self.current_balances)
            
        except Exception as e:
            logger.error(f"Error updating widgets: {e}")
    
    async def _on_arbitrage_signal(self, signal: ArbitrageSignal):
        """Handle arbitrage signals"""
        try:
            # Execute the trade
            if self.config.trading_mode == TradingMode.LIVE and self.trader:
                await self.trader.execute_arbitrage(signal)
            elif self.simulator:
                await self.simulator.execute_arbitrage(signal)
            
            logger.info(f"Arbitrage signal processed: {signal.symbol} "
                       f"{signal.buy_exchange}->{signal.sell_exchange} "
                       f"Profit: {signal.profit_percent:.3f}%")
            
        except Exception as e:
            logger.error(f"Error processing arbitrage signal: {e}")
    
    async def action_start_stop(self):
        """Start or stop the trading bot"""
        if self.trading_active:
            await self._stop_bot()
        else:
            await self._start_bot()
    
    async def _start_bot(self):
        """Start the trading bot"""
        try:
            # Start strategy
            if self.strategy:
                await self.strategy.start()
            
            # Start trader/simulator
            if self.config.trading_mode == TradingMode.LIVE and self.trader:
                await self.trader.start()
            elif self.simulator:
                await self.simulator.start()
            
            # Connect to exchanges
            for exchange_name, exchange in self.exchanges.items():
                await exchange.connect_ws(self.config.arbitrage.symbols)
            
            self.trading_active = True
            logger.info("Trading bot started")
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
    
    async def _stop_bot(self):
        """Stop the trading bot"""
        try:
            # Stop strategy
            if self.strategy:
                await self.strategy.stop()
            
            # Stop trader/simulator
            if self.trader:
                await self.trader.stop()
            elif self.simulator:
                await self.simulator.stop()
            
            # Disconnect from exchanges and close sessions
            for exchange in self.exchanges.values():
                await exchange.disconnect_ws()
                if hasattr(exchange, 'session') and exchange.session and not exchange.session.closed:
                    await exchange.session.close()
            
            self.trading_active = False
            logger.info("Trading bot stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop bot: {e}")
    
    async def action_reset(self):
        """Reset the bot state"""
        try:
            if self.trading_active:
                await self._stop_bot()
            
            # Reset simulator if using simulation mode
            if self.simulator:
                self.simulator = TradingSimulator(self.config, self.database)
            
            # Clear UI data
            self.recent_trades = []
            self.current_opportunities = []
            self.ui_state.total_profit = 0
            self.ui_state.total_trades = 0
            
            logger.info("Bot state reset")
            
        except Exception as e:
            logger.error(f"Failed to reset bot: {e}")
    
    async def action_help(self):
        """Show help information"""
        help_text = """
        ArBot - Arbitrage Trading Bot
        
        Keyboard Shortcuts:
        - q: Quit the application
        - s: Start/Stop trading
        - r: Reset bot state
        - h: Show this help
        
        Tabs:
        - Dashboard: Main view with prices, trades, and opportunities
        - Controls: Trading configuration and controls
        - Logs: System logs and messages
        
        Trading Modes:
        - Live: Real trading with actual funds
        - Simulation: Paper trading with simulated funds
        - Backtest: Historical data analysis
        """
        
        log_widget = self.query_one("#log_widget", RichLog)
        log_widget.write(help_text)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "start_button":
            await self._start_bot()
        elif event.button.id == "stop_button":
            await self._stop_bot()
        elif event.button.id == "reset_button":
            await self.action_reset()
    
    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes"""
        if event.select.id == "mode_select":
            try:
                new_mode = TradingMode(event.value)
                if new_mode != self.config.trading_mode:
                    self.config.trading_mode = new_mode
                    await self._initialize_components()
                    logger.info(f"Trading mode changed to {new_mode.value}")
            except Exception as e:
                logger.error(f"Failed to change trading mode: {e}")
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes"""
        try:
            if event.input.id == "min_profit_input":
                value = float(event.value)
                self.config.arbitrage.min_profit_threshold = value / 100  # Convert to decimal
                logger.info(f"Min profit threshold set to {value}%")
            elif event.input.id == "trade_amount_input":
                value = float(event.value)
                self.config.arbitrage.trade_amount_usd = value
                logger.info(f"Trade amount set to ${value}")
        except ValueError:
            pass  # Ignore invalid input
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
    
    async def on_unmount(self) -> None:
        """Called when app shuts down"""
        try:
            if self.update_task:
                self.update_task.cancel()
            
            if self.trading_active:
                await self._stop_bot()
            
            # Ensure all exchanges are properly cleaned up
            await self._cleanup_exchanges()
            
        except Exception as e:
            logger.error(f"Error during app unmount: {e}")
    
    async def _cleanup_exchanges(self):
        """Clean up all exchange resources"""
        logger.info(f"Starting cleanup of {len(self.exchanges)} exchanges")
        for exchange_name, exchange in self.exchanges.items():
            try:
                logger.info(f"Cleaning up exchange: {exchange_name}")
                # Close WebSocket connections
                await exchange.disconnect_ws()
                # Close HTTP sessions
                if hasattr(exchange, 'session') and exchange.session and not exchange.session.closed:
                    await exchange.session.close()
                    logger.info(f"Closed session for {exchange_name}")
            except Exception as e:
                logger.error(f"Error cleaning up exchange {exchange_name}: {e}")
        logger.info("Exchange cleanup completed")


async def run_ui(config: Config, database: Database):
    """Run the Textual UI"""
    app = ArbitrageBotApp(config, database)
    try:
        logger.info("Starting Textual UI application")
        await app.run_async()
        logger.info("Textual UI application finished normally")
    except Exception as e:
        logger.error(f"Error in UI app: {e}")
        import traceback
        logger.error(f"UI app traceback: {traceback.format_exc()}")
    finally:
        logger.info("Running UI cleanup")
        # Ensure cleanup happens even if the app exits unexpectedly
        await app._cleanup_exchanges()