#!/bin/bash
# Downloads the raw source files every build_*.py script reads from.
set -e
cd "$(dirname "$0")/.."
mkdir -p tmp/bible tmp/quran

echo "KJV Bible..."
BOOKS="Genesis Exodus Leviticus Numbers Deuteronomy Joshua Judges Ruth 1Samuel 2Samuel 1Kings 2Kings 1Chronicles 2Chronicles Ezra Nehemiah Esther Job Psalms Proverbs Ecclesiastes SongofSolomon Isaiah Jeremiah Lamentations Ezekiel Daniel Hosea Joel Amos Obadiah Jonah Micah Nahum Habakkuk Zephaniah Haggai Zechariah Malachi Matthew Mark Luke John Acts Romans 1Corinthians 2Corinthians Galatians Ephesians Philippians Colossians 1Thessalonians 2Thessalonians 1Timothy 2Timothy Titus Philemon Hebrews James 1Peter 2Peter 1John 2John 3John Jude Revelation"
for b in $BOOKS; do
    [ -s "tmp/bible/$b.json" ] && continue
    curl -sfL -m 60 -o "tmp/bible/$b.json" \
        "https://raw.githubusercontent.com/aruljohn/Bible-kjv/master/$b.json" &
    while [ "$(jobs -rp | wc -l)" -ge 8 ]; do wait -n; done
done
wait

echo "Quran (Pickthall)..."
for n in $(seq 1 114); do
    [ -s "tmp/quran/$n.json" ] && continue
    curl -sfL -m 60 -o "tmp/quran/$n.json" \
        "https://api.quran.com/api/v4/verses/by_chapter/$n?translations=19&per_page=300&fields=verse_key" &
    while [ "$(jobs -rp | wc -l)" -ge 6 ]; do wait -n; done
done
wait
curl -sfL -m 60 -o tmp/quran-chapters.json "https://api.quran.com/api/v4/chapters?language=en"

echo "Book of Mormon (Gutenberg #17)..."
[ -s tmp/book-of-mormon.txt ] || curl -sfL -m 120 -o tmp/book-of-mormon.txt "https://www.gutenberg.org/cache/epub/17/pg17.txt"

echo "Bhagavad Gita (Gutenberg #2388, Edwin Arnold)..."
[ -s tmp/bhagavad-gita.txt ] || curl -sfL -m 120 -o tmp/bhagavad-gita.txt "https://www.gutenberg.org/cache/epub/2388/pg2388.txt"

echo "Done."
