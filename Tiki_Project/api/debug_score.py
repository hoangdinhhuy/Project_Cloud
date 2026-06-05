import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import logging; logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from search_engine.smart_search import SmartSearch
from search_engine.normalizer import preprocess_query, has_diacritics, accent_lower
from search_engine.category_matcher import CategoryMatcher

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json')
with open(DATA, encoding='utf-8') as f:
    raw = json.load(f)
df = pd.DataFrame(raw)
engine = SmartSearch(products_df=df)

keyword = "váy cho chó"
q_norm = preprocess_query(keyword)
q_compact = q_norm.replace(" ", "")

print(f"RAW QUERY    : {keyword}")
print(f"NORMALIZED   : {q_norm}")
print(f"COMPACT      : {q_compact}")
print(f"has_diacritic: {has_diacritics(keyword)}")

# Category matching
cat_result = engine._category_matcher.match(q_norm, q_compact)

print(f"\n--- CATEGORY MATCHING ---")
print(f"matched_category : {cat_result['matched_category']}")
print(f"confidence       : {cat_result['confidence']:.4f}")
print(f"result_type      : {cat_result['result_type']}")
print(f"all_scores (top5):")
top5 = sorted(cat_result['all_scores'].items(), key=lambda x: x[1], reverse=True)[:5]
for slug, sc in top5:
    print(f"  {sc:.4f}  {slug}")

# Search with debug
results = engine.search(keyword, limit=5, debug=True)
print(f"\n--- TOP RESULTS (debug) ---")
for i, r in enumerate(results, 1):
    dbg = r.get('_debug', {})
    print(f"\n#{i} {r['title'][:65]}")
    print(f"   category    : {r['categoryName']}")
    print(f"   final_score : {dbg.get('final_score')}")
    print(f"   exact_name  : {dbg.get('exact_name_score')}")
    print(f"   cat_score   : {dbg.get('category_score')}")
    print(f"   phrase_score: {dbg.get('phrase_score')}")
    print(f"   semantic    : {dbg.get('semantic_score')}")
    print(f"   popularity  : {dbg.get('popularity_score')}")
    print(f"   reason      : {dbg.get('matched_reason')}")
    print(f"   result_type : {dbg.get('result_type')}")
    print(f"   in_cat      : {dbg.get('in_matched_cat')}")
