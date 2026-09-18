# Sortes

Six scriptures side by side, each fallen open at a random passage. Every column
lights the passage on its reading line and lets the rest of the page fade
around it. One button, or the <kbd>R</kbd> key, opens all six somewhere else.

Every one of the 100,451 passages is also labelled by what it *does* — whether
it commands, promises, threatens, narrates, explains, praises, or describes
harm — so the margins carry colored rules, and a statistics screen shows what
each book spends its words on.

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
- **Statistics** opens a full screen: a map of each book with one pixel per
  passage, and the share of each book carrying each kind. Hovering a kind
  leaves only that kind lit; hovering a pixel reads the passage it stands for.

## How it lays out

Columns are sized so the whole spread always fits the screen; the spread itself
never scrolls, because a page scrollbar behind six independent scrollers is
unreachable.

| Viewport width | Layout |
| --- | --- |
| 1368px and up | six columns across, full height |
| 684–1367px | three columns, two rows, each half height |
| under 684px | one or two columns per screenful, swipe sideways |

## The marks in the margin

Each passage is labelled by its form — what the passage is doing, not what it
is about. Seven codes, from ordinary literary form-criticism:

| Code | Kind | The passage… |
| --- | --- | --- |
| `L` | Law | instructs, commands, prohibits |
| `P` | Promise | holds out a good outcome |
| `T` | Threat | holds a bad outcome over the hearer |
| `V` | Violence | describes harm done, to anyone |
| `N` | Narrative | recounts an event |
| `D` | Doctrine | explains how things are |
| `W` | Worship | addresses or adores the divine |

A passage often carries more than one: a command with a punishment attached is
`LT`, a warned-of atrocity `TV`. Five of the seven are marked in the margin
with a colored rule in a **fixed slot**, so an indented lone rule is a threat
and not a law whether or not the hues can be told apart — six pigments cannot
be made safe for every kind of colour blindness, so position does the work that
colour alone cannot. Narrative and worship are named in the column head
instead; narrative is the commonest kind in four of the six books, and marking
it would put a rule on most of the page.

Threat and violence are deliberately separate. A threat warns somebody what is
coming for them; violence is harm described, whoever it falls on. Being the
victim is not being threatened. Collapsing the two makes a book that narrates a
war look like a book that issues warnings.

`scripts/taxonomy.md` is the guide the classifiers actually read, with worked
examples. The full reasoning, and where the labels are known to be weak, is in
`KNOWN-ISSUES.md`.

## What each book spends its words on

Share of each book's passages carrying each kind. A passage can do more than
one thing, so rows do not add to a hundred; the last column is the share
carrying none of the seven — setting formulas, name-lists, bare replies.

| Text | Law | Promise | Threat | Violence | Narrative | Doctrine | Worship | none |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bhagavad Gita | 12% | 17% | 1% | 2% | 5% | 58% | 15% | 13% |
| Quran | 19% | 7% | 10% | 3% | 37% | 39% | 5% | 3% |
| Book of Mormon | 11% | 9% | 7% | 13% | 59% | 19% | 4% | 2% |
| New Testament | 15% | 6% | 4% | 4% | 55% | 29% | 4% | 1% |
| Old Testament | 18% | 7% | 7% | 9% | 51% | 16% | 7% | 2% |
| Pali Canon | 17% | 1% | 2% | 1% | 34% | 42% | 1% | 10% |

**These are a small model's readings, not scholarship.** They were produced by
Claude Haiku working 100 passages at a time, and they are wrong often enough to
be worth checking against the passage beside them. `python3 scripts/labels.py
audit` ranks chunks by how many blanks look like sentences a classifier simply
skipped; several are still flagged.

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

## Rebuilding the labels

Labels live at `data/<text>/labels/NNNN.json`, one code string per passage,
alongside the chunk they describe. A chunk file existing *and validating* is
what "done" means — there is no state to get out of step with the filesystem.

    python3 labels.py status           what is done, what is left
    python3 labels.py next 6           the next chunks to hand to classifiers
    python3 labels.py prepare <t> <n>  split a chunk into 100-line parts
    python3 labels.py assemble <t> <n> join the parts back, validating
    python3 labels.py audit            finished chunks ranked by suspect blanks

Each chunk is 400 passages, split into four parts of 100. The split matters:
shown 400 at once a classifier finds a rhythm and labels to it — on one trial
it put exactly two codes on 338 of 400 — where at 100 it reads each line. One
classifier still does all four parts, so the setup cost is paid once.

`scripts/reclass.py` re-judges a single distinction across the whole corpus
without relabelling it; it was written for the threat/violence split and holds
the candidate query for that.

`python3 scripts/stats.py` rolls the labels into `data/stats.json` and the
per-passage bitmaps in `data/map/`, which is what the statistics screen fetches
— reading all 253 label files in the browser would cost more than the passages
themselves.

See `NOTES.md` for the design reasoning.
