"""Build the Bhagavad Gita from Edwin Arnold's verse translation (Gutenberg #2388)."""
import os
import re

from common import TMP, squash, write_text

SOURCE = 'Project Gutenberg eBook #2388'
LICENSE = 'Public domain (The Song Celestial, Sir Edwin Arnold, 1885)'

START = 'CHAPTER I'
END = 'HERE ENDS, WITH CHAPTER XVIII.'

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII']

CHAPTER = re.compile(r'^CHAPTER ([IVX]+)$')
# Arnold's notes are printed at the end of the book; drop their call-outs.
FOOTNOTE = re.compile(r'\s*\[FN#\d+\]')
# Arnold closes each chapter with a colophon naming the yoga it teaches.
COLOPHON = re.compile(r'^HERE END(ETH|S,) ', re.I)


def collect():
    with open(os.path.join(TMP, 'bhagavad-gita.txt')) as f:
        body = f.read()
    body = body[body.index('\n' + START + '\n'):]
    body = body[:body.index(END)]

    chapter = 'I'
    stanza = 0
    for block in body.split('\n\n'):
        # Arnold wrote blank verse; the line breaks are the poem, so they are
        # kept and the app renders them.
        block = FOOTNOTE.sub('', block)
        text = '\n'.join(filter(None, (squash(l) for l in block.splitlines())))
        if not text:
            continue
        heading = CHAPTER.match(text.replace('\n', ' '))
        if heading:
            chapter = heading.group(1)
            stanza = 0
            continue
        if COLOPHON.match(text.replace('\n', ' ')):
            continue
        stanza += 1
        yield f'Chapter {ROMAN.index(chapter) + 1}, stanza {stanza}', text


def build():
    return [write_text('bhagavad-gita', 'The Bhagavad Gita', 'Bhagavad Gita',
                       'The Song Celestial, translated by Sir Edwin Arnold',
                       SOURCE, LICENSE, collect())]


if __name__ == '__main__':
    build()
