# Design notes

**Subject.** Not "a text viewer" — it's two old things at once. *Sortes*: the
practice of opening a holy book at random and reading where your finger lands,
which exists in every one of these six traditions. And the **polyglot**: the
ruled parallel columns of Walton's or the Complutensian, scriptures laid side
by side on one spread so the eye can cross between them.

**A column is a tradition, not a book.** Six columns is the polyglot; thirteen
is a spreadsheet. So the column is the shelf — Islam's holds the Quran and the
six hadith collections, Hinduism's the Gita, the Rig Veda, the Upanishads and
Manu — and a jump takes a book down at random. This is also truer to *sortes*
than a fixed column per book: you go to the shelf, not to the volume.

**Books within a tradition come up equally often, not by length.** Weighted by
length the Islam column would be 85% hadith and the Hinduism column would show
the Gita's 245 stanzas once in forty. Equal weighting means a short book
repeats sooner, which is the cheaper cost by a long way.

**The statistics screen is one block per tradition, ruled apart and stacked.**
Every block keeps the column width of the widest tradition, so a book column is
the same width wherever it appears, and every bar is on one scale across all
thirteen books. A row therefore compares as well down the screen as across it,
and a block can still be read on its own — what the six hadith collections do
against each other is a question the old single wide table could not ask.

**The one bold move.** Rubrication. Across Hebrew, Christian, Islamic, Buddhist
and Sanskrit manuscript traditions the body was written in black and the
chapter/verse marks in red (*rubrum*). So: running heads are red marginalia,
the body is ink, and nothing else gets a color. The "highlight" is not a marker
— it is the rest of the column losing its ink, the way your eye drops
everything but the line you are on.

**The reading line.** Every column lands its passage on the same mark, 34% down,
so one horizontal line of full-strength ink runs across all six books. That
line is what makes it a spread rather than six widgets. Scrolling a column
moves its own light and its own reference; the columns are otherwise
independent.

**Not doing.** Cream #F4F1EA + terracotta. Gold-leaf illumination. A color per
religion. All-caps eyebrows. Cards.

**Palette.** Flax-gray ground (#E3E1D8) — cooler and grayer than the cream
default — blue-black ink, a four-step fade ramp, cinnabar rubric (#A32B1B).

**Type.** Spectral alone, roman and italic. A Gutenberg-referencing serif built
for screen reading; italic carries the marginal register, so no second family is
needed.

**Layout rule.** Every column scrolls itself, so the spread must never need
scrolling too — a page scrollbar sitting behind six scrollers is unreachable.
Rows are therefore sized to fill the screen exactly, and once they would be too
cramped to read the spread becomes a row you swipe along a screenful at a time.

**Motion.** One orchestrated moment: on landing, the ink soaks into the passage.
Jumps are cuts, not journeys — animating a scroll through seventy paragraphs of
a book you were not reading is motion that means nothing.
