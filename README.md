# Sortes

Six scriptures side by side, each fallen open at a random passage. Every column
lights the passage on its reading line and lets the rest of the page fade
around it. One button, or the <kbd>R</kbd> key, opens all six somewhere else.

    ./serve.sh          # http://localhost:8099

Any static file server works — nothing runs on the server, and the data is
plain JSON.

## Reading it

- **Open at random** (or <kbd>R</kbd>, or <kbd>Enter</kbd>) re-opens every book
  on screen at a new passage.
- Scrolling a column moves that column's light: whatever passage crosses its
  reading line becomes the lit one, and the red running head updates.
- The book names in the bar drop to one text, full width, with the running head
  hung in the margin beside the passage. **All six** returns to the spread.
- The URL carries the whole spread
  (`#old-testament:1864,quran:797,…`), so a set of passages can be linked to.
  A URL naming one book opens that book alone.

## How it lays out

Columns are sized so the whole spread always fits the screen; the spread itself
never scrolls, because a page scrollbar behind six independent scrollers is
unreachable.

| Viewport width | Layout |
| --- | --- |
| 1368px and up | six columns across, full height |
| 684–1367px | three columns, two rows, each half height |
| under 684px | one or two columns per screenful, swipe sideways |

## The texts

| Text | Translation | Passages | Source |
| --- | --- | --- | --- |
| Old Testament | King James Version | 23,145 | [Bible-kjv](https://github.com/aruljohn/Bible-kjv) |
| New Testament | King James Version | 7,957 | [Bible-kjv](https://github.com/aruljohn/Bible-kjv) |
| Quran | Marmaduke Pickthall, 1930 | 6,236 | [quran.com API](https://api-docs.quran.com/) |
| Book of Mormon | 1830 text | 6,598 | [Gutenberg #17](https://www.gutenberg.org/ebooks/17) |
| Bhagavad Gita | Edwin Arnold, *The Song Celestial*, 1885 | 245 | [Gutenberg #2388](https://www.gutenberg.org/ebooks/2388) |
| Pali Canon (Tipitaka) | Bhikkhu Sujato and Bhikkhu Brahmali | 56,270 | [bilara-data](https://github.com/suttacentral/bilara-data) |

All six are public domain, except the Pali Canon translations, which their
translators released under CC0. The Tipitaka is complete across all three
baskets: Vinaya, Sutta (all five nikayas) and Abhidhamma.

## Rebuilding the data

    scripts/fetch_sources.sh      # downloads into tmp/ (about 100 MB, cached)
    cd scripts && python3 build_all.py

`build_all.py` writes `data/<text>/NNNN.json` — 400 paragraphs per file as
`[reference, text]` pairs — plus `data/manifest.json`. The app fetches only the
chunks it renders, so opening the middle of the Pali Canon costs a couple of
hundred kilobytes rather than sixteen megabytes.

The Pali Canon build reads bilara's markup layer alongside the English so that
paragraph breaks, headings and verse lines come from the source rather than
from guesses about the segment numbering, and cites suttas the way
SuttaCentral does (`MN 77 5.1`). Verse keeps its line breaks; so does Arnold's
blank-verse Gita.

Add a text by writing a `scripts/build_*.py` that hands `common.write_text` an
id, titles, provenance, and an iterable of `(reference, text)` pairs, then
listing it in `build_all.py`.

See `NOTES.md` for the design reasoning.
