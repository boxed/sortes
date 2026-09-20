"""Build the Pali Canon from SuttaCentral's bilara-data translations in tmp/.

bilara keeps the English in one layer and the markup in another, keyed by the
same segment ids. The markup layer is what says where a paragraph starts, which
lines are verse, and which segments are only headings — so the two are read
together rather than guessed at from the segment numbering.

The canon comes out as six texts rather than one. Fifty-six thousand passages
under a single name is not a book anyone reads or cites, and on the statistics
screen it was one column dwarfing every other. These are the divisions the
tradition itself uses: the Vinaya, and the five nikayas of the Sutta Pitaka,
each cited by its own acronym.

The third basket, the Abhidhamma, is not here. bilara-data has no English
translation of it — the directory the earlier build read was empty, and the
count came out the same with and without it. Two baskets of three.

The Khuddaka is partial too: nine of its books are translated (Dhammapada,
Udana, Itivuttaka, Sutta Nipata, Theragatha, Therigatha, Jataka,
Khuddakapatha, Cariyapitaka), and the rest are not. So this is a large part of
the Pali Canon and not the whole of it, which is why no text here is called
"the Pali Canon".
"""
import json
import os
import re

from common import TMP, squash, write_text

SOURCE = 'github.com/suttacentral/bilara-data (published branch)'
LICENSE = ('Creative Commons Zero — translations by Bhikkhu Sujato (Sutta) '
           'and Bhikkhu Brahmali (Vinaya)')

ROOT = os.path.join(TMP, 'bilara-data-published')
TRANSLATIONS = os.path.join(ROOT, 'translation', 'en')
MARKUP = os.path.join(ROOT, 'html', 'pli', 'ms')

# In canonical order: the Vinaya, then the five nikayas of the Sutta Pitaka.
# Short names are kept to one word because they head a narrow column on the
# statistics screen, where "Buddhism" already stands above them.
BASKETS = [
    ('brahmali/vinaya', 'vinaya-pitaka', 'The Vinaya Pitaka', 'Vinaya',
     'The monastic code, translated by Bhikkhu Brahmali'),
    ('sujato/sutta/dn', 'digha-nikaya', 'The Digha Nikaya', 'D\u012bgha',
     'The long discourses, translated by Bhikkhu Sujato'),
    ('sujato/sutta/mn', 'majjhima-nikaya', 'The Majjhima Nikaya', 'Majjhima',
     'The middle-length discourses, translated by Bhikkhu Sujato'),
    ('sujato/sutta/sn', 'samyutta-nikaya', 'The Samyutta Nikaya', 'Sa\u1e41yutta',
     'The linked discourses, translated by Bhikkhu Sujato'),
    ('sujato/sutta/an', 'anguttara-nikaya', 'The Anguttara Nikaya',
     'A\u1e45guttara',
     'The numbered discourses, translated by Bhikkhu Sujato'),
    ('sujato/sutta/kn', 'khuddaka-nikaya', 'The Khuddaka Nikaya', 'Khuddaka',
     'Nine of its books, translated by Bhikkhu Sujato'),
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


def collect(directory, basket):
    for filename in files_in(directory):
        uid = os.path.basename(filename).split('_translation')[0]
        citation, known = cite(uid)
        for title, key, text in read_text(filename):
            # The acronym already says which nikaya; only the Vinaya, whose
            # uids are opaque, needs its basket spelled out.
            name = title or basket
            if title and not known:
                name = f'{title}, {basket}'
            yield f'{name} ({citation} {key})', TAG.sub('', text)


def build():
    return [write_text(text_id, title, short, subtitle, SOURCE, LICENSE,
                       collect(directory, title.removeprefix('The ')),
                       tradition='buddhism')
            for directory, text_id, title, short, subtitle in BASKETS]


if __name__ == '__main__':
    build()
