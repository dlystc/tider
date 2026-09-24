import asyncio
from typing import Any

async def ainput(msg: str = "") -> str:
    #return await asyncio.to_thread(lambda x: input(x), msg)
    return input(msg)

async def aprint(*args: Any, end: str = "\n", sep: str = " ") -> None:
    return await asyncio.to_thread(lambda x, y, z: print(*x, end=y, sep=z), args, end, sep)
