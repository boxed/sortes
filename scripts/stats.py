"""Roll the per-chunk labels up into one small file the page can fetch.

Reading 253 chunk files to draw one panel would cost more than the passages
themselves, so the counting happens here and the page fetches the answer.

  python3 stats.py            write data/stats.json and data/map/<text>.txt
  python3 stats.py --print    show the table without writing
"""
import json
import os
import sys

from common import DATA
from labels import CODES, ORDER, chunk_count, manifest, paths, validate


def tally(text_id, total):
    """How many passages in this text carry each code, and how many none."""
    counts = dict.fromkeys(CODES, 0)
    blank = 0
    labelled = 0
    for number in range(-(-total // 400)):
        if validate(text_id, number) is not None:
            continue
        _, path = paths(text_id, number)
        with open(path) as f:
            for entry in json.load(f):
                labelled += 1
                if not entry:
                    blank += 1
                for code in entry:
                    counts[code] += 1
    return counts, blank, labelled


# Two hex digits per passage: a bitmask of every code it carries, in BITS
# order. A single character per passage would have to pick one code and throw
# the rest away, and then isolating a kind on the map would quietly miss every
# passage where that kind was not the one picked — a threat that is also
# violence belongs under both.
BITS = 'LPTVDW'


def strip(text_id, total):
    """The whole text as one byte per passage, hex encoded."""
    out = []
    for number in range(-(-total // 400)):
        _, path = paths(text_id, number)
        if validate(text_id, number) is not None:
            out.append('00' * min(400, total - number * 400))
            continue
        with open(path) as f:
            for entry in json.load(f):
                mask = 0
                for i, code in enumerate(BITS):
                    if code in entry:
                        mask |= 1 << i
                if 'N' in entry:
                    mask |= 1 << len(BITS)
                out.append('%02x' % mask)
    return ''.join(out)[:total * 2]


def write_maps(rows):
    folder = os.path.join(DATA, 'map')
    os.makedirs(folder, exist_ok=True)
    for row in rows:
        with open(os.path.join(folder, row['id'] + '.txt'), 'w') as f:
            f.write(strip(row['id'], row['count']))


def collect():
    texts = manifest()
    out = []
    for text_id in ORDER:
        text = texts[text_id]
        total = text['count']
        counts, blank, labelled = tally(text_id, total)
        if not labelled:
            continue
        out.append({
            'id': text_id,
            'short': text['short'],
            # A passage can carry up to three codes, so these shares are each
            # "how much of this book does X", not slices of one pie.
            'share': {c: counts[c] / labelled for c in CODES},
            'blank': blank / labelled,
            'labelled': labelled,
            'count': total,
        })
    return out


def main():
    rows = collect()
    if '--print' in sys.argv:
        head = '  '.join(f'{c}' .rjust(5) for c in CODES)
        print(f'{"":16} {head}   none   passages')
        for row in rows:
            bar = '  '.join(f'{row["share"][c]:4.0%}'.rjust(5) for c in CODES)
            print(f'{row["short"]:16} {bar}  {row["blank"]:4.0%}'
                  f'  {row["labelled"]:,}/{row["count"]:,}')
        return
    target = os.path.join(DATA, 'stats.json')
    with open(target, 'w') as f:
        json.dump({'codes': CODES, 'texts': rows}, f, separators=(',', ':'))
    write_maps(rows)
    print(f'{target}  ({len(rows)} texts, maps in {os.path.join(DATA, "map")})')


if __name__ == '__main__':
    main()
