"""
Unified Platform Company Directory Service:
Loads and indexes 39,000+ verified enterprise companies across all 13 ATS platforms:
- Ashby (3,437 companies)
- BambooHR (6,296 companies)
- Breezy (2,042 companies)
- Greenhouse (5,533 companies)
- iCIMS (2,332 companies)
- Lever (1,714 companies)
- Oracle Taleo (1,651 companies)
- Personio (2,075 companies)
- Recruitee (879 companies)
- Rippling (1,411 companies)
- SmartRecruiters (3,163 companies)
- Workable (5,216 companies)
- Workday (3,713 companies)

Provides fast O(1) slug/token lookup, country filtering, and cross-platform search.
"""
import os
import csv
import re
from typing import Dict, Any, List, Optional
from collections import defaultdict
from urllib.parse import urlparse

from utils.logging_config import logger

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def clean_company_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    name = raw_name.strip()
    name = re.sub(r"^(?:US|UK|IN|EU|CA|AU):\s*", "", name, flags=re.I)
    m = re.match(r"^([^\(]+)\s*\([^\)]+\)", name)
    if m:
        name = m.group(1).strip()
    for suffix in [
        " LLC", ", LLC", " Inc.", ", Inc.", " Ltd", " Ltd.", " Limited",
        " S.A.S.", " Corp", ", Corp", " Corporation", " GMBH", " Pty", " N. A.", " NA", " Inc", " Co", " Co."
    ]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    name = re.sub(r"[,.\s]+$", "", name)
    return name.strip() or raw_name.strip()

def make_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")

class UnifiedPlatformDirectoryService:
    _instance: Optional["UnifiedPlatformDirectoryService"] = None

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        self._all_companies: List[Dict[str, Any]] = []
        self._companies_by_slug: Dict[str, Dict[str, Any]] = {}
        self._companies_by_platform: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._companies_by_country: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._platform_counts: Dict[str, int] = defaultdict(int)
        self._load_all_csvs()

    @classmethod
    def get_instance(cls) -> "UnifiedPlatformDirectoryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_all_csvs(self):
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory not found at {self.data_dir}")
            return

        import glob
        pattern = os.path.join(self.data_dir, "companies-using-*.csv")
        csv_files = glob.glob(pattern)

        seen_keys = set()
        for fpath in sorted(csv_files):
            fname = os.path.basename(fpath)
            platform = fname.replace("companies-using-", "").replace(".csv", "").lower()
            try:
                with open(fpath, "r", encoding="utf-8-sig", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        raw_name = (row.get("company") or "").strip()
                        if not raw_name:
                            continue

                        c_name = clean_company_name(raw_name)
                        country = (row.get("main_country") or "").strip().upper() or "GLOBAL"
                        careers_page = (row.get("careers_page") or "").strip()
                        website = (row.get("website") or "").strip()
                        open_jobs_str = (row.get("open_jobs") or "").strip()
                        open_jobs = int(open_jobs_str) if open_jobs_str.isdigit() else 0

                        slug = make_slug(c_name)
                        key = (platform, slug)
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)

                        record = {
                            "company_name": c_name,
                            "company_raw": raw_name,
                            "slug": slug,
                            "platform": platform,
                            "main_country": country,
                            "careers_page": careers_page,
                            "website": website,
                            "open_jobs": open_jobs
                        }

                        self._all_companies.append(record)
                        self._companies_by_platform[platform].append(record)
                        self._companies_by_country[country].append(record)
                        self._platform_counts[platform] += 1

                        # Index by slug
                        if slug not in self._companies_by_slug:
                            self._companies_by_slug[slug] = record
            except Exception as e:
                logger.error(f"Error loading {fpath}: {e}")

        logger.info(f"Unified Directory loaded {len(self._all_companies)} enterprise companies across {len(self._companies_by_platform)} platforms.")

    def get_company(self, key: str, platform: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not key:
            return None
        norm_key = key.lower().strip()
        slug = make_slug(norm_key)

        if platform:
            plat_low = platform.lower().strip()
            for c in self._companies_by_platform.get(plat_low, []):
                if c["slug"] == slug or c["company_name"].lower() == norm_key:
                    return c

        if slug in self._companies_by_slug:
            return self._companies_by_slug[slug]
        for c in self._all_companies:
            if c["company_name"].lower() == norm_key or slug in c["slug"]:
                return c
        return None

    def search_companies(
        self,
        query: str = "",
        platform: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        results = []
        q_low = (query or "").lower().strip()
        plat_low = platform.lower().strip() if platform and platform != "all" else None
        c_upper = country.upper().strip() if country and country != "all" else None

        source_list = self._companies_by_platform[plat_low] if plat_low else self._all_companies

        for c in source_list:
            if c_upper and c["main_country"] != c_upper:
                continue
            if not q_low or q_low in c["company_name"].lower() or q_low in c["slug"]:
                results.append(c)
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_companies": len(self._all_companies),
            "platform_breakdown": dict(self._platform_counts),
            "top_countries": sorted(
                [(c, len(comps)) for c, comps in self._companies_by_country.items()],
                key=lambda x: -x[1]
            )[:15]
        }

# Global Singleton
unified_directory = UnifiedPlatformDirectoryService.get_instance()
