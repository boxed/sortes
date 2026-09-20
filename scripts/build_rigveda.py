"""Build the Rig Veda from Griffith's 1896 translation.

The source JSON holds one English string per hymn, with the stanzas run
together and numbered in the text. A stanza is the unit worth landing on, so
they are split apart again here. Griffith's stanzas are printed as verse and
the line breaks are kept, as they are for Arnold's Gita.
"""
import json
import os
import re

from common import TMP, squash, write_text

SOURCE = 'github.com/aasi-archive/rigveda (from sacred-texts.com)'
LICENSE = 'Public domain (The Hymns of the Rigveda, Ralph T. H. Griffith, 1896)'

# A stanza opens with its number at the start of a line. The scan behind this
# text lost the odd numeral — "1ṬHE well thou clavest" — so the marker is
# permissive about what follows the digits, and the stanzas are then renumbered
# in the order they appear rather than by the numeral that was read.
MARKER = re.compile(r'(?m)^\d+[\s,.]*')
# The same scan read a few line-initial "I" as a "1", which would cut a stanza
# in half mid-sentence. A stanza never opens in lower case, so that is the tell.
OPENS = re.compile(r'[^a-z]')


def stanzas(hymn):
    """Split one hymn's English into its stanzas, keeping the verse lines."""
    cuts = [m.start() for m in MARKER.finditer(hymn)
            if OPENS.match(MARKER.sub('', hymn[m.start():m.end() + 2], count=1))]
    if not cuts or cuts[0] != 0:
        cuts.insert(0, 0)       # a hymn whose first numeral was lost
    for start, stop in zip(cuts, cuts[1:] + [len(hymn)]):
        block = MARKER.sub('', hymn[start:stop], count=1)
        lines = [squash(line) for line in block.splitlines()]
        text = '\n'.join(filter(None, lines))
        if text:
            yield text


def collect():
    with open(os.path.join(TMP, 'hindu', 'rig-veda.json')) as f:
        book = json.load(f)
    for mandala in range(1, 11):
        hymns = book[str(mandala)]
        for hymn in range(1, len(hymns) + 1):
            for number, text in enumerate(stanzas(hymns[str(hymn)]['EN']), 1):
                yield f'{mandala}.{hymn}.{number}', text


def build():
    return [write_text('rig-veda', 'The Rig Veda', 'Rig Veda',
                       'Translated by Ralph T. H. Griffith',
                       SOURCE, LICENSE, collect(), tradition='hinduism')]


if __name__ == '__main__':
    build()
