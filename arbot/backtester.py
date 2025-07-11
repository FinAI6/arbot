import asyncio
import csv
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging
import pandas as pd

from .database import Database, TickerRecord, TradeRecord
from .strategy import ArbitrageStrategy, ArbitrageSignal
from .simulator import TradingSimulator
from .exchanges.base import Ticker
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    start_date: datetime
    end_date: datetime
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_profit: float
    total_fees: float
    net_profit: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_profit_per_trade: float
    total_volume: float
    profit_factor: float
    trades: List[TradeRecord] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    portfolio_values: List[Tuple[datetime, float]] = field(default_factory=list)


class Backtester:
    def __init__(self, config: Config, database: Database):
        self.config = config
        self.database = database
        self.strategy = ArbitrageStrategy(config, database)
        self.simulator = TradingSimulator(config, database)
        self.historical_data: Dict[str, List[TickerRecord]] = {}
        self.current_time = 0.0
        self.backtest_start_time = 0.0
        self.backtest_end_time = 0.0
        
        # Performance tracking
        self.portfolio_values = []
        self.daily_returns = []
        self.trades_executed = []
        
        # Connect strategy to simulator
        self.strategy.add_signal_callback(self._on_arbitrage_signal)
    
    async def load_historical_data(self, start_date: str, end_date: str, 
                                 symbols: List[str], exchanges: List[str]) -> None:
        """Load historical data from database or CSV files"""
        
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        
        self.backtest_start_time = start_datetime.timestamp()
        self.backtest_end_time = end_datetime.timestamp()
        
        if self.config.backtest.data_source == 'database':
            await self._load_from_database(start_datetime, end_datetime, symbols, exchanges)
        elif self.config.backtest.data_source == 'csv':
            await self._load_from_csv(symbols, exchanges)
        else:
            raise ValueError(f"Unknown data source: {self.config.backtest.data_source}")
        
        logger.info(f"Loaded historical data from {start_date} to {end_date}")
        for exchange in exchanges:
            for symbol in symbols:
                key = f"{exchange}_{symbol}"
                count = len(self.historical_data.get(key, []))
                logger.info(f"  {exchange} {symbol}: {count} records")
    
    async def _load_from_database(self, start_datetime: datetime, end_datetime: datetime,
                                symbols: List[str], exchanges: List[str]) -> None:
        """Load historical data from database"""
        
        start_timestamp = start_datetime.timestamp()
        end_timestamp = end_datetime.timestamp()
        
        # Query database for historical ticker data
        async with self.database.db_path as db_path:
            import aiosqlite
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                
                for exchange in exchanges:
                    for symbol in symbols:
                        cursor = await db.execute('''
                            SELECT * FROM tickers 
                            WHERE exchange = ? AND symbol = ? 
                            AND timestamp >= ? AND timestamp <= ?
                            ORDER BY timestamp ASC
                        ''', (exchange, symbol, start_timestamp, end_timestamp))
                        
                        rows = await cursor.fetchall()
                        
                        key = f"{exchange}_{symbol}"
                        self.historical_data[key] = [
                            TickerRecord(**dict(row)) for row in rows
                        ]
    
    async def _load_from_csv(self, symbols: List[str], exchanges: List[str]) -> None:
        """Load historical data from CSV files"""
        
        if not self.config.backtest.csv_path:
            raise ValueError("CSV path not specified in config")
        
        import os
        csv_dir = self.config.backtest.csv_path
        
        for exchange in exchanges:
            for symbol in symbols:
                csv_file = os.path.join(csv_dir, f"{exchange}_{symbol}.csv")
                
                if not os.path.exists(csv_file):
                    logger.warning(f"CSV file not found: {csv_file}")
                    continue
                
                key = f"{exchange}_{symbol}"
                self.historical_data[key] = []
                
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        # Assuming CSV format: timestamp,bid,ask,bid_size,ask_size
                        timestamp = float(row['timestamp'])
                        
                        # Filter by date range
                        if timestamp < self.backtest_start_time or timestamp > self.backtest_end_time:
                            continue
                        
                        ticker = TickerRecord(
                            exchange=exchange,
                            symbol=symbol,
                            bid=float(row['bid']),
                            ask=float(row['ask']),
                            bid_size=float(row['bid_size']),
                            ask_size=float(row['ask_size']),
                            timestamp=timestamp
                        )
                        
                        self.historical_data[key].append(ticker)
    
    async def run_backtest(self) -> BacktestResult:
        """Run the backtest simulation"""
        
        if not self.historical_data:
            raise ValueError("No historical data loaded")
        
        logger.info("Starting backtest simulation...")
        
        # Initialize simulator and strategy
        await self.simulator.start()
        await self.strategy.start()
        
        # Get all timestamps and sort them
        all_timestamps = set()
        for data_list in self.historical_data.values():
            for record in data_list:
                all_timestamps.add(record.timestamp)
        
        sorted_timestamps = sorted(all_timestamps)
        
        # Track initial portfolio value
        initial_value = self.simulator._calculate_portfolio_value()
        self.portfolio_values.append((datetime.fromtimestamp(self.backtest_start_time), initial_value))
        
        # Process each timestamp
        total_ticks = len(sorted_timestamps)
        processed_ticks = 0
        
        for timestamp in sorted_timestamps:
            self.current_time = timestamp
            
            # Process all ticker updates for this timestamp
            await self._process_timestamp(timestamp)
            
            # Record portfolio value (daily)
            if processed_ticks % 86400 == 0:  # Once per day (assuming 1-second intervals)
                current_value = self.simulator._calculate_portfolio_value()
                self.portfolio_values.append((datetime.fromtimestamp(timestamp), current_value))
            
            processed_ticks += 1
            
            # Progress logging
            if processed_ticks % 10000 == 0:
                progress = (processed_ticks / total_ticks) * 100
                logger.info(f"Backtest progress: {progress:.1f}% ({processed_ticks}/{total_ticks})")
        
        # Stop simulator and strategy
        await self.simulator.stop()
        await self.strategy.stop()
        
        # Calculate final results
        result = await self._calculate_results()
        
        logger.info("Backtest completed")
        logger.info(f"Total trades: {result.total_trades}")
        logger.info(f"Net profit: ${result.net_profit:.2f}")
        logger.info(f"Win rate: {result.win_rate:.1f}%")
        logger.info(f"Max drawdown: {result.max_drawdown:.2f}%")
        logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
        
        return result
    
    async def _process_timestamp(self, timestamp: float) -> None:
        """Process all ticker updates for a given timestamp"""
        
        # Find all ticker records for this timestamp
        ticker_updates = []
        
        for key, data_list in self.historical_data.items():
            for record in data_list:
                if record.timestamp == timestamp:
                    ticker_updates.append(record)
        
        # Process ticker updates
        for ticker_record in ticker_updates:
            # Convert to Ticker object
            ticker = Ticker(
                symbol=ticker_record.symbol,
                bid=ticker_record.bid,
                ask=ticker_record.ask,
                bid_size=ticker_record.bid_size,
                ask_size=ticker_record.ask_size,
                timestamp=ticker_record.timestamp
            )
            
            # Send to strategy for arbitrage detection
            await self.strategy._on_ticker_update(ticker)
    
    async def _on_arbitrage_signal(self, signal: ArbitrageSignal) -> None:
        """Handle arbitrage signals during backtest"""
        
        # Execute the signal using the simulator
        success = await self.simulator.execute_arbitrage(signal)
        
        if success:
            self.trades_executed.append(signal)
            self.strategy.mark_signal_executed(signal.profit)
    
    async def _calculate_results(self) -> BacktestResult:
        """Calculate backtest results"""
        
        # Get simulator statistics
        sim_stats = self.simulator.get_stats()
        
        # Calculate daily returns
        self.daily_returns = []
        for i in range(1, len(self.portfolio_values)):
            prev_value = self.portfolio_values[i-1][1]
            curr_value = self.portfolio_values[i][1]
            daily_return = (curr_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)
        
        # Calculate Sharpe ratio
        if len(self.daily_returns) > 0:
            avg_return = sum(self.daily_returns) / len(self.daily_returns)
            return_std = (sum([(r - avg_return) ** 2 for r in self.daily_returns]) / len(self.daily_returns)) ** 0.5
            sharpe_ratio = (avg_return / return_std) * (252 ** 0.5) if return_std > 0 else 0  # Annualized
        else:
            sharpe_ratio = 0
        
        # Calculate profit factor
        winning_trades = [t for t in self.simulator.completed_trades if t.actual_profit > 0]
        losing_trades = [t for t in self.simulator.completed_trades if t.actual_profit <= 0]
        
        total_wins = sum(t.actual_profit for t in winning_trades)
        total_losses = abs(sum(t.actual_profit for t in losing_trades))
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Get completed trades from database
        completed_trades = await self.database.get_trades(limit=1000)
        
        return BacktestResult(
            start_date=datetime.fromtimestamp(self.backtest_start_time),
            end_date=datetime.fromtimestamp(self.backtest_end_time),
            total_trades=sim_stats['total_trades'],
            successful_trades=sim_stats['successful_trades'],
            failed_trades=sim_stats['failed_trades'],
            total_profit=sim_stats['total_profit'],
            total_fees=sim_stats['total_fees'],
            net_profit=sim_stats['net_profit'],
            max_drawdown=sim_stats['max_drawdown'],
            sharpe_ratio=sharpe_ratio,
            win_rate=sim_stats['success_rate'],
            avg_profit_per_trade=sim_stats['net_profit'] / sim_stats['total_trades'] if sim_stats['total_trades'] > 0 else 0,
            total_volume=sim_stats['total_volume'],
            profit_factor=profit_factor,
            trades=completed_trades,
            daily_returns=self.daily_returns,
            portfolio_values=self.portfolio_values
        )
    
    async def export_results(self, result: BacktestResult, output_file: str) -> None:
        """Export backtest results to CSV"""
        
        # Export summary
        summary_file = output_file.replace('.csv', '_summary.csv')
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Start Date', result.start_date.strftime('%Y-%m-%d')])
            writer.writerow(['End Date', result.end_date.strftime('%Y-%m-%d')])
            writer.writerow(['Total Trades', result.total_trades])
            writer.writerow(['Successful Trades', result.successful_trades])
            writer.writerow(['Failed Trades', result.failed_trades])
            writer.writerow(['Win Rate (%)', f"{result.win_rate:.2f}"])
            writer.writerow(['Total Profit ($)', f"{result.total_profit:.2f}"])
            writer.writerow(['Total Fees ($)', f"{result.total_fees:.2f}"])
            writer.writerow(['Net Profit ($)', f"{result.net_profit:.2f}"])
            writer.writerow(['Max Drawdown (%)', f"{result.max_drawdown:.2f}"])
            writer.writerow(['Sharpe Ratio', f"{result.sharpe_ratio:.2f}"])
            writer.writerow(['Avg Profit Per Trade ($)', f"{result.avg_profit_per_trade:.2f}"])
            writer.writerow(['Total Volume ($)', f"{result.total_volume:.2f}"])
            writer.writerow(['Profit Factor', f"{result.profit_factor:.2f}"])
        
        # Export trades
        trades_file = output_file.replace('.csv', '_trades.csv')
        with open(trades_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Symbol', 'Buy Exchange', 'Sell Exchange', 'Buy Price', 
                           'Sell Price', 'Quantity', 'Profit', 'Profit %', 'Status', 'Timestamp'])
            
            for trade in result.trades:
                writer.writerow([
                    trade.id,
                    trade.symbol,
                    trade.buy_exchange,
                    trade.sell_exchange,
                    trade.buy_price,
                    trade.sell_price,
                    trade.quantity,
                    trade.profit,
                    trade.profit_percent,
                    trade.status,
                    datetime.fromtimestamp(trade.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        # Export portfolio values
        portfolio_file = output_file.replace('.csv', '_portfolio.csv')
        with open(portfolio_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Portfolio Value', 'Daily Return'])
            
            for i, (date, value) in enumerate(result.portfolio_values):
                daily_return = result.daily_returns[i-1] if i > 0 else 0
                writer.writerow([
                    date.strftime('%Y-%m-%d'),
                    f"{value:.2f}",
                    f"{daily_return:.6f}"
                ])
        
        logger.info(f"Backtest results exported to {summary_file}, {trades_file}, {portfolio_file}")
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generate a detailed backtest report"""
        
        report = f"""
ARBOT BACKTEST REPORT
====================

Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}
Duration: {(result.end_date - result.start_date).days} days

TRADING PERFORMANCE
------------------
Total Trades: {result.total_trades}
Successful Trades: {result.successful_trades}
Failed Trades: {result.failed_trades}
Win Rate: {result.win_rate:.2f}%

PROFIT & LOSS
------------
Total Profit: ${result.total_profit:.2f}
Total Fees: ${result.total_fees:.2f}
Net Profit: ${result.net_profit:.2f}
Average Profit per Trade: ${result.avg_profit_per_trade:.2f}
Total Volume: ${result.total_volume:.2f}

RISK METRICS
-----------
Max Drawdown: {result.max_drawdown:.2f}%
Sharpe Ratio: {result.sharpe_ratio:.2f}
Profit Factor: {result.profit_factor:.2f}

STRATEGY PERFORMANCE
-------------------
"""
        
        if result.trades:
            # Top performing symbols
            symbol_profits = {}
            for trade in result.trades:
                if trade.symbol not in symbol_profits:
                    symbol_profits[trade.symbol] = 0
                symbol_profits[trade.symbol] += trade.profit
            
            sorted_symbols = sorted(symbol_profits.items(), key=lambda x: x[1], reverse=True)
            
            report += "Top Performing Symbols:\n"
            for symbol, profit in sorted_symbols[:5]:
                report += f"  {symbol}: ${profit:.2f}\n"
            
            # Exchange performance
            exchange_profits = {}
            for trade in result.trades:
                key = f"{trade.buy_exchange}-{trade.sell_exchange}"
                if key not in exchange_profits:
                    exchange_profits[key] = 0
                exchange_profits[key] += trade.profit
            
            sorted_exchanges = sorted(exchange_profits.items(), key=lambda x: x[1], reverse=True)
            
            report += "\nTop Exchange Pairs:\n"
            for pair, profit in sorted_exchanges[:5]:
                report += f"  {pair}: ${profit:.2f}\n"
        
        return report
    
    async def run_parameter_optimization(self, parameters: Dict[str, List[float]]) -> Dict[str, any]:
        """Run parameter optimization across different strategy settings"""
        
        best_result = None
        best_params = None
        best_score = float('-inf')
        
        # Generate parameter combinations
        import itertools
        
        param_names = list(parameters.keys())
        param_values = list(parameters.values())
        
        combinations = list(itertools.product(*param_values))
        
        logger.info(f"Running parameter optimization with {len(combinations)} combinations...")
        
        for i, combination in enumerate(combinations):
            param_dict = dict(zip(param_names, combination))
            
            logger.info(f"Testing parameters {i+1}/{len(combinations)}: {param_dict}")
            
            # Update config with new parameters
            original_config = {}
            for param_name, param_value in param_dict.items():
                if hasattr(self.config.arbitrage, param_name):
                    original_config[param_name] = getattr(self.config.arbitrage, param_name)
                    setattr(self.config.arbitrage, param_name, param_value)
            
            try:
                # Run backtest with these parameters
                result = await self.run_backtest()
                
                # Calculate optimization score (maximize Sharpe ratio * net profit)
                score = result.sharpe_ratio * result.net_profit
                
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_params = param_dict.copy()
                
                logger.info(f"Result: Net Profit ${result.net_profit:.2f}, Sharpe {result.sharpe_ratio:.2f}, Score {score:.2f}")
                
            except Exception as e:
                logger.error(f"Error running backtest with parameters {param_dict}: {e}")
            
            finally:
                # Restore original config
                for param_name, original_value in original_config.items():
                    setattr(self.config.arbitrage, param_name, original_value)
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_score': best_score
        }