#!/bin/bash
# Downloads the raw source files every build_*.py script reads from.
set -e
cd "$(dirname "$0")/.."
mkdir -p tmp/bible tmp/quran tmp/hadith tmp/hindu

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

echo "Hadith (the six books)..."
for b in bukhari muslim abudawud tirmidhi nasai ibnmajah; do
    [ -s "tmp/hadith/$b.json" ] && continue
    curl -sfL -m 300 -o "tmp/hadith/$b.json" \
        "https://raw.githubusercontent.com/AhmedBaset/hadith-json/main/db/by_book/the_9_books/$b.json" &
done
wait

echo "Rig Veda (Griffith)..."
[ -s tmp/hindu/rig-veda.json ] || curl -sfL -m 300 -o tmp/hindu/rig-veda.json \
    "https://raw.githubusercontent.com/aasi-archive/rigveda/main/rig-veda.json"

# sacred-texts.com sits behind a challenge that refuses scripted requests, so
# the SBE volumes come from the Wayback Machine's copy of the same pages.
# id_ asks for the bytes as archived rather than a rewritten page.
WB=https://web.archive.org/web/2020id_/https://sacred-texts.com/hin
# The archive throttles bursts, and a throttled request answers 429 rather
# than waiting, so this goes two at a time and retries through the refusals
# rather than dropping the page. --retry-all-errors is what makes curl treat a
# 429 as worth retrying at all.
fetch_st() {  # <local name> <path under hin/>
    [ -s "tmp/hindu/$1" ] && return
    curl -sfL -m 120 --retry 6 --retry-delay 5 --retry-all-errors \
        -o "tmp/hindu/$1" "$WB/$2" || { rm -f "tmp/hindu/$1"; echo "  missed $1"; }
}

echo "The Upanishads (Muller, SBE 1 and 15)..."
for n in $(seq -w 0 243); do
    fetch_st "sbe01$n.htm" "sbe01/sbe01$n.htm" &
    while [ "$(jobs -rp | wc -l)" -ge 2 ]; do wait -n; done
done
wait
for n in $(seq -w 0 118); do
    fetch_st "sbe15$n.htm" "sbe15/sbe15$n.htm" &
    while [ "$(jobs -rp | wc -l)" -ge 2 ]; do wait -n; done
done
wait

echo "The Laws of Manu (Buhler, SBE 25)..."
for n in $(seq -w 1 12); do
    fetch_st "manu$n.htm" "manu/manu$n.htm" &
    while [ "$(jobs -rp | wc -l)" -ge 2 ]; do wait -n; done
done
wait

echo "Done."
