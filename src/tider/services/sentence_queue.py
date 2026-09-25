import asyncio
import os
import pathlib
import uuid
import hashlib
from pydantic import BaseModel, field_serializer

from datetime import datetime, timezone

from ..utils import ayml
import re

chunk_filename_re = re.compile(r'^(\d+)\.yaml$')

class Sentence(BaseModel):
    uuid: uuid.UUID
    content: str
    character: str | None
    source: str | None
    author: str | None
    created_at: datetime

    @field_serializer('uuid')
    def serialize_uuid(self, uid: uuid.UUID):
        return str(uid)

    def __hash__(self):
        return self.uuid.int

    @property
    def hash_id(self) -> str:
        h = hashlib.sha512()
        h.update(self.content.encode("utf-8"))
        if self.author is not None:
            h.update(self.author.encode('utf-8'))
        if self.character is not None:
            h.update(self.character.encode('utf-8'))
        if self.source is not None:
            h.update(self.source.encode('utf-8'))
        return h.hexdigest()

class Chunk(BaseModel):
    chunk_id: int
    updated_at: datetime
    sentences: list[Sentence]

class SentenceQueueRepo:
    ROUND_COUNT = 256

    def gen_uuid(self) -> uuid.UUID:
        return uuid.uuid7() # pyright: ignore[reportAttributeAccessIssue]
    
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

        self.chunk_loaded: set[int] = set()
        self.chunk_noexist: set[int] = set()
        self.chunk_updated: set[int] = set()

        self.map: dict[int, Sentence] = {}

    async def chunk_load(self, cid: int) -> Chunk | None:
        if 0 > cid or cid > self.ROUND_COUNT - 1:
            raise Exception() # TODO: to a exp class

        if await asyncio.to_thread(lambda x: os.path.isfile(x), self.path / f'{cid}.yaml'):
            content = await ayml.aread(self.path / f'{cid}.yaml')

            chunk = Chunk.model_validate(content)

            assert chunk.chunk_id == cid

            self.chunk_noexist.discard(cid)
            self.chunk_loaded.add(cid)

            for stc in chunk.sentences:
                self.map[stc.uuid.int] = stc

            return chunk
        else:
            self.chunk_noexist.add(cid)

            return None

    async def chunk_saves(self, *cids: int):
        pass

    async def split_by_chunk(self):
        result: dict[int, set[Sentence]] = {}

        for stc in self.map.values():
            cid = stc.uuid.int % self.ROUND_COUNT

            if cid not in result:
                result[cid] = set()

            result[cid].add(stc)

        return result

    async def chunk_load_all(self):
        await asyncio.gather(*(
            self.chunk_load(i) \
            for i in \
                (
                    int(z[0]) \
                    for z in \
                        (
                            y.groups() \
                            for y in \
                                (
                                    re.fullmatch(chunk_filename_re, x) \
                                    for x in \
                                        await asyncio.to_thread(
                                            lambda p: os.listdir(p), self.path \
                                        )
                                )
                            if y is not None
                        )
                    if len(z) == 1
                )
            if i >= 0 and i <= self.ROUND_COUNT - 1
        ))

    async def iter(self):
        await self.chunk_load_all() # TODO: progressive load

        for v in self.map.values():
            yield v

    async def get_all_stc(self) -> set[Sentence]:
        result: set[Sentence] = set()

        async for s in self.iter():
            result.add(s)

        return result

    async def get(self, uid: uuid.UUID) -> Sentence | None:
        c = self.map[uid.int]

        if c == None:
            if uid.int % self.ROUND_COUNT not in self.chunk_noexist:
                return None
            else:
                await self.chunk_load(uid.int % self.ROUND_COUNT)

                return await self.get(uid)

    async def set(self, stc: Sentence):
        if stc.uuid.int % self.ROUND_COUNT not in self.chunk_loaded:
            await self.chunk_load(stc.uuid.int % self.ROUND_COUNT)

        if stc.uuid.int in self.map:
            if self.map[stc.uuid.int].hash_id == stc.hash_id:
                return

        self.map[stc.uuid.int] = stc

        self.chunk_updated.add(stc.uuid.int % self.ROUND_COUNT)

    async def remove(self, src: Sentence | uuid.UUID):
        if isinstance(src, Sentence):
            src = src.uuid

        uint = src.int

        if uint in self.map:
            del self.map[uint]
            self.chunk_updated.add(uint % self.ROUND_COUNT)

    async def flush(self):
        stcs = await self.split_by_chunk()

        for cid in self.chunk_updated:
            await ayml.awrite(self.path / f'{cid}.yaml', Chunk(
                chunk_id = cid,
                updated_at = datetime.now(timezone.utc),
                sentences = list(stcs.get(cid, set()))
            ).model_dump())

        self.chunk_updated = set()

    async def force_flush(self):
        await self.chunk_load_all()

        stcs = await self.split_by_chunk()

        for cid in self.chunk_loaded:
            await ayml.awrite(self.path / f'{cid}.yaml', Chunk(
                chunk_id = cid,
                updated_at = datetime.now(timezone.utc),
                sentences = list(stcs.get(cid, set()))
            ).model_dump())
