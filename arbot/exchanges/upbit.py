import asyncio
import json
import time
import hmac
import hashlib
import uuid
from typing import Dict, List, Optional
from urllib.parse import urlencode, parse_qs, urlparse
import aiohttp
import websockets
import jwt
from .base import BaseExchange, Ticker, OrderBook, Order, Balance, OrderSide, OrderType, OrderStatus
import logging

logger = logging.getLogger(__name__)


class UpbitExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = "https://api.upbit.com"
        self.ws_url = "wss://api.upbit.com/websocket/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self.exchange_name = "upbit"
        self._krw_to_usd_rate = 1.0 / 1300.0  # Default rate, updated dynamically
        self._rate_last_updated = 0
        
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _generate_jwt_token(self, query_params: Optional[Dict] = None) -> str:
        """Generate JWT token for authenticated requests"""
        payload = {
            'access_key': self.api_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query_params:
            query_string = urlencode(query_params, doseq=True)
            payload['query_hash'] = hashlib.sha512(query_string.encode()).hexdigest()
            payload['query_hash_alg'] = 'SHA512'
        
        return jwt.encode(payload, self.api_secret, algorithm='HS256')
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                          signed: bool = False) -> Dict:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        headers = {}
        request_params = {}
        
        if signed:
            token = self._generate_jwt_token(params)
            headers['Authorization'] = f'Bearer {token}'
        
        if method == 'GET':
            request_params['params'] = params
        else:
            request_params['json'] = params
            headers['Content-Type'] = 'application/json'
        
        try:
            async with session.request(method, url, headers=headers, **request_params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Upbit API error ({response.status}): {error_data}")
        except Exception as e:
            raise e
    
    async def _get_krw_to_usd_rate(self) -> float:
        """Get current KRW to USD exchange rate with caching"""
        current_time = time.time()
        
        # Update rate every 10 minutes
        if current_time - self._rate_last_updated > 600:
            try:
                # Try to get USD/KRW rate from Upbit
                data = await self._make_request('GET', '/v1/ticker', {'markets': 'KRW-USDT'})
                if data:
                    krw_per_usdt = float(data[0]['trade_price'])
                    self._krw_to_usd_rate = 1.0 / krw_per_usdt
                    self._rate_last_updated = current_time
                    logger.info(f"Updated KRW/USD rate: {self._krw_to_usd_rate:.6f} (1 USD = {krw_per_usdt:.2f} KRW)")
            except Exception as e:
                logger.warning(f"Failed to update KRW/USD rate: {e}, using default rate")
                # Keep existing rate or use default
                if self._krw_to_usd_rate == 0:
                    self._krw_to_usd_rate = 1.0 / 1300.0
        
        return self._krw_to_usd_rate
    
    async def connect_ws(self, symbols: List[str]) -> None:
        """Connect to Upbit WebSocket and subscribe to ticker data"""
        self.symbols = symbols
        
        # Upbit WebSocket connection limit - conservative approach
        max_symbols_per_connection = 100
        
        if len(symbols) > max_symbols_per_connection:
            logger.warning(f"Upbit WebSocket: Too many symbols ({len(symbols)}), limiting to {max_symbols_per_connection}")
            print(f"⚠️ Upbit 심볼 수 제한: {len(symbols)} → {max_symbols_per_connection}")
            symbols = symbols[:max_symbols_per_connection]
            self.symbols = symbols
        
        try:
            self.ws_connection = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.connected = True
            
            # Subscribe to ticker data for all symbols
            await self._subscribe_tickers(symbols)
            
            print(f"✅ Upbit 구독 완료: {len(symbols)}개 심볼")
            logger.info(f"✅ Upbit WebSocket connected with {len(symbols)} symbols")
            
            self._ws_task = asyncio.create_task(self._handle_ws_messages())
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Upbit WebSocket: {e}")
            print(f"❌ Upbit WebSocket 연결 실패: {e}")
            self.connected = False
    
    async def _subscribe_tickers(self, symbols: List[str]) -> None:
        """Subscribe to ticker data for given symbols"""
        # Convert symbols to Upbit format (e.g., BTCUSDT -> KRW-BTC)
        upbit_symbols = []
        for symbol in symbols:
            if symbol.endswith('USDT'):
                # For USDT pairs, use KRW equivalent
                base = symbol[:-4]  # Remove 'USDT'
                upbit_symbols.append(f"KRW-{base}")
            elif symbol.endswith('BTC'):
                # For BTC pairs, use BTC equivalent
                base = symbol[:-3]  # Remove 'BTC'
                upbit_symbols.append(f"BTC-{base}")
            else:
                # Use as is for other formats
                upbit_symbols.append(symbol)
        
        subscribe_message = [
            {"ticket": str(uuid.uuid4())},
            {
                "type": "ticker",
                "codes": upbit_symbols
            }
        ]
        
        await self.ws_connection.send(json.dumps(subscribe_message))
        logger.info(f"Upbit WebSocket: Subscribed to {len(upbit_symbols)} symbols")
    
    async def disconnect_ws(self) -> None:
        """Disconnect from WebSocket"""
        self.connected = False
        
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
                logger.warning(f"Error closing Upbit WebSocket connection: {e}")
            finally:
                self.ws_connection = None
        
        logger.info("Upbit WebSocket disconnected")
    
    async def _handle_ws_messages(self) -> None:
        """Handle incoming WebSocket messages"""
        message_count = 0
        
        try:
            async for message in self.ws_connection:
                if not self.connected:
                    break
                
                message_count += 1
                
                # Debug first few messages
                if message_count <= 3:
                    logger.info(f"📨 Upbit message #{message_count} received")
                
                try:
                    # Upbit sends binary data, decode it
                    if isinstance(message, bytes):
                        data = json.loads(message.decode('utf-8'))
                    else:
                        data = json.loads(message)
                    
                    # Handle ticker data
                    if data.get('type') == 'ticker':
                        await self._handle_ticker_data(data)
                    elif data.get('type') == 'orderbook':
                        await self._handle_orderbook_data(data)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Upbit WebSocket: Failed to parse message: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Upbit WebSocket: Error handling message: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Upbit WebSocket connection error: {e}")
            self.connected = False
    
    async def _handle_ticker_data(self, data: Dict) -> None:
        """Handle ticker data from WebSocket"""
        try:
            # Map Upbit ticker format to our Ticker format
            symbol = data['code']
            
            # Convert KRW-BTC format back to BTCUSDT format for consistency
            if symbol.startswith('KRW-'):
                base = symbol[4:]  # Remove 'KRW-'
                symbol = f"{base}USDT"
                # Convert KRW price to USD using dynamic rate
                krw_to_usd = await self._get_krw_to_usd_rate()
                trade_price = float(data['trade_price']) * krw_to_usd
            elif symbol.startswith('BTC-'):
                base = symbol[4:]  # Remove 'BTC-'
                symbol = f"{base}BTC"
                trade_price = float(data['trade_price'])
            else:
                trade_price = float(data['trade_price'])
            
            # Create small spread around trade price
            spread = trade_price * 0.0001  # 0.01% spread
            bid = trade_price - spread
            ask = trade_price + spread
            
            ticker = Ticker(
                symbol=symbol,
                bid=bid,
                ask=ask,
                bid_size=float(data.get('acc_trade_volume_24h', 0)),  # Use 24h volume as size
                ask_size=float(data.get('acc_trade_volume_24h', 0)),
                timestamp=float(data.get('timestamp', time.time() * 1000)) / 1000
            )
            
            await self._emit_ticker(ticker)
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error processing Upbit ticker data: {e}, data: {data}")
    
    async def _handle_orderbook_data(self, data: Dict) -> None:
        """Handle orderbook data from WebSocket"""
        try:
            symbol = data['code']
            
            # Convert symbol format
            if symbol.startswith('KRW-'):
                base = symbol[4:]
                symbol = f"{base}USDT"
            elif symbol.startswith('BTC-'):
                base = symbol[4:]
                symbol = f"{base}BTC"
            
            # Parse orderbook data
            orderbook_units = data.get('orderbook_units', [])
            
            bids = []
            asks = []
            
            for unit in orderbook_units:
                if 'bid_price' in unit and 'bid_size' in unit:
                    bids.append((float(unit['bid_price']), float(unit['bid_size'])))
                if 'ask_price' in unit and 'ask_size' in unit:
                    asks.append((float(unit['ask_price']), float(unit['ask_size'])))
            
            orderbook = OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=float(data.get('timestamp', time.time() * 1000)) / 1000
            )
            
            await self._emit_orderbook(orderbook)
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error processing Upbit orderbook data: {e}, data: {data}")
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker data via REST API"""
        # Convert symbol to Upbit format
        upbit_symbol = self._convert_symbol_to_upbit(symbol)
        
        data = await self._make_request('GET', f'/v1/ticker', {'markets': upbit_symbol})
        ticker_data = data[0] if data else {}
        
        trade_price = float(ticker_data.get('trade_price', 0))
        
        # Convert KRW price to USD if needed
        if upbit_symbol.startswith('KRW-'):
            krw_to_usd = await self._get_krw_to_usd_rate()
            trade_price = trade_price * krw_to_usd
        
        spread = trade_price * 0.0001
        
        return Ticker(
            symbol=symbol,
            bid=trade_price - spread,
            ask=trade_price + spread,
            bid_size=float(ticker_data.get('acc_trade_volume_24h', 0)),
            ask_size=float(ticker_data.get('acc_trade_volume_24h', 0)),
            timestamp=time.time()
        )
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> OrderBook:
        """Get orderbook data via REST API"""
        upbit_symbol = self._convert_symbol_to_upbit(symbol)
        
        data = await self._make_request('GET', f'/v1/orderbook', {'markets': upbit_symbol})
        orderbook_data = data[0] if data else {}
        
        orderbook_units = orderbook_data.get('orderbook_units', [])
        
        bids = []
        asks = []
        
        for unit in orderbook_units:
            if 'bid_price' in unit and 'bid_size' in unit:
                bids.append((float(unit['bid_price']), float(unit['bid_size'])))
            if 'ask_price' in unit and 'ask_size' in unit:
                asks.append((float(unit['ask_price']), float(unit['ask_size'])))
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=time.time()
        )
    
    def _convert_symbol_to_upbit(self, symbol: str) -> str:
        """Convert standard symbol to Upbit format"""
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            return f"KRW-{base}"
        elif symbol.endswith('BTC'):
            base = symbol[:-3]
            return f"BTC-{base}"
        else:
            return symbol
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None) -> Order:
        """Place an order"""
        upbit_symbol = self._convert_symbol_to_upbit(symbol)
        
        params = {
            'market': upbit_symbol,
            'side': 'bid' if side == OrderSide.BUY else 'ask',
            'ord_type': 'limit' if order_type == OrderType.LIMIT else 'market'
        }
        
        if order_type == OrderType.LIMIT and price is not None:
            params['price'] = str(price)
            params['volume'] = str(quantity)
        else:
            if side == OrderSide.BUY:
                params['price'] = str(quantity)  # For market buy, quantity is in quote currency
            else:
                params['volume'] = str(quantity)  # For market sell, quantity is in base currency
        
        data = await self._make_request('POST', '/v1/orders', params, signed=True)
        
        return Order(
            order_id=data['uuid'],
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.NEW,
            timestamp=time.time()
        )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            await self._make_request('DELETE', '/v1/order', {'uuid': order_id}, signed=True)
            return True
        except Exception:
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Get order status"""
        data = await self._make_request('GET', '/v1/order', {'uuid': order_id}, signed=True)
        
        side = OrderSide.BUY if data['side'] == 'bid' else OrderSide.SELL
        order_type = OrderType.LIMIT if data['ord_type'] == 'limit' else OrderType.MARKET
        
        return Order(
            order_id=data['uuid'],
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=float(data['volume']),
            price=float(data['price']) if data['price'] else None,
            status=self._map_order_status(data['state']),
            filled_quantity=float(data['executed_volume']),
            timestamp=time.time()
        )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """Get account balance"""
        data = await self._make_request('GET', '/v1/accounts', signed=True)
        
        balances = {}
        for balance_data in data:
            asset_name = balance_data['currency']
            if asset is None or asset_name == asset:
                balance = float(balance_data['balance'])
                locked = float(balance_data['locked'])
                free = balance - locked
                
                balances[asset_name] = Balance(
                    asset=asset_name,
                    free=free,
                    locked=locked,
                    total=balance
                )
        
        return balances
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get trading fees for a symbol"""
        # Upbit has standard fees, return default values
        # This would need to be implemented with actual fee API if available
        return {
            'maker': 0.0005,  # 0.05% maker fee
            'taker': 0.0005   # 0.05% taker fee
        }
    
    async def get_symbols(self) -> List[str]:
        """Get all available trading symbols"""
        data = await self._make_request('GET', '/v1/market/all')
        
        symbols = []
        for market_data in data:
            market = market_data['market']
            # Convert Upbit format to standard format
            if market.startswith('KRW-'):
                base = market[4:]
                symbols.append(f"{base}USDT")
            elif market.startswith('BTC-'):
                base = market[4:]
                symbols.append(f"{base}BTC")
            else:
                symbols.append(market)
        
        return symbols
    
    async def get_all_tickers(self) -> List[Dict]:
        """Get all ticker data"""
        try:
            # Get all markets first
            markets_data = await self._make_request('GET', '/v1/market/all')
            markets = [market['market'] for market in markets_data]
            
            # Get ticker data for all markets
            tickers_data = await self._make_request('GET', '/v1/ticker', {'markets': ','.join(markets)})
            
            # Convert to standard format
            result = []
            for ticker in tickers_data:
                result.append({
                    'symbol': ticker['market'],
                    'volume': ticker.get('acc_trade_volume_24h', 0),
                    'quoteVolume': ticker.get('acc_trade_price_24h', 0),
                    'lastPrice': ticker.get('trade_price', 0)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get Upbit tickers: {e}")
            return []
    
    def _map_order_status(self, upbit_status: str) -> OrderStatus:
        """Map Upbit order status to our OrderStatus enum"""
        status_map = {
            'wait': OrderStatus.NEW,
            'watch': OrderStatus.NEW,
            'done': OrderStatus.FILLED,
            'cancel': OrderStatus.CANCELED
        }
        return status_map.get(upbit_status, OrderStatus.NEW)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_ws()
        if self.session and not self.session.closed:
            await self.session.close()