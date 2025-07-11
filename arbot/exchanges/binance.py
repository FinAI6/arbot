import asyncio
import json
import time
import hmac
import hashlib
from typing import Dict, List, Optional
from urllib.parse import urlencode
import aiohttp
import websockets
from .base import BaseExchange, Ticker, OrderBook, Order, Balance, OrderSide, OrderType, OrderStatus


class BinanceExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        self.ws_url = "wss://testnet.binance.vision/ws" if testnet else "wss://stream.binance.com:9443/ws"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._server_time_offset = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _generate_signature(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _sync_server_time(self) -> None:
        """Synchronize with Binance server time to avoid timestamp errors"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/v3/time") as response:
                if response.status == 200:
                    data = await response.json()
                    server_time = data['serverTime']
                    local_time = int(time.time() * 1000)
                    self._server_time_offset = server_time - local_time
        except Exception as e:
            print(f"Failed to sync server time: {e}")
            self._server_time_offset = 0

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                          signed: bool = False) -> Dict:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        if signed:
            # Sync server time on first signed request or if previous requests failed
            if self._server_time_offset == 0:
                await self._sync_server_time()
            
            timestamp = int(time.time() * 1000) + self._server_time_offset
            params['timestamp'] = timestamp
            query_string = urlencode(params)
            signature = self._generate_signature(query_string)
            params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': self.api_key} if self.api_key else {}
        
        try:
            async with session.request(method, url, params=params, headers=headers) as response:
                data = await response.json()
                if response.status != 200:
                    # If timestamp error, try to resync and retry once
                    if data.get('code') == -1021 and signed:
                        await self._sync_server_time()
                        timestamp = int(time.time() * 1000) + self._server_time_offset
                        params['timestamp'] = timestamp
                        query_string = urlencode(params)
                        signature = self._generate_signature(query_string)
                        params['signature'] = signature
                        
                        async with session.request(method, url, params=params, headers=headers) as retry_response:
                            retry_data = await retry_response.json()
                            if retry_response.status != 200:
                                raise Exception(f"Binance API error: {retry_data}")
                            return retry_data
                    else:
                        raise Exception(f"Binance API error: {data}")
                return data
        except Exception as e:
            raise e
    
    async def connect_ws(self, symbols: List[str]) -> None:
        self.symbols = symbols
        stream_names = []
        
        for symbol in symbols:
            symbol_lower = symbol.lower()
            stream_names.append(f"{symbol_lower}@ticker")
            stream_names.append(f"{symbol_lower}@depth5")
        
        stream_url = f"{self.ws_url}/{'/'.join(stream_names)}"
        
        try:
            self.ws_connection = await websockets.connect(stream_url)
            self.connected = True
            self._ws_task = asyncio.create_task(self._handle_ws_messages())
        except Exception as e:
            print(f"Failed to connect to Binance WebSocket: {e}")
            self.connected = False
    
    async def disconnect_ws(self) -> None:
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
        
        self.connected = False
    
    async def _handle_ws_messages(self) -> None:
        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                
                if 'stream' in data:
                    stream = data['stream']
                    stream_data = data['data']
                    
                    if '@ticker' in stream:
                        await self._handle_ticker_data(stream_data)
                    elif '@depth' in stream:
                        await self._handle_depth_data(stream_data)
                        
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.connected = False
    
    async def _handle_ticker_data(self, data: Dict) -> None:
        ticker = Ticker(
            symbol=data['s'],
            bid=float(data['b']),
            ask=float(data['a']),
            bid_size=float(data['B']),
            ask_size=float(data['A']),
            timestamp=float(data['E']) / 1000
        )
        await self._emit_ticker(ticker)
    
    async def _handle_depth_data(self, data: Dict) -> None:
        orderbook = OrderBook(
            symbol=data['s'],
            bids=[(float(price), float(size)) for price, size in data['bids']],
            asks=[(float(price), float(size)) for price, size in data['asks']],
            timestamp=float(data['E']) / 1000
        )
        await self._emit_orderbook(orderbook)
    
    async def get_ticker(self, symbol: str) -> Ticker:
        data = await self._make_request('GET', '/api/v3/ticker/bookTicker', {'symbol': symbol})
        return Ticker(
            symbol=data['symbol'],
            bid=float(data['bidPrice']),
            ask=float(data['askPrice']),
            bid_size=float(data['bidQty']),
            ask_size=float(data['askQty']),
            timestamp=time.time()
        )
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> OrderBook:
        data = await self._make_request('GET', '/api/v3/depth', {'symbol': symbol, 'limit': limit})
        return OrderBook(
            symbol=symbol,
            bids=[(float(price), float(size)) for price, size in data['bids']],
            asks=[(float(price), float(size)) for price, size in data['asks']],
            timestamp=time.time()
        )
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None) -> Order:
        params = {
            'symbol': symbol,
            'side': side.value.upper(),
            'type': order_type.value.upper(),
            'quantity': str(quantity),
        }
        
        if order_type == OrderType.LIMIT and price is not None:
            params['price'] = str(price)
            params['timeInForce'] = 'GTC'
        
        data = await self._make_request('POST', '/api/v3/order', params, signed=True)
        
        return Order(
            order_id=str(data['orderId']),
            symbol=data['symbol'],
            side=OrderSide(data['side'].lower()),
            type=OrderType(data['type'].lower()),
            quantity=float(data['origQty']),
            price=float(data['price']) if data['price'] != '0.00000000' else None,
            status=self._map_order_status(data['status']),
            filled_quantity=float(data['executedQty']),
            timestamp=float(data['transactTime']) / 1000
        )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            await self._make_request('DELETE', '/api/v3/order', 
                                   {'symbol': symbol, 'orderId': order_id}, signed=True)
            return True
        except Exception:
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        data = await self._make_request('GET', '/api/v3/order', 
                                      {'symbol': symbol, 'orderId': order_id}, signed=True)
        
        return Order(
            order_id=str(data['orderId']),
            symbol=data['symbol'],
            side=OrderSide(data['side'].lower()),
            type=OrderType(data['type'].lower()),
            quantity=float(data['origQty']),
            price=float(data['price']) if data['price'] != '0.00000000' else None,
            status=self._map_order_status(data['status']),
            filled_quantity=float(data['executedQty']),
            average_price=float(data['cummulativeQuoteQty']) / float(data['executedQty']) if float(data['executedQty']) > 0 else None,
            timestamp=float(data['time']) / 1000
        )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        data = await self._make_request('GET', '/api/v3/account', signed=True)
        balances = {}
        
        for balance_data in data['balances']:
            asset_name = balance_data['asset']
            if asset is None or asset_name == asset:
                free = float(balance_data['free'])
                locked = float(balance_data['locked'])
                balances[asset_name] = Balance(
                    asset=asset_name,
                    free=free,
                    locked=locked,
                    total=free + locked
                )
        
        return balances
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        try:
            data = await self._make_request('GET', '/api/v3/account', signed=True)
            
            if not data or not isinstance(data, dict):
                print(f"Invalid account data from Binance for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            maker_commission = data.get('makerCommission')
            taker_commission = data.get('takerCommission')
            
            try:
                maker_fee = float(maker_commission) / 10000 if maker_commission is not None else 0.001
                taker_fee = float(taker_commission) / 10000 if taker_commission is not None else 0.001
            except (ValueError, TypeError):
                print(f"Invalid commission values from Binance for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            return {
                'maker': maker_fee,
                'taker': taker_fee
            }
            
        except Exception as e:
            print(f"Error getting Binance trading fees for {symbol}: {e}, using default rates")
            return {'maker': 0.001, 'taker': 0.001}
    
    async def get_symbols(self) -> List[str]:
        data = await self._make_request('GET', '/api/v3/exchangeInfo')
        return [symbol_info['symbol'] for symbol_info in data['symbols'] 
                if symbol_info['status'] == 'TRADING']
    
    async def get_all_tickers(self) -> List[Dict]:
        """Get all 24hr ticker statistics"""
        try:
            data = await self._make_request('GET', '/api/v3/ticker/24hr')
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to get Binance tickers: {e}")
            return []
    
    def _map_order_status(self, binance_status: str) -> OrderStatus:
        status_map = {
            'NEW': OrderStatus.NEW,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'FILLED': OrderStatus.FILLED,
            'CANCELED': OrderStatus.CANCELED,
            'REJECTED': OrderStatus.REJECTED,
            'EXPIRED': OrderStatus.CANCELED
        }
        return status_map.get(binance_status, OrderStatus.NEW)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_ws()
        if self.session and not self.session.closed:
            await self.session.close()