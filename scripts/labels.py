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
}

# Seven codes, and the threat/violence split means a warned-of atrocity in a
# story can legitimately carry four: narrative, threat, violence, and the law
# it enforces.
MAX_CODES = 4

# A worker that loses the thread stops labelling rather than labelling badly.
# Genuine registers (Ezra's census rolls) run to about a quarter empty; past
# this it is the worker, not the text, and the chunk goes back in the queue.
MAX_EMPTY = 0.4

# Smallest first, so whole texts finish early rather than everything finishing
# at once at the end.
ORDER = ['bhagavad-gita', 'quran', 'book-of-mormon', 'new-testament',
         'old-testament', 'tripitaka']


def manifest():
    with open(os.path.join(DATA, 'manifest.json')) as f:
        return {t['id']: t for t in json.load(f)['texts']}


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

    empty = sum(1 for entry in got if not entry) / len(got)
    if empty > MAX_EMPTY:
        return f'{empty:.0%} of passages left unlabelled — worker lost the thread'
    return None


# A worker that stops reading does not always stop labelling — sometimes it just
# leaves the hard lines blank. Most blanks are legitimate: setting stubs, bare
# replies, and the Pali elision fragments that stand in for a repeated formula.
# A blank that is a full sentence with no elision mark is none of those.
MIN_ASSERTION = 40


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
    for text_id in ORDER:
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
    for text_id in ORDER:
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
    for text_id in ORDER:
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
