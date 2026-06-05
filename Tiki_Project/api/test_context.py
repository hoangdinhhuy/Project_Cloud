"""
Test context suggestion with SEARCH RESULTS only (as used in production).
Run from: d:\\Cloud\\Project\\Project_Cloud\\Tiki_Project\\api\\
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import logging; logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from search_engine.smart_search import SmartSearch
from context_detection import (
    groupByContext, getSuggestedContexts, getContextLabel, pick_primary_context,
)

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json')
with open(DATA, encoding='utf-8') as f:
    raw = json.load(f)

df = pd.DataFrame(raw)  # raw slugs
engine = SmartSearch(products_df=df)

TEST_QUERIES = [
    "váy cho nam",
    "váy",
    "áo cho chó",
    "xe máy",
    "phụ kiện xe máy",
    "điện thoại",
    "phụ kiện điện thoại",
    "truyện tranh",
    "sách về kinh tế",
    "mô hình xe máy",
    "dụng cụ sửa xe máy",
]

FORBIDDEN_PATTERNS = ["Sách về ", "Mô hình/đồ chơi ", "Dụng cụ liên quan ", "Khác liên quan "]

print("=" * 72)
print("CONTEXT SUGGESTION — WITH REAL SEARCH RESULTS (production flow)")
print("=" * 72)

pass_count = fail_count = 0

for query in TEST_QUERIES:
    results = engine.search(query, limit=20)
    if not results:
        print(f"\n  SKIP '{query}' — no results")
        continue

    grouped = groupByContext(results, keyword=query)
    primary = pick_primary_context(grouped)
    primary_label = getContextLabel(query, primary)
    suggestions = getSuggestedContexts(query, grouped, primary, max_suggestions=6)

    suggestion_labels = [s["label"] for s in suggestions]
    bad_labels = [lbl for lbl in FORBIDDEN_PATTERNS if any(lbl in sl for sl in suggestion_labels + [primary_label])]

    status = "+" if not bad_labels else "X"
    if not bad_labels:
        pass_count += 1
    else:
        fail_count += 1

    print(f"\n[{status}] '{query}'  ({len(results)} results)")
    print(f"    primary context: {primary_label}")
    if suggestions:
        for s in suggestions:
            ev = s.get("evidence_count", "?")
            val = "OK" if s.get("is_validated_by_data") else "!!"
            tmpl = " [TEMPLATE]" if s.get("is_template_generated") else ""
            print(f"    [{val}] {s['label']} (n={s['count']}, evidence={ev}){tmpl}")
    else:
        print("    (no extra suggestions)")
    if bad_labels:
        print(f"    FORBIDDEN: {bad_labels}")

print(f"\n{'─'*72}")
print(f"PASS={pass_count}  FAIL={fail_count}  TOTAL={pass_count+fail_count}")
print("Key: [+] no forbidden labels  [X] forbidden template labels found")
print("=" * 72)
