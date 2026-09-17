"""Build the Quran from the per-surah quran.com responses in tmp/quran."""
import json
import os
import re

from common import TMP, squash, write_text

SOURCE = 'quran.com API (translation id 19)'
LICENSE = 'Public domain (Pickthall translation, 1930)'

FOOTNOTE = re.compile(r'<sup[^>]*>.*?</sup>', re.S)
TAG = re.compile(r'<[^>]+>')


def clean(text):
    return squash(TAG.sub('', FOOTNOTE.sub('', text)))


def collect():
    with open(os.path.join(TMP, 'quran-chapters.json')) as f:
        names = {c['id']: c['name_simple'] for c in json.load(f)['chapters']}
    for number in range(1, 115):
        with open(os.path.join(TMP, 'quran', f'{number}.json')) as f:
            verses = json.load(f)['verses']
        for verse in verses:
            ref = f"{names[number]} {number}:{verse['verse_number']}"
            yield ref, clean(verse['translations'][0]['text'])


def build():
    return [write_text('quran', 'The Quran', 'Quran',
                       'Translated by Marmaduke Pickthall',
                       SOURCE, LICENSE, collect())]


if __name__ == '__main__':
    build()
