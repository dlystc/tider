from typing import Callable, Coroutine
import asyncio
from functools import wraps

def asyncify(func: Callable) -> Callable:
    @wraps(func)
    def _(*args, **kwds):
        return asyncio.to_thread(lambda a, k: func(*a, **k), args, kwds)
    return _