"""Roll the per-chunk labels up into one small file the page can fetch.

Reading 253 chunk files to draw one panel would cost more than the passages
themselves, so the counting happens here and the page fetches the answer.

  python3 stats.py            write data/stats.json and data/map/<text>.txt
  python3 stats.py --print    show the table without writing
  python3 stats.py --markdown the same table as README.md wants it
"""
import json
import os
import sys

from common import DATA, TRADITIONS
from labels import CODES, FRAME, chunk_count, manifest, paths, validate


def tally(text_id, total):
    """How many passages carry each code, how many none, how many only a chain.

    A passage whose one code is provenance says nothing about what it does — a
    hadith carrying an isnad and no matn. With provenance counted it belongs
    under that; with provenance left out it belongs under "none of these", not
    nowhere, so it is counted separately and the screen puts it where the
    reader has asked for it to go.
    """
    counts = dict.fromkeys(CODES, 0)
    blank = 0
    chain = 0
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
                elif entry == FRAME:
                    chain += 1
                for code in entry:
                    counts[code] += 1
    return counts, blank, chain, labelled


# Two hex digits per passage: a bitmask of every code it carries, in BITS
# order. A single character per passage would have to pick one code and throw
# the rest away, and then isolating a kind on the map would quietly miss every
# passage where that kind was not the one picked — a threat that is also
# violence belongs under both.
BITS = 'LPTVDWA'


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
                    mask |= 1 << len(BITS)   # the eighth and last bit of the byte
                out.append('%02x' % mask)
    return ''.join(out)[:total * 2]


def fold(rows):
    """Roll the per-text figures up into one row per tradition.

    A column on the statistics screen is a tradition, the same as a column on
    the spread. Twenty books abreast was a spreadsheet, and the seams inside a
    book — a rule at every one of the Quran's 114 surahs — came too often to
    read. One column per tradition, with its books shown as bands down the map,
    is the comparison the screen is actually for.
    """
    texts = manifest()
    by_id = {row['id']: row for row in rows}
    out = []
    for tradition, title in TRADITIONS:
        parts = [by_id[text_id] for text_id in texts
                 if texts[text_id]['tradition'] == tradition
                 and text_id in by_id]
        if not parts:
            continue
        out.append({
            'id': tradition,
            'short': title,
            # Summed, not averaged: Islam's figure is across all of its
            # passages, so the long books weigh what they actually weigh.
            'counts': {code: sum(part['counts'][code] for part in parts)
                       for code in CODES},
            'blank': sum(part['blank'] for part in parts),
            'chain': sum(part['chain'] for part in parts),
            'labelled': sum(part['labelled'] for part in parts),
            'count': sum(part['count'] for part in parts),
            # Where each book starts down the column, so the map can band them
            # and a hovered pixel can say which book it came from.
            'parts': [{'id': part['id'], 'short': part['short'],
                       'count': part['count']} for part in parts],
        })
    return out


def write_maps(rows):
    """One map per tradition: its books laid end to end in reading order."""
    folder = os.path.join(DATA, 'map')
    os.makedirs(folder, exist_ok=True)
    for row in rows:
        strips = [strip(part['id'], part['count']) for part in row['parts']]
        with open(os.path.join(folder, row['id'] + '.txt'), 'w') as f:
            f.write(''.join(strips))


def collect():
    texts = manifest()
    out = []
    # Reading order, not size order: the statistics screen lays the books out
    # under their traditions the way the spread does.
    for text_id in texts:
        text = texts[text_id]
        total = text['count']
        counts, blank, chain, labelled = tally(text_id, total)
        if not labelled:
            continue
        out.append({
            'id': text_id,
            'tradition': text['tradition'],
            'short': text['short'],
            # Counts, not shares. The screen divides by a different total
            # depending on whether provenance is being excluded — a passage
            # whose only code is a chain of narrators drops out of the corpus
            # entirely when it is — so the denominator is the page's business
            # and only the raw numbers belong here.
            'counts': {c: counts[c] for c in CODES},
            'blank': blank,
            'chain': chain,
            'labelled': labelled,
            'count': total,
        })
    return out


def markdown(rows):
    """The table README.md carries, so it is never retyped by hand."""
    texts = manifest()
    names = dict(TRADITIONS)
    print('| Tradition | Text | ' + ' | '.join(CODES.values()) + ' | none |')
    print('| --- | --- | ' + ' | '.join('---' for _ in CODES) + ' | --- |')
    for row in rows:
        share, blank = shares(row)
        cells = ' | '.join(f'{share[c]:.0%}' for c in CODES)
        print(f'| {names[texts[row["id"]]["tradition"]]} | {row["short"]} '
              f'| {cells} | {blank:.0%} |')


def shares(row, counting=True):
    """Shares of a row, over the total the reader has asked to divide by."""
    total = row['labelled'] - (0 if counting else row['chain'])
    if not total:
        return {code: 0.0 for code in CODES}, 0.0
    return ({code: row['counts'][code] / total for code in CODES},
            row['blank'] / total)


def main():
    rows = collect()
    if '--markdown' in sys.argv:
        markdown(rows)
        return
    if '--print' in sys.argv:
        head = '  '.join(f'{c}' .rjust(5) for c in CODES)
        print(f'{"":16} {head}   none   passages')
        for row in rows:
            share, blank = shares(row)
            bar = '  '.join(f'{share[c]:4.0%}'.rjust(5) for c in CODES)
            print(f'{row["short"]:16} {bar}  {blank:4.0%}'
                  f'  {row["labelled"]:,}/{row["count"]:,}')
        return
    target = os.path.join(DATA, 'stats.json')
    columns = fold(rows)
    with open(target, 'w') as f:
        json.dump({'codes': CODES, 'traditions': columns}, f,
                  separators=(',', ':'))
    write_maps(columns)
    print(f'{target}  ({len(rows)} texts in {len(columns)} traditions, '
          f'maps in {os.path.join(DATA, "map")})')


if __name__ == '__main__':
    main()
