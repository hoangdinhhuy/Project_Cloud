# ============================================================
# DATA LOADER - Load JSON Data Files
# ============================================================

import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Any

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Load and manage all JSON data files
    - products.json (2,980 products)
    - reviews.json (31,604 reviews)
    - timeseries.json (610 timeseries rows)
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize data loader

        Args:
            data_dir: Path to data directory containing JSON files
        """
        self.data_dir = Path(data_dir)
        self.products_df = None
        self.reviews_df = None
        self.timeseries_df = None
        self.raw_products_df = None
        self.url_by_product_id = {}
        self.urls_by_name = {}
        self.url_lookup_cache = {}

        self._load_all()

    def _load_all(self):
        """Load all data files"""
        import pandas as pd

        logger.info("📥 Loading data files...")

        # Load products
        products_path = self.data_dir / "products.json"
        if products_path.exists():
            with open(products_path, "r", encoding="utf-8") as f:
                products_data = json.load(f)
            self.products_df = pd.DataFrame(products_data)

            # Standardize category names
            CATEGORY_MAPPING = {
                "dien-thoai-may-tinh-bang": "Điện thoại - Máy tính bảng",
                "laptop-may-tinh-bo": "Laptop - Máy tính bộ",
                "thiet-bi-dien-tu": "Thiết bị điện tử",
                "do-gia-dung": "Đồ gia dụng",
                "thoi-trang-nam": "Thời trang nam",
                "thoi-trang-nu": "Thời trang nữ",
                "my-pham-lam-dep": "Mỹ phẩm - Làm đẹp",
                "sach-truyen": "Sách truyện",
                "the-thao-da-ngoai": "Thể thao - Dã ngoại",
                "o-to-xe-may": "Ô tô - Xe máy",
            }
            if not self.products_df.empty and "category" in self.products_df.columns:
                self.products_df["category"] = self.products_df["category"].map(
                    lambda x: CATEGORY_MAPPING.get(x, x)
                )

            logger.info(f"   ✅ Loaded {len(self.products_df):,} products")
        else:
            logger.warning(f"   ⚠️  Products file not found: {products_path}")
            self.products_df = pd.DataFrame()

        # Load reviews
        reviews_path = self.data_dir / "reviews.json"
        if reviews_path.exists():
            with open(reviews_path, "r", encoding="utf-8") as f:
                reviews_data = json.load(f)
            self.reviews_df = pd.DataFrame(reviews_data)
            logger.info(f"   ✅ Loaded {len(self.reviews_df):,} reviews")
        else:
            logger.warning(f"   ⚠️  Reviews file not found: {reviews_path}")
            self.reviews_df = pd.DataFrame()

        # Load timeseries
        timeseries_path = self.data_dir / "timeseries.json"
        if timeseries_path.exists():
            with open(timeseries_path, "r", encoding="utf-8") as f:
                timeseries_data = json.load(f)
            self.timeseries_df = pd.DataFrame(timeseries_data)
            if "ds" in self.timeseries_df.columns:
                self.timeseries_df["ds"] = pd.to_datetime(self.timeseries_df["ds"])
            logger.info(f"   ✅ Loaded {len(self.timeseries_df):,} timeseries rows")
        else:
            logger.warning(f"   ⚠️  Timeseries file not found: {timeseries_path}")
            self.timeseries_df = pd.DataFrame()

        # Load crawled raw CSV for URL resolution
        raw_products_path = self.data_dir / "tiki_products_raw.csv"
        if raw_products_path.exists():
            try:
                usecols = ["product_id", "name", "category", "url_path"]
                self.raw_products_df = pd.read_csv(raw_products_path, usecols=usecols)
                self._build_url_indexes()
                logger.info(
                    f"   ✅ Loaded {len(self.raw_products_df):,} raw products for URL mapping"
                )
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to load raw products CSV: {e}")
                self.raw_products_df = pd.DataFrame()
        else:
            logger.warning(f"   ⚠️  Raw products file not found: {raw_products_path}")
            self.raw_products_df = pd.DataFrame()

    @staticmethod
    def _normalize_text(value: Any) -> str:
        """Normalize text for stable matching across accented/cased variants."""
        if value is None:
            return ""

        text = str(value).strip().lower()
        if not text:
            return ""

        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _safe_product_id(value: Any) -> str:
        """Convert product id from mixed source types to canonical string."""
        if value is None:
            return ""
        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            return str(value).strip()

    def _build_url_indexes(self):
        """Create fast URL lookup maps from crawled raw CSV."""
        self.url_by_product_id = {}
        self.urls_by_name = {}

        if self.raw_products_df is None or self.raw_products_df.empty:
            return

        for _, row in self.raw_products_df.iterrows():
            raw_url = row.get("url_path")
            if raw_url is None:
                continue

            url = str(raw_url).strip()
            if not url:
                continue

            pid = self._safe_product_id(row.get("product_id"))
            if pid:
                self.url_by_product_id[pid] = url

            name_norm = self._normalize_text(row.get("name"))
            if not name_norm:
                continue

            entry = {
                "url": url,
                "product_id": pid,
                "category_norm": self._normalize_text(row.get("category")),
                "name_norm": name_norm,
            }
            self.urls_by_name.setdefault(name_norm, []).append(entry)

    def resolve_product_url(
        self, product_id: Any, name: Any = None, category: Any = None
    ) -> str:
        """
        Resolve canonical Tiki product URL from crawled data.
        Priority: product_id -> exact normalized name -> fuzzy normalized name.
        """
        pid = self._safe_product_id(product_id)
        name_norm = self._normalize_text(name)
        category_norm = self._normalize_text(category)
        cache_key = (pid, name_norm, category_norm)

        if cache_key in self.url_lookup_cache:
            return self.url_lookup_cache[cache_key]

        # 1) Exact product_id match
        if pid and pid in self.url_by_product_id:
            url = self.url_by_product_id[pid]
            self.url_lookup_cache[cache_key] = url
            return url

        # 2) Exact normalized name match
        if name_norm and name_norm in self.urls_by_name:
            entries = self.urls_by_name[name_norm]
            if category_norm:
                for entry in entries:
                    if entry["category_norm"] == category_norm:
                        self.url_lookup_cache[cache_key] = entry["url"]
                        return entry["url"]

            url = entries[0]["url"]
            self.url_lookup_cache[cache_key] = url
            return url

        # 3) Fuzzy normalized name match (safety threshold)
        best_url = ""
        best_score = 0.0
        if name_norm and self.urls_by_name:
            query_tokens = set(name_norm.split())

            for candidate_name, entries in self.urls_by_name.items():
                ratio = SequenceMatcher(None, name_norm, candidate_name).ratio()

                if query_tokens:
                    cand_tokens = set(candidate_name.split())
                    overlap = len(query_tokens & cand_tokens) / max(
                        len(query_tokens), 1
                    )
                else:
                    overlap = 0.0

                score = (0.7 * ratio) + (0.3 * overlap)
                if score > best_score:
                    if category_norm:
                        category_entries = [
                            e for e in entries if e["category_norm"] == category_norm
                        ]
                        chosen = category_entries[0] if category_entries else entries[0]
                    else:
                        chosen = entries[0]

                    best_score = score
                    best_url = chosen["url"]

        if best_score >= 0.82 and best_url:
            self.url_lookup_cache[cache_key] = best_url
            return best_url

        # Final fallback for click-through continuity
        fallback_url = f"https://tiki.vn/p/{pid}" if pid else ""
        self.url_lookup_cache[cache_key] = fallback_url
        return fallback_url

    def get_products(self):
        """Get products DataFrame"""
        return self.products_df

    def get_reviews(self):
        """Get reviews DataFrame"""
        return self.reviews_df

    def get_timeseries(self):
        """Get timeseries DataFrame"""
        return self.timeseries_df

    def search_products(
        self, keyword: str, limit: int = 20, use_relevance_boost: bool = True
    ) -> List[Dict]:
        """
        Search products by keyword with combined relevance and sales ranking.

        Args:
            keyword: Search keyword
            limit: Max number of results
            use_relevance_boost: If True, boost relevance for specialized searches (with model/brand terms)

        Returns:
            List of product dictionaries sorted by relevance + sales
        """
        if self.products_df.empty:
            return []

        # Search in name and category
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()

        # Dùng word boundary (\b) để tránh match substring (vd: "xe" không match "Boxer")
        pattern = r"\b" + re.escape(keyword_lower) + r"\b"

        mask = self.products_df["name"].str.lower().str.contains(
            pattern, na=False, regex=True
        ) | self.products_df["category"].str.lower().str.contains(
            pattern, na=False, regex=True
        )

        results_df = self.products_df[mask].copy()

        # Fallback 1: Nếu không có kết quả khớp chính xác cụm từ, khớp tất cả các từ đơn lẻ trong từ khóa
        if results_df.empty and keyword_words:
            word_masks = []
            for word in keyword_words:
                escaped_word = re.escape(word)
                word_pattern = r"\b" + escaped_word + r"\b"
                word_mask = self.products_df["name"].str.lower().str.contains(word_pattern, na=False, regex=True) | \
                            self.products_df["category"].str.lower().str.contains(word_pattern, na=False, regex=True)
                word_masks.append(word_mask)
            
            if word_masks:
                combined_mask = word_masks[0]
                for m in word_masks[1:]:
                    combined_mask = combined_mask & m
                results_df = self.products_df[combined_mask].copy()

        # Fallback 2: Nếu khớp tất cả từ vẫn trống, cho phép khớp linh hoạt hơn không có \b (nửa từ, hoặc ký tự đặc biệt)
        if results_df.empty and keyword_words:
            word_masks = []
            for word in keyword_words:
                escaped_word = re.escape(word)
                word_mask = self.products_df["name"].str.lower().str.contains(escaped_word, na=False) | \
                            self.products_df["category"].str.lower().str.contains(escaped_word, na=False)
                word_masks.append(word_mask)
            
            if word_masks:
                combined_mask = word_masks[0]
                for m in word_masks[1:]:
                    combined_mask = combined_mask & m
                results_df = self.products_df[combined_mask].copy()

        if results_df.empty:
            return []

        # === RELEVANCE SCORING ===
        # Score products based on keyword match quality
        def calculate_relevance_score(row):
            title = str(row.get("name", "")).lower()
            category = str(row.get("category", "")).lower()
            text = f"{title} {category}"

            score = 0

            # Exact keyword match in title (highest priority)
            if re.search(pattern, title):
                score += 10

            # Keyword in category
            if re.search(pattern, category):
                score += 3

            # Count how many keyword words match (for multi-word searches)
            matching_words = sum(1 for word in keyword_words if word in text)
            score += matching_words * 5

            return score

        results_df["relevance_score"] = results_df.apply(
            calculate_relevance_score, axis=1
        )

        # === COMBINED RANKING ===
        # Normalize quantity_sold for fair comparison
        max_quantity = results_df["quantity_sold"].max()
        results_df["quantity_norm"] = (
            (results_df["quantity_sold"] / max_quantity) if max_quantity > 0 else 0
        )

        # Detect if this is a specialized search (contains model/brand terms)
        # These searches should prioritize relevance over sales volume
        vehicle_keywords = [
            "xe",
            "oto",
            "o to",
            "xe may",
            "xemay",
            "xe dap",
            "xedap",
            "future",
            "vision",
            "pcx",
            "lead",
            "air blade",
        ]
        is_specialized_search = any(kw in keyword_lower for kw in vehicle_keywords)

        if use_relevance_boost and is_specialized_search:
            # For specialized searches: prioritize relevance (70%) over sales (30%)
            results_df["final_score"] = (results_df["relevance_score"] * 0.7) + (
                results_df["quantity_norm"] * 30
            )
        else:
            # For general searches: balanced approach (40% relevance, 60% sales)
            results_df["final_score"] = (results_df["relevance_score"] * 0.4) + (
                results_df["quantity_norm"] * 60
            )

        # Sort by final score (descending), then by quantity_sold as tiebreaker
        results_df = results_df.sort_values(
            ["final_score", "quantity_sold"], ascending=[False, False]
        )

        # Convert to list of dicts
        products = []
        for _, row in results_df.head(limit).iterrows():
            product_url = self.resolve_product_url(
                product_id=row.get("product_id"),
                name=row.get("name"),
                category=row.get("category"),
            )
            products.append(
                {
                    "product_id": str(row["product_id"]),
                    "title": row["name"],
                    "categoryName": row["category"],
                    "price": float(row["original_price"]),
                    "rating": float(row["original_rating"]),
                    "boughtInLastMonth": int(row["quantity_sold"]),
                    "estimated_revenue": float(
                        row["original_price"] * row["quantity_sold"]
                    ),
                    "product_url": product_url,
                    "url_path": product_url,
                }
            )

        return products

    def get_product_by_id(self, product_id: int) -> Dict:
        """Get single product by ID"""
        if self.products_df.empty:
            return {}

        product = self.products_df[self.products_df["product_id"] == product_id]
        if product.empty:
            return {}

        row = product.iloc[0]
        product_url = self.resolve_product_url(
            product_id=row.get("product_id"),
            name=row.get("name"),
            category=row.get("category"),
        )
        return {
            "product_id": str(row["product_id"]),
            "title": row["name"],
            "categoryName": row["category"],
            "price": float(row["original_price"]),
            "rating": float(row["original_rating"]),
            "boughtInLastMonth": int(row["quantity_sold"]),
            "estimated_revenue": float(row["original_price"] * row["quantity_sold"]),
            "product_url": product_url,
            "url_path": product_url,
        }

    def get_reviews_by_product(self, product_id: int):
        """Get all reviews for a product"""
        if self.reviews_df.empty:
            import pandas as pd

            return pd.DataFrame()

        return self.reviews_df[self.reviews_df["product_id"] == product_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get data statistics"""
        return {
            "total_products": len(self.products_df),
            "total_reviews": len(self.reviews_df),
            "total_timeseries_rows": len(self.timeseries_df),
            "data_loaded": not self.products_df.empty,
        }
