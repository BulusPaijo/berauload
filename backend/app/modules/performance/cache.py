"""Bounded short-lived aggregate cache. Explicitly invalidated on reading writes.

The deployment runs a single Uvicorn worker. With multiple workers a shared
cache/invalidation strategy is required before enabling a longer-lived cache.
"""
from collections import OrderedDict
from threading import RLock
from time import monotonic

_MAX = 128
_TTL_SECONDS = 45
_lock = RLock()
_cache = OrderedDict()
_generation = 0


def clear_reading_cache():
    """Invalidate every cached series after any successful measurement commit."""
    global _generation
    with _lock:
        _generation += 1
        _cache.clear()


def get_or_compute(key, compute):
    with _lock:
        generation = _generation
        entry = _cache.get(key)
        if entry and monotonic() - entry[0] <= _TTL_SECONDS:
            _cache.move_to_end(key)
            return entry[1]
    result = compute()
    with _lock:
        if generation == _generation:
            _cache[key] = (monotonic(), result)
            _cache.move_to_end(key)
            while len(_cache) > _MAX:
                _cache.popitem(last=False)
    return result
