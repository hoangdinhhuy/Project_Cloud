"""
verify_setup.py — Pre-flight check for Tiki RAG API
Exits 0 if everything looks OK, exits 1 if critical files are missing.
"""

import sys
import os

# Resolve paths relative to this file (api/ folder)
BASE = os.path.dirname(os.path.abspath(__file__))

def check(label: str, path: str, required: bool = True) -> bool:
    abs_path = os.path.normpath(os.path.join(BASE, path))
    exists = os.path.exists(abs_path)
    status = "[OK]  " if exists else ("[FAIL]" if required else "[WARN]")
    print(f"  {status} {label}: {abs_path}")
    return exists

print("\n  Checking paths from config...")

ok = True

# Data directory
data_ok = check("DATA_PATH (data dir)", "../data", required=True)
if not data_ok:
    ok = False

# Module / models directory
models_ok = check("MODELS_PATH (module dir)", "../module", required=False)

# Chroma DB directory (optional – only needed if RAG is active)
check("CHROMA_DB_PATH", "../chroma_db", required=False)

# Key API files
for fname in ["main.py", "config.py", "data_loader.py", "search_engine_v2.py"]:
    f_ok = check(fname, fname, required=True)
    if not f_ok:
        ok = False

print()

if ok:
    print("  [OK]   All critical checks passed.")
    sys.exit(0)
else:
    print("  [WARN] Some items are missing – backend may start with limited functionality.")
    sys.exit(1)
