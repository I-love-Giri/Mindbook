import logging
import time

logger = logging.getLogger(__name__)

def _retry( func , retries: 3 , base_wait: float = 1.0 ):

    last_exc: Exception = RuntimeError("No attempts made ")

    for attempt in range(retries):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            wait= base_wait * ( 2 ** attempt)
            logger.debug(
                "Attempt %d/%d failed (%s); retrying in %.1fs",
                attempt + 1, retries, exc, wait,
            )
            time.sleep(wait)

    raise last_exc
