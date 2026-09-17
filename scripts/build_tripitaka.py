"""Build the Pali Canon from SuttaCentral's bilara-data translations in tmp/.

bilara keeps the English in one layer and the markup in another, keyed by the
same segment ids. The markup layer is what says where a paragraph starts, which
lines are verse, and which segments are only headings — so the two are read
together rather than guessed at from the segment numbering.
"""
import json
import os
import re

from common import TMP, squash, write_text

SOURCE = 'github.com/suttacentral/bilara-data (published branch)'
LICENSE = ('Creative Commons Zero — translations by Bhikkhu Sujato '
           '(Sutta, Abhidhamma) and Bhikkhu Brahmali (Vinaya)')

ROOT = os.path.join(TMP, 'bilara-data-published')
TRANSLATIONS = os.path.join(ROOT, 'translation', 'en')
MARKUP = os.path.join(ROOT, 'html', 'pli', 'ms')

# Canonical order of the three baskets, as (directory, label) pairs.
BASKETS = [
    ('brahmali/vinaya', 'Vinaya Pitaka'),
    ('sujato/sutta/dn', 'Digha Nikaya'),
    ('sujato/sutta/mn', 'Majjhima Nikaya'),
    ('sujato/sutta/sn', 'Samyutta Nikaya'),
    ('sujato/sutta/an', 'Anguttara Nikaya'),
    ('sujato/sutta/kn', 'Khuddaka Nikaya'),
    ('sujato/abhidhamma', 'Abhidhamma Pitaka'),
]

NUMBERS = re.compile(r'(\d+)')
UID = re.compile(r'^([a-z]+)([\d.-]+)$')

# How SuttaCentral cites each collection. Anything not listed — the Vinaya and
# Abhidhamma, whose uids are opaque — keeps its uid and is named by its basket.
ACRONYMS = {
    'dn': 'DN', 'mn': 'MN', 'sn': 'SN', 'an': 'AN', 'dhp': 'Dhp', 'ud': 'Ud',
    'iti': 'Iti', 'snp': 'Snp', 'thag': 'Thag', 'thig': 'Thig', 'ja': 'Ja',
    'kp': 'Kp', 'cp': 'Cp', 'vv': 'Vv', 'pv': 'Pv', 'bv': 'Bv', 'ne': 'Ne',
    'pe': 'Pe', 'mil': 'Mil', 'pli-tv': None,
}
HEADING = re.compile(r'<h[1-6][\s>]')
BREAK = re.compile(r'<(p|blockquote|div|li|tr)[\s>]')
TAG = re.compile(r'<[^>]+>')


def cite(uid):
    """'sn35.63' -> ('SN 35.63', True); 'pli-tv-kd6' -> ('pli-tv-kd6', False)."""
    match = UID.match(uid)
    if match and ACRONYMS.get(match.group(1)):
        return f'{ACRONYMS[match.group(1)]} {match.group(2)}', True
    return uid, False


def natural_key(path):
    """Sort dn2 before dn10, and sn1.1 before sn1.10."""
    return [int(part) if part.isdigit() else part
            for part in NUMBERS.split(os.path.basename(path))]


def files_in(directory):
    found = []
    for base, _, names in os.walk(os.path.join(TRANSLATIONS, directory)):
        found += [os.path.join(base, n) for n in names if n.endswith('.json')]
    return sorted(found, key=natural_key)


def markup_for(filename):
    """The html layer beside a translation file, or {} when there is none."""
    relative = os.path.relpath(filename, TRANSLATIONS)
    # sujato/sutta/dn/dn1_translation-en-sujato.json -> sutta/dn/dn1_html.json
    parts = relative.split(os.sep)[1:]
    parts[-1] = parts[-1].split('_translation')[0] + '_html.json'
    path = os.path.join(MARKUP, *parts)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def read_text(filename):
    """Yield (title, paragraph key, text) for one translation, in order."""
    with open(filename) as f:
        segments = json.load(f)
    markup = markup_for(filename)

    title = None
    key = None
    lines = []

    def done():
        # Verse lines keep their breaks; prose sentences run together.
        body = '\n'.join(squash(line) for line in lines if squash(line))
        return (title, key, body) if body else None

    for segment_id, text in segments.items():
        text = text.strip()
        path = segment_id.split(':', 1)[1]
        html = markup.get(segment_id, '')

        if path.startswith('0.'):
            # Front matter: collection, then chapter, then the text's own title.
            if text:
                title = text
            continue
        if HEADING.search(html):
            continue
        if not text:
            continue

        if BREAK.search(html) or key is None:
            finished = done()
            if finished:
                yield finished
            key, lines = path, []
        if 'verse-line' in html or not lines:
            lines.append(text)
        else:
            lines[-1] += ' ' + text

    finished = done()
    if finished:
        yield finished


def collect():
    for directory, basket in BASKETS:
        for filename in files_in(directory):
            uid = os.path.basename(filename).split('_translation')[0]
            citation, known = cite(uid)
            for title, key, text in read_text(filename):
                # The acronym already says which nikaya; only the Vinaya and
                # Abhidhamma need their basket spelled out.
                name = title or basket
                if title and not known:
                    name = f'{title}, {basket}'
                yield f'{name} ({citation} {key})', TAG.sub('', text)


def build():
    return [write_text('tripitaka', 'The Pali Canon (Tipitaka)', 'Pali Canon',
                       'Translated by Bhikkhu Sujato and Bhikkhu Brahmali',
                       SOURCE, LICENSE, collect())]


if __name__ == '__main__':
    build()
