import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in parent directory
parent_dir = Path(__file__).parent.parent
load_dotenv(parent_dir / ".env")


class TradingMode(Enum):
    LIVE = "live"
    SIMULATION = "simulation"
    BACKTEST = "backtest"


@dataclass
class ExchangeConfig:
    name: str
    api_key: str
    api_secret: str
    testnet: bool = False
    enabled: bool = True
    arbitrage_enabled: bool = True
    region: str = "global"
    premium_baseline: float = 0.0


@dataclass
class PremiumDetectionConfig:
    enabled: bool = True
    lookback_periods: int = 100
    min_samples: int = 50
    outlier_threshold: float = 2.0


@dataclass
class ArbitrageConfig:
    min_profit_threshold: float = 0.001  # 0.1%
    max_position_size: float = 1000.0  # USD
    max_trades_per_hour: int = 50
    trade_amount_usd: float = 100.0
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    max_symbols: int = 200  # Maximum number of symbols to monitor
    slippage_tolerance: float = 0.001  # 0.1%
    max_spread_age_seconds: float = 5.0
    use_dynamic_symbols: bool = True
    max_spread_threshold: float = 2.0  # Maximum spread percentage (200%) to filter out anomalies
    
    # Symbol filtering by quote currency
    enabled_quote_currencies: List[str] = field(default_factory=lambda: ["USDT"])  # Enabled quote currencies
    available_quote_currencies: List[str] = field(default_factory=lambda: ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"])  # All available options
    
    # Moving average settings
    moving_average_periods: int = 30  # Moving average period in seconds
    
    # Trend-based arbitrage filtering
    use_trend_filter: bool = True  # Enable trend-based arbitrage filtering
    trend_filter_mode: str = "uptrend_buy_low"  # Modes: "uptrend_buy_low", "downtrend_sell_high", "both", "disabled"
    trend_confirmation_threshold: float = 0.001  # 0.1% price movement to confirm trend
    
    premium_detection: PremiumDetectionConfig = field(default_factory=PremiumDetectionConfig)


@dataclass
class RiskManagementConfig:
    max_drawdown_percent: float = 5.0
    stop_loss_percent: float = 2.0
    position_sizing_method: str = "fixed"  # "fixed" or "kelly"
    max_concurrent_trades: int = 3
    balance_threshold_percent: float = 10.0  # Stop trading if balance drops below this %


@dataclass
class DatabaseConfig:
    db_path: str = "data/arbot.db"
    backup_interval_hours: int = 24
    max_history_days: int = 30


@dataclass
class UIConfig:
    refresh_rate_ms: int = 500
    enable_notifications: bool = True
    log_level: str = "INFO"
    theme: str = "dark"


@dataclass
class BacktestConfig:
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    initial_balance: float = 10000.0
    data_source: str = "database"  # "database" or "csv"
    csv_path: Optional[str] = None


class Config:
    def __init__(self, config_file: str = "config.json"):
        # Config files are in parent directory
        parent_dir = Path(__file__).parent.parent
        self.config_file = parent_dir / config_file
        self.local_config_file = parent_dir / config_file.replace('.json', '.local.json')
        self.trading_mode = TradingMode.SIMULATION
        self.exchanges: Dict[str, ExchangeConfig] = {}
        self.arbitrage = ArbitrageConfig()
        self.risk_management = RiskManagementConfig()
        self.database = DatabaseConfig()
        self.ui = UIConfig()
        self.backtest = BacktestConfig()
        self.regional_premiums: Dict = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from main config file, then overlay local config"""
        # Load main config
        config_data = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                print(f"✅ 메인 설정 파일 로드: {self.config_file}")
            except Exception as e:
                print(f"❌ 메인 설정 파일 로드 실패: {e}")
        
        # Load and overlay local config
        if os.path.exists(self.local_config_file):
            try:
                with open(self.local_config_file, 'r') as f:
                    local_config = json.load(f)
                config_data = self._deep_merge_dict(config_data, local_config)
                print(f"✅ 로컬 설정 파일 오버레이: {self.local_config_file}")
            except Exception as e:
                print(f"❌ 로컬 설정 파일 로드 실패: {e}")
        
        if config_data:
            self._update_from_dict(config_data)
        
        self._load_from_env()
    
    def _deep_merge_dict(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge two dictionaries, overlay takes precedence"""
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result
    
    def _update_from_dict(self, config_data: Dict) -> None:
        """Update configuration from dictionary"""
        if 'trading_mode' in config_data:
            self.trading_mode = TradingMode(config_data['trading_mode'])
        
        if 'exchanges' in config_data:
            for name, exchange_data in config_data['exchanges'].items():
                if name in self.exchanges:
                    # Update existing config
                    existing = self.exchanges[name]
                    self.exchanges[name] = ExchangeConfig(
                        name=name,
                        api_key=exchange_data.get('api_key', existing.api_key),
                        api_secret=exchange_data.get('api_secret', existing.api_secret),
                        testnet=exchange_data.get('testnet', existing.testnet),
                        enabled=exchange_data.get('enabled', existing.enabled),
                        arbitrage_enabled=exchange_data.get('arbitrage_enabled', existing.arbitrage_enabled),
                        region=exchange_data.get('region', existing.region),
                        premium_baseline=exchange_data.get('premium_baseline', existing.premium_baseline)
                    )
                else:
                    # Create new config with values from config file (no defaults from ExchangeConfig)
                    self.exchanges[name] = ExchangeConfig(
                        name=name,
                        api_key=exchange_data.get('api_key', ''),
                        api_secret=exchange_data.get('api_secret', ''),
                        testnet=exchange_data.get('testnet', False),
                        enabled=exchange_data.get('enabled', True),  # Only use True as fallback for new configs
                        arbitrage_enabled=exchange_data.get('arbitrage_enabled', True),
                        region=exchange_data.get('region', 'global'),
                        premium_baseline=exchange_data.get('premium_baseline', 0.0)
                    )
        
        if 'arbitrage' in config_data:
            arb_data = config_data['arbitrage']
            
            # Handle premium detection config
            premium_config = PremiumDetectionConfig()
            if 'premium_detection' in arb_data:
                pd_data = arb_data['premium_detection']
                premium_config = PremiumDetectionConfig(
                    enabled=pd_data.get('enabled', True),
                    lookback_periods=pd_data.get('lookback_periods', 100),
                    min_samples=pd_data.get('min_samples', 50),
                    outlier_threshold=pd_data.get('outlier_threshold', 2.0)
                )
            
            self.arbitrage = ArbitrageConfig(
                min_profit_threshold=arb_data.get('min_profit_threshold', 0.001),
                max_position_size=arb_data.get('max_position_size', 1000.0),
                max_trades_per_hour=arb_data.get('max_trades_per_hour', 50),
                trade_amount_usd=arb_data.get('trade_amount_usd', 100.0),
                symbols=arb_data.get('symbols', ["BTCUSDT", "ETHUSDT"]),
                max_symbols=arb_data.get('max_symbols', 200),
                slippage_tolerance=arb_data.get('slippage_tolerance', 0.001),
                max_spread_age_seconds=arb_data.get('max_spread_age_seconds', 5.0),
                use_dynamic_symbols=arb_data.get('use_dynamic_symbols', True),
                max_spread_threshold=arb_data.get('max_spread_threshold', 2.0),
                enabled_quote_currencies=arb_data.get('enabled_quote_currencies', ["USDT"]),
                available_quote_currencies=arb_data.get('available_quote_currencies', ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"]),
                moving_average_periods=arb_data.get('moving_average_periods', 30),
                use_trend_filter=arb_data.get('use_trend_filter', True),
                trend_filter_mode=arb_data.get('trend_filter_mode', "uptrend_buy_low"),
                trend_confirmation_threshold=arb_data.get('trend_confirmation_threshold', 0.001),
                premium_detection=premium_config
            )
        
        if 'risk_management' in config_data:
            risk_data = config_data['risk_management']
            self.risk_management = RiskManagementConfig(
                max_drawdown_percent=risk_data.get('max_drawdown_percent', 5.0),
                stop_loss_percent=risk_data.get('stop_loss_percent', 2.0),
                position_sizing_method=risk_data.get('position_sizing_method', 'fixed'),
                max_concurrent_trades=risk_data.get('max_concurrent_trades', 3),
                balance_threshold_percent=risk_data.get('balance_threshold_percent', 10.0)
            )
        
        if 'database' in config_data:
            db_data = config_data['database']
            self.database = DatabaseConfig(
                db_path=db_data.get('db_path', 'arbot.db'),
                backup_interval_hours=db_data.get('backup_interval_hours', 24),
                max_history_days=db_data.get('max_history_days', 30)
            )
        
        if 'ui' in config_data:
            ui_data = config_data['ui']
            self.ui = UIConfig(
                refresh_rate_ms=ui_data.get('refresh_rate_ms', 500),
                enable_notifications=ui_data.get('enable_notifications', True),
                log_level=ui_data.get('log_level', 'INFO'),
                theme=ui_data.get('theme', 'dark')
            )
        
        if 'backtest' in config_data:
            bt_data = config_data['backtest']
            self.backtest = BacktestConfig(
                start_date=bt_data.get('start_date', '2024-01-01'),
                end_date=bt_data.get('end_date', '2024-12-31'),
                initial_balance=bt_data.get('initial_balance', 10000.0),
                data_source=bt_data.get('data_source', 'database'),
                csv_path=bt_data.get('csv_path')
            )
        
        # Load regional premiums
        if 'regional_premiums' in config_data:
            self.regional_premiums = config_data['regional_premiums']
    
    def _load_from_env(self) -> None:
        """Load sensitive configuration from environment variables"""
        # Exchange API keys from environment
        for exchange_name in ['binance', 'bybit', 'okx', 'bitget']:
            api_key = os.getenv(f"{exchange_name.upper()}_API_KEY")
            api_secret = os.getenv(f"{exchange_name.upper()}_API_SECRET")
            testnet = os.getenv(f"{exchange_name.upper()}_TESTNET", "false").lower() == "true"
            
            if api_key and api_secret:
                # Get existing config to preserve enabled/arbitrage_enabled settings
                existing = self.exchanges.get(exchange_name)
                if existing:
                    # Update existing config with API credentials, preserve other settings
                    self.exchanges[exchange_name] = ExchangeConfig(
                        name=exchange_name,
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=testnet,
                        enabled=existing.enabled,  # Preserve existing enabled setting
                        arbitrage_enabled=existing.arbitrage_enabled,  # Preserve existing arbitrage_enabled setting
                        region=existing.region,
                        premium_baseline=existing.premium_baseline
                    )
                else:
                    # Create new config only if no existing config found
                    self.exchanges[exchange_name] = ExchangeConfig(
                        name=exchange_name,
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=testnet,
                        enabled=True  # Default to enabled for new exchanges
                    )
        
        # Trading mode
        trading_mode = os.getenv("TRADING_MODE")
        if trading_mode:
            try:
                self.trading_mode = TradingMode(trading_mode.lower())
            except ValueError:
                pass
        
        # Database path
        db_path = os.getenv("DATABASE_PATH")
        if db_path:
            self.database.db_path = db_path
        else:
            # Default to relative path from project root
            parent_dir = Path(__file__).parent.parent
            self.database.db_path = str(parent_dir / "data" / "arbot.db")
        
        # Log level
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            self.ui.log_level = log_level.upper()
    
    def save_config(self) -> None:
        """Save configuration to file (excluding sensitive data)"""
        config_data = {
            'trading_mode': self.trading_mode.value,
            'exchanges': {
                name: {
                    'testnet': exchange.testnet,
                    'enabled': exchange.enabled
                } for name, exchange in self.exchanges.items()
            },
            'arbitrage': {
                'min_profit_threshold': self.arbitrage.min_profit_threshold,
                'max_position_size': self.arbitrage.max_position_size,
                'max_trades_per_hour': self.arbitrage.max_trades_per_hour,
                'trade_amount_usd': self.arbitrage.trade_amount_usd,
                'symbols': self.arbitrage.symbols,
                'slippage_tolerance': self.arbitrage.slippage_tolerance,
                'max_spread_age_seconds': self.arbitrage.max_spread_age_seconds
            },
            'risk_management': {
                'max_drawdown_percent': self.risk_management.max_drawdown_percent,
                'stop_loss_percent': self.risk_management.stop_loss_percent,
                'position_sizing_method': self.risk_management.position_sizing_method,
                'max_concurrent_trades': self.risk_management.max_concurrent_trades,
                'balance_threshold_percent': self.risk_management.balance_threshold_percent
            },
            'database': {
                'db_path': self.database.db_path,
                'backup_interval_hours': self.database.backup_interval_hours,
                'max_history_days': self.database.max_history_days
            },
            'ui': {
                'refresh_rate_ms': self.ui.refresh_rate_ms,
                'enable_notifications': self.ui.enable_notifications,
                'log_level': self.ui.log_level,
                'theme': self.ui.theme
            },
            'backtest': {
                'start_date': self.backtest.start_date,
                'end_date': self.backtest.end_date,
                'initial_balance': self.backtest.initial_balance,
                'data_source': self.backtest.data_source,
                'csv_path': self.backtest.csv_path
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get_enabled_exchanges(self) -> List[str]:
        """Get list of enabled exchange names"""
        return [name for name, config in self.exchanges.items() if config.enabled]
    
    def get_arbitrage_exchanges(self) -> List[str]:
        """Get list of exchanges enabled for arbitrage"""
        return [name for name, config in self.exchanges.items() 
                if config.enabled and config.arbitrage_enabled]
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not self.exchanges:
            errors.append("No exchanges configured")
        
        arbitrage_exchanges = self.get_arbitrage_exchanges()
        if len(arbitrage_exchanges) < 2:
            errors.append("At least 2 exchanges must be enabled for arbitrage")
        
        for name, exchange in self.exchanges.items():
            if exchange.enabled:
                if not exchange.api_key:
                    errors.append(f"API key missing for {name}")
                if not exchange.api_secret:
                    errors.append(f"API secret missing for {name}")
        
        if not self.arbitrage.symbols:
            errors.append("No trading symbols configured")
        
        if self.arbitrage.min_profit_threshold <= 0:
            errors.append("Minimum profit threshold must be positive")
        
        if self.arbitrage.trade_amount_usd <= 0:
            errors.append("Trade amount must be positive")
        
        return errors


# Global configuration instance
config = Config()