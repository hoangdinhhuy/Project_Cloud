import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import logging; logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from search_engine.smart_search import SmartSearch

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json')
with open(DATA, encoding='utf-8') as f:
    raw = json.load(f)
df = pd.DataFrame(raw)

# Provide a dummy resolve_url to avoid errors
def resolve_url(**kwargs): return ""
engine = SmartSearch(products_df=df, resolve_url_fn=resolve_url)

keyword = "váy cho chó"
print(f"SEARCHING: '{keyword}' (limit=9999 as in market report)")
results = engine.search(keyword, limit=9999, debug=True)

print(f"Total returned products: {len(results)}")

cats = {}
for r in results:
    c = r['categoryName']
    cats[c] = cats.get(c, 0) + 1

print("\n--- Top Categories returned ---")
for c, cnt in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:5]:
    pct = cnt / len(results) * 100 if results else 0
    print(f"{c:30s} {cnt:3d} ({pct:.1f}%)")

print("\n--- Example Results ---")
for i, r in enumerate(results[:5], 1):
    print(f"#{i} {r['title'][:60]} (score={r.get('_debug', {}).get('final_score')})")
