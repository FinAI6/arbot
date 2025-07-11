from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass
class Ticker:
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: float


@dataclass
class OrderBook:
    symbol: str
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]  # (price, size)
    timestamp: float


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    timestamp: Optional[float] = None


@dataclass
class Balance:
    asset: str
    free: float
    locked: float
    total: float


class BaseExchange(ABC):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.connected = False
        self.symbols: List[str] = []
        self._callbacks: Dict[str, List[callable]] = {}
    
    @abstractmethod
    async def connect_ws(self, symbols: List[str]) -> None:
        """Subscribe to live ticker/orderbook data via WebSocket"""
        pass
    
    @abstractmethod
    async def disconnect_ws(self) -> None:
        """Disconnect WebSocket connection"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get current ticker data for a symbol"""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 100) -> OrderBook:
        """Return current orderbook (bid/ask) for a symbol"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None) -> Order:
        """Submit an order to the exchange"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an active order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Get the status of an order"""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """Retrieve account balance for all assets or specific asset"""
        pass
    
    @abstractmethod
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get trading fees for a symbol (maker/taker)"""
        pass
    
    @abstractmethod
    async def get_symbols(self) -> List[str]:
        """Get all available trading symbols"""
        pass
    
    @abstractmethod
    async def get_all_tickers(self) -> List[Dict]:
        """Get all ticker data with volume information"""
        pass
    
    def on_ticker(self, callback: callable) -> None:
        """Register callback for ticker updates"""
        if 'ticker' not in self._callbacks:
            self._callbacks['ticker'] = []
        self._callbacks['ticker'].append(callback)
    
    def on_orderbook(self, callback: callable) -> None:
        """Register callback for orderbook updates"""
        if 'orderbook' not in self._callbacks:
            self._callbacks['orderbook'] = []
        self._callbacks['orderbook'].append(callback)
    
    def on_order_update(self, callback: callable) -> None:
        """Register callback for order updates"""
        if 'order_update' not in self._callbacks:
            self._callbacks['order_update'] = []
        self._callbacks['order_update'].append(callback)
    
    async def _emit_ticker(self, ticker: Ticker) -> None:
        """Emit ticker update to registered callbacks"""
        if 'ticker' in self._callbacks:
            for callback in self._callbacks['ticker']:
                try:
                    await callback(ticker)
                except Exception as e:
                    print(f"Error in ticker callback: {e}")
    
    async def _emit_orderbook(self, orderbook: OrderBook) -> None:
        """Emit orderbook update to registered callbacks"""
        if 'orderbook' in self._callbacks:
            for callback in self._callbacks['orderbook']:
                try:
                    await callback(orderbook)
                except Exception as e:
                    print(f"Error in orderbook callback: {e}")
    
    async def _emit_order_update(self, order: Order) -> None:
        """Emit order update to registered callbacks"""
        if 'order_update' in self._callbacks:
            for callback in self._callbacks['order_update']:
                try:
                    await callback(order)
                except Exception as e:
                    print(f"Error in order update callback: {e}")
    
    @property
    def name(self) -> str:
        """Return the exchange name"""
        return self.__class__.__name__.lower().replace('exchange', '')