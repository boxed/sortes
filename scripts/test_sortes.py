"""Tests for the parts of this that have broken before.

    python3 scripts/test_sortes.py            all of it
    python3 scripts/test_sortes.py Contracts  one class

No dependencies: the app has none and neither does this. Run it after changing
a code, a reference format, or anything stats.json carries.

What it covers is the joins — the places where two files have to agree and
nothing checks that they do. Every bug worth writing a test for in this project
so far has lived in one: a constant declared twice and then changed once, a bit
order shared between Python and JavaScript, a field the page reads and the
script stopped writing, a text left on disk after the manifest forgot it.

What it does not cover is whether a label is *right*. That is a judgement about
a passage of scripture and no assertion settles it; `classify.py calibrate` and
reading the output are the tools for that.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common
import labels
import stats
from common import DATA, ROOT

# classify.py needs the TypeSafe SDK and exits at import without it. Everything
# else here runs on the standard library, so the suite is still worth running
# outside the venv; the handful of tests that need it say why they skipped.
try:
    import classify
except SystemExit:
    classify = None

needs_sdk = unittest.skipIf(
    classify is None, 'the TypeSafe SDK is not installed — '
    'run .venv/bin/python scripts/test_sortes.py for these')

APP = os.path.join(ROOT, 'app.js')


def app_source():
    with open(APP) as f:
        return f.read()


def scratch_dir(case):
    """A throwaway directory under the project, cleaned up after the test."""
    path = os.path.join(ROOT, 'tmp', 'test-scratch', case.id().rsplit('.', 1)[-1])
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)
    case.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path


class Contracts(unittest.TestCase):
    """Constants that live in two files and have to agree."""

    @needs_sdk
    def test_max_codes_is_not_restated(self):
        # classify.py used to keep its own copy. labels.py was raised to five
        # for provenance and this one was not, so 5,912 hadith were truncated
        # to four codes by a cap the validator would have accepted.
        self.assertIs(classify.MAX_CODES, labels.MAX_CODES)

    @needs_sdk
    def test_every_code_has_a_question(self):
        self.assertEqual(set(classify.QUESTIONS), set(labels.CODES))

    def test_bit_order_matches_the_page(self):
        # stats.py packs a passage into one byte and app.js unpacks it. If the
        # orders drift, every map is wrong and nothing errors.
        found = re.search(r'const BITS = \[(.*?)\];', app_source(), re.S)
        self.assertIsNotNone(found, 'app.js has no BITS array')
        page = re.findall(r"'([A-Z])'", found.group(1))
        self.assertEqual(page, list(stats.BITS) + ['N'])

    def test_byte_is_wide_enough(self):
        # strip() writes two hex digits per passage.
        self.assertLessEqual(len(stats.BITS) + 1, 8)

    def test_frame_code_matches_the_page(self):
        found = re.search(r"const FRAME = '([A-Z])';", app_source())
        self.assertIsNotNone(found, 'app.js has no FRAME')
        self.assertEqual(found.group(1), labels.FRAME)

    def test_every_code_reaches_the_reader(self):
        # A code is either a rule in the margin or named in the column head.
        # Adding one and surfacing it nowhere is the easy mistake.
        source = app_source()
        rules = set(re.findall(r"\['([A-Z])', '[A-Za-z]+'\]", source))
        named = set(re.findall(r"(\w): '[a-z]+'",
                              re.search(r'const MODES = \{(.*?)\};',
                                        source).group(1)))
        self.assertEqual(rules | named, set(labels.CODES))

    def test_app_parses(self):
        if not shutil.which('node'):
            self.skipTest('node is not installed')
        subprocess.run(['node', '--check', APP], check=True)


class Validate(unittest.TestCase):
    """labels.validate is what "this chunk is done" means."""

    def setUp(self):
        # Its own directory, not data/: a test that dies half way should not
        # leave a text behind for the corpus checks to trip over.
        self.scratch = scratch_dir(self)
        self.real = labels.DATA
        labels.DATA = self.scratch
        self.addCleanup(setattr, labels, 'DATA', self.real)
        self.text = 'test-text'
        os.makedirs(os.path.join(self.scratch, self.text, 'labels'))
        self.write_passages(
            ['A passage which plainly asserts something, at length.'] * 4)

    def write_passages(self, bodies):
        with open(labels.paths(self.text, 0)[0], 'w') as f:
            json.dump([[f'ref {i}', b] for i, b in enumerate(bodies)], f)

    def write_labels(self, codes):
        with open(labels.paths(self.text, 0)[1], 'w') as f:
            json.dump(codes, f)

    def test_sound_chunk_passes(self):
        self.write_labels(['L', 'ND', '', 'W'])
        self.assertIsNone(labels.validate(self.text, 0))

    def test_missing_file(self):
        self.assertEqual(labels.validate(self.text, 0), 'missing')

    def test_wrong_length(self):
        self.write_labels(['L', 'N'])
        self.assertIn('2 labels for 4 passages', labels.validate(self.text, 0))

    def test_unknown_code(self):
        self.write_labels(['L', 'N', 'Z', 'W'])
        self.assertIn("'Z' is not a code", labels.validate(self.text, 0))

    def test_repeated_code(self):
        self.write_labels(['LL', 'N', '', 'W'])
        self.assertIn('repeats a code', labels.validate(self.text, 0))

    def test_too_many_codes(self):
        self.write_labels(['LPTVDW', 'N', '', 'W'])
        self.assertIn('more than', labels.validate(self.text, 0))

    def test_five_codes_are_allowed(self):
        # A warned-of atrocity in a hadith: narrative, threat, violence, the
        # law it enforces, and the chain that carried it.
        self.write_labels(['NTVLA', 'N', '', 'W'])
        self.assertIsNone(labels.validate(self.text, 0))

    def test_blank_on_assertions_is_rejected(self):
        self.write_labels([''] * 4)
        self.assertIn('came back blank', labels.validate(self.text, 0))

    def test_blank_on_rolls_of_names_is_fine(self):
        # A genealogy carries none of the codes and that is a real answer.
        self.write_passages([
            'And the sons of Jehaleleel; Ziph, and Ziphah, Tiria, and Asareel.',
            'Of the sons of Hebron; Eliel the chief, and his brethren fourscore:',
            'And at Bilhah, and at Ezem, and at Tolad, and at Bethuel,',
            'This hadith is narrated on the authority of Zuhri, same chain.',
        ])
        self.write_labels([''] * 4)
        self.assertIsNone(labels.validate(self.text, 0))


class Suspect(unittest.TestCase):
    """Which blanks are a classifier skipping work and which are the text."""

    def assert_suspect(self, body):
        self.assertTrue(labels.suspect(body), body)

    def assert_excused(self, body):
        self.assertFalse(labels.suspect(body), body)

    def test_assertions_are_suspect(self):
        for body in [
            'And Jesus wept, and the disciples marvelled greatly at the sight.',
            'There are five kinds of rags: those from a charnel ground, a shop.',
            'When a procedure of demotion has three qualities, it is illegitimate.',
            'And Moses said unto the LORD, See, thou sayest unto me, Bring up.',
        ]:
            self.assert_suspect(body)

    def test_rolls_of_names_are_excused(self):
        for body in [
            'Of the sons of Hebron; Eliel the chief, and his brethren fourscore:',
            'And the sons of Jehaleleel; Ziph, and Ziphah, Tiria, and Asareel.',
            'And at Bilhah, and at Ezem, and at Tolad, and at Bethuel, and Hormah.',
            'Shallum his son, Mibsam his son, Mishma his son, Hamuel his son.',
        ]:
            self.assert_excused(body)

    def test_chains_of_transmission_are_excused(self):
        for body in [
            'This hadith is narrated on the authority of Zuhri with the same chain.',
            'There is another chain of Tawus reporting like the reports before.',
            'Another hadith like it has been narrated by the same chain of men.',
        ]:
            self.assert_excused(body)

    def test_structural_excuses(self):
        self.assert_excused('At Savatthi.')                    # too short
        self.assert_excused('Thus have I heard. The Buddha was staying near.')
        self.assert_excused('Is it not so that a mendicant should train thus?')


@needs_sdk
class CodesFor(unittest.TestCase):
    """Turning eight probabilities into the string a label file holds."""

    def codes(self, cut=0.5, **given):
        answers = {code: given.get(code, 0.0) for code in labels.CODES}
        return classify.codes_for(answers, cut)

    def test_nothing_over_the_cut(self):
        self.assertEqual(self.codes(L=0.4, N=0.49), '')

    def test_threshold_is_inclusive(self):
        self.assertEqual(self.codes(L=0.5), 'L')

    def test_taxonomy_order_not_probability_order(self):
        # "LT", never "TL", however the probabilities fell.
        self.assertEqual(self.codes(T=0.99, L=0.51), 'LT')

    def test_caps_at_max_codes_keeping_the_likeliest(self):
        got = self.codes(L=0.99, P=0.98, T=0.97, N=0.96, D=0.95, W=0.94, V=0.93)
        self.assertEqual(len(got), labels.MAX_CODES)
        self.assertEqual(got, 'LPTND')

    def test_provenance_survives_alongside_content(self):
        self.assertEqual(self.codes(L=0.9, A=0.95), 'LA')


class Builders(unittest.TestCase):
    """Reference parsing, where a source's oddities get in."""

    def test_rigveda_splits_stanzas_on_the_numeral(self):
        import build_rigveda
        hymn = '1 First line here,\nand its second.\n2 Second stanza.'
        self.assertEqual(list(build_rigveda.stanzas(hymn)),
                         ['First line here,\nand its second.', 'Second stanza.'])

    def test_rigveda_ignores_a_misread_capital_i(self):
        # The scan behind the text read a line-initial "I" as a "1", which
        # would cut a stanza in half. A stanza never opens in lower case.
        import build_rigveda
        hymn = '1 THIS laud shall be supreme.\n1 beg renown of Varuna.'
        self.assertEqual(len(list(build_rigveda.stanzas(hymn))), 1)

    def test_manu_verse_without_its_point(self):
        import build_manu
        self.assertTrue(build_manu.VERSE.match('39 (Horse-faced) Kinnaras, monkeys'))
        self.assertTrue(build_manu.VERSE.match('1. The great sages approached'))

    def test_upanishad_reference_shapes(self):
        import build_upanishads as up
        cases = {
            'The Upanishads (SBE01): Khandogya Upanishad: I, 9':
                ('Khandogya Upanishad', '1.9'),
            'The Upanishads (SBE01): Aitareya-Aranyaka: I, 5, 2':
                ('Aitareya-Aranyaka', '1.5.2'),
            'The Upanishads (SBE15): Svetasvatara Upanishad: Adhyâya II':
                ('Svetasvatara Upanishad', '2'),
            'The Upanishads (SBE15): Prasna Upanishad: Fourth Question':
                ('Prasna Upanishad', '4'),
        }
        for title, want in cases.items():
            self.assertEqual(up.reference(title), want, title)

    def test_upanishad_skips_front_matter_and_other_translations(self):
        import build_upanishads as up
        for title in [
            'The Upanishads (SBE01): Introduction: Introduction',
            'The Upanishads (SBE01): Introduction to the Upanishads: Rammohun Roy',
            'The Upanishads (SBE15): Brihadaranyaka Upanishad: VI, 4: Hume Translation',
        ]:
            self.assertIsNone(up.reference(title), title)


class WriteText(unittest.TestCase):
    """Rebuilding a text must not throw away the labels inside it."""

    def setUp(self):
        self.scratch = scratch_dir(self)
        self.real = common.DATA
        common.DATA = self.scratch
        self.addCleanup(setattr, common, 'DATA', self.real)

    def build(self, count):
        # write_text reports what it wrote, which is noise in a test run.
        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet):
            return common.write_text(
                'scratch', 'A Text', 'Text', 'sub', 'src', 'lic',
                ((f'ref {i}', f'body {i}') for i in range(count)),
                tradition='judaism')

    def test_labels_survive_a_rebuild(self):
        # A full build used to rmtree the text directory, and labels/ lives
        # inside it. Hours of classifying went with it.
        self.build(3)
        keep = os.path.join(self.scratch, 'scratch', 'labels')
        os.makedirs(keep)
        with open(os.path.join(keep, '0000.json'), 'w') as f:
            json.dump(['L', 'N', ''], f)
        self.build(3)
        with open(os.path.join(keep, '0000.json')) as f:
            self.assertEqual(json.load(f), ['L', 'N', ''])

    def test_a_shorter_text_leaves_no_stale_chunk(self):
        self.build(common.CHUNK * 2)
        self.build(3)
        chunks = [n for n in os.listdir(os.path.join(self.scratch, 'scratch'))
                  if n.endswith('.json')]
        self.assertEqual(chunks, ['0000.json'])


def manifest_or_skip(case):
    path = os.path.join(DATA, 'manifest.json')
    if not os.path.exists(path):
        case.skipTest('no built corpus; run scripts/build_all.py')
    with open(path) as f:
        return json.load(f)


class Corpus(unittest.TestCase):
    """What is on disk, against what the manifest and the page expect."""

    def setUp(self):
        self.manifest = manifest_or_skip(self)
        self.texts = {t['id']: t for t in self.manifest['texts']}

    def test_no_text_left_on_disk_after_the_manifest_forgot_it(self):
        # An orphan directory is invisible until a stale manifest in somebody's
        # browser asks for a chunk of it and the whole app fails on a 404.
        on_disk = {name for name in os.listdir(DATA)
                   if os.path.isdir(os.path.join(DATA, name)) and name != 'map'}
        self.assertEqual(on_disk - set(self.texts), set())

    def test_every_text_has_its_chunks(self):
        for text_id, text in self.texts.items():
            want = labels.chunk_count(text)
            got = len([n for n in os.listdir(os.path.join(DATA, text_id))
                       if n.endswith('.json')])
            self.assertEqual(got, want, text_id)

    def test_traditions_name_texts_that_exist(self):
        listed = [t for tradition in self.manifest['traditions']
                  for t in tradition['texts']]
        self.assertEqual(sorted(listed), sorted(self.texts))

    def test_traditions_are_in_the_order_the_spread_uses(self):
        order = [t for t, _ in common.TRADITIONS]
        got = [t['id'] for t in self.manifest['traditions']]
        self.assertEqual(got, [t for t in order if t in got])


class Stats(unittest.TestCase):
    """stats.json is a contract with app.js, and the page cannot check it."""

    def setUp(self):
        manifest_or_skip(self)
        path = os.path.join(DATA, 'stats.json')
        if not os.path.exists(path):
            self.skipTest('no stats.json; run scripts/stats.py')
        with open(path) as f:
            self.stats = json.load(f)

    def test_the_page_finds_the_fields_it_reads(self):
        # A row without `counts` took the whole statistics screen down, blank
        # and silent, because the shape changed under a cached copy.
        self.assertEqual(set(self.stats), {'codes', 'traditions'})
        self.assertEqual(set(self.stats['codes']), set(labels.CODES))
        for row in self.stats['traditions']:
            self.assertEqual(
                set(row),
                {'id', 'short', 'counts', 'blank', 'chain', 'labelled',
                 'count', 'parts'}, row.get('id'))
            self.assertEqual(set(row['counts']), set(labels.CODES))
            for part in row['parts']:
                self.assertEqual(set(part), {'id', 'short', 'count'})

    def test_counts_are_within_the_total(self):
        for row in self.stats['traditions']:
            self.assertLessEqual(row['labelled'], row['count'], row['id'])
            self.assertLessEqual(row['blank'] + row['chain'], row['labelled'])
            for code, n in row['counts'].items():
                self.assertLessEqual(n, row['labelled'], (row['id'], code))

    def test_excluding_provenance_leaves_a_positive_total(self):
        # The page divides by labelled - chain. Zero would be a blank screen.
        for row in self.stats['traditions']:
            self.assertGreater(row['labelled'] - row['chain'], 0, row['id'])

    def test_parts_add_up_to_the_column(self):
        for row in self.stats['traditions']:
            self.assertEqual(sum(p['count'] for p in row['parts']),
                             row['count'], row['id'])

    def test_a_map_holds_one_byte_per_passage(self):
        # place() in app.js walks parts and indexes the strip; a short file
        # silently drops the tail of the last book.
        for row in self.stats['traditions']:
            path = os.path.join(DATA, 'map', row['id'] + '.txt')
            self.assertTrue(os.path.exists(path), path)
            self.assertEqual(os.path.getsize(path), row['count'] * 2, row['id'])


class Labelling(unittest.TestCase):
    """Every chunk on disk validates — which is what "done" means here."""

    def test_all_labels_validate(self):
        manifest_or_skip(self)
        texts = labels.manifest()
        bad = []
        for text_id in labels.order():
            for number in range(labels.chunk_count(texts[text_id])):
                problem = labels.validate(text_id, number)
                if problem and problem != 'missing':
                    bad.append(f'{text_id}/{number:04d}: {problem}')
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
