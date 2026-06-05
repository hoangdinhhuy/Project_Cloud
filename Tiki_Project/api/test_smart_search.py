"""
Test SmartSearch v3 — Category-locked search validation.
Run from: d:\\Cloud\\Project\\Project_Cloud\\Tiki_Project\\api\\
"""
import sys, os, json

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from search_engine.normalizer import preprocess_query
from search_engine.category_matcher import CategoryMatcher
from search_engine.smart_search import SmartSearch

# --- Load data (with raw slugs for category_matcher) ---
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json')
with open(DATA_PATH, encoding='utf-8') as f:
    products_data = json.load(f)

df_raw = pd.DataFrame(products_data)  # keep raw slugs → used by CategoryMatcher

CATEGORY_MAPPING = {
    "dien-thoai-may-tinh-bang": "Dien thoai - May tinh bang",
    "do-gia-dung":              "Do gia dung",
    "my-pham-lam-dep":          "My pham - Lam dep",
    "o-to-xe-may":              "O to - Xe may",
    "sach-truyen":              "Sach truyen",
    "the-thao-da-ngoai":        "The thao - Da ngoai",
    "thiet-bi-dien-tu":         "Thiet bi dien tu",
    "thoi-trang-nam":           "Thoi trang nam",
    "thoi-trang-nu":            "Thoi trang nu",
}
# Reverse: display → slug (for test validation)
DISPLAY_TO_SLUG = {v: k for k, v in CATEGORY_MAPPING.items()}

# df for SmartSearch (with display names in 'category' for UI)
# but SmartSearch v3 internally keeps raw slugs from the row — 
# pass raw-slug df so category matching works correctly
engine = SmartSearch(products_df=df_raw)

# ─── Test 1: Category-lock queries ───────────────────────────────
LOCKED_TESTS = [
    ("dien-thoai-may-tinh-bang", [
        "điện thoại",
        "dien thoai",
        "dienthoai",
        "điên thoại",
        "smartphone",
        "phone",
        "mobile",
        "máy tính bảng",
        "tablet",
    ]),
    ("sach-truyen", [
        "truyện tranh",
        "truyen tranh",
        "sách",
    ]),
    ("thoi-trang-nu", [
        "váy",
        "đầm nữ",
    ]),
    ("o-to-xe-may", [
        "xe máy",
        "xemay",
    ]),
]

print("=" * 72)
print("SMART SEARCH v3 — CATEGORY-LOCK VALIDATION")
print("=" * 72)

PASS = 0
FAIL = 0

for expected_slug, queries in LOCKED_TESTS:
    print(f"\n[EXPECTED: {expected_slug}]")
    for query in queries:
        q_norm = preprocess_query(query)
        results = engine.search(query, limit=5, debug=True)

        if not results:
            print(f"  [X] '{query}' → NO RESULTS")
            FAIL += 1
            continue

        dbg = results[0].get("_debug", {})
        matched_slug  = dbg.get("matched_category", "N/A")
        confidence    = dbg.get("category_confidence", 0.0)
        result_type   = dbg.get("result_type", "N/A")

        # Validate: matched_category == expected, all results in expected category
        cat_correct   = (matched_slug == expected_slug)
        type_ok       = result_type in ("category_locked", "category_preferred")
        all_cats      = [r.get("categoryName", "") for r in results]
        # products in results should be from expected slug
        all_in_cat    = all(c == expected_slug for c in all_cats)

        ok = cat_correct and type_ok and all_in_cat

        if ok:
            PASS += 1
            indicator = "+"
        else:
            FAIL += 1
            indicator = "X"

        print(f"  [{indicator}] '{query}'")
        print(f"       norm='{q_norm}' | cat={matched_slug}({confidence:.3f}) | type={result_type}")
        if not all_in_cat:
            for r in results:
                c = r.get("categoryName", "?")
                status_mark = "OK" if c == expected_slug else "!!"
                print(f"       [{status_mark}] {c}: {r['title'][:50]}")
        else:
            top = results[0]['title'][:55]
            print(f"       top={top}")

print(f"\n{'─'*72}")
print(f"RESULTS: PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")

# ─── Test 2: Category matcher raw scores ─────────────────────────
print("\n" + "=" * 72)
print("CATEGORY MATCHER — Score breakdown")
print("=" * 72)

matcher = CategoryMatcher(df_raw)

all_test_queries = [
    "dienthoai", "smartphone", "phone", "mobile", "dien thoai",
    "may tinh bang", "tablet", "vay", "xe may", "sach",
]

for q in all_test_queries:
    q_norm = preprocess_query(q)
    q_compact = q_norm.replace(" ", "")
    r = matcher.match(q_norm, q_compact)
    scores = r["all_scores"]
    top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"\n  '{q}' → norm='{q_norm}'  matched={r['matched_category']}({r['confidence']:.3f})  type={r['result_type']}")
    for slug, score in top3:
        print(f"    {score:.3f} {slug}")

print("\n" + "=" * 72)
print("DONE")
print("=" * 72)
