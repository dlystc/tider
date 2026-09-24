import time
import uuid

from .utils import acli
from .utils import ayml
from .services import sentence_queue, hitokoto_upstream
import pathlib
from datetime import datetime, timezone
from readchar import readkey
REPO_DIR = pathlib.Path("./data/dlystc-sentences-bundle")

ACCEPTED_DIR = REPO_DIR / '..' / 'dlystc-sentences-bundle.accepted'
REJECTED_DIR = REPO_DIR / '..' / 'dlystc-sentences-bundle.rejected'

def h_to_s(src: hitokoto_upstream.HitokotoSentence):
    return sentence_queue.Sentence(
        content = src.content,
        author = src.author,
        source = src.source,
        uuid = src.uuid,
        created_at = src.created_at,
        character = None
    )

async def amain():
    a_repo = sentence_queue.SentenceQueueRepo(ACCEPTED_DIR)
    r_repo = sentence_queue.SentenceQueueRepo(REJECTED_DIR)
    
    hallstc = set(map(h_to_s, await hitokoto_upstream.get_all_stcs()))
    aallstc = await a_repo.get_all_stc()
    rallstc = await r_repo.get_all_stc()

    wait_check = hallstc - aallstc - rallstc

    tcnt = len(wait_check)
    ccnt = 0

    try:
        go = True
        while go and (stc := wait_check.pop()):
            ccnt += 1
            await acli.aprint(
                '',
                f' {str(ccnt).rjust(len(str(tcnt)))} / {tcnt} #{str(stc.uuid)}',
                '',
                f'    {stc.content}',
                '',
                f'Chara : {stc.character if stc.character is not None else ''}',
                f'Source: {stc.source if stc.source is not None else ''}',
                f'Author: {stc.author if stc.author is not None else ''}',
                f'CTime : {stc.created_at.isoformat()}'
                '',
                '',
                sep = '\n'
            )

            while True:
                try:
                    print('[y/n/s/q]')
                    res = readkey()
                    res = res.strip().lower()

                    match res:
                        case 'y':
                            await a_repo.set(stc)
                            break
                        case 'n':
                            await r_repo.set(stc)
                            break
                        case 'q':
                            go = False
                            break
                        case 's': break
                except KeyboardInterrupt:
                    pass

    except EOFError:
        print('quit')
    finally:
        print("exit")
        try:
            await a_repo.flush()
        except Exception as e: print(e) 
        try:
            await r_repo.flush()
        except Exception as e: print(e) 
        
