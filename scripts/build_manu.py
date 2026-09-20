"""Build the Laws of Manu from Bühler's translation (SBE 25).

Twelve chapters of numbered verses, one HTML page each, marked up plainly
enough that the verses come straight out of the <P> tags.
"""
import html
import os
import re

from common import TMP, squash, write_text

SOURCE = 'sacred-texts.com/hin/manu (via the Wayback Machine)'
LICENSE = ('Public domain (The Laws of Manu, Georg Bühler, Sacred Books '
           'of the East vol. 25, 1886)')

PARAGRAPH = re.compile(r'(?is)<P>(.*?)</P>')
# The verse number, which is not always followed by its point: I, 39 opens
# "39 (Horse-faced) Kinnaras" with the period dropped.
VERSE = re.compile(r'^(\d+)\.?\s+(.*)$', re.S)
TAG = re.compile(r'<[^>]+>')
# Bühler's page numbers ride along in the text as their own little paragraph.
PAGE = re.compile(r'^p\.\s*\d+$')


def chapter(number):
    path = os.path.join(TMP, 'hindu', 'manu%02d.htm' % number)
    with open(path, encoding='utf-8', errors='replace') as f:
        page = f.read()

    # Every <P> in these pages is a verse or the tail of one, so an unnumbered
    # paragraph joins the verse above it rather than being dropped.
    verse = None
    for match in PARAGRAPH.finditer(page):
        body = squash(html.unescape(TAG.sub('', match.group(1))))
        if not body or PAGE.match(body):
            continue
        found = VERSE.match(body)
        if found:
            if verse:
                yield verse
            verse = (int(found.group(1)), found.group(2))
        elif verse:
            verse = (verse[0], verse[1] + ' ' + body)
    if verse:
        yield verse


def collect():
    for number in range(1, 13):
        for verse, body in chapter(number):
            yield f'{number}.{verse}', body


def build():
    return [write_text('laws-of-manu', 'The Laws of Manu', 'Laws of Manu',
                       'Translated by Georg Bühler',
                       SOURCE, LICENSE, collect(), tradition='hinduism')]


if __name__ == '__main__':
    build()
