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


class BitgetExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, passphrase: str = ""):
        super().__init__(api_key, api_secret, testnet)
        self.passphrase = passphrase
        self.base_url = "https://api.bitget.com" if not testnet else "https://api.bitget.com"  # Bitget doesn't have separate testnet URL
        self.ws_url = "wss://ws.bitget.com/spot/v1/stream" if not testnet else "wss://ws.bitget.com/spot/v1/stream"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._server_time_offset = 0
    
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
            timestamp = str(int(time.time() * 1000))
            
            if method == 'GET' and params:
                query_string = urlencode(params)
                request_path += f"?{query_string}"
                url += f"?{query_string}"
            elif method in ['POST', 'PUT', 'DELETE'] and params:
                body = json.dumps(params)
            
            signature = self._generate_signature(timestamp, method, request_path, body)
            
            headers.update({
                'ACCESS-KEY': self.api_key,
                'ACCESS-SIGN': signature,
                'ACCESS-TIMESTAMP': timestamp,
                'ACCESS-PASSPHRASE': self.passphrase,
                'locale': 'en-US'
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
            if data.get('code') != '00000':
                raise Exception(f"Bitget API error: {data}")
            return data
    
    async def connect_ws(self, symbols: List[str]) -> None:
        self.symbols = symbols
        
        # Validate symbols against Bitget's available symbols first
        try:
            print(f"🔍 Bitget: Validating {len(symbols)} symbols...")
            valid_symbols = await self._validate_symbols(symbols)
            print(f"✅ Bitget: {len(valid_symbols)} valid symbols out of {len(symbols)}")
            symbols = valid_symbols
        except Exception as e:
            logger.warning(f"Failed to validate Bitget symbols: {e}, using original list")
        
        # Limit symbols for Bitget to avoid overwhelming the connection
        max_symbols_per_connection = 50  # Reduced limit for batch subscription
        
        if len(symbols) > max_symbols_per_connection:
            logger.warning(f"Bitget WebSocket: Too many symbols ({len(symbols)}), limiting to {max_symbols_per_connection}")
            print(f"⚠️ Bitget 심볼 수 제한: {len(symbols)} → {max_symbols_per_connection}")
            symbols = symbols[:max_symbols_per_connection]
            self.symbols = symbols
        
        try:
            self.ws_connection = await websockets.connect(self.ws_url)
            self.connected = True
            
            # Subscribe using batch subscription to avoid rate limits
            print(f"🔄 Bitget: Batch subscribing to {len(symbols)} symbols...")
            
            await self._subscribe_batch(symbols)
            
            print(f"✅ Bitget 구독 완료: {len(symbols)}개 심볼")
            self._ws_task = asyncio.create_task(self._handle_ws_messages())
        except Exception as e:
            print(f"Failed to connect to Bitget WebSocket: {e}")
            self.connected = False
    
    async def _subscribe_ticker(self, symbol: str) -> None:
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"ticker:{symbol}"]
        }
        await self.ws_connection.send(json.dumps(subscribe_msg))
    
    async def _validate_symbols(self, symbols: List[str]) -> List[str]:
        """Validate symbols against Bitget's available symbols using REST API"""
        try:
            # Get all available symbols from Bitget
            available_symbols = await self.get_symbols()
            available_set = set(available_symbols)
            
            # Filter input symbols to only those available on Bitget
            valid_symbols = [symbol for symbol in symbols if symbol in available_set]
            
            invalid_count = len(symbols) - len(valid_symbols)
            if invalid_count > 0:
                logger.info(f"Bitget: Filtered out {invalid_count} invalid symbols")
            
            return valid_symbols
        except Exception as e:
            logger.error(f"Failed to validate Bitget symbols: {e}")
            return symbols  # Return original list if validation fails
    
    def _convert_to_bitget_symbol(self, symbol: str) -> str:
        """Convert standard symbol format to Bitget format"""
        # Bitget might use different formats for WebSocket vs REST
        # For now, return as is, but this can be extended if needed
        return symbol
    
    async def _subscribe_batch(self, symbols: List[str]) -> None:
        """Subscribe to multiple symbols in batches to avoid rate limits"""
        # Bitget supports batch subscription with multiple channels
        # Split into smaller batches to avoid request size limits
        batch_size = 10  # Conservative batch size
        
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            # Create batch subscription for both ticker and orderbook
            # According to Bitget API docs, the format should be channel:symbol
            args = []
            for symbol in batch_symbols:
                # Convert symbol to Bitget format if needed
                bitget_symbol = self._convert_to_bitget_symbol(symbol)
                
                # Add ticker channel - format: "ticker:SYMBOL"
                args.append(f"ticker:{bitget_symbol}")
                # Add orderbook channel - format: "books5:SYMBOL"
                args.append(f"books5:{bitget_symbol}")
            
            subscribe_msg = {
                "op": "subscribe",
                "args": args
            }
            
            try:
                await self.ws_connection.send(json.dumps(subscribe_msg))
                logger.info(f"Bitget: Sent batch subscription for {len(batch_symbols)} symbols")
                
                # Add delay between batches to prevent rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to send batch subscription: {e}")
                # Fallback to individual subscriptions for this batch
                for symbol in batch_symbols:
                    try:
                        bitget_symbol = self._convert_to_bitget_symbol(symbol)
                        await self._subscribe_ticker(bitget_symbol)
                        await self._subscribe_orderbook(bitget_symbol)
                        await asyncio.sleep(0.1)
                    except Exception as sub_e:
                        logger.warning(f"Failed to subscribe to {symbol}: {sub_e}")
    
    async def _subscribe_orderbook(self, symbol: str) -> None:
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"books5:{symbol}"]
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
                        
                        if channel == 'ticker':
                            for ticker_data in data['data']:
                                await self._handle_ticker_data(ticker_data)
                        elif channel == 'books5':
                            for orderbook_data in data['data']:
                                await self._handle_orderbook_data(orderbook_data)
                    elif 'event' in data:
                        if data['event'] == 'subscribe':
                            # Extract readable info from subscription response
                            arg = data.get('arg', 'unknown')
                            if isinstance(arg, str) and ':' in arg:
                                channel, inst_id = arg.split(':', 1)
                                print(f"✅ Bitget {channel} 구독: {inst_id}")
                            else:
                                print(f"✅ Bitget 구독: {arg}")
                        elif data['event'] == 'error':
                            # More detailed error handling
                            error_msg = data.get('msg', 'Unknown error')
                            error_code = data.get('code', 'Unknown code')
                            arg = data.get('arg', {})
                            
                            # Check if it's a symbol existence error
                            if "doesn't exist" in error_msg:
                                # arg is now a string in format "channel:symbol"
                                arg = data.get('arg', 'unknown')
                                if isinstance(arg, str) and ':' in arg:
                                    channel, inst_id = arg.split(':', 1)
                                    logger.warning(f"Bitget symbol not found: {inst_id} (channel: {channel})")
                                else:
                                    logger.warning(f"Bitget symbol not found: {arg}")
                                # Don't print these errors to console to reduce noise
                            elif error_code == '30016':  # param error
                                print(f"⚠️ Bitget param error: {error_msg}")
                                logger.warning(f"Bitget parameter error: {error_msg}")
                                # Log the problematic subscription for debugging
                                arg = data.get('arg', 'unknown')
                                if arg:
                                    logger.warning(f"Problematic subscription: {arg}")
                            else:
                                print(f"❌ Bitget 오류 ({error_code}): {error_msg}")
                    else:
                        # Silently ignore other messages
                        pass
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to parse Bitget WebSocket message: {e}, message: {message}")
                except Exception as e:
                    print(f"Error handling Bitget WebSocket message: {e}, data: {message}")
                        
        except Exception as e:
            print(f"Bitget WebSocket connection error: {e}")
            self.connected = False
    
    async def _handle_ticker_data(self, data: Dict) -> None:
        try:
            # Get symbol from either instId or symbol field
            symbol = data.get('instId') or data.get('symbol')
            if not symbol:
                return  # Silently skip if no symbol
            
            # Use bidPr/askPr if available, otherwise use lastPr
            bid_price = data.get('bidPr')
            ask_price = data.get('askPr')
            last_price = data.get('lastPr') or data.get('lastPrice')
            
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
            print(f"Error processing Bitget ticker data: {e}, data: {data}")
    
    async def _handle_orderbook_data(self, data: Dict) -> None:
        try:
            # Bitget uses different field names: symbol, bids, asks
            required_fields = ['bids', 'asks']
            if not all(key in data for key in required_fields):
                # Missing required fields - skip silently
                return
            
            # Determine symbol field - could be 'symbol' or 'instId'
            symbol = data.get('symbol') or data.get('instId')
            if not symbol:
                # No symbol info available - skip silently
                return
            
            orderbook = OrderBook(
                symbol=symbol,
                bids=[(float(bid[0]), float(bid[1])) for bid in data['bids'] if len(bid) >= 2],
                asks=[(float(ask[0]), float(ask[1])) for ask in data['asks'] if len(ask) >= 2],
                timestamp=float(data.get('ts', time.time() * 1000)) / 1000
            )
            await self._emit_orderbook(orderbook)
        except (KeyError, ValueError, TypeError, IndexError) as e:
            print(f"Error processing Bitget orderbook data: {e}, data: {data}")
    
    async def get_ticker(self, symbol: str) -> Ticker:
        data = await self._make_request('GET', '/api/spot/v1/market/ticker', {'symbol': symbol})
        ticker_data = data['data']
        return Ticker(
            symbol=ticker_data['symbol'],
            bid=float(ticker_data['bidPr']),
            ask=float(ticker_data['askPr']),
            bid_size=float(ticker_data['bidSz']),
            ask_size=float(ticker_data['askSz']),
            timestamp=float(ticker_data['ts']) / 1000
        )
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> OrderBook:
        limit = min(limit, 150)  # Bitget max is 150
        data = await self._make_request('GET', '/api/spot/v1/market/depth', 
                                      {'symbol': symbol, 'limit': limit, 'type': 'step0'})
        orderbook_data = data['data']
        return OrderBook(
            symbol=symbol,
            bids=[(float(bid[0]), float(bid[1])) for bid in orderbook_data['bids']],
            asks=[(float(ask[0]), float(ask[1])) for ask in orderbook_data['asks']],
            timestamp=float(orderbook_data['ts']) / 1000
        )
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None) -> Order:
        params = {
            'symbol': symbol,
            'side': side.value,
            'orderType': order_type.value,
            'quantity': str(quantity),
        }
        
        if order_type == OrderType.LIMIT and price is not None:
            params['price'] = str(price)
        
        data = await self._make_request('POST', '/api/spot/v1/trade/orders', params, signed=True)
        order_data = data['data']
        
        return Order(
            order_id=order_data['orderId'],
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.NEW,
            timestamp=time.time()
        )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            await self._make_request('POST', '/api/spot/v1/trade/cancel-order', 
                                   {'symbol': symbol, 'orderId': order_id}, signed=True)
            return True
        except Exception:
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        data = await self._make_request('GET', '/api/spot/v1/trade/orderInfo', 
                                      {'symbol': symbol, 'orderId': order_id}, signed=True)
        
        order_data = data['data']
        
        return Order(
            order_id=order_data['orderId'],
            symbol=order_data['symbol'],
            side=OrderSide(order_data['side']),
            type=OrderType(order_data['orderType']),
            quantity=float(order_data['quantity']),
            price=float(order_data['price']) if order_data['price'] else None,
            status=self._map_order_status(order_data['status']),
            filled_quantity=float(order_data['fillQuantity']),
            average_price=float(order_data['priceAvg']) if order_data['priceAvg'] else None,
            timestamp=float(order_data['cTime']) / 1000
        )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        data = await self._make_request('GET', '/api/spot/v1/account/assets', signed=True)
        
        balances = {}
        for balance_data in data['data']:
            asset_name = balance_data['coinName']
            if asset is None or asset_name == asset:
                free = float(balance_data['available'])
                locked = float(balance_data['frozen'])
                balances[asset_name] = Balance(
                    asset=asset_name,
                    free=free,
                    locked=locked,
                    total=free + locked
                )
        
        return balances
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        # Bitget doesn't have a direct API for trading fees, using default spot rates
        # Users should check their VIP level for actual rates
        return {
            'maker': 0.001,  # 0.1% default maker fee
            'taker': 0.001   # 0.1% default taker fee
        }
    
    async def get_symbols(self) -> List[str]:
        try:
            data = await self._make_request('GET', '/api/spot/v1/public/products')
            symbols = []
            for symbol_info in data['data']:
                if symbol_info['status'] == 'online':
                    symbol = symbol_info['symbol']
                    # Bitget uses different symbol format (e.g., BTCUSDT_SPBL)
                    # Convert to standard format
                    if '_SPBL' in symbol:
                        symbol = symbol.replace('_SPBL', '')
                    symbols.append(symbol)
            
            logger.info(f"Bitget: Found {len(symbols)} online symbols")
            return symbols
            
        except Exception as e:
            logger.error(f"Failed to get Bitget symbols: {e}")
            return []
    
    async def get_all_tickers(self) -> List[Dict]:
        """Get all ticker statistics"""
        try:
            data = await self._make_request('GET', '/api/spot/v1/market/tickers')
            if data and 'data' in data:
                return data['data']
            return []
        except Exception as e:
            logger.error(f"Failed to get Bitget tickers: {e}")
            return []
    
    def _map_order_status(self, bitget_status: str) -> OrderStatus:
        status_map = {
            'new': OrderStatus.NEW,
            'partial_fill': OrderStatus.PARTIALLY_FILLED,
            'full_fill': OrderStatus.FILLED,
            'cancelled': OrderStatus.CANCELED,
            'rejected': OrderStatus.REJECTED
        }
        return status_map.get(bitget_status, OrderStatus.NEW)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_ws()
        if self.session and not self.session.closed:
            await self.session.close()