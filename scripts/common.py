"""Shared helpers for the build_*.py scripts."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, 'tmp')
DATA = os.path.join(ROOT, 'data')

# Paragraphs per chunk file. The app only downloads the chunks it renders, so
# this trades request count against how much of a 15 MB text a jump pulls in.
CHUNK = 400

# A column of the spread is a tradition, not a book: Islam has seven books
# here and Judaism one, and six columns of tradition compare better than
# thirteen columns of book. The order is the order they appear across the
# spread. The Old Testament sits under Judaism and the New under Christianity
# — a rough cut, since the Old Testament is scripture to both, but the
# alternative is printing it twice.
TRADITIONS = [
    ('judaism', 'Judaism'),
    ('christianity', 'Christianity'),
    ('islam', 'Islam'),
    ('mormonism', 'Mormonism'),
    ('hinduism', 'Hinduism'),
    ('buddhism', 'Buddhism'),
]


def squash(text):
    """Collapse hard-wrapped source lines into a single run of text."""
    return re.sub(r'\s+', ' ', text).strip()


def chunk_files(directory):
    """The chunk files of a text directory, which is everything but labels/."""
    return [name for name in os.listdir(directory) if name.endswith('.json')]


def write_text(text_id, title, short, subtitle, source, license_note, paragraphs,
               tradition):
    """Write one text as data/<text_id>/ and return its manifest entry."""
    paragraphs = [[ref, body] for ref, body in paragraphs if body]
    directory = os.path.join(DATA, text_id)
    # Clear out the old chunks — a text that got shorter must not leave a
    # stray tail behind — but leave labels/ where it is. Labelling the corpus
    # is hours of work and it lives inside this directory; a rebuild that
    # quietly threw it away would be a very expensive surprise. Labels are
    # checked against their chunk's length by labels.py, so a chunk that has
    # genuinely changed is caught there rather than by deleting everything.
    os.makedirs(directory, exist_ok=True)
    for name in chunk_files(directory):
        os.remove(os.path.join(directory, name))

    for start in range(0, len(paragraphs), CHUNK):
        path = os.path.join(directory, '%04d.json' % (start // CHUNK))
        with open(path, 'w') as f:
            json.dump(paragraphs[start:start + CHUNK], f,
                      ensure_ascii=False, separators=(',', ':'))

    total = sum(os.path.getsize(os.path.join(directory, n))
                for n in chunk_files(directory))
    print(f'{text_id}: {len(paragraphs)} paragraphs, '
          f'{-(-len(paragraphs) // CHUNK)} chunks, {total / 1e6:.1f} MB')
    return {
        'id': text_id,
        'tradition': tradition,
        'title': title,
        'short': short,
        'subtitle': subtitle,
        'source': source,
        'license': license_note,
        'count': len(paragraphs),
        'chunk': CHUNK,
    }
