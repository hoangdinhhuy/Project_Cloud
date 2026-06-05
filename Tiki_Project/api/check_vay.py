import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('../data/products.json', encoding='utf-8') as f:
    prods = json.load(f)
vay = [p for p in prods if 'vay' in p.get('name','').lower() or 'váy' in p.get('name','').lower()]
print(f"Total vay products: {len(vay)}")
from collections import Counter
cats = Counter(p['category'] for p in vay)
for cat, count in cats.most_common():
    print(f"  {cat}: {count}")
print("\nSample vay products in thoi-trang-nam:")
for p in [x for x in vay if x['category'] == 'thoi-trang-nam'][:5]:
    print(f"  {p['name'][:70]}")
