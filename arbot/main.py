#!/usr/bin/env python3
"""
ArBot - Arbitrage Trading Bot
Main entry point for the application
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import time

from .config import Config, TradingMode
from .database import Database
from .strategy import ArbitrageStrategy
from .trader import LiveTrader
from .simulator import TradingSimulator
from .backtester import Backtester
from .ui import run_ui
from .exchanges import BinanceExchange, BybitExchange, BitgetExchange, OKXExchange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ArBot:
    """Main application class for ArBot"""
    
    def __init__(self, config: Config):
        self.config = config
        self.database = Database(config.database.db_path)
        self.exchanges = {}
        self.strategy = None
        self.trader = None
        self.simulator = None
        self.backtester = None
        self.is_running = False
        self.spread_monitor_task = None
        self.last_spreads = {}
        self.dynamic_symbols = []
        self.spread_history = {}  # For premium detection
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration and log warnings"""
        errors = self.config.validate_config()
        if errors:
            logger.error("❌ 설정 검증 실패:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
        
        print("✅ 설정 검증 완료")
        print(f"📊 거래 모드: {self._get_trading_mode_display()}")
        print(f"🏪 활성화된 거래소: {', '.join(self.config.get_enabled_exchanges())}")
        arbitrage_exchanges = self.config.get_arbitrage_exchanges()
        print(f"⚡ 차익거래 거래소: {', '.join(arbitrage_exchanges)} ({len(arbitrage_exchanges)}개)")
        print(f"🔍 동적 심볼 탐지: {'✅' if self.config.arbitrage.use_dynamic_symbols else '❌'}")
        print(f"💰 최소 볼륨: ${self.config.arbitrage.min_volume_usdt:,.0f}")
        print(f"🚫 최대 스프레드: {self.config.arbitrage.max_spread_threshold:.1f}% (이상치 필터링)")
        print(f"📈 프리미엄 감지: {'✅' if self.config.arbitrage.premium_detection.enabled else '❌'}")
        print()
    
    def _get_trading_mode_display(self):
        """거래 모드를 한글로 표시"""
        mode_display = {
            'live': '💰 실거래',
            'simulation': '🎮 시뮬레이션',
            'backtest': '📊 백테스트'
        }
        return mode_display.get(self.config.trading_mode.value, self.config.trading_mode.value)
    
    def normalize_ticker(self, ticker_data: Dict, exchange_name: str) -> Dict:
        """Normalize ticker data from different exchanges"""
        normalized = {}
        
        def safe_float(value, default=0.0):
            """Safely convert value to float"""
            try:
                return float(value) if value is not None and value != '' else default
            except (ValueError, TypeError):
                return default
        
        if exchange_name.lower() == 'bybit':
            # Bybit ticker format
            normalized = {
                'symbol': ticker_data.get('symbol'),
                'bid': safe_float(ticker_data.get('bid1Price')) or None,
                'ask': safe_float(ticker_data.get('ask1Price')) or None,
                'last_price': safe_float(ticker_data.get('lastPrice')),
                'volume': safe_float(ticker_data.get('volume24h')),
                'timestamp': time.time()
            }
        elif exchange_name.lower() == 'binance':
            # Binance ticker format
            normalized = {
                'symbol': ticker_data.get('symbol'),
                'bid': safe_float(ticker_data.get('bidPrice')) or None,
                'ask': safe_float(ticker_data.get('askPrice')) or None,
                'last_price': safe_float(ticker_data.get('price')) or safe_float(ticker_data.get('lastPrice')),
                'volume': safe_float(ticker_data.get('volume')),
                'timestamp': time.time()
            }
        elif exchange_name.lower() == 'okx':
            # OKX ticker format
            normalized = {
                'symbol': ticker_data.get('instId'),  # OKX uses instId
                'bid': safe_float(ticker_data.get('bidPx')) or None,
                'ask': safe_float(ticker_data.get('askPx')) or None,
                'last_price': safe_float(ticker_data.get('last')),
                'volume': safe_float(ticker_data.get('vol24h')),
                'timestamp': time.time()
            }
        elif exchange_name.lower() == 'bitget':
            # Bitget ticker format
            normalized = {
                'symbol': ticker_data.get('symbol'),
                'bid': safe_float(ticker_data.get('buyOne')) or None,  # Bitget uses buyOne for bid
                'ask': safe_float(ticker_data.get('sellOne')) or None,  # Bitget uses sellOne for ask
                'last_price': safe_float(ticker_data.get('close')) or safe_float(ticker_data.get('lastPrice')),
                'volume': safe_float(ticker_data.get('baseVol')),  # Bitget uses baseVol
                'timestamp': time.time()
            }
        else:
            # Default format - use lastPrice if available
            normalized = {
                'symbol': ticker_data.get('symbol'),
                'bid': safe_float(ticker_data.get('bidPrice')) or None,
                'ask': safe_float(ticker_data.get('askPrice')) or None,
                'last_price': safe_float(ticker_data.get('lastPrice')),
                'volume': safe_float(ticker_data.get('volume24h')) or safe_float(ticker_data.get('volume')),
                'timestamp': time.time()
            }
        
        return normalized
    
    def calculate_spread(self, ticker1: Dict, ticker2: Dict, exchange1: str, exchange2: str) -> Dict:
        """Calculate spread between two tickers"""
        try:
            # Use bid/ask if available, otherwise use last_price
            price1 = ticker1.get('ask') or ticker1.get('last_price')
            price2 = ticker2.get('bid') or ticker2.get('last_price')
            
            if not price1 or not price2 or price1 <= 0 or price2 <= 0:
                return None
            
            # Calculate spread percentage
            spread_pct = ((price2 - price1) / price1) * 100
            
            return {
                'symbol': ticker1['symbol'],
                'exchange1': exchange1,
                'exchange2': exchange2,
                'price1': price1,
                'price2': price2,
                'spread_pct': spread_pct,
                'spread_abs': price2 - price1,
                'timestamp': time.time()
            }
        except (TypeError, ZeroDivisionError, KeyError):
            return None
    
    async def get_all_spreads(self) -> List[Dict]:
        """Get all current spreads between arbitrage exchanges"""
        spreads = []
        exchange_names = self.config.get_arbitrage_exchanges()
        
        if len(exchange_names) < 2:
            return spreads
        
        # Get ticker data from all exchanges
        exchange_tickers = {}
        for exchange_name, exchange in self.exchanges.items():
            try:
                # Get all tickers for this exchange
                tickers = await exchange.get_all_tickers()
                if tickers:
                    exchange_tickers[exchange_name] = {
                        ticker['symbol']: self.normalize_ticker(ticker, exchange_name) 
                        for ticker in tickers if ticker.get('symbol')
                    }
            except Exception as e:
                logger.debug(f"Failed to get tickers from {exchange_name}: {e}")
                continue
        
        # Calculate spreads for all symbol pairs
        if len(exchange_tickers) >= 2:
            for i, exchange1 in enumerate(exchange_names):
                for j, exchange2 in enumerate(exchange_names):
                    if i >= j or exchange1 not in exchange_tickers or exchange2 not in exchange_tickers:
                        continue
                    
                    tickers1 = exchange_tickers[exchange1]
                    tickers2 = exchange_tickers[exchange2]
                    
                    # Find common symbols
                    common_symbols = set(tickers1.keys()) & set(tickers2.keys())
                    
                    for symbol in common_symbols:
                        ticker1 = tickers1[symbol]
                        ticker2 = tickers2[symbol]
                        
                        # Calculate spread in both directions
                        spread1 = self.calculate_spread(ticker1, ticker2, exchange1, exchange2)
                        spread2 = self.calculate_spread(ticker2, ticker1, exchange2, exchange1)
                        
                        if spread1:
                            spreads.append(spread1)
                        if spread2:
                            spreads.append(spread2)
        
        return spreads
    
    def filter_valid_spreads(self, spreads: List[Dict]) -> List[Dict]:
        """Filter out spreads that are too large (likely data anomalies)"""
        if not spreads:
            return []
        
        max_threshold = self.config.arbitrage.max_spread_threshold
        valid_spreads = []
        
        for spread in spreads:
            abs_spread = abs(spread['spread_pct'])
            if abs_spread <= max_threshold:
                valid_spreads.append(spread)
            # Silently filter out anomalous spreads
        
        return valid_spreads
    
    def get_top_spreads(self, spreads: List[Dict], n: int = 3) -> List[Dict]:
        """Get top N spreads by absolute percentage"""
        if not spreads:
            return []
        
        # Filter out anomalous spreads first
        valid_spreads = self.filter_valid_spreads(spreads)
        
        if not valid_spreads:
            return []
        
        # Sort by absolute spread percentage (descending)
        sorted_spreads = sorted(valid_spreads, key=lambda x: abs(x['spread_pct']), reverse=True)
        return sorted_spreads[:n]
    
    def update_spread_history(self, spread: Dict):
        """Update spread history for premium detection"""
        if not self.config.arbitrage.premium_detection.enabled:
            return
        
        key = f"{spread['exchange1']}_{spread['exchange2']}_{spread['symbol']}"
        
        if key not in self.spread_history:
            self.spread_history[key] = []
        
        self.spread_history[key].append(spread['spread_pct'])
        
        # Keep only recent history
        max_periods = self.config.arbitrage.premium_detection.lookback_periods
        if len(self.spread_history[key]) > max_periods:
            self.spread_history[key] = self.spread_history[key][-max_periods:]
    
    def get_adjusted_spread(self, spread: Dict) -> Dict:
        """Adjust spread based on historical premium"""
        if not self.config.arbitrage.premium_detection.enabled:
            return spread
        
        key = f"{spread['exchange1']}_{spread['exchange2']}_{spread['symbol']}"
        history = self.spread_history.get(key, [])
        
        if len(history) < self.config.arbitrage.premium_detection.min_samples:
            return spread
        
        # Calculate average and standard deviation
        import statistics
        avg_spread = statistics.mean(history)
        
        try:
            std_spread = statistics.stdev(history)
        except statistics.StatisticsError:
            std_spread = 0
        
        # Adjust current spread by removing average premium
        adjusted_spread_pct = spread['spread_pct'] - avg_spread
        
        # Check if this is an outlier (potential opportunity)
        if std_spread > 0:
            z_score = abs(adjusted_spread_pct) / std_spread
            is_outlier = z_score > self.config.arbitrage.premium_detection.outlier_threshold
        else:
            is_outlier = False
        
        adjusted_spread = spread.copy()
        adjusted_spread['spread_pct'] = adjusted_spread_pct
        adjusted_spread['avg_premium'] = avg_spread
        adjusted_spread['z_score'] = abs(adjusted_spread_pct) / std_spread if std_spread > 0 else 0
        adjusted_spread['is_outlier'] = is_outlier
        
        return adjusted_spread
    
    def format_spread_display(self, spread: Dict) -> str:
        """Format spread for display"""
        symbol = spread['symbol']
        pct = spread['spread_pct']
        sign = "+" if pct >= 0 else ""
        
        # Show outlier indicator if premium detection is enabled
        outlier_indicator = ""
        if spread.get('is_outlier', False):
            outlier_indicator = " 🚨"
        
        return f"{symbol} ({sign}{pct:.2f}%){outlier_indicator}"
    
    async def monitor_spreads(self):
        """Monitor and display top spreads continuously"""
        while self.is_running:
            try:
                spreads = await self.get_all_spreads()
                
                # Update spread history and get adjusted spreads
                adjusted_spreads = []
                for spread in spreads:
                    self.update_spread_history(spread)
                    adjusted_spread = self.get_adjusted_spread(spread)
                    adjusted_spreads.append(adjusted_spread)
                
                # Get top spreads based on adjusted values
                top_spreads = self.get_top_spreads(adjusted_spreads, 3)
                
                if top_spreads:
                    spread_strs = [self.format_spread_display(s) for s in top_spreads]
                    print(f"🔝 Top 3 스프레드: {' | '.join(spread_strs)}")
                    
                    # Show premium info for top spread if detection is enabled
                    if (self.config.arbitrage.premium_detection.enabled and 
                        top_spreads[0].get('avg_premium') is not None):
                        top = top_spreads[0]
                        print(f"    📊 {top['symbol']} 평균 프리미엄: {top['avg_premium']:.2f}%, "
                              f"Z-스코어: {top['z_score']:.1f}")
                else:
                    print("📊 스프레드 데이터를 수집 중...")
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"스프레드 모니터링 오류: {e}")
                await asyncio.sleep(5)
    
    async def initialize(self):
        """Initialize all components"""
        try:
            print("🔧 ArBot 초기화 중...")
            
            # Initialize database
            await self.database.initialize()
            print("✅ 데이터베이스 초기화 완료")
            
            # Initialize exchanges
            await self._initialize_exchanges()
            
            # Initialize strategy
            self.strategy = ArbitrageStrategy(self.config, self.database)
            await self.strategy.initialize(self.exchanges)
            print("✅ 차익거래 전략 초기화 완료")
            
            # Initialize trader or simulator based on mode
            if self.config.trading_mode == TradingMode.LIVE:
                self.trader = LiveTrader(self.config, self.database)
                await self.trader.initialize(self.exchanges)
                print("✅ 실거래 트레이더 초기화 완료")
            else:
                self.simulator = TradingSimulator(self.config, self.database)
                print("✅ 시뮬레이션 트레이더 초기화 완료")
            
            # Initialize backtester
            self.backtester = Backtester(self.config, self.database)
            print("✅ 백테스터 초기화 완료")
            
            # Connect strategy to trader/simulator
            if self.config.trading_mode == TradingMode.LIVE:
                self.strategy.add_signal_callback(self.trader.execute_arbitrage)
            else:
                self.strategy.add_signal_callback(self.simulator.execute_arbitrage)
            
            print("🎉 ArBot 초기화 완료!")
            print()
            
        except Exception as e:
            logger.error(f"❌ ArBot 초기화 실패: {e}")
            raise
    
    async def _initialize_exchanges(self):
        """Initialize exchange connections"""
        print("🏪 거래소 연결 중...")
        
        # Show disabled exchanges info
        disabled_exchanges = [name for name, config in self.config.exchanges.items() if not config.enabled]
        if disabled_exchanges:
            print(f"❌ 비활성화된 거래소: {', '.join(disabled_exchanges)}")
        
        for exchange_name, exchange_config in self.config.exchanges.items():
            if not exchange_config.enabled:
                continue
            
            try:
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
                elif exchange_name == 'bitget':
                    exchange = BitgetExchange(
                        exchange_config.api_key,
                        exchange_config.api_secret,
                        exchange_config.testnet
                    )
                elif exchange_name == 'okx':
                    exchange = OKXExchange(
                        exchange_config.api_key,
                        exchange_config.api_secret,
                        exchange_config.testnet
                    )
                else:
                    logger.warning(f"⚠️ 알 수 없는 거래소: {exchange_name}")
                    continue
                
                self.exchanges[exchange_name] = exchange
                print(f"✅ {exchange_name.upper()} 거래소 연결 완료")
                
            except Exception as e:
                logger.error(f"❌ {exchange_name} 거래소 연결 실패: {e}")
                continue
        
        if not self.exchanges:
            raise ValueError("연결 가능한 거래소가 없습니다")
        
        print(f"🎯 총 {len(self.exchanges)}개 거래소 연결 완료")
    
    async def get_common_symbols_with_volume(self) -> List[str]:
        """Get common symbols across arbitrage exchanges with minimum volume"""
        arbitrage_exchanges = self.config.get_arbitrage_exchanges()
        if len(arbitrage_exchanges) < 2:
            print("⚠️ 차익거래용 거래소가 2개 미만입니다")
            return self.config.arbitrage.symbols
        
        print("🔍 공통 심볼 및 볼륨 검사 중...")
        
        # Get symbols and volumes from each exchange
        exchange_symbols = {}
        exchange_volumes = {}
        
        for exchange_name in arbitrage_exchanges:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                print(f"⚠️ {exchange_name} 거래소 객체를 찾을 수 없습니다")
                continue
            
            # Check if exchange has API credentials
            config = self.config.exchanges.get(exchange_name)
            if config and not config.api_key:
                print(f"⚠️ {exchange_name} API 키가 설정되지 않았습니다")
                
            try:
                # Get all tickers with volume info
                tickers = await exchange.get_all_tickers()
                if tickers:
                    symbols = set()
                    volumes = {}
                    
                    for ticker in tickers:
                        symbol = ticker.get('symbol')
                        if not symbol:
                            continue
                        
                        # Extract volume (24h in USDT)
                        volume_usdt = 0
                        try:
                            if exchange_name.lower() == 'bybit':
                                volume_usdt = float(ticker.get('turnover24h', 0))
                            elif exchange_name.lower() == 'binance':
                                # For Binance, use quoteVolume which is already in USDT
                                volume_usdt = float(ticker.get('quoteVolume', 0))
                                if volume_usdt == 0:
                                    # Fallback: calculate volume * price
                                    volume = float(ticker.get('volume', 0))
                                    price = float(ticker.get('weightedAvgPrice', 0)) or float(ticker.get('lastPrice', 0))
                                    volume_usdt = volume * price
                            elif exchange_name.lower() == 'okx':
                                # OKX uses volCcy24h for volume in quote currency
                                volume_usdt = float(ticker.get('volCcy24h', 0))
                            elif exchange_name.lower() == 'bitget':
                                # Bitget uses quoteVol (not quoteVolume)
                                volume_usdt = float(ticker.get('quoteVol', 0))
                                if volume_usdt == 0:
                                    volume = float(ticker.get('baseVol', 0))
                                    price = float(ticker.get('close', 0)) or float(ticker.get('lastPrice', 0))
                                    volume_usdt = volume * price
                            else:
                                # Default calculation
                                volume = float(ticker.get('volume24h', 0)) or float(ticker.get('volume', 0))
                                price = float(ticker.get('lastPrice', 0))
                                volume_usdt = volume * price
                        except (ValueError, TypeError):
                            volume_usdt = 0
                        
                        if volume_usdt >= self.config.arbitrage.min_volume_usdt:
                            symbols.add(symbol)
                            volumes[symbol] = volume_usdt
                    
                    exchange_symbols[exchange_name] = symbols
                    exchange_volumes[exchange_name] = volumes
                    print(f"✅ {exchange_name}: {len(symbols)}개 심볼 (볼륨 기준 충족)")
                    
            except Exception as e:
                print(f"❌ {exchange_name} 심볼 조회 실패: {e}")
                continue
        
        if not exchange_symbols:
            print("⚠️ 심볼 데이터를 가져올 수 없습니다. 기본 설정 사용")
            return self.config.arbitrage.symbols
        
        # Find common symbols
        common_symbols = None
        for exchange_name, symbols in exchange_symbols.items():
            if common_symbols is None:
                common_symbols = symbols.copy()
            else:
                common_symbols &= symbols
        
        if not common_symbols:
            print("⚠️ 공통 심볼이 없습니다. 기본 설정 사용")
            return self.config.arbitrage.symbols
        
        # Sort by average volume across exchanges
        symbol_avg_volumes = {}
        for symbol in common_symbols:
            volumes = [exchange_volumes[ex].get(symbol, 0) for ex in exchange_volumes]
            symbol_avg_volumes[symbol] = sum(volumes) / len(volumes)
        
        # Sort by volume descending
        sorted_symbols = sorted(symbol_avg_volumes.keys(), 
                              key=lambda s: symbol_avg_volumes[s], reverse=True)
        
        print(f"🎯 공통 심볼 {len(sorted_symbols)}개 발견 (최소 볼륨: ${self.config.arbitrage.min_volume_usdt:,.0f})")
        
        # Show top 10 symbols by volume
        top_symbols = sorted_symbols[:10]
        for i, symbol in enumerate(top_symbols, 1):
            volume = symbol_avg_volumes[symbol]
            print(f"  {i:2}. {symbol}: ${volume:,.0f}")
        
        return sorted_symbols
    
    async def start(self):
        """Start the trading bot"""
        try:
            print("🚀 ArBot 거래 시작...")
            
            # Get dynamic symbols if enabled
            if self.config.arbitrage.use_dynamic_symbols:
                self.dynamic_symbols = await self.get_common_symbols_with_volume()
            else:
                self.dynamic_symbols = self.config.arbitrage.symbols
                print(f"📋 설정된 심볼 사용: {len(self.dynamic_symbols)}개")
            
            # Start strategy
            await self.strategy.start()
            
            # Start trader/simulator
            if self.config.trading_mode == TradingMode.LIVE:
                await self.trader.start()
            else:
                await self.simulator.start()
            
            # Connect to exchange WebSocket feeds
            print("🔗 거래소 WebSocket 연결 중...")
            symbols_to_monitor = self.dynamic_symbols[:50]  # Limit to top 50 for performance
            print(f"📡 모니터링 심볼: {len(symbols_to_monitor)}개")
            
            for exchange_name, exchange in self.exchanges.items():
                try:
                    await exchange.connect_ws(symbols_to_monitor)
                    print(f"✅ {exchange_name.upper()} WebSocket 연결 완료")
                except Exception as e:
                    logger.error(f"❌ {exchange_name} WebSocket 연결 실패: {e}")
            
            self.is_running = True
            print("🎉 ArBot 거래 시작 완료!")
            print("💡 차익거래 기회를 실시간으로 모니터링합니다...")
            print("=" * 60)
            
            # Start spread monitoring
            self.spread_monitor_task = asyncio.create_task(self.monitor_spreads())
            
        except Exception as e:
            logger.error(f"❌ ArBot 시작 실패: {e}")
            raise
    
    async def stop(self):
        """Stop the trading bot"""
        try:
            print("🛑 ArBot 중지 중...")
            
            self.is_running = False
            
            # Stop spread monitoring
            if self.spread_monitor_task:
                self.spread_monitor_task.cancel()
                try:
                    await self.spread_monitor_task
                except asyncio.CancelledError:
                    pass
            
            # Stop strategy
            if self.strategy:
                await self.strategy.stop()
            
            # Stop trader/simulator
            if self.trader:
                await self.trader.stop()
            elif self.simulator:
                await self.simulator.stop()
            
            # Disconnect from exchanges
            for exchange_name, exchange in self.exchanges.items():
                try:
                    await exchange.disconnect_ws()
                    print(f"✅ {exchange_name.upper()} 연결 해제")
                except Exception as e:
                    logger.error(f"❌ {exchange_name} 연결 해제 오류: {e}")
            
            print("🎉 ArBot 정상 종료")
            
        except Exception as e:
            logger.error(f"❌ ArBot 종료 오류: {e}")
    
    async def run_forever(self):
        """Run the bot indefinitely"""
        try:
            await self.start()
            
            # Keep running until interrupted
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.stop()
    
    async def run_backtest(self, start_date: str, end_date: str, 
                          symbols: Optional[list] = None, 
                          exchanges: Optional[list] = None):
        """Run backtest simulation"""
        try:
            logger.info(f"Starting backtest from {start_date} to {end_date}")
            
            # Use config symbols and exchanges if not specified
            if symbols is None:
                symbols = self.config.arbitrage.symbols
            if exchanges is None:
                exchanges = self.config.get_enabled_exchanges()
            
            # Load historical data
            await self.backtester.load_historical_data(start_date, end_date, symbols, exchanges)
            
            # Run backtest
            result = await self.backtester.run_backtest()
            
            # Generate report
            report = self.backtester.generate_report(result)
            print(report)
            
            # Export results
            output_file = f"backtest_results_{start_date}_{end_date}.csv"
            await self.backtester.export_results(result, output_file)
            logger.info(f"Backtest results exported to {output_file}")
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        status = {
            'is_running': self.is_running,
            'trading_mode': self.config.trading_mode.value,
            'exchanges': list(self.exchanges.keys()),
            'symbols': self.config.arbitrage.symbols
        }
        
        # Add strategy stats
        if self.strategy:
            status['strategy'] = self.strategy.get_stats()
        
        # Add trader/simulator stats
        if self.trader:
            status['trader'] = self.trader.get_stats()
        elif self.simulator:
            status['simulator'] = self.simulator.get_stats()
        
        return status


def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "trading_mode": "simulation",
        "exchanges": {
            "binance": {
                "testnet": True,
                "enabled": True
            },
            "bybit": {
                "testnet": True,
                "enabled": True
            }
        },
        "arbitrage": {
            "min_profit_threshold": 0.001,
            "max_position_size": 1000.0,
            "trade_amount_usd": 100.0,
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "slippage_tolerance": 0.001,
            "max_spread_age_seconds": 5.0
        },
        "risk_management": {
            "max_drawdown_percent": 5.0,
            "stop_loss_percent": 2.0,
            "max_concurrent_trades": 3
        }
    }
    
    import json
    with open('config.json', 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print("Sample configuration created: config.json")
    print("Please edit this file with your API keys and preferences.")


def create_sample_env():
    """Create a sample .env file"""
    sample_env = """# ArBot Environment Variables
# Copy this file to .env and fill in your API keys

# Binance API Keys
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true

# Bybit API Keys
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_api_secret_here
BYBIT_TESTNET=true

# Trading Mode (live, simulation, backtest)
TRADING_MODE=simulation

# Database
DATABASE_PATH=arbot.db

# Logging
LOG_LEVEL=INFO
"""
    
    with open('.env.sample', 'w') as f:
        f.write(sample_env)
    
    print("Sample environment file created: .env.sample")
    print("Copy this to .env and fill in your API keys.")


def print_welcome_message():
    """친절한 환영 메시지 출력"""
    print("=" * 60)
    print("🚀 ArBot - 차익거래 트레이딩 봇에 오신 것을 환영합니다! 🚀")
    print("=" * 60)
    print("📈 실시간 암호화폐 차익거래 기회를 모니터링합니다")
    print("🔄 다중 거래소 간의 가격 차이를 분석합니다")
    print("💰 안전하고 수익성 있는 거래를 지원합니다")
    print("=" * 60)
    print()


async def main():
    """Main entry point"""
    # 환영 메시지 출력
    print_welcome_message()
    
    parser = argparse.ArgumentParser(description='ArBot - Arbitrage Trading Bot')
    parser.add_argument('--config', '-c', default='config.json', help='Configuration file path')
    parser.add_argument('--mode', '-m', choices=['live', 'simulation', 'backtest', 'ui'], 
                       default='ui', help='Trading mode')
    parser.add_argument('--start-date', help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='Trading symbols for backtest')
    parser.add_argument('--exchanges', nargs='+', help='Exchanges for backtest')
    parser.add_argument('--create-config', action='store_true', help='Create sample config file')
    parser.add_argument('--create-env', action='store_true', help='Create sample .env file')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Handle utility commands
    if args.create_config:
        create_sample_config()
        return
    
    if args.create_env:
        create_sample_env()
        return
    
    # Load configuration
    try:
        config = Config(args.config)
        
        # Override trading mode if specified
        if args.mode != 'ui':
            config.trading_mode = TradingMode(args.mode)
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Create and initialize bot
    bot = ArBot(config)
    
    try:
        await bot.initialize()
        
        # Run based on mode
        if args.mode == 'ui':
            # Run UI
            database = Database(config.database.db_path)
            await database.initialize()
            run_ui(config, database)
        
        elif args.mode == 'backtest':
            # Run backtest
            if not args.start_date or not args.end_date:
                logger.error("Start date and end date are required for backtest mode")
                sys.exit(1)
            
            await bot.run_backtest(
                args.start_date,
                args.end_date,
                args.symbols,
                args.exchanges
            )
        
        else:
            # Run live trading or simulation
            await bot.run_forever()
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        if bot.is_running:
            await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)