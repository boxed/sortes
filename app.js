/* Sortes — six scriptures side by side, each fallen open at a random passage.
 *
 * Texts are built into data/<id>/NNNN.json, each holding `chunk` paragraphs as
 * [reference, text] pairs, so opening the middle of a 56,000-paragraph canon
 * downloads a couple of hundred kilobytes rather than seventeen megabytes.
 *
 * Every book is a column with its own scroll. Whatever paragraph crosses that
 * column's reading line is the lit one, and the column fades away from it. The
 * columns are otherwise independent; the only thing they share is the button.
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

const chunks = new Map();
const columns = new Map();   // text id -> column state, one per text

let texts = [];
let byId = {};
let mode = 'all';            // 'all' for the polyglot, or a single text id
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

/** Paragraphs [from, to) of a text, fetching whichever chunks that spans. */
async function slice(text, from, to) {
  const first = Math.floor(from / text.chunk);
  const last = Math.floor((to - 1) / text.chunk);
  const wanted = [];
  for (let n = first; n <= last; n += 1) wanted.push(chunkAt(text, n * text.chunk));
  const loaded = await Promise.all(wanted);
  const base = first * text.chunk;
  return loaded.flat().slice(from - base, to - base);
}

/* ---- columns -------------------------------------------------------- */

function buildColumn(text) {
  const root = document.createElement('section');
  root.className = 'column';
  root.dataset.text = text.id;

  // The running head: which book, and where in it you are. In the polyglot it
  // sits above the column; given room it hangs in the margin at the reading
  // line, beside the passage it names.
  const head = document.createElement('header');
  head.className = 'head';
  const book = document.createElement('h2');
  book.className = 'head-book';
  book.textContent = text.short;
  const reference = document.createElement('p');
  reference.className = 'head-ref';
  head.append(book, reference);

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
    text, root, reference, stream, page, edge,
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

function paragraph(index, body) {
  const p = document.createElement('p');
  p.className = 'para';
  p.dataset.index = index;
  p.textContent = body;
  return p;
}

function fill(from, paragraphs) {
  return paragraphs.map((pair, i) => paragraph(from + i, pair[1]));
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

async function render(column, from, to) {
  const paragraphs = await slice(column.text, from, to);
  column.page.replaceChildren(...fill(from, paragraphs));
  column.shown = { from, to, refs: paragraphs.map((pair) => pair[0]) };
  column.edge.hidden = to < column.text.count;
}

/** Pull in more paragraphs when the reader nears either end of the column. */
async function extend(column, end) {
  const { text } = column;
  const region = column.shown;
  const { from, to } = region;

  if (end === 'start') {
    if (from === 0) return;
    const start = Math.max(0, from - EXTEND);
    const paragraphs = await slice(text, start, from);
    // A jump may have replaced this column while we were fetching.
    if (column.shown !== region || region.from !== from) return;
    const first = column.page.firstElementChild;
    const before = first.offsetTop;
    column.page.prepend(...fill(start, paragraphs));
    column.stream.scrollTop += first.offsetTop - before;
    region.from = start;
    region.refs.unshift(...paragraphs.map((pair) => pair[0]));
  } else {
    if (to >= text.count) return;
    const stop = Math.min(text.count, to + EXTEND);
    const paragraphs = await slice(text, to, stop);
    if (column.shown !== region || region.to !== to) return;
    column.page.append(...fill(to, paragraphs));
    region.to = stop;
    region.refs.push(...paragraphs.map((pair) => pair[0]));
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

async function open(column, index, token) {
  column.settling = true;
  column.lit = null;

  const { text } = column;
  const from = Math.max(0, index - WINDOW);
  await render(column, from, Math.min(text.count, index + WINDOW + 1));
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

async function jump() {
  const token = ++generation;
  await Promise.all(onScreen().map(async (column) => {
    const index = await choose(column.text);
    if (token === generation) await open(column, index, token);
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

function buildNav() {
  const options = [{ id: 'all', short: 'All six' }, ...texts];
  booksNav.replaceChildren(...options.map((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = option.short;
    button.setAttribute('aria-pressed', String(option.id === mode));
    button.addEventListener('click', () => {
      for (const other of booksNav.children) {
        other.setAttribute('aria-pressed', String(other === button));
      }
      mode = option.id;
      show();
      jump();
    });
    return button;
  }));
}

function buildSources() {
  const list = document.getElementById('sources-list');
  for (const text of texts) {
    const dt = document.createElement('dt');
    dt.textContent = `${text.title} — ${text.subtitle}`;
    const dd = document.createElement('dd');
    dd.textContent = `${text.count.toLocaleString('en')} passages. `
      + `${text.source}. ${text.license}.`;
    list.append(dt, dd);
  }
}

function showSources(visible) {
  sources.hidden = !visible;
  sourcesToggle.setAttribute('aria-expanded', String(visible));
}

/* ---- linking -------------------------------------------------------- */

let pending = 0;

/** Keep the URL pointing at the spread on screen, so it can be linked to. */
function rememberPlaces() {
  clearTimeout(pending);
  pending = setTimeout(() => {
    const places = onScreen()
      .filter((column) => column.lit)
      .map((column) => `${column.text.id}:${column.lit.dataset.index}`);
    if (places.length) history.replaceState(null, '', `#${places.join(',')}`);
  }, 300);
}

function readPlaces() {
  const found = [];
  for (const part of decodeURIComponent(location.hash.slice(1)).split(',')) {
    const [id, at] = part.split(':');
    if (byId[id] && /^\d+$/.test(at || '')) {
      found.push([byId[id], Math.min(Number(at), byId[id].count - 1)]);
    }
  }
  return found;
}

/* ---- start ---------------------------------------------------------- */

async function start() {
  // Land on the passage, not near it: measure only once the real face is in.
  await document.fonts.ready.catch(() => {});
  const manifest = await fetch('data/manifest.json').then((r) => r.json());
  texts = manifest.texts;
  byId = Object.fromEntries(texts.map((t) => [t.id, t]));
  for (const text of texts) columns.set(text.id, buildColumn(text));

  const places = readPlaces();
  if (places.length === 1) mode = places[0][0].id;

  buildNav();
  buildSources();
  show();

  jumpButton.addEventListener('click', jump);
  sourcesToggle.addEventListener('click', () => showSources(sources.hidden));
  document.getElementById('sources-close').addEventListener('click',
    () => { showSources(false); sourcesToggle.focus(); });

  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.target.closest('input, textarea, select, [contenteditable]')) return;
    if (event.key === 'Escape') {
      if (!sources.hidden) showSources(false);
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
      places.map(([text, at]) => open(columns.get(text.id), at, token)));
  } else {
    await jump();
  }
}

start().catch((error) => {
  grid.textContent = `These texts could not be loaded (${error.message}). `
    + 'Serve this folder over HTTP rather than opening the file directly.';
});
