"""Build the Old and New Testament from the KJV verse JSON in tmp/bible."""
import json
import os

from common import TMP, squash, write_text

OLD = [
    ('Genesis', 'Genesis'), ('Exodus', 'Exodus'), ('Leviticus', 'Leviticus'),
    ('Numbers', 'Numbers'), ('Deuteronomy', 'Deuteronomy'), ('Joshua', 'Joshua'),
    ('Judges', 'Judges'), ('Ruth', 'Ruth'), ('1Samuel', '1 Samuel'),
    ('2Samuel', '2 Samuel'), ('1Kings', '1 Kings'), ('2Kings', '2 Kings'),
    ('1Chronicles', '1 Chronicles'), ('2Chronicles', '2 Chronicles'), ('Ezra', 'Ezra'),
    ('Nehemiah', 'Nehemiah'), ('Esther', 'Esther'), ('Job', 'Job'),
    ('Psalms', 'Psalms'), ('Proverbs', 'Proverbs'), ('Ecclesiastes', 'Ecclesiastes'),
    ('SongofSolomon', 'Song of Solomon'), ('Isaiah', 'Isaiah'), ('Jeremiah', 'Jeremiah'),
    ('Lamentations', 'Lamentations'), ('Ezekiel', 'Ezekiel'), ('Daniel', 'Daniel'),
    ('Hosea', 'Hosea'), ('Joel', 'Joel'), ('Amos', 'Amos'), ('Obadiah', 'Obadiah'),
    ('Jonah', 'Jonah'), ('Micah', 'Micah'), ('Nahum', 'Nahum'), ('Habakkuk', 'Habakkuk'),
    ('Zephaniah', 'Zephaniah'), ('Haggai', 'Haggai'), ('Zechariah', 'Zechariah'),
    ('Malachi', 'Malachi'),
]

NEW = [
    ('Matthew', 'Matthew'), ('Mark', 'Mark'), ('Luke', 'Luke'), ('John', 'John'),
    ('Acts', 'Acts'), ('Romans', 'Romans'), ('1Corinthians', '1 Corinthians'),
    ('2Corinthians', '2 Corinthians'), ('Galatians', 'Galatians'),
    ('Ephesians', 'Ephesians'), ('Philippians', 'Philippians'),
    ('Colossians', 'Colossians'), ('1Thessalonians', '1 Thessalonians'),
    ('2Thessalonians', '2 Thessalonians'), ('1Timothy', '1 Timothy'),
    ('2Timothy', '2 Timothy'), ('Titus', 'Titus'), ('Philemon', 'Philemon'),
    ('Hebrews', 'Hebrews'), ('James', 'James'), ('1Peter', '1 Peter'),
    ('2Peter', '2 Peter'), ('1John', '1 John'), ('2John', '2 John'),
    ('3John', '3 John'), ('Jude', 'Jude'), ('Revelation', 'Revelation'),
]

SOURCE = 'github.com/aruljohn/Bible-kjv'
LICENSE = 'Public domain (King James Version, 1611/1769)'


def collect(books):
    for filename, name in books:
        with open(os.path.join(TMP, 'bible', filename + '.json')) as f:
            book = json.load(f)
        for chapter in book['chapters']:
            for verse in chapter['verses']:
                ref = f"{name} {chapter['chapter']}:{verse['verse']}"
                yield ref, squash(verse['text'])


def build():
    return [
        write_text('old-testament', 'The Old Testament', 'Old Testament',
                   'King James Version',
                   SOURCE, LICENSE, collect(OLD)),
        write_text('new-testament', 'The New Testament', 'New Testament',
                   'King James Version',
                   SOURCE, LICENSE, collect(NEW)),
    ]


if __name__ == '__main__':
    build()
