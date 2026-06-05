import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import logging; logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from search_engine.smart_search import SmartSearch
from search_engine.normalizer import has_diacritics

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json')
with open(DATA, encoding='utf-8') as f:
    raw = json.load(f)
df = pd.DataFrame(raw)
engine = SmartSearch(products_df=df)

# 1. Verify has_diacritics detection
print("=== has_diacritics() detection ===")
tests = ["vay", "vay cho nam", "dien thoai", "dienthoai",
         "váy", "váy cho nam", "điện thoại", "điên thoại", "Vảy Cá"]
for t in tests:
    print(f"  {t!r:30s} → {has_diacritics(t)}")

# 2. Compare search results: accent vs no-accent
print()
for q_acc, q_no in [("váy cho nam", "vay cho nam"), ("váy", "vay"), ("điện thoại", "dien thoai")]:
    print(f"\n{'─'*65}")
    for q in [q_acc, q_no]:
        results = engine.search(q, limit=5, debug=True)
        acc = has_diacritics(q)
        print(f"\n  QUERY: '{q}'  [accent={acc}]")
        for i, r in enumerate(results[:3], 1):
            dbg = r.get('_debug', {})
            title = r['title'][:52]
            exact = dbg.get('exact_name_score', 0)
            final = dbg.get('final_score', 0)
            reason = dbg.get('matched_reason', '')
            print(f"    #{i} {title}")
            print(f"         final={final}  exact={exact}  reason={reason}")
