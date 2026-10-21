import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from config import Config
from utils.logging_config import logger

class AdzunaCollector(BaseCollector):
    platform_name = "adzuna"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "AIJobAgent/2.0 (Career Intelligence Assistant)",
            "Accept": "application/json"
        })

    def fetch_jobs(self, company_key: str = "in", limit: int = 25, **kwargs) -> List[RawJobRecord]:
        """
        Fetches live jobs using the official Adzuna REST API.
        company_key: country code (e.g., 'in', 'us', 'gb', 'ca') or search topic.
        """
        app_id = Config.ADZUNA_APP_ID or os.getenv("ADZUNA_APP_ID", "")
        app_key = Config.ADZUNA_APP_KEY or os.getenv("ADZUNA_APP_KEY", "")

        if not app_id or not app_key:
            logger.warning("Adzuna API credentials (ADZUNA_APP_ID, ADZUNA_APP_KEY) not configured.")
            return []

        # Determine country from company_key or default to 'in'
        supported_countries = {"in", "us", "gb", "ca", "au", "de", "fr", "nl", "pl", "sg", "za"}
        country = company_key.lower().strip() if company_key.lower().strip() in supported_countries else "in"
        query_what = kwargs.get("what", "developer software engineer data")

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": min(limit, 50),
            "what": query_what
        }

        jobs: List[RawJobRecord] = []
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(f"Adzuna API returned {resp.status_code}: {resp.text[:200]}")
                return jobs

            data = resp.json()
            results = data.get("results", [])

            for item in results[:limit]:
                job_id = str(item.get("id", "")).strip()
                if not job_id:
                    continue

                title = item.get("title", "").strip()
                # Clean up any HTML in title
                if "<" in title and ">" in title:
                    title = BeautifulSoup(title, "html.parser").get_text().strip()

                company_obj = item.get("company", {})
                company_name = company_obj.get("display_name", "Unknown Employer").strip() if isinstance(company_obj, dict) else str(company_obj).strip()

                location_obj = item.get("location", {})
                loc_name = location_obj.get("display_name", "") if isinstance(location_obj, dict) else str(location_obj)

                raw_desc = item.get("description", "")
                plain_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n").strip() if raw_desc else ""

                redirect_url = item.get("redirect_url", "").strip()
                if not redirect_url:
                    continue

                # Parse created date (ISO 8601 like '2026-10-19T02:50:22Z')
                created_str = item.get("created", "")
                published_at = None
                if created_str:
                    try:
                        clean_created = created_str.replace("Z", "+00:00")
                        published_at = datetime.fromisoformat(clean_created)
                    except Exception:
                        published_at = None

                # Extract category tag
                category_obj = item.get("category", {})
                cat_label = category_obj.get("label", "") if isinstance(category_obj, dict) else ""
                skills = [cat_label] if cat_label else []

                # Work mode heuristic
                work_mode = "remote" if "remote" in title.lower() or "remote" in plain_desc.lower()[:200] else "on-site"

                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary_min = float(salary_min) if salary_min is not None else None
                salary_max = float(salary_max) if salary_max is not None else None

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key=country,
                    source_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=loc_name or f"{country.upper()}",
                    work_mode=work_mode,
                    employment_type=item.get("contract_time", "full-time").replace("_", "-"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    description=plain_desc,
                    raw_description=raw_desc,
                    required_skills=skills,
                    original_url=redirect_url,
                    apply_url=redirect_url,
                    published_at=published_at,
                    source_metadata={
                        "adzuna_id": job_id,
                        "adref": item.get("adref"),
                        "category": cat_label,
                        "country": country
                    }
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching Adzuna jobs: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        return super().verify_job_live(original_url, apply_url or "")
