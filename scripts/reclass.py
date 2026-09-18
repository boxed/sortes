"""Re-judge the passages that the threat/violence split affects.

`T` was doing two jobs: warning a hearer, and describing harm. Splitting out
`V` means every passage that might sit on either side has to be looked at
again — but only those, which is a twentieth of the corpus rather than all of
it. Two sources of candidates:

  * everything currently labelled `T`, since some of it is description, and
  * everything whose text carries violence vocabulary, since narrated harm was
    mostly never labelled `T` at all and would otherwise stay invisible.

The second is a keyword sweep and so has false negatives — violence described
without any of these words is missed. It is a floor, not a guarantee.

  python3 reclass.py prepare        write the work parts and their index
  python3 reclass.py assemble <n>   merge one job's answers back
  python3 reclass.py status         how many jobs are done
"""
import json
import os
import re
import sys

from common import DATA
from labels import (CODES, MAX_CODES, ORDER, WORK, chunk_count, manifest,
                    paths, validate)

VIOLENCE = re.compile(
    r'\b(slew|slay|slain|smote|smite|smitten|kill|killed|killing|murder\w*|'
    r'sword|spear|arrow|blood|bloodshed|slaughter\w*|massacre|stoned|stoning|'
    r'burnt|burned|destroy\w*|war|wars|battle|beat|beaten|scourge\w*|'
    r'crucif\w+|behead\w*|strangle\w*|wound\w*|perish\w*|devour\w*|'
    r'famine|plague|sacrifice\w*|captive\w*|slave\w*)\b', re.I)

PART = 100
PARTS_PER_JOB = 4
INDEX = os.path.join(WORK, 'reclass-index.json')


def candidates():
    """Every passage the split could move, with where it lives."""
    texts = manifest()
    found = []
    for text_id in ORDER:
        text = texts[text_id]
        for number in range(chunk_count(text)):
            source, labels = paths(text_id, number)
            if validate(text_id, number) is not None:
                continue
            with open(source) as f:
                rows = json.load(f)
            with open(labels) as f:
                codes = json.load(f)
            for offset, ((_, body), code) in enumerate(zip(rows, codes)):
                if 'T' in code or VIOLENCE.search(body):
                    found.append({
                        'text': text_id, 'chunk': number, 'offset': offset,
                        'codes': code, 'body': body.replace('\n', ' / '),
                    })
    return found


def prepare():
    os.makedirs(WORK, exist_ok=True)
    rows = candidates()
    jobs = -(-len(rows) // (PART * PARTS_PER_JOB))
    index = []

    for job in range(jobs):
        block = rows[job * PART * PARTS_PER_JOB:(job + 1) * PART * PARTS_PER_JOB]
        for part in range(-(-len(block) // PART)):
            lines = block[part * PART:(part + 1) * PART]
            path = os.path.join(WORK, f'reclass-{job:03d}.p{part}.txt')
            with open(path, 'w') as f:
                for n, row in enumerate(lines):
                    f.write(f'{n}\t{row["codes"] or "-"}\t{row["body"]}\n')
        index.append(block)

    with open(INDEX, 'w') as f:
        json.dump(index, f)
    print(f'{len(rows):,} passages to re-judge, {jobs} jobs of up to 400')
    return jobs


def load_index():
    with open(INDEX) as f:
        return json.load(f)


def assemble(job):
    """Apply one job's answers to the label files they came from."""
    index = load_index()
    if job >= len(index):
        return f'no job {job}'
    block = index[job]

    got = []
    for part in range(-(-len(block) // PART)):
        path = os.path.join(WORK, f'reclass-{job:03d}.p{part}.json')
        if not os.path.exists(path):
            return f'part {part} missing'
        with open(path) as f:
            got += json.load(f)
    if len(got) != len(block):
        return f'{len(got)} answers for {len(block)} passages'

    for i, entry in enumerate(got):
        if not isinstance(entry, str):
            return f'index {i}: {entry!r} is not a string'
        if len(entry) > MAX_CODES or len(set(entry)) != len(entry):
            return f'index {i}: {entry!r} is not a valid code set'
        for code in entry:
            if code not in CODES:
                return f'index {i}: {code!r} is not a code'

    # Group by chunk so each label file is rewritten once.
    touched = {}
    for row, entry in zip(block, got):
        touched.setdefault((row['text'], row['chunk']), []).append(
            (row['offset'], entry))
    for (text_id, number), edits in touched.items():
        _, path = paths(text_id, number)
        with open(path) as f:
            codes = json.load(f)
        for offset, entry in edits:
            codes[offset] = entry
        with open(path, 'w') as f:
            json.dump(codes, f, separators=(',', ':'))
        problem = validate(text_id, number)
        if problem:
            return f'{text_id}/{number:04d} broke: {problem}'
    return None


def status():
    index = load_index()
    done = 0
    for job in range(len(index)):
        parts = -(-len(index[job]) // PART)
        if all(os.path.exists(os.path.join(WORK, f'reclass-{job:03d}.p{p}.json'))
               for p in range(parts)):
            done += 1
    print(f'{done}/{len(index)} reclassification jobs answered')
    return done, len(index)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if command == 'prepare':
        prepare()
    elif command == 'assemble':
        problem = assemble(int(sys.argv[2]))
        print(problem or 'ok')
        sys.exit(1 if problem else 0)
    elif command == 'status':
        status()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
