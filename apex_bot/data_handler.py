"""APEX BOT - Data Handler (with caching & rate-limit protection)"""
import ccxt
import pandas as pd
import time
import logging
from config import Config

logger = logging.getLogger("APEX")


class DataHandler:
    def __init__(self):
        self.exchange = getattr(ccxt, Config.EXCHANGE)({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'enableRateLimit': True,  # ccxt built-in throttle
            'options': {
                'defaultType': 'spot',
            }
        })
        
        # === Cache system ===
        self._cache = {}
        self._cache_ttl = {
            '1m': 30,      # cache 30s
            '5m': 60,      # cache 1 min
            '15m': 120,    # cache 2 min  (une bougie 15m = 900s, pas besoin de refresh toutes les min)
            '1h': 300,     # cache 5 min
            '4h': 600,     # cache 10 min (une bougie 4h = 14400s)
            '1d': 1800,    # cache 30 min
        }
        self._price_cache = {}
        self._price_cache_ttl = 10  # Prix live : cache 10 secondes
        
        # === Rate limit tracking ===
        self._request_count = 0
        self._last_reset = time.time()
        self._ban_until = 0
    
    def _is_banned(self) -> bool:
        """Check if we're currently IP banned"""
        if time.time() < self._ban_until:
            remaining = self._ban_until - time.time()
            logger.warning(f"⛔ IP still banned — {remaining:.0f}s remaining")
            return True
        return False
    
    def _handle_rate_error(self, e):
        """Handle 418/429 errors from Binance"""
        error_str = str(e)
        
        # Cherche le timestamp de fin de ban dans le message d'erreur
        if "banned until" in error_str.lower():
            try:
                # Extrait le timestamp du message d'erreur Binance
                import re
                match = re.search(r'banned until (\d+)', error_str)
                if match:
                    ban_ts = int(match.group(1)) / 1000  # ms → s
                    self._ban_until = ban_ts
                    remaining = ban_ts - time.time()
                    logger.error(f"🚫 IP BANNED by Binance — waiting {remaining:.0f}s ({remaining/3600:.1f}h)")
                    return
            except Exception:
                pass
        
        # Fallback : backoff de 5 minutes
        self._ban_until = time.time() + 300
        logger.error(f"🚫 Rate limited — backing off 5 minutes")
    
    def _safe_request(self, func, *args, **kwargs):
        """Wrapper with retry logic for API calls"""
        if self._is_banned():
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._request_count += 1
                result = func(*args, **kwargs)
                return result
            
            except (ccxt.RateLimitExceeded, ccxt.DDoSProtection) as e:
                self._handle_rate_error(e)
                return None
            
            except ccxt.ExchangeNotAvailable as e:
                if '418' in str(e) or 'teapot' in str(e).lower():
                    self._handle_rate_error(e)
                    return None
                
                wait = (attempt + 1) * 10
                logger.warning(f"⚠️ Exchange unavailable, retry in {wait}s... ({e})")
                time.sleep(wait)
            
            except ccxt.NetworkError as e:
                wait = (attempt + 1) * 5
                logger.warning(f"⚠️ Network error, retry in {wait}s... ({e})")
                time.sleep(wait)
            
            except Exception as e:
                logger.error(f"❌ Unexpected API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise
        
        return None
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
        """Fetch OHLCV data with cache"""
        cache_key = f"{symbol}_{timeframe}_{limit}"
        now = time.time()
        
        # Check cache
        if cache_key in self._cache:
            data, cached_at = self._cache[cache_key]
            ttl = self._cache_ttl.get(timeframe, 60)
            if now - cached_at < ttl:
                logger.debug(f"📦 Cache hit: {cache_key} (age: {now - cached_at:.0f}s / TTL: {ttl}s)")
                return data
        
        # Fetch from exchange
        raw = self._safe_request(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
        
        if raw is None:
            # Return cached data even if stale (better than nothing)
            if cache_key in self._cache:
                logger.warning(f"⚠️ Using stale cache for {cache_key}")
                return self._cache[cache_key][0]
            raise Exception(f"Failed to fetch {cache_key} and no cache available")
        
        df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Store in cache
        self._cache[cache_key] = (df, now)
        logger.debug(f"✅ Fetched & cached: {cache_key} ({len(df)} candles)")
        
        return df
    
    def fetch_price(self, symbol: str) -> float:
        """Fetch current price with cache"""
        now = time.time()
        
        # Check price cache
        if symbol in self._price_cache:
            price, cached_at = self._price_cache[symbol]
            if now - cached_at < self._price_cache_ttl:
                return price
        
        # Fetch from exchange
        ticker = self._safe_request(self.exchange.fetch_ticker, symbol)
        
        if ticker is None:
            # Return stale price if available
            if symbol in self._price_cache:
                logger.warning(f"⚠️ Using stale price for {symbol}")
                return self._price_cache[symbol][0]
            raise Exception(f"Failed to fetch price for {symbol} and no cache available")
        
        price = ticker['last']
        self._price_cache[symbol] = (price, now)
        return price
    
    def get_stats(self) -> dict:
        """Return data handler stats for dashboard"""
        return {
            'request_count': self._request_count,
            'cache_entries': len(self._cache),
            'is_banned': self._is_banned(),
            'ban_remaining': max(0, self._ban_until - time.time()),
        }
