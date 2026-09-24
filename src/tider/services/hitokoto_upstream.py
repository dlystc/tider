import pathlib
from pydantic import BaseModel, field_serializer
import uuid
from datetime import datetime
from .sentence_queue import Sentence
from ..utils import ajson
import hashlib
REPO_DIR = pathlib.Path("./data/hitokoto-sentences-bundle")

CTG_PATH = REPO_DIR / 'categories.json'

STC_DIR_PATH = REPO_DIR

class HitokotoSentence(BaseModel):
    uuid: uuid.UUID
    content: str
    source: str | None
    author: str | None
    created_at: datetime

    def __hash__(self):
        return self.uuid.int

    @property
    def hash_id(self) -> str:
        h = hashlib.sha512()
        h.update(self.content.encode("utf-8"))
        if self.author is not None:
            h.update(self.author.encode('utf-8'))
        if self.source is not None:
            h.update(self.source.encode('utf-8'))
        return h.hexdigest()

async def get_all_stcs() -> set[HitokotoSentence]:
    result: set[HitokotoSentence] = set()

    for ctg in await ajson.aread(CTG_PATH):
        ctgp = STC_DIR_PATH / ctg['path']

        c = await ajson.aread(ctgp)

        for d in c:
            try:
                result.add(HitokotoSentence(
                    uuid = uuid.UUID(d['uuid']),
                    content = d['hitokoto'],
                    author = d['from_who'],
                    source = d['from'],
                    created_at = datetime.fromtimestamp(float(d['created_at']))
                ))
            except:
                result.add(HitokotoSentence(
                    uuid = uuid.UUID(d['uuid']),
                    content = d['hitokoto'],
                    author = d['from_who'],
                    source = d['from'],
                    created_at = datetime.fromtimestamp(float(d['created_at']) / 1000)
                ))

    return result