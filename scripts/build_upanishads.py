"""Build the twelve principal Upanishads from Müller's SBE volumes 1 and 15.

Both volumes are one HTML page per khanda, and the page title already names
which Upanishad and which chapter it is — "The Upanishads, Part 1 (SBE01):
Khândogya Upanishad: I, 9" — so the reference comes out of the title and only
the verse number has to be read off the text. Pages whose title has no chapter
reference are Müller's introduction, front matter and indexes, and are skipped:
they are his prose, not the Upanishads.
"""
import glob
import html
import os
import re

from common import TMP, squash, write_text

SOURCE = 'sacred-texts.com/hin/sbe01 and sbe15 (via the Wayback Machine)'
LICENSE = ('Public domain (The Upanishads, F. Max Müller, Sacred Books of '
           'the East vols. 1 and 15, 1879 and 1884)')

TITLE = re.compile(r'(?is)<title>(.*?)</title>')
TAG = re.compile(r'<[^>]+>')

# What separates Müller's own pages from the translation: a chapter reference.
# He heads a chapter in whichever word the Upanishad itself uses, so there are
# three shapes of it — "I, 9" and "I, 5, 2" for the two he numbers outright,
# "Khanda IV" or "Adhyâya II" for most of the rest, and "Fourth Question" for
# the Prasña, which is put as six questions.
NUMBERED = re.compile(r'^([IVXLC]+)((?:,\s*\d+)*)$')
DIVISION = re.compile(
    r'^(?:Khanda|Adhy\u00e2ya|Prap\u00e2thaka|Valli|Anuv\u00e2ka|Question|'
    r'Br\u00e2hmana)\s+([IVXLC]+)$', re.I)
ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh',
            'eighth', 'ninth', 'tenth']
WORDED = re.compile(
    r'^(' + '|'.join(ORDINALS) + r')\s+'
    r'(?:Question|Prap\u00e2thaka|Khanda|Adhy\u00e2ya|Valli|Anuv\u00e2ka)$', re.I)

# Müller titles a work at length and then repeats the short name people use.
# Nothing is lost by taking the short one, and the reference is read at a
# glance rather than unpicked.
SHORTER = {
    'Talavak\u00e2ra or Kena-Upanishad': 'Kena-Upanishad',
    'Vâgasaneyi-Samhitâ-Upanishad, sometimes called Îsâvâsya or '
    'Îsâ-Upanishad.': 'Îsâ-Upanishad',
}

ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}


def arabic(numeral):
    total = 0
    for this, following in zip(numeral, numeral[1:] + ' '):
        total += -ROMAN[this] if ROMAN.get(following, 0) > ROMAN[this] \
            else ROMAN[this]
    return total


def chapter_of(tail, work):
    """The chapter part of a reference, or None where the page is not one."""
    found = NUMBERED.match(tail)
    if found:
        rest = [n.strip() for n in found.group(2).split(',') if n.strip()]
        return '.'.join([str(arabic(found.group(1)))] + rest)
    found = DIVISION.match(tail)
    if found:
        return str(arabic(found.group(1).upper()))
    found = WORDED.match(tail)
    if found:
        return str(ORDINALS.index(found.group(1).lower()) + 1)
    # A work of a single chapter names itself again instead of numbering: the
    # Îsâ page is headed with the full title and then "Îsâ-Upanishad", and is
    # one run of eighteen verses. A heading that repeats itself exactly is not
    # that — it is front matter, "Introduction: Introduction".
    short = tail.rstrip('.')
    if short and short != work and short in work:
        return '1'
    return None


def reference(title):
    """('Kena-Upanishad', '1') for a translation page, else None.

    The volume also carries Hume's translation of one Brihadâranyaka chapter
    alongside Müller's. Its title ends "Hume Translation", which is not a
    chapter, so it falls out here rather than doubling that chapter up.
    """
    parts = [part.strip() for part in squash(title).split(':')]
    if len(parts) < 3:
        return None
    work = SHORTER.get(parts[-2], parts[-2])
    chapter = chapter_of(parts[-1], parts[-2])
    return (work, chapter) if chapter else None


# The body runs from the end of the sacred-texts header to the footnotes, or to
# the "Next:" link on a page that has no footnotes.
BODY = re.compile(r'(?is)</font></p>\s*<hr>(.*?)'
                  r'(?:<hr>\s*<h3[^>]*>\s*footnotes|<hr>\s*<center>|</body>)')
PARAGRAPH = re.compile(r'(?is)<p[^>]*>(.*?)</p>')
# A footnote call-out is an anchor into the notes at the foot of the page;
# left in, it puts a stray digit in the middle of a sentence.
FOOTNOTE = re.compile(r'(?is)<a[^>]+href="[^"]*#fn_[^"]*".*?</a>')
ANCHOR = re.compile(r'(?is)<a\s+name="[^"]*"\s*>\s*</a>')
# Page numbers ride along as their own small anchor: "p. 17".
PAGE = re.compile(r'(?is)<a\s+name="page_[^"]*".*?</a>')
VERSE = re.compile(r'^(\d+)\.\s+(.*)$', re.S)
# Pulling a footnote call-out out of a sentence leaves the space it sat in.
ORPHANED = re.compile(r'\s+([,.;:!?])')


def page(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        raw = f.read()
    found = TITLE.search(raw)
    if not found:
        return
    where = reference(html.unescape(TAG.sub('', found.group(1))))
    if not where:
        return
    work, chapter = where

    body = BODY.search(raw)
    if not body:
        return
    text = PAGE.sub('', FOOTNOTE.sub('', ANCHOR.sub('', body.group(1))))

    number = 0
    for block in PARAGRAPH.finditer(text):
        # <I> tags sit inside words to carry diacritics, so the tags come out
        # and the letters stay: "KHA<I>N</I><I>D</I>A" is "KHANDA".
        line = ORPHANED.sub(r'\1',
                            squash(html.unescape(TAG.sub('', block.group(1)))))
        if not line:
            continue
        verse = VERSE.match(line)
        if verse:
            number = int(verse.group(1))
            yield f'{work} {chapter}.{number}', verse.group(2)
        elif number:
            # An unnumbered paragraph continues the verse above it.
            yield f'{work} {chapter}.{number}', line


def passages():
    """Every verse in reading order, volume 1 then volume 15."""
    seen = {}
    order = []
    for volume in ('sbe01', 'sbe15'):
        for path in sorted(glob.glob(os.path.join(TMP, 'hindu', volume + '*.htm'))):
            for ref, body in page(path):
                if ref in seen:
                    seen[ref] += ' ' + body
                else:
                    seen[ref] = body
                    order.append(ref)
    for ref in order:
        yield ref, seen[ref]


def build():
    return [write_text('upanishads', 'The Upanishads', 'Upanishads',
                       'Translated by F. Max Müller',
                       SOURCE, LICENSE, passages(), tradition='hinduism')]


if __name__ == '__main__':
    build()
