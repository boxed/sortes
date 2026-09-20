"""The label queue: what still needs classifying, and whether what came back is sound.

Labels live at data/<text>/labels/NNNN.json, one file per text chunk and the
same 400 paragraphs, holding one code string per paragraph ("LT", "N", "" for
none). A chunk file existing and validating means that chunk is done — there is
no separate state to get out of step with the filesystem.

  python3 labels.py status              what is done, what is left
  python3 labels.py next [n]            the next n chunks to hand to workers
  python3 labels.py prepare <text> <n>  split one chunk into worker input parts
  python3 labels.py assemble <text> <n> join the parts a worker wrote
  python3 labels.py check <text> <n>    validate one chunk a worker just wrote
  python3 labels.py audit [n]           finished chunks ranked by suspect blanks
"""
import json
import os
import re
import sys

from common import DATA

CODES = {
    'L': 'Law',
    'P': 'Promise',
    'T': 'Threat',
    'N': 'Narrative',
    'D': 'Doctrine',
    'W': 'Worship',
    'V': 'Violence',
    'A': 'Provenance',
}

# Provenance is the odd one out and is kept apart from the other seven. It does
# not say what a passage does; it says how the passage reached you — the chain
# of narrators on a hadith, the "Thus have I heard" that opens a sutta. Nearly
# every hadith carries one, so counting the frame alongside the substance made
# the six collections look like almost nothing but narrative. The other seven
# now judge what is being transmitted, and this records that a transmission is
# being claimed at all.
FRAME = 'A'

# The threat/violence split means a warned-of atrocity in a story can
# legitimately carry four — narrative, threat, violence, and the law it
# enforces — and a hadith reporting one carries provenance on top.
MAX_CODES = 5

# Blank is a real answer, and some registers are mostly blank by right: the
# Chronicler's levite rosters, Ezra's census, a hadith carrying an isnad and no
# matn. So the guard does not count blanks — it counts blanks on passages that
# plainly assert something, which is the shape of a classifier that skipped
# work rather than a text that carries no form. suspect() below decides which
# is which, and it is a heuristic, not an oracle.
#
# Set where wholesale failure lives rather than where the cleanest chunk sits.
# Real failures ran past half: the Vinaya's taxonomies came back near 50% when
# the Doctrine question could not see them. The list-heaviest chunks in the
# corpus that are genuinely list-heavy — Joshua's tally of defeated kings at
# old-testament/0015, and 1 Chronicles' genealogies at old-testament/0026 —
# sit at 29% and 36%, and "The king of Jericho, one; the king of Ai, one" is
# correctly blank however it is counted. Tightening the number below those
# would reject good work to catch nothing.
MAX_UNREAD = 0.45


def manifest():
    with open(os.path.join(DATA, 'manifest.json')) as f:
        return {t['id']: t for t in json.load(f)['texts']}


def order():
    """Every text, smallest first, so whole texts finish early rather than
    everything finishing at once at the end."""
    texts = manifest()
    return sorted(texts, key=lambda text_id: texts[text_id]['count'])


def chunk_count(text):
    return -(-text['count'] // text['chunk'])


def paths(text_id, number):
    name = '%04d.json' % number
    return (os.path.join(DATA, text_id, name),
            os.path.join(DATA, text_id, 'labels', name))


WORK = os.path.join(os.path.dirname(DATA), 'tmp', 'work')

# Shown a long file, the model finds a rhythm and labels to it instead of
# reading each line — at 400 passages it put exactly two codes on 338 of them.
# Small parts fix that. One worker still does several, so the agent scaffold
# (most of the cost) is paid once rather than once per part.
PART = 100


def part_paths(text_id, number, index):
    stem = os.path.join(WORK, f'{text_id}-{number:04d}.p{index}')
    return stem + '.txt', stem + '.json'


def prepare(text_id, number):
    """Split one chunk into `index<TAB>text` part files a worker can label."""
    source, _ = paths(text_id, number)
    with open(source) as f:
        rows = json.load(f)
    os.makedirs(WORK, exist_ok=True)

    written = []
    for index, start in enumerate(range(0, len(rows), PART)):
        text_path, _ = part_paths(text_id, number, index)
        with open(text_path, 'w') as f:
            for offset, (_, body) in enumerate(rows[start:start + PART]):
                f.write(f'{offset}\t{body.replace(chr(10), " / ")}\n')
        written.append((text_path, min(PART, len(rows) - start)))
    return written


def assemble(text_id, number):
    """Join a worker's part files into the chunk's label file."""
    source, target = paths(text_id, number)
    with open(source) as f:
        total = len(json.load(f))

    codes = []
    for index in range(-(-total // PART)):
        _, part = part_paths(text_id, number, index)
        if not os.path.exists(part):
            return f'part {index} missing'
        with open(part) as f:
            codes += json.load(f)

    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w') as f:
        json.dump(codes, f, separators=(',', ':'))
    problem = validate(text_id, number)
    if problem:
        os.remove(target)
    return problem


def validate(text_id, number):
    """Return an error string, or None when the chunk's labels are sound."""
    source, labels = paths(text_id, number)
    if not os.path.exists(labels):
        return 'missing'
    try:
        with open(labels) as f:
            got = json.load(f)
    except json.JSONDecodeError as error:
        return f'not valid JSON: {error}'
    with open(source) as f:
        expected = len(json.load(f))
    if not isinstance(got, list):
        return 'not a list'
    if len(got) != expected:
        return f'{len(got)} labels for {expected} passages'
    for i, entry in enumerate(got):
        if not isinstance(entry, str):
            return f'index {i}: {entry!r} is not a string'
        if len(entry) > MAX_CODES:
            return f'index {i}: {entry!r} has more than {MAX_CODES} codes'
        if len(set(entry)) != len(entry):
            return f'index {i}: {entry!r} repeats a code'
        for code in entry:
            if code not in CODES:
                return f'index {i}: {code!r} is not a code'

    with open(source) as f:
        rows = json.load(f)
    missed = sum(1 for entry, row in zip(got, rows)
                 if not entry and suspect(row[1])) / len(got)
    if missed > MAX_UNREAD:
        return (f'{missed:.0%} of passages assert something and came back '
                f'blank — the chunk was not read')
    return None


# A worker that stops reading does not always stop labelling — sometimes it just
# leaves the hard lines blank. Most blanks are legitimate: setting stubs, bare
# replies, and the Pali elision fragments that stand in for a repeated formula.
# A blank that is a full sentence with no elision mark is none of those.
MIN_ASSERTION = 40

# A roll of names — the Chronicler's levites, Numbers' tribal heads — is a list
# however long it runs, and carries none of the seven. So is a hadith that
# records only who passed it on.
ROSTER = re.compile(r'^(And )?(of|the sons of|the children of|Of the)\b',
                    re.I)
ISNAD = re.compile(r'^(This|Another|There is another) (hadith|chain)\b|'
                   r'^It has been (narrated|transmitted|reported) on the '
                   r'authority of .{0,60}(chain|same|similar)', re.I)

# The rest of the rolls do not open with a tell, they just read like one:
# "And at Bilhah, and at Ezem, and at Tolad", "Shallum his son, Mibsam his
# son", "The king of Jericho, one; the king of Ai, one". What marks them is
# shape rather than vocabulary — a run of short fragments, most carrying a
# name. Counting capitals instead was tried and could not tell those from "And
# Moses said unto the LORD, See, thou sayest unto me", which the King James
# capitalises four times in thirteen words.
FRAGMENT = re.compile(r'[,;]|\band\b')
WORD = re.compile(r"[A-Za-z][A-Za-z'\u2019-]*")
LIST_RUN = 3        # fragments before a sentence starts to read as a list
LIST_SHARE = 0.6    # how many of them have to look like an entry
ENTRY_WORDS = 4     # an entry is short; a clause is not


def roster(body):
    """True when a passage is a roll of names rather than a statement."""
    parts = [FRAGMENT.split(body)[0]] + FRAGMENT.split(body)[1:]
    parts = [p for p in (p.strip() for p in parts) if p]
    if len(parts) < LIST_RUN:
        return False
    # The passage's own first word is capitalised for being first, so a name
    # has to turn up somewhere past it for the fragment to count as an entry.
    opening = WORD.search(body)
    opening = opening.group() if opening else ''
    entries = 0
    for i, part in enumerate(parts):
        words = WORD.findall(part)
        if not words or len(words) > ENTRY_WORDS:
            continue
        named = [w for w in words if w[0].isupper()]
        if i == 0 and named and named[0] == opening:
            named = named[1:]
        if named:
            entries += 1
    return entries / len(parts) >= LIST_SHARE


def unexplained(text_id, number):
    """Blanks that look like a full sentence the worker simply skipped."""
    source, labels = paths(text_id, number)
    if validate(text_id, number) is not None:
        return None
    with open(source) as f:
        rows = json.load(f)
    with open(labels) as f:
        got = json.load(f)
    return [i for i, code in enumerate(got)
            if not code and suspect(rows[i][1])]


def suspect(body):
    """True when a blank has no structural excuse — it asserts something."""
    body = body.strip()
    if len(body) < MIN_ASSERTION:
        return False          # setting stub, bare reply, speaker tag
    if ROSTER.match(body) or roster(body):
        return False          # a roll of names asserts nothing about anything
    if ISNAD.match(body):
        return False          # a chain of transmitters with no hadith on it
    if '\u2026' in body or '...' in body:
        return False          # peyyala elision standing in for a formula
    if body.rstrip('\u201d\'"').endswith('?'):
        return False          # a question asserts nothing; blank by convention
    if body.startswith('(') and body.endswith(')'):
        return False          # editorial note: "(Tell in full as in ...)"
    if body.endswith('are complete.') or body.endswith('is complete.'):
        return False          # colophon closing a division
    if ('that is what I heard' in body
            or body.startswith('Thus have I heard')
            or body.startswith('The Buddha spoke this matter')):
        return False          # the formulas framing every Itivuttaka sutta
    return True


def audit(limit):
    """Rank finished chunks by how many blanks have no structural excuse."""
    texts = manifest()
    rows = []
    for text_id in order():
        for number in range(chunk_count(texts[text_id])):
            missed = unexplained(text_id, number)
            if missed:
                rows.append((len(missed), text_id, number))
    rows.sort(reverse=True)
    for count, text_id, number in rows[:limit]:
        flag = ' <-- worth a re-run' if count >= 25 else ''
        print(f'{text_id}/{number:04d}  {count:3} unexplained blanks{flag}')
    if not rows:
        print('no chunk has an unexplained blank')


def pending():
    """Every chunk still to do, in the order they should be worked."""
    texts = manifest()
    todo = []
    for text_id in order():
        text = texts[text_id]
        for number in range(chunk_count(text)):
            if validate(text_id, number) is not None:
                todo.append((text_id, number))
    return todo


def status():
    texts = manifest()
    left = pending()
    outstanding = {}
    for text_id, _ in left:
        outstanding[text_id] = outstanding.get(text_id, 0) + 1

    done_all = 0
    total_all = 0
    for text_id in order():
        text = texts[text_id]
        total = chunk_count(text)
        done = total - outstanding.get(text_id, 0)
        done_all += done
        total_all += total
        bar = '#' * round(20 * done / total) + '.' * (20 - round(20 * done / total))
        print(f'{text["short"]:16} {bar} {done:3}/{total:<3} chunks'
              f'  {min(done * text["chunk"], text["count"]):>6,}/{text["count"]:,}')
    print(f'\n{done_all}/{total_all} chunks classified '
          f'({100 * done_all / total_all:.1f}%)')
    return done_all, total_all


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if command == 'status':
        status()
    elif command == 'next':
        want = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        for text_id, number in pending()[:want]:
            print(f'{text_id} {number:04d}')
    elif command == 'prepare':
        for path, count in prepare(sys.argv[2], int(sys.argv[3])):
            print(f'{path} ({count} passages)')
    elif command == 'assemble':
        problem = assemble(sys.argv[2], int(sys.argv[3]))
        print(problem or 'ok')
        sys.exit(1 if problem else 0)
    elif command == 'audit':
        audit(int(sys.argv[2]) if len(sys.argv) > 2 else 15)
    elif command == 'check':
        problem = validate(sys.argv[2], int(sys.argv[3]))
        print(problem or 'ok')
        sys.exit(1 if problem else 0)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
