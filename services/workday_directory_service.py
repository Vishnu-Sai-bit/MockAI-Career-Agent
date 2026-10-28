"""
Workday Company Directory Service:
Loads and indexes 3,700+ verified enterprise companies using Workday ATS
from 'companies-using-workday.csv'.
Provides fast O(1) slug/tenant lookup, country-based filtering, and search.
"""
import os
import csv
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from utils.logging_config import logger

PRIMARY_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "companies-using-workday.csv")
FALLBACK_CSV_PATH = r"c:\Users\Vishn\Downloads\companies-using-workday.csv"

def clean_company_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    name = raw_name.strip()
    # Strip leading regional prefixes like 'US: '
    name = re.sub(r"^(?:US|UK|IN|EU|CA|AU):\s*", "", name, flags=re.I)
    # Strip subsidiary or legal entity qualifiers like '(BEL Innovex Belgium NV)'
    m = re.match(r"^([^\(]+)\s*\([^\)]+\)", name)
    if m:
        name = m.group(1).strip()
    # Clean legal suffixes
    for suffix in [
        " LLC", ", LLC", " Inc.", ", Inc.", " Ltd", " Ltd.", " Limited",
        " S.A.S.", " Corp", ", Corp", " Corporation", " GMBH", " Pty", " N. A.", " NA", " Inc"
    ]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    # Clean trailing punctuation
    name = re.sub(r"[,.\s]+$", "", name)
    return name.strip() or raw_name.strip()

def make_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")

class WorkdayDirectoryService:
    _instance: Optional["WorkdayDirectoryService"] = None

    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = csv_path or PRIMARY_CSV_PATH
        if not os.path.exists(self.csv_path) and os.path.exists(FALLBACK_CSV_PATH):
            self.csv_path = FALLBACK_CSV_PATH

        self._companies_by_slug: Dict[str, Dict[str, Any]] = {}
        self._companies_by_tenant: Dict[str, Dict[str, Any]] = {}
        self._all_companies: List[Dict[str, Any]] = []
        self._load_csv()

    @classmethod
    def get_instance(cls) -> "WorkdayDirectoryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_csv(self):
        if not os.path.exists(self.csv_path):
            logger.warning(f"Workday CSV not found at {self.csv_path}")
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                seen_slugs = set()

                for row in reader:
                    careers_page = (row.get("careers_page") or "").strip()
                    if not careers_page or "myworkdayjobs.com" not in careers_page:
                        continue

                    parsed = urlparse(careers_page)
                    host = parsed.netloc
                    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                    site = path_parts[0] if path_parts else ""
                    tenant = host.split(".")[0] if "." in host else ""

                    raw_company = (row.get("company") or "").strip()
                    company_name = clean_company_name(raw_company) or tenant.title()
                    country = (row.get("main_country") or "").strip().upper() or "GLOBAL"
                    website = (row.get("website") or "").strip()
                    open_jobs_str = (row.get("open_jobs") or "").strip()
                    open_jobs = int(open_jobs_str) if open_jobs_str.isdigit() else 0

                    slug = make_slug(company_name) or tenant.lower()

                    item = {
                        "company_name": company_name,
                        "company_raw": raw_company,
                        "slug": slug,
                        "tenant": tenant,
                        "host": host,
                        "site": site,
                        "careers_page": careers_page,
                        "website": website,
                        "main_country": country,
                        "open_jobs": open_jobs,
                        "platform": "workday"
                    }

                    # Index by unique slug
                    if slug not in seen_slugs:
                        seen_slugs.add(slug)
                        self._companies_by_slug[slug] = item
                        self._all_companies.append(item)

                    # Also index by tenant for fast URL / key lookups
                    if tenant:
                        self._companies_by_tenant[tenant.lower()] = item

            logger.info(f"Loaded {len(self._all_companies)} Workday companies from {self.csv_path}")
        except Exception as e:
            logger.error(f"Error loading Workday CSV {self.csv_path}: {e}")

    def get_company(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Fast lookup by slug, tenant, or normalized company name.
        """
        if not key:
            return None
        k_norm = make_slug(key)
        if k_norm in self._companies_by_slug:
            return self._companies_by_slug[k_norm]

        k_low = key.lower().strip()
        if k_low in self._companies_by_tenant:
            return self._companies_by_tenant[k_low]

        # Case-insensitive search on company_name
        for comp in self._all_companies:
            if comp["company_name"].lower() == k_low:
                return comp

        return None

    def search_companies(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Filters companies by search keyword and country.
        """
        results = self._all_companies
        if country and country.upper() != "ALL":
            c_target = country.upper().strip()
            results = [c for c in results if c["main_country"] == c_target]

        if query:
            q_norm = query.lower().strip()
            results = [
                c for c in results
                if q_norm in c["company_name"].lower()
                or q_norm in c["slug"]
                or q_norm in c["tenant"].lower()
            ]

        return results[:limit]

    def get_india_companies(self, limit: int = 150) -> List[Dict[str, Any]]:
        """Returns companies with main operations or offices in India."""
        return [c for c in self._all_companies if c["main_country"] == "IN"][:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistical overview of the Workday dataset."""
        countries: Dict[str, int] = {}
        for c in self._all_companies:
            country = c["main_country"]
            countries[country] = countries.get(country, 0) + 1

        top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_companies": len(self._all_companies),
            "total_indexed_tenants": len(self._companies_by_tenant),
            "india_companies_count": countries.get("IN", 0),
            "us_companies_count": countries.get("US", 0),
            "top_countries": dict(top_countries)
        }

# Global singleton accessor
workday_directory = WorkdayDirectoryService.get_instance()
