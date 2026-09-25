import sys
import time
import unicodedata
import uuid

from .utils import acli
from .utils import ayml
from .utils import dsu
from .services import sentence_queue, hitokoto_upstream
import pathlib
from datetime import datetime, timezone
from readchar import readkey
REPO_DIR = pathlib.Path("./data/dlystc-sentences-bundle")

ACCEPTED_DIR = REPO_DIR / '..' / 'dlystc-sentences-bundle.accepted'
REJECTED_DIR = REPO_DIR / '..' / 'dlystc-sentences-bundle.rejected'
DUPLICATED_DIR = REPO_DIR / '..' / 'dlystc-sentences-bundle.duplicated'

def str2vec(s: str):
    vec: dict[str, int] = {}

    for c in s:
        if c in vec:
            vec[c] += 1
        else:
            vec[c] = 1

    return vec

def vecdiff(s1: dict[str, int], s2: dict[str, int]):
    vs = set(s1.keys()) | set(s2.keys())

    dif: dict[str, int]= {}

    for c in vs:
        dif[c] = abs(s1.get(c, 0) - s2.get(c, 0))

    return dif

def vecdel(s1: dict[str, int], s2: dict[str, int]):
    dif = vecdiff(s1, s2)
    tdeltol = sum(dif.values())
    tdelavg = tdeltol / len(dif)

    return tdelavg


def strdel(s1: str, s2: str):
    return vecdel(str2vec(s1), str2vec(s2))


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
    d_repo = sentence_queue.SentenceQueueRepo(DUPLICATED_DIR)

    match sys.argv[1]:
        case 'chk':
            st = time.perf_counter()
            
            hallstc = set(map(h_to_s, await hitokoto_upstream.get_all_stcs()))
            aallstc = await a_repo.get_all_stc()
            rallstc = await r_repo.get_all_stc()
            dallstc = await d_repo.get_all_stc()

            hstcmap: dict[int, sentence_queue.Sentence] = {}

            for stc in hallstc:
                hstcmap[stc.uuid.int] = stc

            wait_check = hallstc - aallstc - dallstc - rallstc

            et = time.perf_counter()

            print(f"total: {len(hallstc)} left: {len(wait_check)} prct: {(1 - (len(wait_check) / len(hallstc))) * 100:.4f}%")
            print(f"ready in {et * 1000 - st * 1000:.4f}ms")

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
                        f'Chara : {stc.character if stc.character is not None else ""}',
                        f'Source: {stc.source if stc.source is not None else ""}',
                        f'Author: {stc.author if stc.author is not None else ""}',
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

                            print(res)

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
                                case '!':
                                    try:
                                        uid = uuid.UUID(input("\n\nfix: "))
                                        while True:
                                            print('[a/r/q]')
                                            
                                            r = readkey()
                                            r = r.strip().lower()

                                            print(r)

                                            match r:
                                                case 'a':
                                                    await r_repo.remove(hstcmap[uid.int])
                                                    await a_repo.set(hstcmap[uid.int])
                                                    break
                                                case 'r':
                                                    await a_repo.remove(hstcmap[uid.int])
                                                    await r_repo.set(hstcmap[uid.int])
                                                    break
                                                case 'q': break
                                    except Exception as e: print("Oops:", e)
                        except EOFError:
                            go = False
                            break
                        except KeyboardInterrupt:
                            pass
            finally:
                print("exit")
                try:
                    await a_repo.flush()
                except Exception as e: print(e)
                try:
                    await r_repo.flush()
                except Exception as e: print(e)
        case 'find':
            category = sys.argv[3] if len(sys.argv) == 4 else None
            pat = sys.argv[2]
            if category != None:
                pat, category = category, pat

            aallstc = await a_repo.get_all_stc()
            rallstc = await r_repo.get_all_stc()

            stcs: set[sentence_queue.Sentence] = set()

            match category:
                case 'a':
                    for stc in aallstc:
                        stcs.add(stc)
                case 'r':
                    for stc in rallstc:
                        stcs.add(stc)
                case _:
                    for stc in aallstc:
                        stcs.add(stc)
                    for stc in rallstc:
                        stcs.add(stc)

            for stc in stcs:
                if pat in stc.content or pat in (stc.source or '') or pat in (stc.author or '') or pat in (stc.character or ''):
                    await acli.aprint(
                        '',
                        f' #{str(stc.uuid)}',
                        '',
                        f'    {stc.content}',
                        '',
                        f'Chara : {stc.character if stc.character is not None else ""}',
                        f'Source: {stc.source if stc.source is not None else ""}',
                        f'Author: {stc.author if stc.author is not None else ""}',
                        f'CTime : {stc.created_at.isoformat()}'
                        '',
                        f'Accepted: {stc in aallstc}',
                        f'Rejected: {stc in rallstc}',
                        '',
                        sep = '\n'
                    )


        case 'dedup':
            aallstc = await a_repo.get_all_stc()

            astcmap: dict[int, sentence_queue.Sentence] = {}
            normad: dict[int, str] = {}

            for stc in aallstc:
                astcmap[stc.uuid.int] = stc

                sc = ''.join(ch for ch in unicodedata.normalize('NFKC', stc.content)
                        if unicodedata.category(ch)[0] not in {'Z', 'C', 'P', 'S'}
                )

                normad[stc.uuid.int] = sc

            pol: dict[int, dict[str, int]] = {}

            chrs: set[str] = set()

            for stc in aallstc:
                pol[stc.uuid.int] = str2vec(normad[stc.uuid.int])
                for c in normad[stc.uuid.int]:
                    chrs.add(c)

            print(len(pol), len(chrs))

            try:
                for ci, c in enumerate(chrs):
                    print(ci+1, c)
                    pat = c
                    pols: dict[tuple[int, int], float] = {}
                    for astc in (stc for stc in aallstc if pat in stc.content):
                        for bstc in aallstc:
                            if astc.uuid.int >= bstc.uuid.int:
                                continue
                            sid = astc.uuid.int, bstc.uuid.int

                            pols[sid] = vecdel(pol[astc.uuid.int], pol[bstc.uuid.int])

                    same = list(((k[0], k[1]), v) for k, v in pols.items() if v < 0.5)

                    ds: dsu.DSU[int] = dsu.DSU()

                    for si, d in enumerate(same):
                        k, v = d
                        s1, s2 = k
                        if s2 == s1: continue
                        elif s2 > s1: s2, s1 = s1, s2

                        print(
                            '',
                            f'{str(si + 1).rjust(len(str(len(same))))} / {len(same)}'
                            '',
                            f'{astcmap[s1]}',
                            f'{astcmap[s2]}',
                            f'Delta: {v:.4f}',
                            '',
                            sep = '\n'
                        )

                        dup = v == 0 and astcmap[s1].content == astcmap[s2].content

                        if not dup:
                            while True:
                                print('[y/n]')
                            
                                r = readkey()
                                r = r.strip().lower()
                            
                                print(r)
                            
                                match r:
                                    case 'y':
                                        dup = True
                                        break
                                    case 'n':
                                        break

                        if dup:
                            ds.union(s1, s2)

                    for sstc in ds.groups():
                        cstc = list(sstc)

                        for i, s in enumerate(cstc):
                            print(f'{i}.', astcmap[s])

                        ri = input('idx: ')

                        if ri == 's':
                            continue

                        if ri != 'n':
                            del cstc[int(ri)]

                        for s in cstc:
                            await a_repo.remove(astcmap[s])
                            await d_repo.set(astcmap[s])

                        await a_repo.flush()
                        await d_repo.flush()
            finally:
                print("exit")
                try:
                    await a_repo.flush()
                except Exception as e: print(e)
                try:
                    await d_repo.flush()
                except Exception as e: print(e)