"""Rebuild every data/<text>/ directory and the manifest that indexes them."""
import json
import os

import build_bhagavad_gita
import build_bible
import build_book_of_mormon
import build_quran
import build_tripitaka
from common import DATA

BUILDERS = [
    build_bible,
    build_quran,
    build_book_of_mormon,
    build_bhagavad_gita,
    build_tripitaka,
]

if __name__ == '__main__':
    os.makedirs(DATA, exist_ok=True)
    texts = []
    for builder in BUILDERS:
        texts += builder.build()
    with open(os.path.join(DATA, 'manifest.json'), 'w') as f:
        json.dump({'texts': texts}, f, ensure_ascii=False, indent=1)
    print(f'manifest.json: {len(texts)} texts, '
          f'{sum(t["count"] for t in texts)} paragraphs')
