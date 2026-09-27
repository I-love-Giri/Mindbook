import logging
import time
from threading import Lock

logger = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            item = self.cache.get(key)

            if item is None:
                return None

            value, timestamp = item
            now = time.monotonic()

            if now - timestamp > self.ttl:
                del self.cache[key]
                logger.debug("Cache expired for key '%s'", key)
                return None

            logger.debug("Cache hit for key '%s'", key)
            return value

    def set(self, key, value):
        with self.lock:
            self.cache[key] = (value, time.monotonic())
            logger.debug("Cached key '%s'", key)

    def delete(self, key):
        with self.lock:
            self.cache.pop(key, None)

    def clear(self):
        with self.lock:
            self.cache.clear()

    def cleanup(self):
        """Remove all expired cache entries."""
        now = time.monotonic()

        with self.lock:
            expired_keys = [
                key
                for key, (_, timestamp) in self.cache.items()
                if now - timestamp > self.ttl
            ]

            for key in expired_keys:
                del self.cache[key]