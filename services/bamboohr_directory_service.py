"""
BambooHR Company Directory Service:
Loads and indexes 6,200+ verified enterprise companies using BambooHR ATS
from 'companies-using-bamboohr.csv'.
Provides fast O(1) slug/subdomain lookup, country-based filtering, and search.
"""
import os
import csv
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from utils.logging_config import logger

PRIMARY_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "companies-using-bamboohr.csv")

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
        " S.A.S.", " Corp", ", Corp", " Corporation", " GMBH", " Pty", " N. A.", " NA", " Inc"
    ]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    name = re.sub(r"[,.\s]+$", "", name)
    return name.strip() or raw_name.strip()

def make_slug(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")

class BambooHRDirectoryService:
    _instance: Optional["BambooHRDirectoryService"] = None

    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = csv_path or PRIMARY_CSV_PATH
        self._companies_by_slug: Dict[str, Dict[str, Any]] = {}
        self._companies_by_subdomain: Dict[str, Dict[str, Any]] = {}
        self._all_companies: List[Dict[str, Any]] = []
        self._load_csv()

    @classmethod
    def get_instance(cls) -> "BambooHRDirectoryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_csv(self):
        if not os.path.exists(self.csv_path):
            logger.warning(f"BambooHR CSV not found at {self.csv_path}")
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                seen_subdomains = set()

                for row in reader:
                    careers_page = (row.get("careers_page") or "").strip()
                    if not careers_page or "bamboohr.com" not in careers_page:
                        continue

                    parsed = urlparse(careers_page)
                    host = parsed.netloc
                    subdomain = host.split(".")[0] if "." in host else ""
                    if not subdomain:
                        continue

                    raw_company = (row.get("company") or "").strip()
                    company_name = clean_company_name(raw_company) or subdomain.title()
                    country = (row.get("main_country") or "").strip().upper() or "GLOBAL"
                    website = (row.get("website") or "").strip()
                    open_jobs_str = (row.get("open_jobs") or "").strip()
                    open_jobs = int(open_jobs_str) if open_jobs_str.isdigit() else 0

                    slug = make_slug(company_name) or subdomain.lower()

                    item = {
                        "company_name": company_name,
                        "company_raw": raw_company,
                        "slug": slug,
                        "subdomain": subdomain.lower(),
                        "careers_page": careers_page,
                        "website": website,
                        "main_country": country,
                        "open_jobs": open_jobs,
                        "platform": "bamboohr"
                    }

                    if subdomain.lower() not in seen_subdomains:
                        seen_subdomains.add(subdomain.lower())
                        self._companies_by_subdomain[subdomain.lower()] = item
                        if slug not in self._companies_by_slug:
                            self._companies_by_slug[slug] = item
                        self._all_companies.append(item)

            logger.info(f"Loaded {len(self._all_companies)} BambooHR companies from {self.csv_path}")
        except Exception as e:
            logger.error(f"Error loading BambooHR CSV {self.csv_path}: {e}")

    def get_company(self, key: str) -> Optional[Dict[str, Any]]:
        if not key:
            return None
        norm_key = key.lower().strip()
        # Direct subdomain match
        if norm_key in self._companies_by_subdomain:
            return self._companies_by_subdomain[norm_key]
        # Direct slug match
        if norm_key in self._companies_by_slug:
            return self._companies_by_slug[norm_key]
        # Make slug
        s = make_slug(norm_key)
        if s in self._companies_by_slug:
            return self._companies_by_slug[s]
        return None

    def search_companies(self, query: str = "", country: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        results = []
        q_low = (query or "").lower().strip()
        c_upper = country.upper() if country else None

        for item in self._all_companies:
            if c_upper and item["main_country"] != c_upper:
                continue
            if not q_low or q_low in item["company_name"].lower() or q_low in item["subdomain"]:
                results.append(item)
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_companies": len(self._all_companies),
            "csv_path": self.csv_path
        }

# Global Singleton
bamboohr_directory = BambooHRDirectoryService.get_instance()
