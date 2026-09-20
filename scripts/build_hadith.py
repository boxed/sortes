"""Build the six canonical hadith collections from the hadith-json dumps.

The Kutub al-Sittah: the two Sahihs and the four Sunan. Each is its own text
rather than one merged "Hadith", because they are separate books with separate
compilers and separate numbering, and a passage has to be citable.

Unlike every other text here, these English translations are not demonstrably
public domain — see LICENSE below and the note in README.md.
"""
import json
import os

from common import TMP, squash, write_text

SOURCE = 'github.com/AhmedBaset/hadith-json (sunnah.com texts)'
LICENSE = ('Translation status uncertain — the standard English versions '
           '(Muhsin Khan, Abdul Hamid Siddiqui and others) are twentieth '
           'century and not demonstrably public domain')

# id, file, title, short name, and whose English this is.
BOOKS = [
    ('sahih-bukhari', 'bukhari', 'Sahih al-Bukhari', 'Bukhari',
     'Compiled by Muhammad al-Bukhari, translated by Muhsin Khan'),
    ('sahih-muslim', 'muslim', 'Sahih Muslim', 'Muslim',
     'Compiled by Muslim ibn al-Hajjaj, translated by Abdul Hamid Siddiqui'),
    ('sunan-abu-dawud', 'abudawud', 'Sunan Abi Dawud', 'Abu Dawud',
     'Compiled by Abu Dawud al-Sijistani, translated by Ahmad Hasan'),
    ('jami-tirmidhi', 'tirmidhi', "Jami' al-Tirmidhi", 'Tirmidhi',
     'Compiled by Muhammad al-Tirmidhi'),
    ('sunan-nasai', 'nasai', "Sunan al-Nasa'i", "Nasa'i",
     'Compiled by Ahmad al-Nasa’i'),
    ('sunan-ibn-majah', 'ibnmajah', 'Sunan Ibn Majah', 'Ibn Majah',
     'Compiled by Ibn Majah al-Qazwini'),
]


def collect(filename):
    with open(os.path.join(TMP, 'hadith', filename + '.json')) as f:
        book = json.load(f)
    chapters = {c['id']: c['english'] for c in book['chapters']}

    for hadith in book['hadiths']:
        english = hadith.get('english') or {}
        # The chain of narration is part of the hadith, not a heading: dropping
        # it would turn "Narrated Abu Huraira:" into an unattributed saying.
        body = squash(f"{english.get('narrator', '')} {english.get('text', '')}")
        chapter = chapters.get(hadith['chapterId'], '')
        yield f"{chapter} {hadith['idInBook']}".strip(), body


def build():
    return [write_text(text_id, title, short, subtitle, SOURCE, LICENSE,
                       collect(filename), tradition='islam')
            for text_id, filename, title, short, subtitle in BOOKS]


if __name__ == '__main__':
    build()
