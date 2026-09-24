import yaml
import asyncio
import aiofiles
import pathlib
from .wrapper import asyncify
from typing import Any

@asyncify
def _read(path: pathlib.Path):
    with open(path) as f:
        return yaml.safe_load(f)

@asyncify
def _write(path: pathlib.Path, data: Any):
    with open(path, mode = 'w') as f:
        return yaml.safe_dump(data, f)


async def aread(path: pathlib.Path) -> Any:
    return await _read(path)

async def awrite(path: pathlib.Path, data: Any) -> None:
    await _write(path, data)