import os, sys
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, ".")
from data_loader import DataLoader
from config import settings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

loader = DataLoader(data_dir=settings.DATA_PATH)

for q in ["truyen tranh", "truyện tranh", "dien thoai", "điện thoại", "ao thun nam", "áo thun nam"]:
    p = loader.search_products(keyword=q, limit=3, debug=True)
    print(f"\n=== {q!r} ===")
    for x in p:
        d = x.get("_debug", {})
        print(f"  [{d.get('tier','?')}|{d.get('final_score','?')}] {x['title'][:55]}")
        print(f"    Cat: {x['categoryName']}")
