"""Label passages with Jev, one request per passage, seven questions at a time.

The taxonomy is seven independent yes/no judgements about one passage, which is
exactly the shape of a noul question, so each passage goes out once with all
seven attached. The passage is the expensive half of the request and it is sent
once, which is what makes labelling a 150,000-passage corpus cost a few dollars
rather than a few hundred.

What comes back is a probability per code rather than a letter, so the cut
between "carries this force" and "does not" is made here, in code, and can be
moved without re-reading anything. That is the main thing this has over the
agent pipeline it replaces: it is repeatable, and every passage is judged
against the same seven questions in the same words.

The passage is sent on its own, with no book name and no neighbours. Form
criticism is meant to be blind — telling the model it is reading the Quran
invites it to label what it expects rather than what is on the line.

  python3 classify.py status              what is labelled, what is left
  python3 classify.py run [text ...]      label everything outstanding
  python3 classify.py run --all           relabel, including finished chunks
  python3 classify.py calibrate [n]       compare thresholds against the
                                          labels already on disk
"""
import asyncio
import json
import os
import sys
import time

# MAX_CODES is imported rather than restated: labels.py validates against
# it, so a second copy here would silently truncate labels the validator
# would have accepted. It did, until provenance made five reachable.
from labels import (CODES, MAX_CODES, chunk_count, manifest, order,
                    paths, validate)

try:
    from typesafe_sdk import AsyncTypeSafeClient, Noul, RetryPolicy
except ImportError:
    sys.exit('pip install typesafe-sdk')

MODEL = 'jev-latest'

# Well under the documented 1,200/min, because nothing here is in a hurry and a
# 429 storm costs more time than it saves. Concurrency is set high enough that
# the pace above is what actually binds — at 30 in flight the round trip was
# the limit instead, and the corpus ran at little over half this rate.
PER_MINUTE = 900
CONCURRENCY = 64

# A probability above this counts as the force being present. 0.5 is the honest
# default for a calibrated probability, and it is left there deliberately.
#
# Against a 400-passage sample of the labels the agent pipeline left behind,
# this cut agrees on 46% of passages outright and puts Promise on three times
# as many. Reading the disagreements, most of them are the older pass being
# wrong in the direction KNOWN-ISSUES.md already complains about: "to him that
# soweth righteousness shall be a sure reward" was filed as Doctrine, and so
# was "He calleth you that He may forgive you". Both name a reward. Tuning the
# cut per code until the shares matched would have fitted the new labels to the
# old ones' mistakes. `calibrate` prints the comparison if you want to argue.
THRESHOLD = 0.5

# Told to every question but the last: judge the substance, not the wrapper it
# arrived in. Without this a hadith is narrative by construction — it always
# reports that somebody said something on some occasion — and the six
# collections came out 81 to 96 per cent narrative, which described their
# grammar rather than their content. Provenance is asked separately, so nothing
# is lost by setting it aside here.
SUBSTANCE = (
    'Judge what is being transmitted, not the frame that transmits it. '
    '"Narrated Abu Huraira:", "It was narrated from Ja\u2019far from his '
    'father that", "Thus have I heard", and "the Prophet said" are the frame: '
    'they say who passed this on and who is being quoted. What the passage '
    'does is whatever is said or done inside that frame.')

# One question per code. The wording is taxonomy.md compressed to a single
# judgement each — Jev answers the question as written, so the distinctions
# that guide gets wrong most often (doctrine swallowing everything, threat
# against violence, an imperative buried at the end of an explanation) are
# spelled out in the criteria rather than left to be inferred.
QUESTIONS = {
    'L': Noul(
        instructions='Does this passage instruct, command, prohibit or '
                     'prescribe — telling the hearer to do or not do '
                     'something?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'Imperative force aimed at the hearer: statutes, ritual '
                    'rules, precepts, "thou shalt", "you should", "let him", '
                    '"abandon", "seek". It counts even when the instruction '
                    'arrives at the end of a long explanation, and even when '
                    'it is reported inside a story, so long as it still binds '
                    'the reader.',
            'false': 'The passage is about a law without issuing one, or the '
                     'instruction is purely internal to a story (a king '
                     'telling his servant to fetch water).',
        }),
    'P': Noul(
        instructions='Does this passage offer somebody a specific good outcome '
                     'they will receive — a reward, blessing, paradise, '
                     'forgiveness, prosperity, merit or liberation?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'A named good thing held out to a person or a people, '
                    'conditionally or not: "those who believe shall have '
                    'gardens underneath which rivers flow", "thy sins are '
                    'forgiven thee", "he shall receive a crown of life".',
            'false': 'Something good merely appearing in the passage is not '
                     'this. A general statement that good conduct benefits the '
                     'doer — "whoso doeth good, it is for his own soul" — '
                     'explains how things work. So does a good state described '
                     'as the fruit of a practice: "abandoning desires which '
                     'shake the mind, he finds full comfort". Praise of God, '
                     'or of what God is to the speaker — "the LORD is my '
                     'shepherd" — adores rather than promises. A good event '
                     'announced, such as a birth, only reports.',
        }),
    'T': Noul(
        instructions='Does this passage hold a bad outcome over the hearer — '
                     'warning somebody in its audience what is coming for '
                     'them?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'A curse, punishment, hell or woe aimed at the hearer: '
                    '"in the day that thou eatest thereof thou shalt surely '
                    'die", "woe unto you, for ye shall be cast down".',
            'false': 'Disapproval with no consequence attached — calling '
                     'somebody wicked is not a threat. Harm suffered by the '
                     'speaker or their own people is not a threat either: '
                     'being the victim is not being threatened.',
        }),
    'V': Noul(
        instructions='Does this passage describe an act of physical harm — '
                     'killing, wounding, war, slaughter, torture, execution, '
                     'or a place destroyed?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'Harm actually described, whoever it falls on, including '
                    'the speaker\u2019s own side: "they stoned Stephen", "he '
                    'was wounded for our transgressions", and harm named '
                    'inside a warning: "I will send a fire upon your cities".',
            'false': 'An act of harm has to be described. A bare statement '
                     'that somebody will die or be ruined, with no act named '
                     '\u2014 "thou shalt surely die", "ye shall be cast down" '
                     '\u2014 is not this, however grave it is. Neither is '
                     'violence named only to say that it ends, as in swords '
                     'beaten into plowshares.',
        }),
    'N': Noul(
        instructions='Does this passage recount an event — someone doing or '
                     'saying something at some time?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'An actor and a time at which they acted, including '
                    'speech reported inside a story.',
            'false': 'A general statement about what a person does, or what '
                     'anyone who does X will find, however concrete it '
                     'sounds. "Abandoning desires which shake the mind, he '
                     'finds full comfort" recounts nothing. Neither does a '
                     'condition or a hypothetical: "in the day that thou '
                     'eatest thereof" names no occasion on which anyone ate. '
                     'And the reporting frame is not the event: a teaching '
                     'quoted inside "Narrated Abu Huraira: the Prophet said" '
                     'is a teaching, not a story. An occasion recounted inside '
                     'that frame \u2014 "the Prophet went out to Khaybar and '
                     'fought" \u2014 still is one.',
        }),
    'D': Noul(
        instructions='Does this passage state how something is \u2014 '
                     'explaining, defining, classifying or enumerating, '
                     'rather than commanding, recounting or praising?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'Doctrine set out: the nature of God, self, world, karma, '
                    'sin or salvation; a simile or parable used to explain; '
                    'moral reasoning that stops short of a command. A '
                    'definition or a classification counts too, including a '
                    'bare enumeration of kinds \u2014 "there are five kinds of '
                    'rags: those from a charnel ground, those from a shop" '
                    'states how a thing is divided, and "there is an offense '
                    'entailing suspension for making physical contact" states '
                    'what a rule is. The subject does not have to be lofty.',
            'false': 'It tells the hearer to act, reports an event, or '
                     'praises, without stating anything. Praise of God cast '
                     'as a description of what God is to the speaker \u2014 '
                     '"the LORD is my shepherd" \u2014 adores rather than '
                     'explains. A bare roll of names or places \u2014 a '
                     'genealogy, a census, a list of who begat whom \u2014 '
                     'says nothing about how anything is, and takes nothing. '
                     'Do not reach for this because the passage is religious '
                     'in subject; ask what it is doing, not what it is about.',
        }),
    'W': Noul(
        instructions='Is this passage an act of worship \u2014 does it exist '
                     'to praise, adore, petition, invoke or bless the divine?'
                     + ' ' + SUBSTANCE,
        criteria={
            'true': 'A hymn, psalm, prayer, invocation, doxology or blessing '
                    'formula, or praise offered to God: "thee alone we '
                    'worship; thee alone we ask for help", "the LORD is my '
                    'shepherd; I shall not want", "in the name of Allah, the '
                    'Beneficent, the Merciful".',
            'false': 'A vocative is not worship. Somebody who addresses a '
                     'divine person by name in the course of a conversation, '
                     'a lament, a question or an argument is talking to them, '
                     'not adoring them: "Killing these must breed but anguish, '
                     'Krishna!" is a protest with a name in it. Nor is a fact '
                     'stated about God to a human audience \u2014 "God is '
                     'merciful and just", offered as information, explains. '
                     'Nor is a story that reports somebody praying: "they '
                     'stoned Stephen, calling upon God" recounts an event.',
        }),
    # The odd one out: not what the passage does, but how it reached you.
    'A': Noul(
        instructions='Does this passage say how it was transmitted \u2014 '
                     'naming who narrated or reported it, or the chain it '
                     'came down?',
        criteria={
            'true': 'A chain of narrators or an attribution formula carried '
                    'with the passage: "Narrated Abu Huraira:", "It was '
                    'narrated from Ja\u2019far bin Muhammad from his father '
                    'that", "Thus have I heard", "This hadith is narrated on '
                    'the authority of Zuhri with the same chain of '
                    'transmitters". It counts whether the chain is all the '
                    'passage contains or merely opens it.',
            'false': 'An ordinary narrative that names no transmitter. "And '
                     'Jesus went up into the mountain" and "And they stoned '
                     'Stephen" report events without saying who handed the '
                     'report on. Naming a speaker inside a story \u2014 '
                     '"Moses said unto the LORD" \u2014 is not a chain of '
                     'transmission either.',
        }),
}


def codes_for(answers, threshold):
    """Turn seven probabilities into the code string the label files hold."""
    over = [(answers[code], code) for code in CODES if answers[code] >= threshold]
    over.sort(reverse=True)
    # Back into taxonomy order, so "LT" never comes out as "TL".
    kept = {code for _, code in over[:MAX_CODES]}
    return ''.join(code for code in CODES if code in kept)


class Pace:
    """Let requests through at a fixed long-run rate."""

    def __init__(self, per_minute):
        self.gap = 60 / per_minute
        self.next = time.monotonic()
        self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            now = time.monotonic()
            self.next = max(self.next, now) + self.gap
            delay = self.next - self.gap - now
        if delay > 0:
            await asyncio.sleep(delay)


async def label_one(client, pace, guard, body):
    async with guard:
        await pace.wait()
        result = await client.system_one(body, QUESTIONS, model=MODEL,
                                         retry=RetryPolicy(max_retries=6))
    return {code: result.nouls[code].noul for code in CODES}


async def label_chunk(client, pace, guard, text_id, number, threshold):
    source, target = paths(text_id, number)
    with open(source) as f:
        rows = json.load(f)

    answers = await asyncio.gather(
        *(label_one(client, pace, guard, body) for _, body in rows))

    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w') as f:
        json.dump([codes_for(a, threshold) for a in answers], f,
                  separators=(',', ':'))
    problem = validate(text_id, number)
    if problem:
        # A chunk that does not validate is worse than an absent one, because
        # everything downstream treats a file on disk as done.
        os.remove(target)
    return problem


def outstanding(wanted, redo):
    """Every chunk still to label.

    A relabel clears the old files before it starts rather than overwriting
    them one by one. Overwriting would leave a half-finished run looking
    finished: the chunks it had not reached yet would still hold labels that
    validate, so resuming with a plain `run` would skip them and leave half the
    corpus judged by the old pipeline and half by this one. Removing them first
    makes the filesystem tell the truth, which is the whole premise of how
    labels.py tracks state.
    """
    texts = manifest()
    todo = []
    for text_id in order():
        if wanted and text_id not in wanted:
            continue
        for number in range(chunk_count(texts[text_id])):
            if redo:
                target = paths(text_id, number)[1]
                if os.path.exists(target):
                    os.remove(target)
                todo.append((text_id, number))
            elif validate(text_id, number) is not None:
                todo.append((text_id, number))
    return todo


async def run(wanted, redo, threshold):
    todo = outstanding(wanted, redo)
    if not todo:
        print('nothing to label')
        return
    passages = 0
    for text_id, number in todo:
        with open(paths(text_id, number)[0]) as f:
            passages += len(json.load(f))
    print(f'{len(todo)} chunks, {passages:,} passages, '
          f'about {passages / PER_MINUTE:.0f} minutes', flush=True)

    pace = Pace(PER_MINUTE)
    guard = asyncio.Semaphore(CONCURRENCY)
    done = 0
    async with AsyncTypeSafeClient() as client:
        for text_id, number in todo:
            problem = await label_chunk(client, pace, guard, text_id, number,
                                        threshold)
            done += 1
            note = f'  {problem}' if problem else ''
            print(f'[{done}/{len(todo)}] {text_id}/{number:04d}{note}',
                  flush=True)


def status():
    texts = manifest()
    for text_id in order():
        total = chunk_count(texts[text_id])
        left = sum(1 for n in range(total) if validate(text_id, n) is not None)
        mark = 'done' if not left else f'{left} chunks left'
        print(f'{texts[text_id]["short"]:18} {total - left:3}/{total:<3} chunks  {mark}')


async def calibrate(sample):
    """Ask Jev about passages that already carry labels, and compare.

    Not a measure of who is right — the labels on disk are a small model's
    readings too, and where the two disagree it is often the older one that is
    wrong. What it is for is the cut: a threshold that leaves Jev marking a
    third of the corpus Doctrine where the old pass marked a sixth would make
    the statistics screen incomparable with itself, and that shows up here.
    """
    texts = manifest()
    rows = []
    for text_id in order():
        for number in range(chunk_count(texts[text_id])):
            if validate(text_id, number) is not None:
                continue
            source, target = paths(text_id, number)
            with open(source) as f:
                bodies = [body for _, body in json.load(f)]
            with open(target) as f:
                rows += list(zip(bodies, json.load(f)))
    if not rows:
        sys.exit('nothing is labelled yet to compare against')

    # Spread the sample over the whole labelled corpus rather than taking the
    # front of it: the opening chunk of every book is genealogy and preface,
    # which is not what the rest of the book reads like.
    step = max(1, len(rows) // sample)
    rows = rows[::step][:sample]

    pace = Pace(PER_MINUTE)
    guard = asyncio.Semaphore(CONCURRENCY)
    async with AsyncTypeSafeClient() as client:
        got = await asyncio.gather(
            *(label_one(client, pace, guard, body) for body, _ in rows))

    print(f'{len(rows)} labelled passages, sampled across the corpus\n')
    was = {c: sum(c in old for _, old in rows) / len(rows) for c in CODES}
    print('               ' + '  '.join(f'{c:>5}' for c in CODES))
    print('on disk        ' + '  '.join(f'{was[c]:5.0%}' for c in CODES))
    print()
    print(f'{"cut":>5}  {"agree":>6}  {"blank":>6}   ' +
          '  '.join(f'{c:>5}' for c in CODES))
    for cut in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        mine = [codes_for(a, cut) for a in got]
        agree = sum(set(a) == set(b) for a, (_, b) in zip(mine, rows))
        blank = sum(1 for m in mine if not m)
        share = '  '.join(f'{sum(c in m for m in mine) / len(mine):5.0%}'
                          for c in CODES)
        print(f'{cut:>5}  {agree / len(rows):>6.0%}  {blank / len(rows):>6.0%}   '
              f'{share}')


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'status'
    rest = sys.argv[2:]
    if command == 'status':
        status()
    elif command == 'run':
        redo = '--all' in rest
        asyncio.run(run([a for a in rest if not a.startswith('-')], redo,
                        THRESHOLD))
    elif command == 'calibrate':
        asyncio.run(calibrate(int(rest[0]) if rest else 200))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
