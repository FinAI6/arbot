import asyncio
import json
import time
import hmac
import hashlib
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode
import aiohttp
import websockets
from .base import BaseExchange, Ticker, OrderBook, Order, Balance, OrderSide, OrderType, OrderStatus

logger = logging.getLogger(__name__)


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
        
        # Binance has a limit on streams per connection (200 streams max)
        # Now that message format is fixed, restore to full capacity
        max_symbols_per_connection = 200  # Full test with all 200 symbols as requested
        
        if len(symbols) > max_symbols_per_connection:
            logger.warning(f"Binance WebSocket: Too many symbols ({len(symbols)}), limiting to {max_symbols_per_connection}")
            print(f"⚠️ Binance 심볼 수 제한: {len(symbols)} → {max_symbols_per_connection}")
            symbols = symbols[:max_symbols_per_connection]
            self.symbols = symbols
        
        stream_names = []
        for symbol in symbols:
            symbol_lower = symbol.lower()
            stream_names.append(f"{symbol_lower}@ticker")
            # Only use ticker stream to reduce connection load
            # stream_names.append(f"{symbol_lower}@depth5")
        
        stream_url = f"{self.ws_url}/{'/'.join(stream_names)}"
        
        # Debug: Log WebSocket URL and stream configuration
        logger.info(f"Binance WebSocket URL length: {len(stream_url)} characters")
        logger.info(f"Binance WebSocket URL: {stream_url[:200]}{'...' if len(stream_url) > 200 else ''}")
        logger.info(f"Binance subscribing to {len(stream_names)} streams for {len(symbols)} symbols")
        logger.info(f"First few streams: {stream_names[:5]}")
        
        # Check if URL is too long (Binance has limits)
        if len(stream_url) > 8000:  # Conservative limit
            logger.warning(f"⚠️ Binance WebSocket URL is very long ({len(stream_url)} chars), may cause connection issues")
        
        try:
            self.ws_connection = await websockets.connect(
                stream_url,
                ping_interval=20,  # 20초마다 ping
                ping_timeout=10,   # ping 응답 대기 시간
                close_timeout=10   # 연결 종료 대기 시간
            )
            self.connected = True
            
            # Show subscription completion message like Bybit
            print(f"✅ Binance 구독 완료: {len(symbols)}개 심볼 (총 {len(stream_names)}개 채널)")
            logger.info(f"✅ Binance WebSocket connected with {len(symbols)} symbols and {len(stream_names)} streams")
            
            # Start with simple message handling first, add reconnection later if needed
            logger.info("🔄 About to start Binance WebSocket message handler task...")
            self._ws_task = asyncio.create_task(self._handle_ws_messages())
            logger.info(f"✅ Binance WebSocket message handler task created: {self._ws_task}")
            
            # Give the task a moment to start
            await asyncio.sleep(0.1)
            logger.info(f"📊 Binance WebSocket task state after 0.1s: {self._ws_task.done()}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Binance WebSocket: {e}")
            print(f"❌ Binance WebSocket 연결 실패: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.connected = False
    
    async def disconnect_ws(self) -> None:
        """Properly disconnect WebSocket with cleanup"""
        self.connected = False  # Signal to stop reconnection attempts
        
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None
        
        if self.ws_connection:
            try:
                await self.ws_connection.close()
            except Exception as e:
                logger.warning(f"Error closing Binance WebSocket connection: {e}")
            finally:
                self.ws_connection = None
        
        logger.info("Binance WebSocket disconnected")
    
    async def _handle_ws_messages_with_reconnect(self) -> None:
        """Handle WebSocket messages with automatic reconnection"""
        max_retries = 10
        retry_count = 0
        base_delay = 1
        max_delay = 60
        
        while self.connected or retry_count == 0:
            try:
                # If this is a reconnection attempt, recreate the WebSocket connection
                if retry_count > 0:
                    stream_names = []
                    for symbol in self.symbols:
                        symbol_lower = symbol.lower()
                        stream_names.append(f"{symbol_lower}@ticker")
                    
                    stream_url = f"{self.ws_url}/{'/'.join(stream_names)}"
                    
                    self.ws_connection = await websockets.connect(
                        stream_url,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=10
                    )
                    logger.info(f"Binance WebSocket reconnected successfully (attempt {retry_count})")
                
                # Reset retry count on successful connection
                retry_count = 0
                self.connected = True
                
                # Process messages
                async for message in self.ws_connection:
                    if not self.connected:
                        break
                        
                    try:
                        data = json.loads(message)
                        
                        if 'stream' in data:
                            stream = data['stream']
                            stream_data = data['data']
                            
                            if '@ticker' in stream:
                                # Debug: Log first few ticker messages to verify reception
                                if not hasattr(self, '_binance_ticker_debug_count'):
                                    self._binance_ticker_debug_count = 0
                                self._binance_ticker_debug_count += 1
                                
                                if self._binance_ticker_debug_count <= 3:
                                    logger.info(f"🟢 Binance WebSocket ticker #{self._binance_ticker_debug_count}: {stream_data.get('s')} = {stream_data.get('b')}/{stream_data.get('a')}")
                                elif self._binance_ticker_debug_count == 4:
                                    logger.info("🟢 Binance WebSocket ticker reception confirmed (continuing...)")
                                
                                await self._handle_ticker_data(stream_data)
                            elif '@depth' in stream:
                                await self._handle_depth_data(stream_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Binance WebSocket: Failed to parse message: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Binance WebSocket: Error handling message: {e}")
                        continue
                        
            except websockets.exceptions.ConnectionClosed as e:
                if not self.connected:
                    logger.info("Binance WebSocket connection closed by user")
                    break
                logger.warning(f"Binance WebSocket connection closed: {e}")
                
            except websockets.exceptions.WebSocketException as e:
                logger.warning(f"Binance WebSocket exception: {e}")
                
            except (OSError, ConnectionError, asyncio.TimeoutError) as e:
                logger.warning(f"Binance WebSocket network error: {e}")
                
            except Exception as e:
                logger.error(f"Binance WebSocket unexpected error: {e}")
            
            # Reconnection logic
            if not self.connected:
                break
                
            retry_count += 1
            if retry_count > max_retries:
                logger.error(f"Binance WebSocket failed to reconnect after {max_retries} attempts")
                self.connected = False
                break
            
            # Exponential backoff
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
            logger.info(f"Binance WebSocket reconnecting in {delay:.2f} seconds (attempt {retry_count}/{max_retries})")
            await asyncio.sleep(delay)
        
        logger.info("Binance WebSocket connection permanently closed")
        self.connected = False

    async def _handle_ws_messages(self) -> None:
        """Simple WebSocket message handler with debugging"""
        logger.info("🔄 Binance WebSocket message handler started")
        print("🔄 Binance WebSocket 메시지 핸들러 시작됨")
        
        message_count = 0
        try:
            logger.info("📡 Starting to listen for Binance WebSocket messages...")
            async for message in self.ws_connection:
                message_count += 1
                
                if message_count <= 3:
                    logger.info(f"📨 Binance message #{message_count} received (length: {len(message)})")
                elif message_count == 4:
                    logger.info("📨 Binance message reception confirmed (continuing silently...)")
                
                if not self.connected:
                    logger.info("Binance WebSocket disconnection requested")
                    break
                    
                try:
                    data = json.loads(message)
                    
                    # Debug: Log message structure for first few messages
                    if message_count <= 3:
                        logger.info(f"🔍 Binance message #{message_count} structure: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                        if isinstance(data, dict):
                            if 'stream' in data:
                                logger.info(f"  Stream: {data['stream']}")
                                logger.info(f"  Data keys: {list(data['data'].keys()) if 'data' in data and isinstance(data['data'], dict) else 'no data'}")
                            else:
                                logger.info(f"  No 'stream' key, keys are: {list(data.keys())}")
                    
                    # Handle both combined stream format and individual stream format
                    if 'stream' in data:
                        # Combined stream format: {'stream': 'btcusdt@ticker', 'data': {...}}
                        stream = data['stream']
                        stream_data = data['data']
                        
                        if '@ticker' in stream:
                            if not hasattr(self, '_binance_ticker_debug_count'):
                                self._binance_ticker_debug_count = 0
                            self._binance_ticker_debug_count += 1
                            
                            if self._binance_ticker_debug_count <= 3:
                                logger.info(f"🟢 Binance WebSocket ticker (combined) #{self._binance_ticker_debug_count}: {stream_data.get('s')} = {stream_data.get('b')}/{stream_data.get('a')}")
                            elif self._binance_ticker_debug_count == 4:
                                logger.info("🟢 Binance WebSocket ticker reception confirmed (continuing...)")
                            
                            await self._handle_ticker_data(stream_data)
                        elif '@depth' in stream:
                            await self._handle_depth_data(stream_data)
                        else:
                            if message_count <= 3:
                                logger.info(f"📊 Binance stream type: {stream} (not ticker or depth)")
                    
                    elif 'e' in data and data.get('e') == '24hrTicker':
                        # Individual ticker format: {'e': '24hrTicker', 's': 'BTCUSDT', 'b': '...', ...}
                        if not hasattr(self, '_binance_ticker_debug_count'):
                            self._binance_ticker_debug_count = 0
                        self._binance_ticker_debug_count += 1
                        
                        if self._binance_ticker_debug_count <= 3:
                            logger.info(f"🟢 Binance WebSocket ticker (individual) #{self._binance_ticker_debug_count}: {data.get('s')} = {data.get('b')}/{data.get('a')}")
                            print(f"🟢 Binance ticker #{self._binance_ticker_debug_count}: {data.get('s')} = {data.get('b')}/{data.get('a')}")
                        elif self._binance_ticker_debug_count == 4:
                            logger.info("🟢 Binance WebSocket ticker reception confirmed (continuing...)")
                            print("🟢 Binance WebSocket ticker 수신 정상 (계속 수신 중...)")
                        
                        await self._handle_ticker_data(data)
                    
                    else:
                        # Unknown message format
                        if message_count <= 3:
                            logger.info(f"⚠️ Binance WebSocket: Unknown message format: {str(data)[:200]}")
                        else:
                            logger.debug(f"Binance WebSocket: Unexpected message format: {message[:100]}")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Binance WebSocket: Failed to parse message: {e}")
                    if message_count <= 3:
                        logger.warning(f"Raw message: {message[:200]}")
                except Exception as e:
                    logger.error(f"Binance WebSocket: Error processing message: {e}")
                    if message_count <= 3:
                        import traceback
                        logger.error(f"Processing error traceback: {traceback.format_exc()}")
                        
        except Exception as e:
            logger.error(f"Binance WebSocket connection error: {e}")
            self.connected = False
        finally:
            logger.info("🔄 Binance WebSocket message handler ended")
    
    async def _handle_ticker_data(self, data: Dict) -> None:
        # Debug first few ticker data processes
        if not hasattr(self, '_ticker_data_debug_count'):
            self._ticker_data_debug_count = 0
        self._ticker_data_debug_count += 1
        
        if self._ticker_data_debug_count <= 2:
            logger.info(f"🎯 Binance _handle_ticker_data #{self._ticker_data_debug_count}: {data.get('s')} = {data.get('b')}/{data.get('a')}")
        
        ticker = Ticker(
            symbol=data['s'],
            bid=float(data['b']),
            ask=float(data['a']),
            bid_size=float(data['B']),
            ask_size=float(data['A']),
            timestamp=float(data['E']) / 1000
        )
        
        if self._ticker_data_debug_count <= 2:
            logger.info(f"🚀 Binance about to emit ticker #{self._ticker_data_debug_count}: {ticker.symbol}")
            
        await self._emit_ticker(ticker)
        
        if self._ticker_data_debug_count <= 2:
            logger.info(f"✅ Binance ticker #{self._ticker_data_debug_count} emitted successfully")
    
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