import asyncio
import json
import time
import hmac
import hashlib
import base64
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode
import aiohttp
import websockets
from .base import BaseExchange, Ticker, OrderBook, Order, Balance, OrderSide, OrderType, OrderStatus

logger = logging.getLogger(__name__)


class OKXExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, passphrase: str = ""):
        super().__init__(api_key, api_secret, testnet)
        self.passphrase = passphrase
        self.base_url = "https://www.okx.com" if not testnet else "https://www.okx.com"  # OKX doesn't have separate testnet URL
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public" if not testnet else "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._server_time_offset = 0
        self._subscription_count = 0
        self._expected_subscriptions = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        message = timestamp + method + request_path + body
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        )
        return signature.decode('utf-8')
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                          signed: bool = False) -> Dict:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        request_path = endpoint
        body = ""
        
        if signed:
            timestamp = time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            if method == 'GET' and params:
                query_string = urlencode(params)
                request_path += f"?{query_string}"
                url += f"?{query_string}"
            elif method in ['POST', 'PUT', 'DELETE'] and params:
                body = json.dumps(params)
            
            signature = self._generate_signature(timestamp, method, request_path, body)
            
            headers.update({
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': self.passphrase
            })
        
        request_params = {}
        if method == 'GET':
            if not signed:
                request_params['params'] = params
        else:
            if params:
                request_params['data'] = body if signed else json.dumps(params)
        
        async with session.request(method, url, headers=headers, **request_params) as response:
            data = await response.json()
            if data.get('code') != '0':
                raise Exception(f"OKX API error: {data}")
            return data
    
    def _convert_symbol_to_okx_format(self, symbol: str) -> str:
        """Convert symbol from BTCUSDT format to BTC-USDT format for OKX"""
        if '-' in symbol:
            return symbol  # Already in OKX format
        
        # Common patterns for conversion
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            return f"{base}-USDT"
        elif symbol.endswith('USDC'):
            base = symbol[:-4]
            return f"{base}-USDC"
        elif symbol.endswith('BTC'):
            base = symbol[:-3]
            return f"{base}-BTC"
        elif symbol.endswith('ETH'):
            base = symbol[:-3]
            return f"{base}-ETH"
        else:
            # Try to split at common positions
            for quote in ['USDT', 'USDC', 'BTC', 'ETH']:
                if symbol.endswith(quote):
                    base = symbol[:-len(quote)]
                    return f"{base}-{quote}"
            
            # If can't determine, return as is
            return symbol
    
    def _convert_symbol_from_okx_format(self, okx_symbol: str) -> str:
        """Convert symbol from BTC-USDT format back to BTCUSDT format"""
        if '-' in okx_symbol:
            return okx_symbol.replace('-', '')
        return okx_symbol

    async def connect_ws(self, symbols: List[str]) -> None:
        self.symbols = symbols
        
        try:
            self.ws_connection = await websockets.connect(self.ws_url)
            self.connected = True
            
            # Subscribe to tickers and orderbooks
            for symbol in symbols:
                okx_symbol = self._convert_symbol_to_okx_format(symbol)
                await self._subscribe_ticker(okx_symbol)
                await self._subscribe_orderbook(okx_symbol)
            
            self._ws_task = asyncio.create_task(self._handle_ws_messages())
        except Exception as e:
            print(f"Failed to connect to OKX WebSocket: {e}")
            self.connected = False
    
    async def _subscribe_ticker(self, symbol: str) -> None:
        subscribe_msg = {
            "op": "subscribe",
            "args": [
                {
                    "channel": "tickers",
                    "instId": symbol
                }
            ]
        }
        await self.ws_connection.send(json.dumps(subscribe_msg))
    
    async def _subscribe_orderbook(self, symbol: str) -> None:
        subscribe_msg = {
            "op": "subscribe",
            "args": [
                {
                    "channel": "books5",
                    "instId": symbol
                }
            ]
        }
        await self.ws_connection.send(json.dumps(subscribe_msg))
    
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
                try:
                    data = json.loads(message)
                    
                    if 'data' in data and 'arg' in data:
                        channel = data['arg']['channel']
                        
                        if channel == 'tickers':
                            for ticker_data in data['data']:
                                await self._handle_ticker_data(ticker_data)
                        elif channel == 'books5':
                            for orderbook_data in data['data']:
                                await self._handle_orderbook_data(orderbook_data)
                    elif 'event' in data:
                        if data['event'] == 'subscribe':
                            # Extract readable info from subscription response
                            arg = data.get('arg', {})
                            channel = arg.get('channel', 'unknown')
                            inst_id = arg.get('instId', 'unknown')
                            print(f"✅ OKX {channel} 구독: {inst_id}")
                        elif data['event'] == 'error':
                            print(f"❌ OKX WebSocket 오류: {data.get('msg', 'Unknown error')}")
                    else:
                        # Silently ignore other messages
                        pass
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to parse OKX WebSocket message: {e}, message: {message}")
                except Exception as e:
                    print(f"Error handling OKX WebSocket message: {e}, data: {message}")
                        
        except Exception as e:
            print(f"OKX WebSocket connection error: {e}")
            self.connected = False
    
    async def _handle_ticker_data(self, data: Dict) -> None:
        try:
            # Get symbol from either instId or symbol field
            okx_symbol = data.get('instId') or data.get('symbol')
            if not okx_symbol:
                return  # Silently skip if no symbol
            
            # Convert back to standard format
            symbol = self._convert_symbol_from_okx_format(okx_symbol)
            
            # Use bidPx/askPx if available, otherwise use last
            bid_price = data.get('bidPx')
            ask_price = data.get('askPx')
            last_price = data.get('last') or data.get('lastPrice')
            
            if bid_price and ask_price:
                bid = float(bid_price)
                ask = float(ask_price)
            elif last_price:
                # Use lastPrice as both bid and ask if bid/ask not available
                last = float(last_price)
                bid = last * 0.9999  # Slightly lower for bid
                ask = last * 1.0001  # Slightly higher for ask
            else:
                return  # Skip if no price data available
            
            ticker = Ticker(
                symbol=symbol,
                bid=bid,
                ask=ask,
                bid_size=float(data.get('bidSz', 0)),
                ask_size=float(data.get('askSz', 0)),
                timestamp=float(data.get('ts', time.time() * 1000)) / 1000
            )
            await self._emit_ticker(ticker)
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error processing OKX ticker data: {e}, data: {data}")
    
    async def _handle_orderbook_data(self, data: Dict) -> None:
        try:
            required_fields = ['bids', 'asks']
            if not all(key in data for key in required_fields):
                # Missing required fields - skip silently
                return
            
            # Determine symbol field
            okx_symbol = data.get('instId') or data.get('symbol')
            if not okx_symbol:
                # No symbol info available - skip silently
                return
            
            # Convert back to standard format
            symbol = self._convert_symbol_from_okx_format(okx_symbol)
            
            orderbook = OrderBook(
                symbol=symbol,
                bids=[(float(bid[0]), float(bid[1])) for bid in data['bids'] if len(bid) >= 2],
                asks=[(float(ask[0]), float(ask[1])) for ask in data['asks'] if len(ask) >= 2],
                timestamp=float(data.get('ts', time.time() * 1000)) / 1000
            )
            await self._emit_orderbook(orderbook)
        except (KeyError, ValueError, TypeError, IndexError) as e:
            print(f"Error processing OKX orderbook data: {e}, data: {data}")
    
    async def get_ticker(self, symbol: str) -> Ticker:
        okx_symbol = self._convert_symbol_to_okx_format(symbol)
        data = await self._make_request('GET', '/api/v5/market/ticker', {'instId': okx_symbol})
        ticker_data = data['data'][0]
        return Ticker(
            symbol=ticker_data['instId'],
            bid=float(ticker_data['bidPx']),
            ask=float(ticker_data['askPx']),
            bid_size=float(ticker_data['bidSz']),
            ask_size=float(ticker_data['askSz']),
            timestamp=float(ticker_data['ts']) / 1000
        )
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> OrderBook:
        okx_symbol = self._convert_symbol_to_okx_format(symbol)
        sz = min(limit, 400)  # OKX max is 400
        data = await self._make_request('GET', '/api/v5/market/books', {'instId': okx_symbol, 'sz': sz})
        orderbook_data = data['data'][0]
        return OrderBook(
            symbol=symbol,
            bids=[(float(bid[0]), float(bid[1])) for bid in orderbook_data['bids']],
            asks=[(float(ask[0]), float(ask[1])) for ask in orderbook_data['asks']],
            timestamp=float(orderbook_data['ts']) / 1000
        )
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None) -> Order:
        okx_symbol = self._convert_symbol_to_okx_format(symbol)
        params = {
            'instId': okx_symbol,
            'tdMode': 'cash',  # Spot trading
            'side': side.value,
            'ordType': order_type.value,
            'sz': str(quantity),
        }
        
        if order_type == OrderType.LIMIT and price is not None:
            params['px'] = str(price)
        
        data = await self._make_request('POST', '/api/v5/trade/order', params, signed=True)
        order_data = data['data'][0]
        
        return Order(
            order_id=order_data['ordId'],
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            price=price,
            status=self._map_order_status(order_data['sCode']),
            timestamp=time.time()
        )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            okx_symbol = self._convert_symbol_to_okx_format(symbol)
            await self._make_request('POST', '/api/v5/trade/cancel-order', 
                                   {'instId': okx_symbol, 'ordId': order_id}, signed=True)
            return True
        except Exception:
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        okx_symbol = self._convert_symbol_to_okx_format(symbol)
        data = await self._make_request('GET', '/api/v5/trade/order', 
                                      {'instId': okx_symbol, 'ordId': order_id}, signed=True)
        
        order_data = data['data'][0]
        
        return Order(
            order_id=order_data['ordId'],
            symbol=order_data['instId'],
            side=OrderSide(order_data['side']),
            type=OrderType(order_data['ordType']),
            quantity=float(order_data['sz']),
            price=float(order_data['px']) if order_data['px'] else None,
            status=self._map_order_status(order_data['state']),
            filled_quantity=float(order_data['fillSz']),
            average_price=float(order_data['avgPx']) if order_data['avgPx'] else None,
            timestamp=float(order_data['cTime']) / 1000
        )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        data = await self._make_request('GET', '/api/v5/account/balance', signed=True)
        
        balances = {}
        for account in data['data']:
            for detail in account['details']:
                asset_name = detail['ccy']
                if asset is None or asset_name == asset:
                    free = float(detail['availBal'])
                    frozen = float(detail['frozenBal'])
                    balances[asset_name] = Balance(
                        asset=asset_name,
                        free=free,
                        locked=frozen,
                        total=free + frozen
                    )
        
        return balances
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        try:
            okx_symbol = self._convert_symbol_to_okx_format(symbol)
            data = await self._make_request('GET', '/api/v5/account/trade-fee', 
                                          {'instType': 'SPOT', 'instId': okx_symbol}, signed=True)
            
            if not data or 'data' not in data or not data['data']:
                print(f"No fee data returned from OKX for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            fee_data = data['data'][0] if data['data'] else None
            if not fee_data or not isinstance(fee_data, dict):
                print(f"Invalid fee data structure from OKX for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            try:
                maker_fee = float(fee_data.get('maker', 0.001))
                taker_fee = float(fee_data.get('taker', 0.001))
            except (ValueError, TypeError):
                print(f"Invalid fee rate values from OKX for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            return {
                'maker': maker_fee,
                'taker': taker_fee
            }
            
        except Exception as e:
            print(f"Error getting OKX trading fees for {symbol}: {e}, using default rates")
            return {'maker': 0.001, 'taker': 0.001}
    
    async def get_symbols(self) -> List[str]:
        data = await self._make_request('GET', '/api/v5/public/instruments', {'instType': 'SPOT'})
        return [instrument['instId'] for instrument in data['data'] 
                if instrument['state'] == 'live']
    
    async def get_all_tickers(self) -> List[Dict]:
        """Get all ticker statistics"""
        try:
            data = await self._make_request('GET', '/api/v5/market/tickers', {'instType': 'SPOT'})
            if data and 'data' in data:
                return data['data']
            return []
        except Exception as e:
            logger.error(f"Failed to get OKX tickers: {e}")
            return []
    
    def _map_order_status(self, okx_status: str) -> OrderStatus:
        status_map = {
            'live': OrderStatus.NEW,
            'partially_filled': OrderStatus.PARTIALLY_FILLED,
            'filled': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELED,
            'mmp_canceled': OrderStatus.CANCELED,
            'rejected': OrderStatus.REJECTED,
            '0': OrderStatus.NEW,  # sCode success
        }
        return status_map.get(okx_status, OrderStatus.NEW)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_ws()
        if self.session and not self.session.closed:
            await self.session.close()