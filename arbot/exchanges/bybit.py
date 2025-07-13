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


class BybitExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.ws_url = "wss://stream-testnet.bybit.com/v5/public/spot" if testnet else "wss://stream.bybit.com/v5/public/spot"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._recv_window = 5000
        self._server_time_offset = 0
        self._subscription_count = 0
        self._expected_subscriptions = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _generate_signature(self, timestamp: str, params: str) -> str:
        param_str = f"{timestamp}{self.api_key}{self._recv_window}{params}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _sync_server_time(self) -> None:
        """Synchronize with Bybit server time to avoid timestamp errors"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/v5/market/time") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        server_time = int(data['result']['timeSecond']) * 1000
                        local_time = int(time.time() * 1000)
                        self._server_time_offset = server_time - local_time
        except Exception as e:
            print(f"Failed to sync Bybit server time: {e}")
            self._server_time_offset = 0

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                          signed: bool = False) -> Dict:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        headers = {}
        
        if signed:
            # Sync server time on first signed request
            if self._server_time_offset == 0:
                await self._sync_server_time()
            
            timestamp = str(int(time.time() * 1000) + self._server_time_offset)
            if method == 'GET':
                param_str = urlencode(params) if params else ""
                signature = self._generate_signature(timestamp, param_str)
                url += f"?{param_str}" if param_str else ""
            else:
                param_str = json.dumps(params) if params else ""
                signature = self._generate_signature(timestamp, param_str)
                headers['Content-Type'] = 'application/json'
            
            headers.update({
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': str(self._recv_window),
                'X-BAPI-SIGN': signature
            })
        
        request_params = {}
        if method == 'GET':
            # For signed GET requests, params are already in the URL
            # For unsigned GET requests, pass params separately
            if not signed:
                request_params['params'] = params
        else:
            request_params['json'] = params
        
        try:
            async with session.request(method, url, headers=headers, **request_params) as response:
                data = await response.json()
                
                # Handle timestamp errors
                if data.get('retCode') == 10002:  # Invalid timestamp
                    await self._sync_server_time()
                    # Retry with corrected timestamp
                    timestamp = str(int(time.time() * 1000) + self._server_time_offset)
                    if method == 'GET':
                        param_str = urlencode(params) if params else ""
                        signature = self._generate_signature(timestamp, param_str)
                        url = f"{self.base_url}{endpoint}"
                        url += f"?{param_str}" if param_str else ""
                    else:
                        param_str = json.dumps(params) if params else ""
                        signature = self._generate_signature(timestamp, param_str)
                    
                    headers.update({
                        'X-BAPI-TIMESTAMP': timestamp,
                        'X-BAPI-SIGN': signature
                    })
                    
                    # For retry, use same request_params logic
                    retry_request_params = {}
                    if method == 'GET':
                        if not signed:
                            retry_request_params['params'] = params
                    else:
                        retry_request_params['json'] = params
                    
                    async with session.request(method, url, headers=headers, **retry_request_params) as retry_response:
                        retry_data = await retry_response.json()
                        if retry_data.get('retCode') != 0:
                            raise Exception(f"Bybit API error: {retry_data}")
                        return retry_data
                elif data.get('retCode') != 0:
                    raise Exception(f"Bybit API error: {data}")
                return data
        except Exception as e:
            raise e
    
    async def connect_ws(self, symbols: List[str]) -> None:
        self.symbols = symbols
        
        # Bybit has stricter limits on WebSocket subscriptions
        # Reduce to ticker only to avoid rate limits and improve stability
        max_symbols_per_connection = 50   # Reduce dramatically to avoid system overload
        
        if len(symbols) > max_symbols_per_connection:
            print(f"⚠️ Bybit 심볼 수 제한: {len(symbols)} → {max_symbols_per_connection}")
            symbols = symbols[:max_symbols_per_connection]
            self.symbols = symbols
        
        self._expected_subscriptions = len(symbols)  # Only ticker subscriptions
        self._subscription_count = 0
        
        try:
            self.ws_connection = await websockets.connect(
                self.ws_url,
                ping_interval=20,  # 표준화된 ping 간격
                ping_timeout=10,   # 표준화된 ping 타임아웃
                close_timeout=10   # 표준화된 종료 타임아웃
            )
            self.connected = True
            
            # Subscribe to tickers only (remove orderbook to reduce load)
            for symbol in symbols:
                await self._subscribe_ticker(symbol)
                # Skip orderbook subscription to reduce connection load
                # await self._subscribe_orderbook(symbol)
            
            self._ws_task = asyncio.create_task(self._handle_ws_messages())
        except Exception as e:
            print(f"Failed to connect to Bybit WebSocket: {e}")
            self.connected = False
    
    async def _subscribe_ticker(self, symbol: str) -> None:
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"tickers.{symbol}"]
        }
        await self.ws_connection.send(json.dumps(subscribe_msg))
    
    async def _subscribe_orderbook(self, symbol: str) -> None:
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"orderbook.1.{symbol}"]
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
        """Handle WebSocket messages with automatic reconnection"""
        max_retries = 5  # Reduce retry attempts to avoid rate limits
        retry_count = 0
        base_delay = 5   # Start with longer delay for rate limit recovery
        max_delay = 120  # Longer max delay
        
        while self.connected or retry_count == 0:
            try:
                # If this is a reconnection attempt, recreate the WebSocket connection
                if retry_count > 0:
                    print(f"🔄 Bybit WebSocket 재연결 시도 {retry_count}/{max_retries}...")
                    self.ws_connection = await websockets.connect(
                        self.ws_url,
                        ping_interval=20,  # 표준화된 ping 간격
                        ping_timeout=10,   # 표준화된 ping 타임아웃
                        close_timeout=10   # 표준화된 종료 타임아웃
                    )
                    
                    # Re-subscribe to all symbols (ticker only)
                    self._subscription_count = 0
                    for symbol in self.symbols:
                        await self._subscribe_ticker(symbol)
                        # Skip orderbook subscription to reduce connection load
                    
                    print(f"✅ Bybit WebSocket 재연결 성공 (시도 {retry_count})")
                
                # Reset retry count on successful connection
                retry_count = 0
                self.connected = True
                
                # Process messages
                async for message in self.ws_connection:
                    if not self.connected:
                        break
                        
                    try:
                        data = json.loads(message)
                        
                        # Handle different message types
                        if 'topic' in data and 'data' in data:
                            topic = data['topic']
                            
                            if topic.startswith('tickers.'):
                                await self._handle_ticker_data(data['data'])
                            elif topic.startswith('orderbook.'):
                                await self._handle_orderbook_data(data['data'])
                        elif 'success' in data:
                            # Subscription success message - count and show summary
                            if data.get('success') and data.get('ret_msg') == 'subscribe':
                                self._subscription_count += 1
                                if self._subscription_count == 1:
                                    # Show connection info on first success
                                    conn_id = data.get('conn_id', 'unknown')
                                    print(f"✅ Bybit WebSocket 연결 완료 (ID: {conn_id[:8]}...)")
                                elif self._subscription_count == self._expected_subscriptions:
                                    # Show final summary when all subscriptions are complete
                                    symbol_count = len(self.symbols) if hasattr(self, 'symbols') else 0
                                    print(f"✅ Bybit 구독 완료: {symbol_count}개 심볼 (총 {self._subscription_count}개 채널)")
                            else:
                                # Parse subscription error details
                                ret_msg = data.get('ret_msg', 'unknown')
                                if 'Invalid symbol' in ret_msg:
                                    # Extract symbol name from error message
                                    import re
                                    symbol_match = re.search(r'\[(.*?)\]', ret_msg)
                                    if symbol_match:
                                        failed_channel = symbol_match.group(1)
                                        # Extract symbol from channel (e.g., tickers.IOTAUSDT -> IOTAUSDT)
                                        if '.' in failed_channel:
                                            symbol = failed_channel.split('.')[-1]
                                            print(f"⚠️ Bybit 구독 실패: Invalid symbol [{symbol}]")
                                        else:
                                            print(f"⚠️ Bybit 구독 실패: {ret_msg}")
                                    else:
                                        print(f"⚠️ Bybit 구독 실패: {ret_msg}")
                                else:
                                    print(f"⚠️ Bybit 구독: {ret_msg}")
                        elif 'ret_msg' in data:
                            # Error message
                            print(f"❌ Bybit 오류: {data.get('ret_msg', 'unknown error')}")
                        else:
                            # Silently ignore other messages
                            pass
                            
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse Bybit WebSocket message: {e}")
                        continue
                    except Exception as e:
                        print(f"Error handling Bybit WebSocket message: {e}")
                        continue
                        
            except websockets.exceptions.ConnectionClosed as e:
                if not self.connected:
                    print("Bybit WebSocket connection closed by user")
                    break
                
                # Check for rate limit related closures
                if "1011" in str(e) or "keepalive ping timeout" in str(e):
                    print(f"⚠️ Bybit WebSocket rate limit detected: {e}")
                    # Add extra delay for rate limit recovery
                    await asyncio.sleep(30)
                else:
                    print(f"⚠️ Bybit WebSocket connection closed: {e}")
                
            except websockets.exceptions.WebSocketException as e:
                print(f"⚠️ Bybit WebSocket exception: {e}")
                
            except (OSError, ConnectionError, asyncio.TimeoutError) as e:
                print(f"⚠️ Bybit WebSocket network error: {e}")
                
            except Exception as e:
                print(f"❌ Bybit WebSocket unexpected error: {e}")
            
            # Reconnection logic
            if not self.connected:
                break
                
            retry_count += 1
            if retry_count > max_retries:
                print(f"❌ Bybit WebSocket failed to reconnect after {max_retries} attempts")
                self.connected = False
                break
            
            # Exponential backoff with rate limit consideration
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
            print(f"⏳ Bybit WebSocket reconnecting in {delay:.2f} seconds (avoiding rate limits)...")
            await asyncio.sleep(delay)
        
        print("Bybit WebSocket connection permanently closed")
        self.connected = False
    
    async def _handle_ticker_data(self, data: Dict) -> None:
        try:
            # Handle both single ticker and list format
            ticker_data = data if isinstance(data, dict) else data[0] if isinstance(data, list) and data else {}
            
            # Check if minimum required fields exist
            if not ticker_data.get('symbol'):
                return  # Silently skip if no symbol
            
            # Use bid1Price/ask1Price if available, otherwise use lastPrice
            bid_price = ticker_data.get('bid1Price')
            ask_price = ticker_data.get('ask1Price')
            last_price = ticker_data.get('lastPrice')
            
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
                symbol=ticker_data['symbol'],
                bid=bid,
                ask=ask,
                bid_size=float(ticker_data.get('bid1Size', 0)),
                ask_size=float(ticker_data.get('ask1Size', 0)),
                timestamp=float(ticker_data.get('ts', time.time() * 1000)) / 1000
            )
            await self._emit_ticker(ticker)
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error processing Bybit ticker data: {e}, data: {data}")
    
    async def _handle_orderbook_data(self, data: Dict) -> None:
        try:
            # Handle both direct data and nested data format
            orderbook_data = data if 's' in data else data.get('data', {}) if isinstance(data, dict) else {}
            
            # Check if required fields exist
            required_fields = ['s', 'b', 'a']
            if not all(key in orderbook_data for key in required_fields):
                # Try alternative format
                if 'symbol' in data and 'bids' in data and 'asks' in data:
                    orderbook_data = data
                    required_fields = ['symbol', 'bids', 'asks']
                else:
                    # Missing required fields - skip silently
                    return
            
            # Handle different data formats
            if 's' in orderbook_data:
                # Standard Bybit format
                symbol = orderbook_data['s']
                bids = orderbook_data['b']
                asks = orderbook_data['a']
            else:
                # Alternative format
                symbol = orderbook_data['symbol']
                bids = orderbook_data['bids']
                asks = orderbook_data['asks']
            
            orderbook = OrderBook(
                symbol=symbol,
                bids=[(float(bid[0]), float(bid[1])) for bid in bids if len(bid) >= 2],
                asks=[(float(ask[0]), float(ask[1])) for ask in asks if len(ask) >= 2],
                timestamp=float(orderbook_data.get('ts', time.time() * 1000)) / 1000
            )
            await self._emit_orderbook(orderbook)
        except (KeyError, ValueError, TypeError, IndexError) as e:
            print(f"Error processing Bybit orderbook data: {e}, data: {data}")
    
    async def get_ticker(self, symbol: str) -> Ticker:
        data = await self._make_request('GET', '/v5/market/tickers', {'category': 'spot', 'symbol': symbol})
        ticker_data = data['result']['list'][0]
        return Ticker(
            symbol=ticker_data['symbol'],
            bid=float(ticker_data['bid1Price']),
            ask=float(ticker_data['ask1Price']),
            bid_size=float(ticker_data['bid1Size']),
            ask_size=float(ticker_data['ask1Size']),
            timestamp=time.time()
        )
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> OrderBook:
        data = await self._make_request('GET', '/v5/market/orderbook', 
                                      {'category': 'spot', 'symbol': symbol, 'limit': limit})
        orderbook_data = data['result']
        return OrderBook(
            symbol=symbol,
            bids=[(float(bid[0]), float(bid[1])) for bid in orderbook_data['b']],
            asks=[(float(ask[0]), float(ask[1])) for ask in orderbook_data['a']],
            timestamp=float(orderbook_data['ts']) / 1000
        )
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None) -> Order:
        params = {
            'category': 'spot',
            'symbol': symbol,
            'side': side.value.title(),
            'orderType': order_type.value.title(),
            'qty': str(quantity),
        }
        
        if order_type == OrderType.LIMIT and price is not None:
            params['price'] = str(price)
        
        data = await self._make_request('POST', '/v5/order/create', params, signed=True)
        order_data = data['result']
        
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
            await self._make_request('POST', '/v5/order/cancel', 
                                   {'category': 'spot', 'symbol': symbol, 'orderId': order_id}, 
                                   signed=True)
            return True
        except Exception:
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        data = await self._make_request('GET', '/v5/order/realtime', 
                                      {'category': 'spot', 'orderId': order_id}, signed=True)
        
        order_data = data['result']['list'][0]
        
        return Order(
            order_id=order_data['orderId'],
            symbol=order_data['symbol'],
            side=OrderSide(order_data['side'].lower()),
            type=OrderType(order_data['orderType'].lower()),
            quantity=float(order_data['qty']),
            price=float(order_data['price']) if order_data['price'] else None,
            status=self._map_order_status(order_data['orderStatus']),
            filled_quantity=float(order_data['cumExecQty']),
            average_price=float(order_data['avgPrice']) if order_data['avgPrice'] else None,
            timestamp=float(order_data['createdTime']) / 1000
        )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        data = await self._make_request('GET', '/v5/account/wallet-balance', 
                                      {'accountType': 'UNIFIED'}, signed=True)
        
        balances = {}
        for account in data['result']['list']:
            for coin in account['coin']:
                asset_name = coin['coin']
                if asset is None or asset_name == asset:
                    free = float(coin['availableToWithdraw'])
                    locked = float(coin['walletBalance']) - free
                    balances[asset_name] = Balance(
                        asset=asset_name,
                        free=free,
                        locked=locked,
                        total=float(coin['walletBalance'])
                    )
        
        return balances
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        try:
            data = await self._make_request('GET', '/v5/account/fee-rate', 
                                          {'category': 'spot', 'symbol': symbol}, signed=True)
            
            # Check if result exists and has data
            if not data or 'result' not in data or not data['result']:
                print(f"No fee data returned for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}  # Default 0.1% fees
            
            result = data['result']
            if 'list' not in result or not result['list']:
                print(f"No fee list returned for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            fee_data = result['list'][0] if result['list'] else None
            if not fee_data or not isinstance(fee_data, dict):
                print(f"Invalid fee data structure for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            # Safely extract fee rates with proper validation
            maker_rate = fee_data.get('makerFeeRate')
            taker_rate = fee_data.get('takerFeeRate')
            
            try:
                maker_fee = float(maker_rate) if maker_rate is not None else 0.001
                taker_fee = float(taker_rate) if taker_rate is not None else 0.001
            except (ValueError, TypeError):
                print(f"Invalid fee rate values for {symbol}, using default rates")
                return {'maker': 0.001, 'taker': 0.001}
            
            return {
                'maker': maker_fee,
                'taker': taker_fee
            }
            
        except Exception as e:
            print(f"Error getting Bybit trading fees for {symbol}: {e}, using default rates")
            return {'maker': 0.001, 'taker': 0.001}  # Default 0.1% fees
    
    async def get_symbols(self) -> List[str]:
        data = await self._make_request('GET', '/v5/market/instruments-info', {'category': 'spot'})
        return [instrument['symbol'] for instrument in data['result']['list'] 
                if instrument['status'] == 'Trading']
    
    async def get_all_tickers(self) -> List[Dict]:
        """Get all ticker statistics"""
        try:
            data = await self._make_request('GET', '/v5/market/tickers', {'category': 'spot'})
            if data and 'result' in data and 'list' in data['result']:
                return data['result']['list']
            return []
        except Exception as e:
            logger.error(f"Failed to get Bybit tickers: {e}")
            return []
    
    def _map_order_status(self, bybit_status: str) -> OrderStatus:
        status_map = {
            'New': OrderStatus.NEW,
            'PartiallyFilled': OrderStatus.PARTIALLY_FILLED,
            'Filled': OrderStatus.FILLED,
            'Cancelled': OrderStatus.CANCELED,
            'Rejected': OrderStatus.REJECTED
        }
        return status_map.get(bybit_status, OrderStatus.NEW)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_ws()
        if self.session and not self.session.closed:
            await self.session.close()