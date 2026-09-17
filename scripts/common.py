"""Shared helpers for the build_*.py scripts."""
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, 'tmp')
DATA = os.path.join(ROOT, 'data')

# Paragraphs per chunk file. The app only downloads the chunks it renders, so
# this trades request count against how much of a 15 MB text a jump pulls in.
CHUNK = 400


def squash(text):
    """Collapse hard-wrapped source lines into a single run of text."""
    return re.sub(r'\s+', ' ', text).strip()


def write_text(text_id, title, short, subtitle, source, license_note, paragraphs):
    """Write one text as data/<text_id>/ and return its manifest entry."""
    paragraphs = [[ref, body] for ref, body in paragraphs if body]
    directory = os.path.join(DATA, text_id)
    shutil.rmtree(directory, ignore_errors=True)
    os.makedirs(directory)

    for start in range(0, len(paragraphs), CHUNK):
        path = os.path.join(directory, '%04d.json' % (start // CHUNK))
        with open(path, 'w') as f:
            json.dump(paragraphs[start:start + CHUNK], f,
                      ensure_ascii=False, separators=(',', ':'))

    total = sum(os.path.getsize(os.path.join(directory, n))
                for n in os.listdir(directory))
    print(f'{text_id}: {len(paragraphs)} paragraphs, '
          f'{-(-len(paragraphs) // CHUNK)} chunks, {total / 1e6:.1f} MB')
    return {
        'id': text_id,
        'title': title,
        'short': short,
        'subtitle': subtitle,
        'source': source,
        'license': license_note,
        'count': len(paragraphs),
        'chunk': CHUNK,
    }
