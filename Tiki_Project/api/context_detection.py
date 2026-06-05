import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


def _norm(value: Any) -> str:
    """Normalize text: remove accents, lowercase, keep alphanumeric + spaces."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    # Handle đ/Đ explicitly (NFD doesn't decompose it)
    text = text.replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# CANONICAL INTENT MAP
# Maps normalized query variants → (canonical_label, context_hint)
# canonical_label: label đẹp có dấu hiển thị trên UI
# context_hint: gợi ý context_id ưu tiên (override fallback)
# ============================================================
_CANONICAL_INTENTS: Dict[str, Dict[str, str]] = {
    # === Điện thoại ===
    "dien thoai":              {"label": "điện thoại", "context": "product"},
    "dien thoai thong minh":   {"label": "điện thoại thông minh", "context": "product"},
    "smartphone":              {"label": "điện thoại", "context": "product"},
    "phone":                   {"label": "điện thoại", "context": "product"},
    "mobile":                  {"label": "điện thoại", "context": "product"},
    "dt":                      {"label": "điện thoại", "context": "product"},
    # === Máy tính bảng ===
    "may tinh bang":           {"label": "máy tính bảng", "context": "product"},
    "tablet":                  {"label": "máy tính bảng", "context": "product"},
    "ipad":                    {"label": "iPad", "context": "product"},
    # === Laptop ===
    "laptop":                  {"label": "laptop", "context": "product"},
    "may tinh xach tay":       {"label": "máy tính xách tay", "context": "product"},
    "notebook":                {"label": "laptop", "context": "product"},
    # === Tai nghe ===
    "tai nghe":                {"label": "tai nghe", "context": "product"},
    "tai nghe bluetooth":      {"label": "tai nghe bluetooth", "context": "product"},
    "tai nghe chong on":       {"label": "tai nghe chống ồn", "context": "product"},
    "headphone":               {"label": "tai nghe", "context": "product"},
    "earphone":                {"label": "tai nghe", "context": "product"},
    "earbuds":                 {"label": "tai nghe", "context": "product"},
    # === TV / Màn hình ===
    "tivi":                    {"label": "tivi", "context": "product"},
    "man hinh":                {"label": "màn hình", "context": "product"},
    "monitor":                 {"label": "màn hình", "context": "product"},
    # === Thời trang ===
    "ao thun":                 {"label": "áo thun", "context": "product"},
    "ao thun nam":             {"label": "áo thun nam", "context": "product"},
    "ao thun nu":              {"label": "áo thun nữ", "context": "product"},
    "ao phong":                {"label": "áo phông", "context": "product"},
    "ao phong nam":            {"label": "áo phông nam", "context": "product"},
    "quan jean":               {"label": "quần jean", "context": "product"},
    "jeans":                   {"label": "quần jean", "context": "product"},
    "vay":                     {"label": "váy", "context": "product"},
    "chan vay":                 {"label": "chân váy", "context": "product"},
    "dam nu":                  {"label": "đầm nữ", "context": "product"},
    "giay the thao":           {"label": "giày thể thao", "context": "product"},
    "sneaker":                 {"label": "giày thể thao", "context": "product"},
    # === Sách ===
    "sach":                    {"label": "sách", "context": "book"},
    "truyen tranh":            {"label": "truyện tranh", "context": "book"},
    "manga":                   {"label": "manga / truyện tranh", "context": "book"},
    "comic":                   {"label": "truyện tranh", "context": "book"},
    # === Xe / Phương tiện ===
    "xe may":                  {"label": "xe máy", "context": "vehicle"},
    "o to":                    {"label": "ô tô", "context": "vehicle"},
    "xe dap":                  {"label": "xe đạp", "context": "vehicle"},
    # === Skincare / Mỹ phẩm ===
    "son moi":                 {"label": "son môi", "context": "product"},
    "lipstick":                {"label": "son môi", "context": "product"},
    "sua rua mat":             {"label": "sữa rửa mặt", "context": "product"},
    "kem chong nang":          {"label": "kem chống nắng", "context": "product"},
    "sunscreen":               {"label": "kem chống nắng", "context": "product"},
    "serum":                   {"label": "serum", "context": "product"},
    "kem duong am":            {"label": "kem dưỡng ẩm", "context": "product"},
    # === Gia dụng ===
    "noi com dien":            {"label": "nồi cơm điện", "context": "product"},
    # === Thể thao ===
    "giay chay bo":            {"label": "giày chạy bộ", "context": "product"},
}


def resolve_canonical(keyword: str) -> Dict[str, str] | None:
    """
    Given a raw keyword, return its canonical info dict if found.
    Returns: {"label": "...", "context": "..."} or None.

    Matching order:
    1. Exact normalized match
    2. Prefix match (longest first)
    """
    kw_norm = _norm(keyword)
    if not kw_norm:
        return None
    # Exact match
    if kw_norm in _CANONICAL_INTENTS:
        return _CANONICAL_INTENTS[kw_norm]
    # Longest prefix match
    best_key = ""
    for key in _CANONICAL_INTENTS:
        if kw_norm.startswith(key) or key.startswith(kw_norm):
            if len(key) > len(best_key):
                best_key = key
    if best_key:
        return _CANONICAL_INTENTS[best_key]
    return None


def _contains_any(haystack: str, needles: List[str]) -> bool:
    return any(n in haystack for n in needles)


def detectContext(product: Dict[str, Any], keyword: str) -> str:
    """
    Classify a product into a context bucket using lightweight heuristics.
    Returns a stable context_id (e.g. vehicle, book, accessory, toy, tool, product, other).

    All checks run on normalized text (_norm) so accented / unaccented queries
    produce identical results.
    """
    kw = _norm(keyword)

    title = _norm(product.get("title") or product.get("name"))
    category = _norm(product.get("categoryName") or product.get("category"))
    description = _norm(
        product.get("description") or product.get("short_description") or ""
    )
    text = f"{title} {category} {description}".strip()

    # ===== CANONICAL INTENT OVERRIDE =====
    # If the query maps to a well-known canonical intent AND the product
    # contains the normalized keyword (or a synonym token), use canonical context.
    # This prevents "dien thoai" / "smartphone" from falling through to "other".
    canonical = resolve_canonical(keyword)
    if canonical:
        canonical_ctx = canonical["context"]
        # Build set of all relevant tokens: query tokens + label tokens
        kw_tokens = set(kw.split())
        label_tokens = set(_norm(canonical["label"]).split())
        all_search_tokens = kw_tokens | label_tokens
        text_tokens = set(text.split())
        token_overlap = all_search_tokens & text_tokens
        if token_overlap or kw in text:
            # Product is relevant to this canonical intent
            # Still allow book/vehicle overrides for specialised contexts
            if canonical_ctx not in ("vehicle", "book"):
                return canonical_ctx

    # ===== TOY CAR DETECTION (Highest Priority for toy cars) =====
    # Detect toy cars/models BEFORE general accessory to separate from vehicle parts
    toy_car_keywords = [
        "do choi xe",
        "toy car",
        "model car",
        "xe do choi",
        "mo hinh xe",
        "mo hinh o to",
        "xe hoi do choi",
        "die cast",
        "toy automobile",
        "model automobile",
    ]
    if _contains_any(text, toy_car_keywords):
        return "toy"

    # ===== ACCESSORY-SPECIFIC KEYWORDS (High Priority) =====
    # These clearly indicate a product is an accessory/part, not a vehicle
    accessory_keywords = [
        "phu kien",
        "accessory",
        "op",
        "bao",
        "tui",
        "cap",
        "sac",
        "charger",
        "adapter",
        "hub",
        "gia do",
        "stand",
        "dan man hinh",
        "bat phu",
        "bac phu",
        "ao trum",
        "guong",
        "guong chieu",
        "dau",  # headlight
        "den xe",
        "chuong",
        "horn",
        "gioang",
        "lo sanh",
        "thung",
    ]

    # ===== EXERCISE EQUIPMENT (Not real vehicles) =====
    exercise_keywords = [
        "tap the duc",
        "tap gym",
        "tap",  # catches "tập" in various contexts
        "xe tap",
        "xe tap the duc",
        "dap tap",
        "trong nha",
        "exercise",
        "indoor",
        "treadmill",
    ]

    # ===== TOOL/MAINTENANCE KEYWORDS =====
    tool_keywords = [
        "dung cu",
        "tool",
        "do nghe",
        "sua chua",
        "repair",
        "bao duong",
        "cham soc",
        "nuoc rua",
        "rua kinh",
        "dung dich",
        "ve sinh",
        "dau nhot",
        "dau phanh",
        "nuoc lam mat",
        "phu gia",
        "thay the",
        "the thu phi",
        "etag",
        "bom",  # pump
        "bom xe",
        "lap",  # cleaning/wiping
    ] + exercise_keywords  # Combine exercise equipment with tools

    # ===== BOOK DETECTION WITH CONTEXT =====
    # More strict: require multiple book indicators or specific book terms
    book_keywords = ["sach", "book", "giao trinh", "huong dan", "cam nang", "tu dien"]
    book_specific = ["sach", "book", "truyen", "tap chi"]
    # Only count as book if it has strong book indicators
    strong_book_indicators = (
        title.count("sach") + title.count("book") + title.count("truyen")
    )

    if strong_book_indicators > 0 or _contains_any(title, book_specific):
        # But NOT if it's just mentioning a vehicle type in the title
        # e.g., "Slam Dunk" or "Monster" shouldn't be classified as "Sách về xe"
        if kw in (
            "xe",
            "oto",
            "o to",
            "xe may",
            "xemay",
            "xe dap",
            "xedap",
            "car",
            "motor",
            "bike",
        ):
            # For vehicle keywords, only classify as book if it explicitly mentions vehicles/vehicle topics
            if _contains_any(
                text,
                ["ky", "nhat ky", "hanh trinh", "du lich", "huong dan", "cam nang"],
            ):
                return "book"
            elif _contains_any(title, ["xe", "oto", "motor", "bike", "dap"]):
                # Check if it's genuinely about vehicles (not just coincidentally has the word)
                vehicle_book_terms = [
                    "hanh trinh",
                    "nhat ky",
                    "du lich",
                    "cam nang",
                    "huong dan",
                    "ky su",
                    "lich su",
                ]
                if _contains_any(text, vehicle_book_terms):
                    return "book"
                # If just has the word "xe" but no context about it, skip book classification
                # (this is likely a manga/light novel that just happens to have "xe" in title)
        else:
            return "book"

    # ===== TOY/MODEL DETECTION =====
    if _contains_any(
        text,
        [
            "do choi",
            "toy",
            "mo hinh",
            "model",
            "figure",
            "lego",
            "mini",
            "phien ban thu nho",
        ],
    ):
        return "toy"

    # ===== TOOL DETECTION =====
    if _contains_any(text, tool_keywords):
        return "tool"

    # ===== PRIMARY: VEHICLE KEYWORD LOGIC =====
    if kw in (
        "xe",
        "oto",
        "o to",
        "xe may",
        "xemay",
        "xe dap",
        "xedap",
        "car",
        "motor",
        "bike",
    ):
        # First check: is this clearly an accessory/part?
        if _contains_any(text, accessory_keywords):
            return "accessory"

        # Second check: is this exercise equipment?
        if _contains_any(text, exercise_keywords):
            return "tool"

        # Now determine if it's a REAL vehicle vs just something that mentions "xe"
        # Be VERY specific to avoid false positives
        vehicle_terms = ["xe dap", "xe may", "oto", "o to", "xe hoi", "phuong tien"]
        # Generic terms like "motor", "scooter" removed to avoid duplicating checks below

        vehicle_brands = [
            "honda",
            "yamaha",
            "suzuki",
            "kawasaki",
            "vespa",
            "vinfast",
            "toyota",
            "hyundai",
            "kia",
            "ford",
            "mazda",
            "mercedes",
            "bmw",
            "audi",
        ]
        # Vehicle specific model/series names (NOT generic terms)
        vehicle_model_terms = [
            "futura",  # Honda Futura
            "future",  # Alias for Futura
            "vision",  # Honda Vision
            "air blade",  # Honda Air Blade
            "sh mode",  # Honda SH Mode - MUST include "mode" to avoid matching "sh" in other words
            "lead",  # Honda LEAD
            "r15",  # Yamaha R15
            "r3",  # Yamaha R3
            "wave",  # Honda Wave
            "winner",  # Hero MotoCorp Winner
            "pcx",  # Honda PCX
            "vario",  # Honda Vario
            "blade",  # Honda Blade (with context check)
            "click",  # Honda Click
            "scoopy",  # Honda Scoopy
            "sh",  # Honda SH (standalone, works in vehicle context)
            "ex",  # Honda EX
            "xr",  # Honda XR
            "rebel",  # Honda Rebel
            "phantom",  # Bajaj Phantom
            "pulsar",  # Bajaj Pulsar
            "xpulse",  # Hero XPulse
            "fascino",  # Hero Fascino
            "splendor",  # Hero Splendor
        ]

        score = 0
        has_strong_indicator = False

        # SCORING: Give points for vehicle indicators
        # Give points for explicit vehicle terms in title (highest priority)
        if _contains_any(title, vehicle_terms):
            score += 3
            has_strong_indicator = True
        # Brand names - STRONG indicator of real vehicle
        if _contains_any(title, vehicle_brands):
            score += 3
            has_strong_indicator = True
        # Model/series names - STRONG indicator
        if _contains_any(title, vehicle_model_terms):
            score += 3
            has_strong_indicator = True
        # Category hints - be very strict (o-to-xe-may has ~200 non-vehicle products)
        # Only count if we're very sure
        if "phuong tien" in category or "xe dap" in category or "xe hoi" in category:
            score += 1

        # THRESHOLD: score >= 3 and must have at least one strong indicator
        # This balances strictness with recall - allows "xe máy future" to pass
        # while still avoiding false positives for accessories
        if score >= 3 and has_strong_indicator:
            return "vehicle"

        return "accessory" if _contains_any(text, accessory_keywords) else "tool"

    if kw in ("laptop", "notebook", "may tinh", "may tinh xach tay"):
        # "laptop + ..." already caught by book/tool/accessory/toy above
        if _contains_any(text, ["laptop", "notebook", "may tinh", "may tinh xach tay"]):
            return "product"

    # Fallback: for vehicle-like keywords, DO NOT create a redundant "product" bucket.
    # If it contains the keyword but isn't a real vehicle, keep it in accessory/tool/other buckets above.
    if kw in (
        "xe",
        "oto",
        "o to",
        "xe may",
        "xemay",
        "xe dap",
        "xedap",
        "car",
        "motor",
        "bike",
    ):
        return "other"

    # Generic fallback: if it mentions the keyword, treat as product-ish; otherwise other
    if kw and (kw in text or _contains_any(text, kw.split())):
        return "product"

    return "other"


def groupByContext(
    products: List[Dict[str, Any]], keyword: str
) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for p in products or []:
        ctx = detectContext(p, keyword)
        grouped.setdefault(ctx, []).append(p)
    return grouped


def _get_context_priority(context_id: str) -> int:
    """
    Return priority score for a context.
    Higher score = higher priority (will be picked as primary context).
    """
    priority_map = {
        "vehicle": 100,  # Highest: actual vehicles
        "accessory": 80,  # High: vehicle parts
        "toy": 70,  # Medium-high: toy cars and models
        "tool": 60,  # Medium: tools and maintenance
        "book": 50,  # Medium-low: books
        "product": 40,  # Low: generic products
        "other": 0,  # Lowest: miscellaneous
    }
    return priority_map.get(context_id, 0)


# ============================================================
# QUERY MODIFIER DETECTION
# Modifiers that legitimately trigger book/toy/tool contexts.
# A context is ONLY shown if:
#   (a) Query contains the modifier explicitly, OR
#   (b) Products in the bucket strongly evidence keyword+context co-occurrence.
# ============================================================
_MODIFIER_PATTERNS: Dict[str, List[str]] = {
    "book":      ["sach ve", "sach", "book", "giao trinh", "cam nang", "tu dien", "truyen"],
    "toy":       ["mo hinh", "do choi", "toy", "figure", "lego", "miniature"],
    "tool":      ["dung cu", "tool", "phu kien sua", "sua chua", "bao duong", "ve sinh"],
    "accessory": ["phu kien", "op lung", "cap sac", "bao da", "dan man hinh"],
}


def _query_has_modifier(query_norm: str, context_id: str) -> bool:
    """Return True if the normalized query explicitly contains a modifier for context_id."""
    patterns = _MODIFIER_PATTERNS.get(context_id, [])
    return any(p in query_norm for p in patterns)


def _context_label(keyword: str, context_id: str) -> str:
    """
    Build display label for a context bucket.
    Only produces human-readable labels — template strings that combine
    context type with keyword are ONLY used when context_id == 'product',
    'vehicle', or 'accessory' (which are always keyword-relevant).
    For book/toy/tool/other, the label reflects what the products actually ARE,
    not a hypothetical relationship to the keyword.
    """
    canonical = resolve_canonical(keyword)
    display_kw = canonical["label"] if canonical else keyword.strip()

    mapping = {
        "vehicle":   f"{display_kw} (phương tiện)",
        "book":      "Sách liên quan",
        "tool":      "Dụng cụ / phụ kiện liên quan",
        "toy":       "Mô hình / đồ chơi liên quan",
        "accessory": f"Phụ kiện {display_kw}" if display_kw else "Phụ kiện",
        "product":   f"{display_kw} (sản phẩm)",
        "other":     "Sản phẩm khác liên quan",
    }
    return mapping.get(context_id, context_id)


def getContextLabel(keyword: str, context_id: str) -> str:
    return _context_label(keyword, context_id)


def getSuggestedContexts(
    keyword: str,
    grouped: Dict[str, List[Dict[str, Any]]],
    selected_context: str,
    max_suggestions: int = 6,
) -> List[Dict[str, Any]]:
    """
    Return data-validated context suggestions.

    A context bucket is only shown if ALL of the following hold:
      1. It has >= min_threshold products.
      2. For 'modifier' contexts (book, toy, tool): either the query explicitly
         contains the modifier keyword, OR >= MIN_EVIDENCE_RATIO of products in
         the bucket have the keyword appearing in their name/category.
         This prevents "Sách về váy" from appearing when query is just "váy".
      3. 'product', 'vehicle', 'accessory' contexts: always shown if count >= threshold
         (these are inherently keyword-relevant — the products contain the keyword).

    Debug fields added to each suggestion:
      is_template_generated: always False (templates removed)
      is_validated_by_data:  True if evidence_ratio >= threshold
      evidence_count:        # products with keyword in name
      evidence_examples:     up to 3 product names proving the context
    """
    kw_norm = _norm(keyword)

    # Minimum product count thresholds per context type
    min_thresholds: Dict[str, int] = {
        "vehicle":   8,
        "accessory": 4,
        "tool":      4,
        "toy":       4,
        "book":      4,
        "product":   3,
        "other":     5,  # "other" has no meaningful label — keep threshold high
    }
    # Contexts that require modifier evidence check
    MODIFIER_CONTEXTS = {"book", "toy", "tool"}
    # Min ratio of products that must contain keyword tokens for modifier contexts
    MIN_EVIDENCE_RATIO = 0.30

    counts: List[Tuple[str, int]] = [
        (ctx, len(items))
        for ctx, items in grouped.items()
        if ctx != selected_context and len(items) > 0
    ]
    counts.sort(key=lambda x: (-_get_context_priority(x[0]), -x[1]))

    kw_tokens = set(kw_norm.split()) if kw_norm else set()

    suggestions = []
    for ctx, cnt in counts:
        min_count = min_thresholds.get(ctx, 5)
        if cnt < min_count:
            continue

        # Skip uninformative "other" bucket unless it's a very strong signal
        if ctx == "other" and cnt < 8:
            continue

        bucket_products = grouped.get(ctx, [])

        # --- Modifier context validation ---
        if ctx in MODIFIER_CONTEXTS:
            # (a) Query explicitly contains the modifier → always show
            query_has_mod = _query_has_modifier(kw_norm, ctx)

            # (b) Evidence check: does keyword appear in product names/categories?
            if not query_has_mod:
                evidence_products = [
                    p for p in bucket_products
                    if kw_tokens and kw_tokens.issubset(
                        set(_norm(
                            str(p.get("title", "") or p.get("name", ""))
                            + " " +
                            str(p.get("categoryName", "") or p.get("category", ""))
                        ).split())
                    )
                ]
                evidence_ratio = len(evidence_products) / cnt if cnt > 0 else 0.0
                if evidence_ratio < MIN_EVIDENCE_RATIO:
                    # Not enough products contain the keyword — skip this context
                    continue
                evidence_examples = [
                    str(p.get("title", p.get("name", "")))[:60]
                    for p in evidence_products[:3]
                ]
                is_validated = True
            else:
                # Query has modifier — validate by checking products too
                evidence_products = [
                    p for p in bucket_products
                    if kw_tokens and kw_tokens.issubset(
                        set(_norm(
                            str(p.get("title", "") or p.get("name", ""))
                            + " " +
                            str(p.get("categoryName", "") or p.get("category", ""))
                        ).split())
                    )
                ]
                evidence_examples = [
                    str(p.get("title", p.get("name", "")))[:60]
                    for p in evidence_products[:3]
                ]
                is_validated = True
        else:
            # Non-modifier context: always show if count >= threshold
            evidence_products = bucket_products
            evidence_examples = [
                str(p.get("title", p.get("name", "")))[:60]
                for p in bucket_products[:3]
            ]
            is_validated = True

        suggestions.append({
            "context_id":            ctx,
            "label":                 _context_label(keyword, ctx),
            "count":                 cnt,
            "is_template_generated": False,
            "is_validated_by_data":  is_validated,
            "evidence_count":        len(evidence_products),
            "evidence_examples":     evidence_examples,
        })
        if len(suggestions) >= max_suggestions:
            break

    return suggestions


def pick_primary_context(grouped: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Pick primary context based on priority hierarchy.
    If multiple contexts have similar counts (at least 60% of largest),
    pick the one with highest priority. Otherwise, pick the one with most products.
    """
    if not grouped:
        return "other"

    if len(grouped) == 1:
        return list(grouped.keys())[0]

    # Get context counts
    context_counts = [(ctx, len(items)) for ctx, items in grouped.items()]

    # Sort by count to find the largest
    sorted_by_count = sorted(context_counts, key=lambda x: x[1], reverse=True)
    largest_count = sorted_by_count[0][1]

    # Find all contexts with at least 60% of largest count
    # This allows similar-sized contexts to compete on priority
    threshold = largest_count * 0.6
    candidates = [ctx for ctx, count in context_counts if count >= threshold]

    # If only one candidate, return it
    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates within threshold - pick by priority
    best_context = max(candidates, key=_get_context_priority)
    return best_context


def filter_by_context(
    products: List[Dict[str, Any]], keyword: str, context_id: str
) -> List[Dict[str, Any]]:
    if not context_id:
        return products or []
    return [p for p in (products or []) if detectContext(p, keyword) == context_id]
