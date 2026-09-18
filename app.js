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
const stats = document.getElementById('stats');
const statsToggle = document.getElementById('stats-toggle');

const chunks = new Map();

// Four of the six codes are shown as rules, in fixed slots so position — not
// colour alone — says which is which. Narrative and worship are named in the
// column head instead: narrative is the commonest kind in four of the six
// books, so marking it would put a rule on most of the page and leave the
// others nothing to stand out against.
const FORCES = [
  ['L', 'Law'], ['P', 'Promise'], ['T', 'Threat'], ['V', 'Violence'],
  ['D', 'Doctrine'],
];
const MODES = { N: 'narrative', W: 'worship' };
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
  book.append(document.createTextNode(text.short));
  const form = document.createElement('span');
  form.className = 'head-form';
  book.append(form);
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
    text, root, reference, form, stream, page, edge,
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

async function render(column, from, to) {
  const { rows, labelled } = await slice(column.text, from, to);
  column.page.replaceChildren(...fill(from, rows));
  column.shown = { from, to, refs: rows.map((row) => row[0]) };
  column.edge.hidden = to < column.text.count;
  column.root.dataset.labelled = labelled ? 'yes' : 'no';
}

/** Pull in more paragraphs when the reader nears either end of the column. */
async function extend(column, end) {
  const { text } = column;
  const region = column.shown;
  const { from, to } = region;

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
  D: '--doctrine', W: '--worship',
};
// Bit order must match BITS in stats.py; narrative takes the seventh bit.
const BITS = ['L', 'P', 'T', 'V', 'D', 'W', 'N'];
// Which colour a passage takes when nothing is isolated and it carries several:
// the sharpest rhetorical force wins, and narrative is ground.
const OVER = ['T', 'V', 'P', 'L', 'W', 'D'];

let statsLoaded = false;
const drawn = new Map();

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

function drawMap(canvas, strip) {
  // Aim for a square, and stop widening at the column — past that the map
  // grows downwards, which in practice is only the Pali Canon. A short book
  // then has fewer, larger pixels rather than a two-pixel smear: every map
  // fills its column, and passage count shows in the grain instead of in the
  // area. It also gives the Gita hover targets you can actually hit.
  const cap = Math.max(1, Math.floor(canvas.parentElement.clientWidth));
  const width = Math.min(cap, Math.ceil(Math.sqrt(strip.length)));
  const rows = Math.ceil(strip.length / width);
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

  for (let i = 0; i < strip.length; i += 1) {
    const mask = strip[i];
    const at = i * 4;
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
    const code = OVER.find((c) => mask & bit[c]);
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

async function buildStats() {
  if (statsLoaded) return;
  statsLoaded = true;
  const body = document.getElementById('stats-body');
  const maps = [];
  const stats = await fetch('data/stats.json').then((r) => r.json());
  const codes = Object.entries(stats.codes);

  // One column per book, held all the way down: the maps line up with the
  // bars beneath them, so a row compares six books on one kind and a column
  // reads one book's whole profile. Every bar is on the same scale.
  const widest = Math.max(...stats.texts.flatMap((t) => Object.values(t.share)));
  body.style.setProperty('--books', stats.texts.length);

  const corner = document.createElement('div');
  corner.className = 'corner';
  body.append(corner);

  for (const row of stats.texts) {
    const head = document.createElement('div');
    head.className = 'book';
    const name = document.createElement('b');
    name.textContent = row.short;
    const count = document.createElement('span');
    count.textContent = `${row.count.toLocaleString('en')} passages`;
    head.append(name, count);

    const canvas = document.createElement('canvas');
    canvas.className = 'map';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label',
      `${row.short}: every passage in reading order, marked where it carries `
      + 'a law, a promise or a threat.');
    head.append(canvas);
    body.append(head);

    wirePeek(canvas, texts.find((t) => t.id === row.id));
    maps.push(fetch(`data/map/${row.id}.txt`)
      .then((r) => r.text())
      .then((text) => { drawn.set(canvas, masks(text)); })
      .catch(() => canvas.remove()));
  }

  for (const [code, name] of codes) {
    const label = document.createElement('button');
    label.type = 'button';
    label.className = 'kind';
    label.dataset.code = code;
    label.textContent = name;
    label.setAttribute('aria-label', `Show only ${name.toLowerCase()}`);
    body.append(label);

    for (const row of stats.texts) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.code = code;
      const bar = document.createElement('i');
      bar.className = 'share';
      if (code in PIXELS) bar.dataset.code = code;
      bar.style.width =
        `calc((100% - var(--figure)) * ${(row.share[code] / widest).toFixed(4)})`;
      bar.setAttribute('aria-hidden', 'true');
      const figure = document.createElement('b');
      figure.textContent = `${Math.round(row.share[code] * 100)}%`;
      cell.append(bar, figure);
      cell.setAttribute('aria-label', `${row.short}, ${name}, ` +
        `${Math.round(row.share[code] * 100)} percent`);
      body.append(cell);
    }
  }

  // The unmarked remainder, so the shares can be read against something.
  const rest = document.createElement('button');
  rest.type = 'button';
  rest.className = 'kind quiet';
  rest.dataset.code = 'none';
  rest.textContent = 'None of these';
  rest.setAttribute('aria-label', 'Show only passages carrying none of these');
  body.append(rest);
  for (const row of stats.texts) {
    const cell = document.createElement('div');
    cell.className = 'cell quiet';
    cell.dataset.code = 'none';
    const figure = document.createElement('b');
    figure.textContent = `${Math.round(row.blank * 100)}%`;
    cell.append(figure);
    body.append(cell);
  }

  wireIsolate(body);

  // The canvases have to be in the document before one can be sized to its
  // column, so the drawing waits for layout.
  await Promise.all(maps);
  redrawMaps();

  const short = stats.texts.filter((t) => t.labelled < t.count);
  document.getElementById('stats-note').textContent = short.length
    ? `${short.map((t) => t.short).join(' and ')} still being labelled; `
      + 'its figures will move.'
    : 'Every passage in all six books is labelled. The labels are a model\u2019s '
      + 'reading of the form, and wrong often enough to be worth checking.';
}

function redrawMaps() {
  for (const [canvas, strip] of drawn) drawMap(canvas, strip);
}

/** A pixel is a passage — hovering one names it and reads it. */
function wirePeek(canvas, text) {
  const peek = document.getElementById('peek');

  canvas.addEventListener('pointermove', async (event) => {
    const box = canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX - box.left) / box.width * canvas.width);
    const y = Math.floor((event.clientY - box.top) / box.height * canvas.height);
    const index = y * canvas.width + x;
    if (index < 0 || index >= text.count) { peek.hidden = true; return; }

    // Claim this hover, so a slow chunk fetch cannot overwrite a later one.
    const token = {};
    canvas.dataset.want = index;
    peek.dataset.token = index;

    const rows = await chunkAt(text, index);
    if (peek.dataset.token !== String(index)) return;
    const [reference, body] = rows[index % text.chunk];

    peek.hidden = false;
    peek.querySelector('.peek-ref').textContent = `${text.short} · ${reference}`;
    peek.querySelector('.peek-body').textContent = body.replace(/\n/g, ' ');

    // Keep the card on screen rather than letting it run off the right edge.
    const width = peek.offsetWidth || 320;
    const left = Math.min(event.clientX + 16, window.innerWidth - width - 12);
    peek.style.left = `${Math.max(12, left)}px`;
    peek.style.top = `${Math.min(event.clientY + 16,
      window.innerHeight - peek.offsetHeight - 12)}px`;
  });

  canvas.addEventListener('pointerleave', () => { peek.hidden = true; });
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
  if (visible) buildStats();
  stats.hidden = !visible;
  statsToggle.setAttribute('aria-expanded', String(visible));
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
      places.map(([text, at]) => open(columns.get(text.id), at, token)));
  } else {
    await jump();
  }
}

start().catch((error) => {
  grid.textContent = `These texts could not be loaded (${error.message}). `
    + 'Serve this folder over HTTP rather than opening the file directly.';
});
