# Known issues

Most of this is about the labels under `data/<text>/labels/`, which are a
model's reading of literary form; the last two sections are about the texts
themselves. For the labels: `scripts/labels.py` rejects a chunk that is the wrong length, uses codes
outside `LPTNDW`, or leaves more than 40% of passages blank. Everything below
passed those checks and is still suspect.

## tripitaka chunk 0037 — unreliable

The Vinaya's Parivara legal digest (with the tail of the Second Council
account). Labelled three times, wrong each time and in a different way:

| attempt | result |
| --- | --- |
| 1 | 34% blank; 258 Doctrine against 5 Narrative |
| 2 | 38% blank; blanks included plain rule statements |
| 3 | 30% blank; the identical `LD` pair on 250 consecutive passages |

Attempt 3 is what is on disk. The third pattern is mechanical rather than
judged, so treat the Law and Doctrine marks in this chunk as unreliable.

Why it resists: the Parivara states rules as bare consequences ("there is an
offense entailing confession for...") and taxonomies as bare counts ("there are
three kinds of..."). Those are `L` and `D` respectively, they look nearly
identical, and a worker that cannot separate them abstains or picks one and
repeats it.

To retry: delete `data/tripitaka/labels/0037.json`, run
`python3 scripts/labels.py prepare tripitaka 37`, and hand a worker the parts.
A more capable model than Haiku is the obvious next lever.

## Watch the blank rate, not the code mix

The 40% guard catches collapse, not degradation. Chunk 0037 sat at 34% and
passed while being plainly wrong. When reviewing, sort chunks by blank rate and
read the top of the list; a chunk where one code dominates a passage of
narrative is the other thing worth a look.

Legitimately sparse chunks exist and are fine: Ezra's census rolls
(`old-testament/0030`, 26%) and parts of the Psalms (`old-testament/0015`, 32%).

The mirror case is a chunk where one code dominates and that is also correct.
`tripitaka/0054` is 94% `D`, which normally means the worker found a rhythm and
stopped reading. It is the Saṅgīti and Dasuttara suttas (DN 33–34), the Dīgha
Nikāya's two list-suttas, which are nothing but enumerated taxonomies from end
to end. `tripitaka/0040` is doctrine-heavy for the same reason. Check the
references before rejecting a lopsided chunk.

High blank rates also cluster in the debate suttas. `tripitaka/0051` (DN 23–25)
is 26% empty because bilara segments dialogue one utterance at a time, and a
turn like "No, worthy Kassapa" carries no form by itself. Expect the same
wherever a sutta is mostly cross-examination.
`tripitaka/0059` is the extreme case at 36%: MN 43–44 are the *vedalla* suttas,
catechism end to end, and the worker coded every answer `D` and left every
question blank. Consistent and defensible — a question asserts nothing — but if
you would rather see questions as `N`, that is the chunk to re-run.

The Saṃyutta Nikāya chunks (roughly `tripitaka/0073` onward) run 20–26% blank
for a third reason: each of its several thousand short suttas opens with a bare
setting stub, "At Sāvatthī." That is correctly empty. `tripitaka/0077` was
re-run because its blanks were not of that kind — it had dropped a homage verse
and a plain doctrinal assertion — and workers from that chunk on are told
explicitly that a speaker-introduction is `N` and a verse of praise is `W`.

A fourth legitimate blank appears from `tripitaka/0082` (SN 22): the *peyyāla*
elision fragments — a bare "Choices …" or "perception …" standing in for a
formula repeated across the five aggregates. bilara segments each as its own
paragraph and they carry no form alone, which is why the Khandhasaṃyutta runs
near a third blank.

A cheap test tells the two apart: count how many of a chunk's blanks are under
40 characters. In `tripitaka/0079` it was 112 of 131 — stubs and elisions, fine.
In `tripitaka/0083` it was 32 of 106, the rest full sentences, so that chunk was
put back in the queue.

## The audit command

`python3 labels.py audit [n]` ranks finished chunks by how many blanks look like
a full sentence the worker simply skipped — a blank that is not a setting stub,
an elision containing "…", a one-line exchange question, a parenthetical
editorial note or a colophon. Under about 20 per 400-passage chunk is normal;
past 25 the chunk is worth re-running, and a re-run typically halves it.

It still over-flags one thing: the *uddāna* mnemonic verses that close a
division ("Six on slanting to the east, / and six on slanting to the ocean …")
are correctly blank but read as full sentences.

`tripitaka/0098` failed two attempts, ending at 36 — it drops narrative, praise
formulas and plain instructions. Its labels are kept because they validate, but
they are the weakest in the Saṃyutta range. Treat it like `0037`.

The chunks labelled before the Saṃyutta guidance landed may also under-code
questions: an earlier version of the worker prompt listed "a question" as
always blank, which is right for the *vedalla* catechism and wrong for a
Socratic teaching question that carries the content. Chunks from `0094` on use
the corrected rule.

From `tripitaka/0108` the canon crosses from the Saṃyutta into the Aṅguttara
Nikāya, which is organized by number and is genuinely near-pure exposition —
0108 is 91% `D` and that is correct, as with DN 33–34 in `0054`.

A sixth structural blank appears in the Itivuttaka (`tripitaka/0129`): every one
of its suttas is framed by "This was said by the Buddha, the Perfected One: that
is what I heard." That is a transmission formula, not content, and it is
correctly blank 125 times in one chunk. The audit discounts it.

## More colours than the checks pass

The margins mark four kinds (law, promise, threat, doctrine) and the statistics
screen colours five, adding worship. Neither set clears the colourblind check
on colour alone. Four pigments score deutan dE 4.8 in light mode and 6.6 in
dark, against a floor of 6 and a target of 8; five is worse. Searching for a
five-hue set that does pass produced neon magenta and electric violet at
dE 6.3 — still only the floor band, and nothing like the rest of the page.

Both places carry a second encoding instead, which is what makes that
acceptable. In the margins it is position: the slots are fixed and always
drawn in the same order, so an indented lone rule is a threat and not a law
whether or not the hues separate.

On the statistics screen it is the isolate: hovering, focusing or
tapping a kind leaves that kind solid and drops everything else to 25% in the
bars and 7% in the maps. That reads identically in black and white, so the
hues are a convenience rather than the encoding. Narrative stays uncoloured on
purpose — it is the commonest kind in four of the six books, and colouring it
would leave nothing for the rest to be figure against.

## The threat/violence split

`T` was originally doing two jobs: warning a hearer, and describing harm. They
were separated into `T` and `V` after the fact, which meant re-judging every
passage either could apply to — 10,907 of them, from two sources: everything
already labelled `T`, and everything whose text matched a violence vocabulary.

The second half is a keyword sweep, so it has false negatives: violence
described without any of those words was never offered to a worker and is still
missing. The category is a floor, not a census. `scripts/reclass.py` holds the
word list and can be re-run with a wider one.

One worker (job 24) went past its brief and coded 39 passages the rest of the
corpus leaves blank — Saṃyutta catechetical questions. Those were reverted;
its threat/violence work was kept. Worth checking for on any future re-run
that tells workers to leave other codes alone.

## The hadith translations are not public domain

Every other text here is public domain or CC0. The standard English hadith
translations are not: Muhsin Khan's Bukhari and Abdul Hamid Siddiqui's Muslim
are twentieth century, widely mirrored, and of uncertain status. They are in
anyway, because the alternative was an Islam column holding one book, and
because no public domain English translation of the six books exists to use
instead. The README, the sources panel and the manifest all say so rather than
claiming a clean sheet. If that trade is not acceptable, drop `build_hadith`
from `BUILDERS` in `scripts/build_all.py` and rebuild.

## Where the new texts are ragged

**The Rig Veda's stanza numbers.** Griffith's stanzas are split apart out of
one string per hymn, on the numeral that opens each. The scan behind that text
misread a few numerals — a line-initial "I" as a "1", and the odd "1ṬHE" with
the space eaten — so `build_rigveda.py` renumbers the stanzas by the order it
finds them rather than trusting the numeral, and refuses a split where the text
after the numeral opens in lower case. That lands at 10,550 stanzas against a
canonical 10,552. The text is complete and in order; a handful of references in
the back half of Mandala 8 are off by a stanza or two, because the Valakhilya
hymns (8.49–8.59) carry their own numbering in the source.

**The Upanishads' footnotes.** Müller's call-outs are anchors in the HTML and
are pulled out by `build_upanishads.py`, along with the space they sat in.
Anything he set as a footnote is gone with them, so a passage that leans on a
note reads thinner here than on the page. Verses split across several
paragraphs are joined back into one passage.

**The Old Testament sits under Judaism and the New under Christianity.** It is
a rough cut — the Old Testament is scripture to both, and the KJV arranges it
the Christian way, not the Tanakh's — but the alternative is printing 23,145
passages twice and having two columns that often fall open on the same verse.
