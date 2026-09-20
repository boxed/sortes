# Sortes

Six traditions side by side, each fallen open at a random passage. A column is
a tradition, not a book — Islam has seven books on the shelf here and Judaism
one — and every jump takes one of them down and opens it somewhere. Each column
lights the passage on its reading line and lets the rest of the page fade
around it. One button, or the <kbd>R</kbd> key, opens all six somewhere else.

Every passage is also labelled by what it *does* — whether it commands,
promises, threatens, narrates, explains, praises, or describes harm — so the
margins carry colored rules, and a statistics screen shows what each book
spends its words on.

    ./serve.sh          # http://localhost:8099

Any static file server works — nothing runs on the server, and the data is
plain JSON.

## Reading it

- **Open at random** (or <kbd>R</kbd>, or <kbd>Enter</kbd>) re-opens every
  column on screen: a fresh book off its tradition's shelf, at a fresh passage.
  Books within a tradition come up equally often, not in proportion to their
  length — weighted by length the Gita's 245 stanzas would never surface
  against the Rig Veda, and the Quran would be buried under 34,000 hadith.
- Scrolling a column moves that column's light: whatever passage crosses its
  reading line becomes the lit one, and the red running head updates.
- The tradition names in the bar drop to one column, full width, with the
  running head hung in the margin beside the passage. A tradition holding more
  than one book then offers them by name on a second row, so a single book can
  be read on its own. **All six** returns to the spread.
- The URL carries the whole spread
  (`#old-testament:1864,quran:797,…`), so a set of passages can be linked to.
  A URL naming one book opens that book alone, and a bare `statistics` or
  `sources` among the passages opens that screen with them.
- **Statistics** opens a full screen: one column per tradition, every passage
  of its scriptures as a single pixel, and the share of that tradition carrying
  each kind. A tradition holding several books stacks them down its column with
  a band of ground between — the Quran above the six hadith collections, the
  Vinaya above the five nikayas — so the seams are visible without twenty
  columns abreast, which is a spreadsheet rather than a comparison. Every bar
  is on one scale, so a row compares the six straight across. Hovering a kind
  leaves only that kind lit; hovering a pixel reads the passage it stands for —
  whichever book of the tradition it came from — and lists what it was
  labelled, read off the same byte the pixel was drawn from.

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
is about. Seven codes, from ordinary literary form-criticism, and an eighth
for how the passage reached you:

| Code | Kind | The passage… |
| --- | --- | --- |
| `L` | Law | instructs, commands, prohibits |
| `P` | Promise | holds out a good outcome |
| `T` | Threat | holds a bad outcome over the hearer |
| `V` | Violence | describes harm done, to anyone |
| `N` | Narrative | recounts an event |
| `D` | Doctrine | explains how things are |
| `W` | Worship | addresses or adores the divine |
| `A` | Provenance | says how it was transmitted, not what it does |

A passage often carries more than one: a command with a punishment attached is
`LT`, a warned-of atrocity `TV`, a hadith prohibiting something `LA`. Five of
the eight are marked in the margin with a colored rule in a **fixed slot**, so
an indented lone rule is a threat and not a law whether or not the hues can be
told apart — six pigments cannot be made safe for every kind of colour
blindness, so position does the work that colour alone cannot. Narrative,
worship and provenance are named in the column head instead; narrative is the
commonest kind in most of these books, and provenance sits on nearly every
hadith, so marking either would put a rule on most of the page.

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
carrying none of the eight — setting formulas, name-lists, bare replies. The
statistics screen folds these into one column per tradition; this is the
per-book breakdown behind it.

| Tradition | Text | Law | Promise | Threat | Narrative | Doctrine | Worship | Violence | Provenance | none |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Judaism | Old Testament | 22% | 11% | 9% | 47% | 17% | 11% | 14% | 0% | 10% |
| Christianity | New Testament | 20% | 14% | 4% | 51% | 31% | 4% | 6% | 0% | 6% |
| Islam | Quran | 25% | 14% | 16% | 26% | 41% | 7% | 9% | 0% | 12% |
| Islam | Bukhari | 39% | 15% | 4% | 76% | 23% | 4% | 16% | 100% | 0% |
| Islam | Muslim | 35% | 13% | 3% | 61% | 22% | 3% | 11% | 98% | 1% |
| Islam | Abu Dawud | 49% | 10% | 3% | 67% | 23% | 5% | 13% | 98% | 0% |
| Islam | Tirmidhi | 42% | 20% | 4% | 56% | 36% | 7% | 10% | 99% | 0% |
| Islam | Nasa'i | 53% | 10% | 3% | 68% | 25% | 5% | 13% | 99% | 0% |
| Islam | Ibn Majah | 48% | 17% | 4% | 57% | 31% | 6% | 11% | 99% | 0% |
| Mormonism | Book of Mormon | 15% | 16% | 9% | 59% | 23% | 4% | 18% | 1% | 6% |
| Hinduism | Bhagavad Gita | 29% | 30% | 2% | 16% | 58% | 27% | 8% | 1% | 7% |
| Hinduism | Rig Veda | 40% | 23% | 1% | 21% | 8% | 86% | 13% | 0% | 3% |
| Hinduism | Upanishads | 24% | 28% | 2% | 26% | 76% | 12% | 2% | 2% | 1% |
| Hinduism | Laws of Manu | 63% | 15% | 8% | 3% | 57% | 1% | 9% | 0% | 1% |
| Buddhism | Vinaya | 39% | 3% | 2% | 41% | 37% | 0% | 3% | 0% | 9% |
| Buddhism | Dīgha | 13% | 9% | 1% | 42% | 47% | 4% | 2% | 0% | 10% |
| Buddhism | Majjhima | 16% | 7% | 2% | 43% | 46% | 2% | 3% | 1% | 9% |
| Buddhism | Saṁyutta | 14% | 10% | 1% | 30% | 49% | 2% | 2% | 0% | 16% |
| Buddhism | Aṅguttara | 16% | 14% | 2% | 20% | 67% | 1% | 3% | 0% | 7% |
| Buddhism | Khuddaka | 18% | 13% | 3% | 29% | 44% | 6% | 4% | 5% | 10% |

**Provenance is the eighth and the statistics screen leaves it out.** It does
not say what a passage does, only how it reached you: the chain of narrators on
a hadith, the *Thus have I heard* that opens a sutta. Nearly every hadith
carries one, so the other seven are judged on what is being transmitted rather
than on the frame around it. **Exclude provenance** is ticked by default on the
statistics screen, and it excludes rather than hides — a passage that is
nothing but a chain of narrators leaves the corpus altogether, taking its pixel
off the map and its weight out of every denominator. Untick it to see
provenance as a kind of its own. The table above counts everything, so the
screen's figures run a little higher than these: Islam's law is 41% here and
43% there, because 2,001 chain-only passages are no longer in the divisor.

That distinction is worth most of the hadith's figures. Counting the frame,
Bukhari came out 96% narrative and Tirmidhi 92% — which described their grammar,
since a hadith always reports that somebody said something at some time.
Judging what is inside the frame puts them at 76% and 56%, and moves the
difference into law and doctrine, which is what the collections are for.

**These are a model's readings, not scholarship.** Every passage was judged by
Jev against the same eight questions — see *Rebuilding the labels* — and they
are wrong often enough to be worth checking against the passage beside them.
`python3 scripts/labels.py audit` ranks chunks by blanks that look like
sentences a classifier skipped.

## The texts

Fifteen books in six traditions. The tradition is the column; the books are
what that column can fall open at.

| Tradition | Text | Translation | Passages | Source |
| --- | --- | --- | --- | --- |
| Judaism | Old Testament | King James Version | 23,145 | [Bible-kjv](https://github.com/aruljohn/Bible-kjv) |
| Christianity | New Testament | King James Version | 7,957 | [Bible-kjv](https://github.com/aruljohn/Bible-kjv) |
| Islam | Quran | Marmaduke Pickthall, 1930 | 6,236 | [quran.com API](https://api-docs.quran.com/) |
| Islam | Sahih al-Bukhari | Muhsin Khan | 7,277 | [hadith-json](https://github.com/AhmedBaset/hadith-json) |
| Islam | Sahih Muslim | Abdul Hamid Siddiqui | 7,458 | [hadith-json](https://github.com/AhmedBaset/hadith-json) |
| Islam | Sunan Abi Dawud | Ahmad Hasan | 5,276 | [hadith-json](https://github.com/AhmedBaset/hadith-json) |
| Islam | Jami' al-Tirmidhi | — | 4,053 | [hadith-json](https://github.com/AhmedBaset/hadith-json) |
| Islam | Sunan al-Nasa'i | — | 5,768 | [hadith-json](https://github.com/AhmedBaset/hadith-json) |
| Islam | Sunan Ibn Majah | — | 4,345 | [hadith-json](https://github.com/AhmedBaset/hadith-json) |
| Mormonism | Book of Mormon | 1830 text | 6,598 | [Gutenberg #17](https://www.gutenberg.org/ebooks/17) |
| Hinduism | Bhagavad Gita | Edwin Arnold, *The Song Celestial*, 1885 | 245 | [Gutenberg #2388](https://www.gutenberg.org/ebooks/2388) |
| Hinduism | Rig Veda | Ralph T. H. Griffith, 1896 | 10,550 | [aasi-archive/rigveda](https://github.com/aasi-archive/rigveda) |
| Hinduism | Upanishads | F. Max Müller, SBE 1 and 15 | 2,212 | sacred-texts.com, via the Wayback Machine |
| Hinduism | Laws of Manu | Georg Bühler, SBE 25 | 2,683 | sacred-texts.com, via the Wayback Machine |
| Buddhism | Vinaya Pitaka | Bhikkhu Brahmali | 17,482 | [bilara-data](https://github.com/suttacentral/bilara-data) |
| Buddhism | Digha Nikaya | Bhikkhu Sujato | 4,556 | [bilara-data](https://github.com/suttacentral/bilara-data) |
| Buddhism | Majjhima Nikaya | Bhikkhu Sujato | 6,660 | [bilara-data](https://github.com/suttacentral/bilara-data) |
| Buddhism | Samyutta Nikaya | Bhikkhu Sujato | 11,942 | [bilara-data](https://github.com/suttacentral/bilara-data) |
| Buddhism | Anguttara Nikaya | Bhikkhu Sujato | 10,132 | [bilara-data](https://github.com/suttacentral/bilara-data) |
| Buddhism | Khuddaka Nikaya | Bhikkhu Sujato | 5,498 | [bilara-data](https://github.com/suttacentral/bilara-data) |

150,073 passages. The Islamic collection is the Kutub al-Sittah, the six books
Sunni tradition treats as canonical; the Hindu one is shruti (the Rig Veda and
the twelve principal Upanishads) plus the two texts that carry the tradition's
law and its philosophy in the form people actually read them.

Every translation is public domain or CC0 **except the hadith**. The standard
English versions of the six books are twentieth century and not demonstrably
public domain, and no public domain English translation of them exists to use
instead. They are here because the alternative was an Islam column with one
book in it; the sources panel, the manifest and `KNOWN-ISSUES.md` all say so
rather than claiming a clean sheet. To drop them, remove `build_hadith` from
`BUILDERS` in `scripts/build_all.py` and rebuild.

The Pali translations are CC0 by their translators' choice. They come out as
six texts rather than one, because "the Pali Canon" would be claiming more than
is here, and because 56,270 passages under a single name is not a book anyone
reads or cites.

**Pali Canon and Tipitaka are the same thing** — the Tipitaka *is* the canon,
three baskets of it, so neither contains the other. What this holds is two of
those three: the Vinaya and the Sutta. There is no English Abhidhamma in
bilara-data to include. The Khuddaka Nikaya is partial as well, nine of its
books rather than all fifteen. So the six texts are named for the divisions
they actually are, and nothing here claims to be the canon entire.

## Rebuilding the data

    scripts/fetch_sources.sh      # downloads into tmp/ (about 100 MB, cached)
    cd scripts && python3 build_all.py

`build_all.py` writes `data/<text>/NNNN.json` — 400 paragraphs per file as
`[reference, text]` pairs — plus `data/manifest.json`, which also carries the
tradition each text belongs to and the order the columns stand in. The app
fetches only the chunks it renders, so opening the middle of the Pali Canon
costs a couple of hundred kilobytes rather than sixteen megabytes.

`fetch_sources.sh` pulls the Sacred Books of the East volumes through the
Wayback Machine: sacred-texts.com now sits behind a challenge that refuses
scripted requests. That path is slow and the archive throttles bursts, so it
goes two at a time and retries through the refusals; a re-run only fetches what
is missing.

The Pali Canon build reads bilara's markup layer alongside the English so that
paragraph breaks, headings and verse lines come from the source rather than
from guesses about the segment numbering, and cites suttas the way
SuttaCentral does (`MN 77 5.1`). Verse keeps its line breaks; so does Arnold's
blank-verse Gita.

Add a text by writing a `scripts/build_*.py` that hands `common.write_text` an
id, titles, provenance, a tradition from `common.TRADITIONS`, and an iterable of
`(reference, text)` pairs, then listing it in `build_all.py`. A new tradition
is a new column, so add it to `TRADITIONS` in the position it should stand in
across the spread.

## Tests

    python3 scripts/test_sortes.py            all of it
    python3 scripts/test_sortes.py Contracts  one class

Standard library only, about a third of a second. Run it after changing a code,
a reference format, or anything `stats.json` carries.

It covers the joins — the places where two files have to agree and nothing
checks that they do, which is where every bug here worth writing a test for has
lived:

- **Constants declared twice.** `classify.py` kept its own `MAX_CODES` and was
  not raised with `labels.py`, so 5,912 hadith were truncated to four codes by a
  cap the validator would have accepted.
- **A bit order shared between Python and JavaScript.** `stats.py` packs a
  passage into a byte and `app.js` unpacks it; if the orders drift every map is
  wrong and nothing errors. The test reads the array out of `app.js`.
- **A field the page reads and the script stopped writing.** A row missing
  `counts` took the whole statistics screen down, blank and silent.
- **A text left on disk after the manifest forgot it.** Invisible until a stale
  manifest asks for a chunk of it and the app dies on a 404.
- **A rebuild eating the labels.** `write_text` used to delete the whole text
  directory, and `labels/` lives inside it.
- **`suspect()`**, which decides whether a blank is a classifier skipping work
  or a genealogy that genuinely carries no form. It is a heuristic and it has
  been wrong in both directions; the cases are pinned here.

What it does not cover is whether a label is *right*. That is a judgement about
a passage of scripture and no assertion settles it — `classify.py calibrate`
and reading the output are the tools for that.

## Rebuilding the labels

Labels live at `data/<text>/labels/NNNN.json`, one code string per passage,
alongside the chunk they describe. A chunk file existing *and validating* is
what "done" means — there is no state to get out of step with the filesystem.

    python3 -m venv .venv && .venv/bin/pip install typesafe-sdk
    export TYPESAFE_API_KEY=...
    .venv/bin/python scripts/classify.py status        what is labelled
    .venv/bin/python scripts/classify.py run           label what is left
    .venv/bin/python scripts/classify.py run --all     relabel everything
    .venv/bin/python scripts/classify.py calibrate     what a threshold costs

`classify.py` asks [Jev](https://docs.typesafe.ai) seven yes/no questions about
each passage — one per code — in a single request. That is the shape the
taxonomy already had: seven independent judgements, not one seven-way choice.
The passage is the expensive half of the request and batching sends it once, so
the whole corpus costs a few dollars.

What comes back is a probability per code rather than a letter, so the cut
between "carries this force" and "does not" is made in `classify.py` and can be
moved without re-reading anything; `calibrate` prints what each cut would do.
The passage goes out on its own, with no book name and no neighbours — form
criticism is meant to be blind, and telling a classifier it is reading the
Quran invites it to label what it expects.

`labels.py` still owns the file format and the validation, and its `audit`
still ranks finished chunks by blanks that look like skipped sentences.

    python3 labels.py status           what is done, what is left
    python3 labels.py audit            finished chunks ranked by suspect blanks

`labels.py prepare`/`assemble` remain from the earlier pipeline, which handed
chunks of 400 passages to agents in parts of 100. That worked, but it was
hand-driven and not repeatable: shown 400 lines at once a classifier finds a
rhythm and labels to it — on one trial it put exactly two codes on 338 of 400.

`scripts/reclass.py` re-judges a single distinction across the whole corpus
without relabelling it; it was written for the threat/violence split and holds
the candidate query for that.

`python3 scripts/stats.py` rolls the labels into `data/stats.json` and the
per-passage bitmaps in `data/map/`, which is what the statistics screen fetches
— reading all 253 label files in the browser would cost more than the passages
themselves.

See `NOTES.md` for the design reasoning.
