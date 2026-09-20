"""Build the Book of Mormon from the Project Gutenberg plain text (#17)."""
import os
import re

from common import TMP, squash, write_text

SOURCE = 'Project Gutenberg eBook #17'
LICENSE = 'Public domain'

START = 'THE FIRST BOOK OF NEPHI HIS REIGN AND MINISTRY (1 Nephi)'
END = '*** END OF THE PROJECT GUTENBERG EBOOK'

# Single-chapter books get an all-caps heading instead of a "... Chapter n" one.
BOOK_HEADINGS = {
    'THE SECOND BOOK OF NEPHI': '2 Nephi',
    'THE BOOK OF JACOB': 'Jacob',
    'THE BOOK OF ENOS': 'Enos',
    'THE BOOK OF JAROM': 'Jarom',
    'THE BOOK OF OMNI': 'Omni',
    'THE WORDS OF MORMON': 'Words of Mormon',
    'THE BOOK OF MOSIAH': 'Mosiah',
    'THE BOOK OF ALMA': 'Alma',
    'THE BOOK OF HELAMAN': 'Helaman',
    'THIRD BOOK OF NEPHI': '3 Nephi',
    'FOURTH NEPHI': '4 Nephi',
    'THE BOOK OF MORMON': 'Mormon',
    'THE BOOK OF ETHER': 'Ether',
    'THE BOOK OF MORONI': 'Moroni',
}

# "1 Nephi Chapter 1", "Alma Chapter 12", ...
CHAPTER = re.compile(r'^(?P<book>[\w\s\d]+?)\s+Chapter\s+\d+\s*$')
# "1:1 I, Nephi, having been born..."
VERSE = re.compile(r'^(?P<chapter>\d+):(?P<verse>\d+)\s')
# 4 Nephi instead spells the book out on every verse: "4 Nephi 1:39 And it was..."
NAMED_VERSE = re.compile(r'^(?P<book>\d+ Nephi) (?P<chapter>\d+):(?P<verse>\d+)\s')


def collect():
    with open(os.path.join(TMP, 'book-of-mormon.txt')) as f:
        body = f.read()
    body = body[body.index(START):]
    body = body[:body.index(END)]

    book = '1 Nephi'
    ref = None
    buffer = []

    def flush():
        if ref and buffer:
            return ref, squash(' '.join(buffer))

    for block in body.split('\n\n'):
        block = block.strip('\n')
        if not block.strip():
            continue
        stripped = block.strip()
        first_line = stripped.split('\n')[0].strip()
        if first_line in BOOK_HEADINGS:
            done = flush()
            if done:
                yield done
            buffer = []
            ref = None
            book = BOOK_HEADINGS[first_line]
            continue
        heading = CHAPTER.match(stripped)
        if heading and '\n' not in stripped:
            done = flush()
            if done:
                yield done
            buffer = []
            ref = None
            book = heading.group('book').strip()
            continue
        first = block.lstrip()
        start = NAMED_VERSE.match(first) or VERSE.match(first)
        if start:
            done = flush()
            if done:
                yield done
            if 'book' in start.groupdict():
                book = start.group('book')
            ref = f"{book} {start.group('chapter')}:{start.group('verse')}"
            buffer = [first[start.end():]]
        elif ref:
            buffer.append(block)
    done = flush()
    if done:
        yield done


def build():
    return [write_text('book-of-mormon', 'The Book of Mormon', 'Book of Mormon',
                       'Another Testament of Jesus Christ',
                       SOURCE, LICENSE, collect(), tradition='mormonism')]


if __name__ == '__main__':
    build()
