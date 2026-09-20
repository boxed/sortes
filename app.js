/* Sortes — six traditions side by side, each fallen open at a random passage.
 *
 * Texts are built into data/<id>/NNNN.json, each holding `chunk` paragraphs as
 * [reference, text] pairs, so opening the middle of a 56,000-paragraph canon
 * downloads a couple of hundred kilobytes rather than seventeen megabytes.
 *
 * A column is a tradition, not a book: Islam has seven books on the shelf here
 * and Judaism one, and six columns of tradition compare better than thirteen
 * columns of book. Each jump takes a book from the column's shelf and opens it
 * somewhere. Whatever paragraph crosses that column's reading line is the lit
 * one, and the column fades away from it. The columns are otherwise
 * independent; the only thing they share is the button.
 */

const WINDOW = 70;      // paragraphs rendered either side of the landing passage
const EXTEND = 50;      // how many more to pull in when you read to an edge
const MARGIN = 15;      // how close to an edge you get before that happens
const LANDING = 0.34;   // where down a column a jump parks the passage
const LINE = 0.4;       // and where that column's reading line sits
const FLOOR = 60;       // characters below which a jump keeps looking
const MIN_WIDTH = 228;  // narrowest a column may be before one is dropped
const MAX_ROWS = 2;     // beyond this the spread turns into a swipeable one

const grid = document.getElementById('grid');
const booksNav = document.getElementById('books');
const jumpButton = document.getElementById('jump');
const sources = document.getElementById('sources');
const sourcesToggle = document.getElementById('sources-toggle');
const stats = document.getElementById('stats');
const statsToggle = document.getElementById('stats-toggle');

const chunks = new Map();

// The index files are rebuilt whenever the corpus is, and a browser holding
// yesterday's copy of one will fetch chunks for a text that no longer exists,
// or read a stats.json whose shape has moved on. Both fail a long way from the
// cause. They are small, so they are always revalidated; the passage chunks
// under them never change in place and are left to cache normally.
const FRESH = { cache: 'no-cache' };

// Four of the six codes are shown as rules, in fixed slots so position — not
// colour alone — says which is which. Narrative and worship are named in the
// column head instead: narrative is the commonest kind in four of the six
// books, so marking it would put a rule on most of the page and leave the
// others nothing to stand out against.
const FORCES = [
  ['L', 'Law'], ['P', 'Promise'], ['T', 'Threat'], ['V', 'Violence'],
  ['D', 'Doctrine'],
];
const MODES = { N: 'narrative', W: 'worship', A: 'provenance' };
const columns = new Map();   // tradition id -> column state, one per tradition

let texts = [];
let traditions = [];
let byId = {};
let mode = 'all';            // 'all' for the polyglot, or a single tradition id
let generation = 0;          // bumped per jump, so a slow one cannot land late

/* ---- data ----------------------------------------------------------- */

function chunkAt(text, index) {
  const number = Math.floor(index / text.chunk);
  const key = `${text.id}/${number}`;
  if (!chunks.has(key)) {
    const name = String(number).padStart(4, '0');
    chunks.set(key, fetch(`data/${text.id}/${name}.json`).then((r) => {
      if (!r.ok) throw new Error(`${text.title} chunk ${number}: ${r.status}`);
      return r.json();
    }));
  }
  return chunks.get(key);
}

/** A chunk's labels, or null where that chunk has not been classified yet. */
function labelsAt(text, index) {
  const number = Math.floor(index / text.chunk);
  const key = `${text.id}/labels/${number}`;
  if (!chunks.has(key)) {
    const name = String(number).padStart(4, '0');
    chunks.set(key, fetch(`data/${text.id}/labels/${name}.json`)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null));
  }
  return chunks.get(key);
}

/** Paragraphs [from, to) as [reference, text, codes], with the chunks they span. */
async function slice(text, from, to) {
  const first = Math.floor(from / text.chunk);
  const last = Math.floor((to - 1) / text.chunk);
  const wantText = [];
  const wantCodes = [];
  for (let n = first; n <= last; n += 1) {
    wantText.push(chunkAt(text, n * text.chunk));
    wantCodes.push(labelsAt(text, n * text.chunk));
  }
  const [loaded, labelled] = await Promise.all(
    [Promise.all(wantText), Promise.all(wantCodes)]);

  const base = first * text.chunk;
  const rows = loaded.flat().slice(from - base, to - base);
  const codes = labelled
    .flatMap((one, i) => one || Array(loaded[i].length).fill(''))
    .slice(from - base, to - base);
  return {
    rows: rows.map((pair, i) => [pair[0], pair[1], codes[i]]),
    labelled: labelled.some(Boolean),
  };
}

/* ---- columns -------------------------------------------------------- */

function buildColumn(tradition) {
  const root = document.createElement('section');
  root.className = 'column';
  root.dataset.tradition = tradition.id;

  // The running head: whose shelf this column is, which book came off it, and
  // where in that book you are. The tradition is the only fixed part — the
  // book changes under it on every jump, which is the whole point of the
  // column — so it is set once here and the title below it is rewritten. In
  // the polyglot the head sits above the column; given room it hangs in the
  // margin at the reading line, beside the passage it names.
  const head = document.createElement('header');
  head.className = 'head';
  const where = document.createElement('p');
  where.className = 'head-where';
  where.textContent = tradition.title;
  const book = document.createElement('h2');
  book.className = 'head-book';
  const title = document.createTextNode('');
  book.append(title);
  const form = document.createElement('span');
  form.className = 'head-form';
  book.append(form);
  const reference = document.createElement('p');
  reference.className = 'head-ref';
  head.append(where, book, reference);

  const stream = document.createElement('div');
  stream.className = 'stream';
  const page = document.createElement('div');
  page.className = 'page';
  const edge = document.createElement('p');
  edge.className = 'edge';
  edge.textContent = 'You have reached the end of this book.';
  edge.hidden = true;
  stream.append(page, edge);

  root.append(head, stream);

  const column = {
    tradition, root, title, reference, form, stream, page, edge,
    // Which books this column can fall open at, and which one it is showing.
    shelf: tradition.texts.map((id) => byId[id]),
    only: null,          // set when one book has been asked for by name
    text: null,
    shown: null, lit: null, settling: false,
  };

  let waiting = false;
  stream.addEventListener('scroll', () => {
    if (waiting) return;
    waiting = true;
    requestAnimationFrame(() => { waiting = false; onScroll(column); });
  }, { passive: true });

  return column;
}

function paragraph(index, body, codes) {
  const p = document.createElement('p');
  p.className = 'para';
  p.dataset.index = index;
  p.dataset.codes = codes;

  // Always three slots, always in this order — an indented lone rule is a
  // threat, not a law, and that is readable without the legend.
  const marks = document.createElement('span');
  marks.className = 'marks';
  const named = [];
  for (const [code, name] of FORCES) {
    const rule = document.createElement('i');
    rule.className = 'rule';
    if (codes.includes(code)) {
      rule.dataset.code = code;
      rule.title = name;
      named.push(name);
    }
    marks.append(rule);
  }
  if (named.length) {
    marks.setAttribute('role', 'img');
    marks.setAttribute('aria-label', named.join(', '));
  } else {
    marks.setAttribute('aria-hidden', 'true');
  }

  p.append(marks, document.createTextNode(body));
  return p;
}

function fill(from, rows) {
  return rows.map((row, i) => paragraph(from + i, row[1], row[2]));
}

/* ---- the reading line ----------------------------------------------- */

/** Fade the two paragraphs on one side of the lit one, nearest first. */
function band(from, direction) {
  let node = from[direction];
  for (const name of ['n1', 'n2']) {
    if (!node) return;
    node.classList.remove('lit', 'n1', 'n2');
    node.classList.add(name);
    node = node[direction];
  }
}

function light(column, target) {
  for (const p of column.page.querySelectorAll('.lit, .n1, .n2')) {
    p.classList.remove('lit', 'n1', 'n2');
  }
  target.classList.add('lit');
  band(target, 'previousElementSibling');
  band(target, 'nextElementSibling');
  column.lit = target;

  const index = Number(target.dataset.index);
  column.reference.textContent = column.shown.refs[index - column.shown.from];

  // The four kinds that are not rules get named here instead.
  const codes = target.dataset.codes || '';
  const modes = [...codes].filter((c) => MODES[c]).map((c) => MODES[c]);
  column.form.textContent = column.root.dataset.labelled === 'no'
    ? 'not yet labelled'
    : modes.join(', ');

  rememberPlaces();
}

/** Light whichever paragraph of this column crosses its reading line. */
function relight(column) {
  const paragraphs = column.page.children;
  if (!paragraphs.length) return;
  const line = column.stream.scrollTop + column.stream.clientHeight * LINE;

  let found = paragraphs[0];
  for (const p of paragraphs) {
    if (p.offsetTop > line) break;
    found = p;
  }
  if (found !== column.lit) light(column, found);
}

async function render(column, text, from, to) {
  const { rows, labelled } = await slice(text, from, to);
  column.page.replaceChildren(...fill(from, rows));
  column.text = text;
  column.title.data = text.short;
  // The region remembers which book it came out of, so a scroll that reaches
  // an edge extends the book it is showing and not whichever one a jump has
  // since put in the column.
  column.shown = { text, from, to, refs: rows.map((row) => row[0]) };
  column.edge.hidden = to < text.count;
  column.root.dataset.labelled = labelled ? 'yes' : 'no';
}

/** Pull in more paragraphs when the reader nears either end of the column. */
async function extend(column, end) {
  const region = column.shown;
  const { text, from, to } = region;

  if (end === 'start') {
    if (from === 0) return;
    const start = Math.max(0, from - EXTEND);
    const { rows } = await slice(text, start, from);
    // A jump may have replaced this column while we were fetching.
    if (column.shown !== region || region.from !== from) return;
    const first = column.page.firstElementChild;
    const before = first.offsetTop;
    column.page.prepend(...fill(start, rows));
    column.stream.scrollTop += first.offsetTop - before;
    region.from = start;
    region.refs.unshift(...rows.map((row) => row[0]));
  } else {
    if (to >= text.count) return;
    const stop = Math.min(text.count, to + EXTEND);
    const { rows } = await slice(text, to, stop);
    if (column.shown !== region || region.to !== to) return;
    column.page.append(...fill(to, rows));
    region.to = stop;
    region.refs.push(...rows.map((row) => row[0]));
    column.edge.hidden = stop < text.count;
  }
}

function onScroll(column) {
  if (column.settling || !column.shown || !column.page.children.length) return;
  relight(column);
  const index = Number(column.lit?.dataset.index ?? column.shown.from);
  if (index - column.shown.from < MARGIN) extend(column, 'start');
  if (column.shown.to - index < MARGIN) extend(column, 'end');
}

/* ---- opening -------------------------------------------------------- */

/** Which book this column falls open at: the one asked for by name, or any
 *  of the tradition's, each as likely as the next. Weighting by length would
 *  bury the Gita's 245 stanzas under the Rig Veda and the Quran under the
 *  hadith, and a column that never shows the Quran is not an Islam column. */
function pick(column) {
  if (column.only) return column.only;
  return column.shelf[Math.floor(Math.random() * column.shelf.length)];
}

/** Where a jump should land in one text: random, but never on "Yes, sir." */
async function choose(text) {
  const index = Math.floor(Math.random() * text.count);
  const base = Math.floor(index / text.chunk) * text.chunk;
  const loaded = await chunkAt(text, index);
  let at = index;
  while (at - base < loaded.length - 1 && loaded[at - base][1].length < FLOOR) {
    at += 1;
  }
  return at;
}

async function open(column, text, index, token) {
  column.settling = true;
  column.lit = null;

  const from = Math.max(0, index - WINDOW);
  await render(column, text, from, Math.min(text.count, index + WINDOW + 1));
  if (token !== generation) return; // a later jump already took this column

  const target = column.page.querySelector(`[data-index="${index}"]`);
  column.stream.scrollTop = Math.max(
    0, target.offsetTop - column.stream.clientHeight * LANDING);

  light(column, target);
  target.classList.add('arrived');
  target.addEventListener('animationend',
    () => target.classList.remove('arrived'), { once: true });

  // Ignore the scroll event our own scrollTop just queued, so the target keeps
  // the light even when it is short enough to sit clear of the reading line.
  requestAnimationFrame(() => { column.settling = false; });
}

/** Put a column's lit passage back on its landing mark, after the geometry
 *  under it has changed — a resize, or the web font arriving late. */
function anchor(column) {
  if (!column.lit) return;
  column.settling = true;
  column.stream.scrollTop = Math.max(
    0, column.lit.offsetTop - column.stream.clientHeight * LANDING);
  requestAnimationFrame(() => { column.settling = false; });
}

function onScreen() {
  return mode === 'all' ? [...columns.values()] : [columns.get(mode)];
}

/** The column a text belongs to — its tradition's. */
function columnFor(text) {
  return columns.get(text.tradition);
}

async function jump() {
  const token = ++generation;
  await Promise.all(onScreen().map(async (column) => {
    const text = pick(column);
    const index = await choose(text);
    if (token === generation) await open(column, text, index, token);
  }));
}

/* ---- layout --------------------------------------------------------- */

/** Fit as many books across as will hold a readable measure.
 *
 *  Every column scrolls itself, so the spread must never need scrolling too —
 *  a page scrollbar behind six scrollers is unreachable. Instead the rows are
 *  sized to fill the screen exactly, and once they would be too cramped to
 *  read the spread becomes a row you swipe along, a screenful at a time.
 */
function layout() {
  const showing = onScreen().length;
  let across = Math.max(1, Math.min(showing, Math.floor(grid.clientWidth / MIN_WIDTH)));
  // Two rows of three beat a row of five and a lonely sixth.
  if (Math.ceil(showing / across) <= MAX_ROWS) {
    across = Math.ceil(showing / Math.ceil(showing / across));
  }
  const rows = Math.ceil(showing / across);
  const swipe = rows > MAX_ROWS;

  grid.dataset.flow = swipe ? 'across' : 'stacked';
  grid.dataset.cols = across;
  grid.style.setProperty('--cols', across);
  grid.style.setProperty('--col-height',
    `${Math.floor(swipe ? grid.clientHeight : grid.clientHeight / rows)}px`);
  for (const column of onScreen()) anchor(column);
}

function show() {
  grid.dataset.mode = mode === 'all' ? 'all' : 'one';
  grid.replaceChildren(...onScreen().map((column) => column.root));
  layout();
}

/* ---- chrome --------------------------------------------------------- */

function button(label, pressed, onPick) {
  const element = document.createElement('button');
  element.type = 'button';
  element.textContent = label;
  element.setAttribute('aria-pressed', String(pressed));
  element.addEventListener('click', onPick);
  return element;
}

/** The bar names the six traditions, not the thirteen books. Thirteen would
 *  not fit and would not help: which book you land in is the column's business.
 *  Drop to one tradition and the books it holds appear as a second row, so a
 *  single book can still be asked for by name. */
function buildNav() {
  const rows = [document.createElement('span'), document.createElement('span')];
  rows.forEach((row) => { row.className = 'nav-row'; });

  const pickMode = (id) => {
    mode = id;
    for (const column of columns.values()) column.only = null;
    buildNav();
    show();
    jump();
  };
  rows[0].append(button('All six', mode === 'all', () => pickMode('all')));
  for (const tradition of traditions) {
    rows[0].append(button(tradition.title, mode === tradition.id,
                          () => pickMode(tradition.id)));
  }

  const column = mode === 'all' ? null : columns.get(mode);
  if (column && column.shelf.length > 1) {
    const pickBook = (text) => {
      column.only = text;
      buildNav();
      jump();
    };
    rows[1].append(button('Any of them', !column.only, () => pickBook(null)));
    for (const text of column.shelf) {
      rows[1].append(button(text.short, column.only === text,
                            () => pickBook(text)));
    }
  }
  booksNav.replaceChildren(...rows.filter((row) => row.children.length));
}

function buildSources() {
  const list = document.getElementById('sources-list');
  const parts = [];
  for (const tradition of traditions) {
    const heading = document.createElement('dt');
    heading.className = 'sources-where';
    heading.textContent = tradition.title;
    parts.push(heading);
    for (const id of tradition.texts) {
      const text = byId[id];
      const dt = document.createElement('dt');
      dt.textContent = `${text.title} — ${text.subtitle}`;
      const dd = document.createElement('dd');
      dd.textContent = `${text.count.toLocaleString('en')} passages. `
        + `${text.source}. ${text.license}.`;
      parts.push(dt, dd);
    }
  }
  list.replaceChildren(...parts);
}

/* ---- statistics -------------------------------------------------------- */

// The map draws one pixel per passage. The canvas is sized to the space it is
// given so a passage is exactly one screen pixel — scaling a pixel map down
// drops passages on the floor and the whole thing turns to static. Only the
// three marked kinds take a pigment; the rest is ground, which is the point:
// you see where the law sits and where the threats gather.
// Law, promise and threat are the three that also appear in the margins.
// Doctrine and worship are coloured here only. Narrative stays as ground —
// it is the commonest kind in four of the six books and colouring it would
// leave nothing for the others to be figure against.
const PIXELS = {
  L: '--law', P: '--promise', T: '--threat', V: '--violence',
  D: '--doctrine', W: '--worship', A: '--provenance',
};
// Bit order must match BITS in stats.py; narrative takes the eighth bit.
const BITS = ['L', 'P', 'T', 'V', 'D', 'W', 'A', 'N'];
// Which colour a passage takes when nothing is isolated and it carries several:
// the sharpest rhetorical force wins. Narrative is ground. Provenance sits
// last and only when it is being counted, so a passage that does something
// keeps the colour of what it does, and only a bare chain of narrators — a
// hadith with an isnad and no matn — comes up in its pigment.
const OVER = ['T', 'V', 'P', 'L', 'W', 'D'];
const OVER_FRAME = [...OVER, 'A'];

// A column is a tradition, and its books run down it end to end with a band of
// ground between them: the Quran above the six hadith collections, the Vinaya
// above the five nikayas. Five rows, left transparent rather than drawn, so it
// reads as a gap in the text and not as a mark on it.
//
// A band at every book *inside* a text — a rule at each of the Quran's 114
// surahs — was tried and came far too often to read; the map turned into more
// seam than text.
const SEAM = 5;
// What sits in a cell that holds no passage.
const PAD = -1;

let statsLoaded = false;
let kindNames = {};              // code -> what to call it, in taxonomy order
const drawn = new Map();
// canvas -> which passage sits in each cell of its grid, -1 for the seams.
// Drawing and hovering both read this, so a pixel cannot mean one passage to
// the eye and a different one to the card that reads it.
const placed = new Map();

function swatch(shade) {
  const probe = getComputedStyle(document.documentElement);
  return probe.getPropertyValue(shade).trim();
}

let isolated = null;
let releaseIsolate = () => {};

/** The hex map file as one mask per passage. */
function masks(text) {
  const out = new Uint8Array(text.length / 2);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = parseInt(text.substr(i * 2, 2), 16);
  }
  return out;
}

/** True when a passage carries a chain of narrators and nothing else.
 *
 *  Such a passage does nothing — a hadith with an isnad and no matn — so with
 *  provenance excluded it is not in the corpus at all, and the map gives it no
 *  pixel rather than a blank one.
 */
function frameOnly(mask) {
  return mask === (1 << BITS.indexOf(FRAME));
}

/** Lay a tradition's books across `width` columns, a band between each.
 *
 *  A book starts on a fresh row rather than partway along one, so the band
 *  reads as a gap right across the map instead of a notch in it.
 */
function place(parts, strip, width) {
  const cells = [];
  let at = 0;
  parts.forEach((part, n) => {
    for (let i = 0; i < part.count; i += 1) {
      if (!counting && frameOnly(strip[at + i])) continue;
      cells.push(at + i);
    }
    at += part.count;
    while (cells.length % width) cells.push(PAD);
    if (n + 1 < parts.length) {
      for (let i = 0; i < width * SEAM; i += 1) cells.push(PAD);
    }
  });
  while (cells.length % width) cells.push(PAD);
  return Int32Array.from(cells);
}

/** Which book of a tradition a passage index falls in, and where inside it. */
function within(parts, index) {
  let at = 0;
  for (const part of parts) {
    if (index < at + part.count) return [byId[part.id], index - at];
    at += part.count;
  }
  return [null, 0];
}

function drawMap(canvas, entry) {
  const { strip, parts } = entry;
  // Aim for a square, and stop widening at the column — past that the map
  // grows downwards, which in practice is only the Pali Canon. A short book
  // then has fewer, larger pixels rather than a two-pixel smear: every map
  // fills its column, and passage count shows in the grain instead of in the
  // area. It also gives the Gita hover targets you can actually hit.
  const cap = Math.max(1, Math.floor(canvas.parentElement.clientWidth));
  const width = Math.min(cap, Math.ceil(Math.sqrt(strip.length)));
  const cells = place(parts, strip, width);
  const rows = cells.length / width;
  placed.set(canvas, cells);
  canvas.width = width;
  canvas.height = rows;
  const ctx = canvas.getContext('2d');
  const image = ctx.createImageData(width, rows);
  const paint = { N: swatch('--fade-2') };
  for (const [code, token] of Object.entries(PIXELS)) paint[code] = swatch(token);
  const rgb = Object.fromEntries(Object.entries(paint).map(([k, hex]) => [k, [
    parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]]));
  const bit = Object.fromEntries(BITS.map((c, i) => [c, 1 << i]));
  const ink = swatch('--ink');
  const inkRgb = [1, 3, 5].map((k) => parseInt(ink.slice(k, k + 2), 16));

  for (let cell = 0; cell < cells.length; cell += 1) {
    const i = cells[cell];
    const at = cell * 4;
    if (i === PAD) continue;
    const mask = strip[i];
    if (isolated) {
      // One kind at a time: the chosen passages stay solid and the rest all
      // but vanish, so the shape is legible without seeing any colour at all.
      // A passage carrying several kinds shows under every one of them.
      const mine = isolated === 'none' ? mask === 0 : Boolean(mask & bit[isolated]);
      const colour = isolated === 'none' ? inkRgb : rgb[isolated];
      [image.data[at], image.data[at + 1], image.data[at + 2]] = colour;
      image.data[at + 3] = mine ? 255 : 18;
      continue;
    }
    const code = (counting ? OVER_FRAME : OVER).find((c) => mask & bit[c]);
    if (code) {
      [image.data[at], image.data[at + 1], image.data[at + 2]] = rgb[code];
      image.data[at + 3] = 255;
    } else if (mask & bit.N) {
      // Narrative sits back so the marked kinds read as figure, not noise.
      [image.data[at], image.data[at + 1], image.data[at + 2]] = rgb.N;
      image.data[at + 3] = 70;
    }
  }
  ctx.putImageData(image, 0, 0);
}

/** One column per tradition, every tradition side by side.
 *
 *  A row of Law reading straight across all six is the comparison the screen
 *  exists for, so the traditions stand next to each other and the books inside
 *  one are bands down its map rather than columns of their own. Twenty columns
 *  was a spreadsheet; six is a polyglot.
 */
function columnHead(row) {
  const head = document.createElement('div');
  head.className = 'book';
  const title = document.createElement('b');
  title.textContent = row.short;
  const count = document.createElement('span');
  count.textContent = row.count.toLocaleString('en');
  const books = document.createElement('i');
  books.className = 'parts';
  // Named top to bottom in the order they run down the map.
  books.textContent = row.parts.map((part) => part.short).join(' · ');
  head.append(title, count, books);
  return head;
}

async function buildStats() {
  if (statsLoaded) return;
  statsLoaded = true;
  const body = document.getElementById('stats-body');
  const maps = [];
  const stats = await fetch('data/stats.json', FRESH).then((r) => r.json());
  const codes = Object.entries(stats.codes);
  kindNames = stats.codes;
  const rows = stats.traditions;
  if (!rows?.every((row) => row.counts)) {
    throw new Error('data/stats.json is from an older build of this app — '
      + 'rerun scripts/stats.py, and reload ignoring the cache');
  }

  // How many passages a share is out of. Excluding provenance takes the
  // chain-only passages out of the corpus, not just out of the picture, so
  // they leave the denominator too and every other figure rises a little.
  const total = (row) => row.labelled - (counting ? 0 : row.chain);
  const share = (row, code) => row.counts[code] / total(row);

  // One scale for every bar, or a row would only be comparable with itself.
  // Fixed against the fuller count, so a bar does not change length for a
  // reason the reader cannot see when the box is ticked.
  const widest = Math.max(...rows.flatMap(
    (t) => Object.keys(stats.codes).map((c) => t.counts[c] / t.labelled)));

  const matrix = document.createElement('div');
  matrix.className = 'matrix';
  matrix.style.setProperty('--books', rows.length);
  figures.length = 0;

  const corner = () => {
    const cell = document.createElement('div');
    cell.className = 'corner';
    return cell;
  };

  // The leftmost column has nothing to its left to be divided from.
  const edge = (node, row) => {
    if (row === rows[0]) node.dataset.edge = '';
    return node;
  };

  matrix.append(corner());
  for (const row of rows) {
    const head = edge(columnHead(row), row);
    const canvas = document.createElement('canvas');
    canvas.className = 'map';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label',
      `${row.short}: every passage of its scriptures in reading order, `
      + 'marked by what each one does, one book above the next.');
    head.append(canvas);
    matrix.append(head);

    wirePeek(canvas, row.parts);
    maps.push(fetch(`data/map/${row.id}.txt`, FRESH)
      .then((r) => r.text())
      .then((text) => {
        drawn.set(canvas, { strip: masks(text), parts: row.parts });
      })
      .catch(() => canvas.remove()));
  }

  for (const [code, label] of codes) {
    const kind = document.createElement('button');
    kind.type = 'button';
    kind.className = 'kind';
    kind.dataset.code = code;
    if (code === FRAME) kind.dataset.frame = '';
    kind.textContent = label;
    kind.setAttribute('aria-label', `Show only ${label.toLowerCase()}`);
    matrix.append(kind);

    for (const row of rows) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.code = code;
      const bar = document.createElement('i');
      bar.className = 'share';
      if (code in PIXELS) bar.dataset.code = code;
      bar.setAttribute('aria-hidden', 'true');
      const figure = document.createElement('b');
      cell.append(bar, figure);
      if (code === FRAME) cell.dataset.frame = '';
      figures.push([cell, bar, figure, row, code, label]);
      matrix.append(edge(cell, row));
    }
  }

  // The unmarked remainder, so the shares can be read against something.
  const rest = document.createElement('button');
  rest.type = 'button';
  rest.className = 'kind quiet';
  rest.dataset.code = 'none';
  rest.textContent = 'None of these';
  rest.setAttribute('aria-label', 'Show only passages carrying none of these');
  matrix.append(rest);
  remainders.length = 0;
  for (const row of rows) {
    const cell = document.createElement('div');
    cell.className = 'cell quiet';
    cell.dataset.code = 'none';
    const figure = document.createElement('b');
    cell.append(figure);
    remainders.push([figure, row]);
    matrix.append(edge(cell, row));
  }

  // Every bar and figure is written here rather than at build time, so ticking
  // the box rewrites them against the other denominator.
  repaint = () => {
    for (const [cell, bar, figure, row, code, label] of figures) {
      const value = share(row, code);
      bar.style.width =
        `calc((100% - var(--figure)) * ${(value / widest).toFixed(4)})`;
      figure.textContent = `${Math.round(value * 100)}%`;
      cell.setAttribute('aria-label', `${row.short}, ${label}, ` +
        `${Math.round(value * 100)} percent`);
    }
    for (const [figure, row] of remainders) {
      figure.textContent = `${Math.round(row.blank / total(row) * 100)}%`;
    }
  };

  body.replaceChildren(matrix);
  wireIsolate(body);
  wireProvenance(body);

  // The canvases have to be in the document before one can be sized to its
  // column, so the drawing waits for layout.
  await Promise.all(maps);
  redrawMaps();

  const counted = new Set(rows.flatMap((t) => t.parts.map((p) => p.id)));
  const waiting = texts.filter((t) => !counted.has(t.id)).map((t) => t.short);
  const partial = rows.filter((t) => t.labelled < t.count).map((t) => t.short);
  const short = [...waiting, ...partial];
  document.getElementById('stats-note').textContent = short.length
    ? `Not on this screen yet, or not finished: ${short.join(', ')}.`
    : 'Every passage of every book here is labelled. The labels are a '
      + 'model\u2019s reading of the form, and wrong often enough to be worth '
      + 'checking.';
}

function redrawMaps() {
  for (const [canvas, entry] of drawn) drawMap(canvas, entry);
}

/** What a passage was labelled, as the card lists it.
 *
 *  Read off the same byte the map was drawn from, so the card cannot disagree
 *  with the pixel under the cursor. Provenance is left out while it is being
 *  excluded, for the same reason: the card describes the corpus on screen.
 */
function carried(mask) {
  return Object.keys(kindNames).filter(
    (code) => (counting || code !== FRAME)
      && (mask & (1 << BITS.indexOf(code))));
}

/** A pixel is a passage — hovering one names it and reads it.
 *
 *  The column holds a whole tradition, so the pixel has to be resolved back to
 *  the book it came from before the passage can be fetched.
 */
function wirePeek(canvas, parts) {
  const peek = document.getElementById('peek');

  canvas.addEventListener('pointermove', async (event) => {
    const box = canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX - box.left) / box.width * canvas.width);
    const y = Math.floor((event.clientY - box.top) / box.height * canvas.height);
    const cells = placed.get(canvas);
    const cell = y * canvas.width + x;
    // Read the same grid the drawing used, so the bands between books report
    // nothing rather than the passage that would have sat there without them.
    const at = cells && cell >= 0 && cell < cells.length ? cells[cell] : -1;
    const [text, index] = at < 0 ? [null, 0] : within(parts, at);
    if (!text) { peek.hidden = true; return; }

    // Claim this hover, so a slow chunk fetch cannot overwrite a later one.
    const token = `${text.id}:${index}`;
    peek.dataset.token = token;

    const rows = await chunkAt(text, index);
    if (peek.dataset.token !== token) return;
    const [reference, body] = rows[index % text.chunk];

    peek.hidden = false;
    peek.querySelector('.peek-ref').textContent = `${text.short} · ${reference}`;
    peek.querySelector('.peek-body').textContent = body.replace(/\n/g, ' ');

    const kinds = carried(drawn.get(canvas)?.strip[at] ?? 0);
    const marks = kinds.map((code) => {
      const mark = document.createElement('i');
      mark.dataset.code = code;
      mark.textContent = kindNames[code];
      return mark;
    });
    if (!marks.length) {
      const none = document.createElement('i');
      none.className = 'nothing';
      none.textContent = 'none of these';
      marks.push(none);
    }
    peek.querySelector('.peek-kinds').replaceChildren(...marks);

    // Keep the card on screen rather than letting it run off the right edge.
    const width = peek.offsetWidth || 320;
    const left = Math.min(event.clientX + 16, window.innerWidth - width - 12);
    peek.style.left = `${Math.max(12, left)}px`;
    peek.style.top = `${Math.min(event.clientY + 16,
      window.innerHeight - peek.offsetHeight - 12)}px`;
  });

  canvas.addEventListener('pointerleave', () => { peek.hidden = true; });
}

// Provenance is the one kind that says nothing about what a passage does, so
// it is left out of the count unless it is asked for.
const FRAME = 'A';
const REMEMBER = 'sortes:provenance';

let counting = false;            // is provenance being counted?
let repaint = () => {};          // rewrite every bar against the current total
const figures = [];              // the bars and their numbers
const remainders = [];           // the "none of these" figures

/** Exclude provenance, or put it back: rows, figures and maps together.
 *
 *  Excluded is the default. Provenance says how a passage reached you and not
 *  what it does, and nearly every hadith carries one, so counting it buries
 *  what the six collections actually say.
 */
function wireProvenance(body) {
  const box = document.getElementById('stats-provenance');
  const apply = (excluded) => {
    counting = !excluded;
    body.toggleAttribute('data-frame', counting);
    repaint();
    // Leaving it isolated while hiding it would dim every other row against a
    // kind that is no longer on screen.
    if (excluded && isolated === FRAME) releaseIsolate();
    redrawMaps();
  };
  let remembered = null;
  try {
    remembered = localStorage.getItem(REMEMBER);
  } catch { /* private window, or storage refused: the default will do */ }
  box.checked = remembered !== 'no';        // excluded unless asked otherwise
  apply(box.checked);
  box.addEventListener('change', () => {
    apply(box.checked);
    try {
      localStorage.setItem(REMEMBER, box.checked ? 'yes' : 'no');
    } catch { /* nothing to do; the screen still works */ }
  });
}

/** Hover, focus or tap a kind to see only that kind, in bars and maps alike. */
function wireIsolate(body) {
  const rows = [...body.querySelectorAll('.kind')];
  const cells = [...body.querySelectorAll('.cell')];
  let locked = null;

  const apply = (code) => {
    if (isolated === code) return;
    isolated = code;
    body.toggleAttribute('data-isolate', Boolean(code));
    rows.forEach((r) => r.classList.toggle('row-on', r.dataset.code === code));
    cells.forEach((c) => c.classList.toggle('row-on', c.dataset.code === code));
    redrawMaps();
  };

  for (const row of rows) {
    const code = row.dataset.code;
    row.addEventListener('pointerenter', () => { if (!locked) apply(code); });
    row.addEventListener('focus', () => { if (!locked) apply(code); });
    row.addEventListener('blur', () => { if (!locked) apply(null); });
    // A tap has no hover to leave, so it locks until tapped again.
    row.addEventListener('click', () => {
      locked = locked === code ? null : code;
      apply(locked || code);
    });
  }
  body.addEventListener('pointerleave', () => { if (!locked) apply(null); });
  releaseIsolate = () => { locked = null; apply(null); };
}

function showStats(visible) {
  if (visible) {
    buildStats().catch((error) => {
      statsLoaded = false;          // so a reload can try again
      document.getElementById('stats-body').textContent =
        `The statistics could not be drawn: ${error.message}`;
    });
  }
  stats.hidden = !visible;
  statsToggle.setAttribute('aria-expanded', String(visible));
  rememberPlaces();
}

function showSources(visible) {
  sources.hidden = !visible;
  sourcesToggle.setAttribute('aria-expanded', String(visible));
  rememberPlaces();
}

/* ---- linking -------------------------------------------------------- */

let pending = 0;

// Which screen is open rides in the URL beside the passages, as a bare word
// among the book:index pairs. A link to the statistics is a thing people want
// to send, and landing back on the spread having asked for the statistics is a
// small betrayal of the link.
const SCREENS = { statistics: () => stats, sources: () => sources };

/** Keep the URL pointing at what is on screen, so it can be linked to. */
function rememberPlaces() {
  clearTimeout(pending);
  pending = setTimeout(() => {
    const parts = onScreen()
      .filter((column) => column.lit)
      .map((column) => `${column.shown.text.id}:${column.lit.dataset.index}`);
    for (const [name, node] of Object.entries(SCREENS)) {
      if (!node().hidden) parts.push(name);
    }
    if (parts.length) history.replaceState(null, '', `#${parts.join(',')}`);
  }, 300);
}

/** The screen the URL asks for, if it asks for one. */
function readScreen() {
  const parts = decodeURIComponent(location.hash.slice(1)).split(',');
  return Object.keys(SCREENS).find((name) => parts.includes(name)) || null;
}

function readPlaces() {
  const found = [];
  // One book per column: a link naming two books of the same tradition would
  // otherwise have them open into the same column and race each other.
  const taken = new Set();
  for (const part of decodeURIComponent(location.hash.slice(1)).split(',')) {
    // Screen names ride in the same list and carry no colon; they fall out
    // here because byId has nothing under them.
    const [id, at] = part.split(':');
    const text = byId[id];
    if (text && /^\d+$/.test(at || '') && !taken.has(text.tradition)) {
      taken.add(text.tradition);
      found.push([text, Math.min(Number(at), text.count - 1)]);
    }
  }
  return found;
}

/* ---- start ---------------------------------------------------------- */

async function start() {
  // Land on the passage, not near it: measure only once the real face is in.
  await document.fonts.ready.catch(() => {});
  const manifest = await fetch('data/manifest.json', FRESH)
    .then((r) => r.json());
  texts = manifest.texts;
  traditions = manifest.traditions;
  byId = Object.fromEntries(texts.map((t) => [t.id, t]));
  for (const tradition of traditions) {
    columns.set(tradition.id, buildColumn(tradition));
  }

  // A link naming one book opens that book alone: its tradition's column, held
  // to that book so a jump stays inside it.
  const places = readPlaces();
  if (places.length === 1) {
    const [text] = places[0];
    mode = text.tradition;
    columnFor(text).only = text;
  }

  buildNav();
  buildSources();
  show();

  jumpButton.addEventListener('click', jump);
  sourcesToggle.addEventListener('click', () => {
    showStats(false);
    showSources(sources.hidden);
  });
  document.getElementById('sources-close').addEventListener('click',
    () => { showSources(false); sourcesToggle.focus(); });
  statsToggle.addEventListener('click', () => {
    showSources(false);
    showStats(stats.hidden);
  });
  window.addEventListener('resize', () => { if (!stats.hidden) redrawMaps(); });
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', redrawMaps);
  document.getElementById('stats-close').addEventListener('click',
    () => { showStats(false); statsToggle.focus(); });

  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.target.closest('input, textarea, select, [contenteditable]')) return;
    if (event.key === 'Escape') {
      if (!sources.hidden) showSources(false);
      if (!stats.hidden) {
        if (isolated) releaseIsolate();
        else showStats(false);
      }
    } else if (event.key === 'r' || event.key === 'R') {
      event.preventDefault();
      jump();
    } else if (event.key === 'Enter' && !event.target.closest('button, a')) {
      // Enter only jumps when it is not already about to press something.
      event.preventDefault();
      jump();
    }
  });

  let resizing = false;
  window.addEventListener('resize', () => {
    if (resizing) return;
    resizing = true;
    requestAnimationFrame(() => { resizing = false; layout(); });
  });

  if (places.length) {
    const token = ++generation;
    await Promise.all(
      places.map(([text, at]) => open(columnFor(text), text, at, token)));
  } else {
    await jump();
  }

  // Last, so that the passages landing underneath cannot write the screen back
  // out of the URL: both share one debounce, and whoever calls it last wins.
  const screen = readScreen();
  if (screen === 'statistics') showStats(true);
  else if (screen === 'sources') showSources(true);
}

start().catch((error) => {
  grid.textContent = `These texts could not be loaded (${error.message}). `
    + 'Serve this folder over HTTP rather than opening the file directly.';
});
