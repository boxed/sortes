"""Rebuild every data/<text>/ directory and the manifest that indexes them."""
import json
import os

import build_bhagavad_gita
import build_bible
import build_book_of_mormon
import build_hadith
import build_manu
import build_quran
import build_rigveda
import build_tripitaka
import build_upanishads
from common import DATA, TRADITIONS

BUILDERS = [
    build_bible,
    build_quran,
    build_hadith,
    build_book_of_mormon,
    build_bhagavad_gita,
    build_rigveda,
    build_upanishads,
    build_manu,
    build_tripitaka,
]

if __name__ == '__main__':
    os.makedirs(DATA, exist_ok=True)
    texts = []
    for builder in BUILDERS:
        texts += builder.build()
    # The spread is a column per tradition, so the manifest carries the
    # grouping the page lays out by. A tradition nobody built a text for is
    # dropped rather than printed empty.
    have = {text['tradition'] for text in texts}
    traditions = [{'id': t, 'title': title, 'texts':
                   [x['id'] for x in texts if x['tradition'] == t]}
                  for t, title in TRADITIONS if t in have]
    with open(os.path.join(DATA, 'manifest.json'), 'w') as f:
        json.dump({'traditions': traditions, 'texts': texts}, f,
                  ensure_ascii=False, indent=1)
    print(f'manifest.json: {len(texts)} texts in {len(traditions)} traditions, '
          f'{sum(t["count"] for t in texts)} paragraphs')
