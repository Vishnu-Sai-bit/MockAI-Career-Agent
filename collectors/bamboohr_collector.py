import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

class BambooHRCollector(BaseCollector):
    platform_name = "bamboohr"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIJobAgent/2.0",
            "Accept": "application/json, text/html"
        })

    def fetch_jobs(self, company_key: str, limit: int = 25, **kwargs) -> List[RawJobRecord]:
        """
        Fetches job postings from BambooHR public careers endpoint.
        Endpoint: https://{subdomain}.bamboohr.com/careers/list
        Dynamically resolves company subdomains across 6,200+ enterprise BambooHR tenants.
        """
        clean_key = (company_key or "").strip()
        subdomain = clean_key.lower()
        company_display = clean_key.replace("-", " ").title()

        try:
            from services.bamboohr_directory_service import bamboohr_directory
            matched = bamboohr_directory.get_company(clean_key)
            if matched:
                subdomain = matched.get("subdomain", subdomain)
                company_display = matched.get("company_name", company_display)
        except Exception:
            pass

        endpoint = f"https://{subdomain}.bamboohr.com/careers/list"
        jobs: List[RawJobRecord] = []

        try:
            resp = self.session.get(endpoint, timeout=self.timeout)
            if resp.status_code != 200:
                logger.info(f"BambooHR endpoint returned status {resp.status_code} for {clean_key} (subdomain: {subdomain})")
                return jobs

            # BambooHR careers/list returns JSON with result list
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = resp.json()
                items = data.get("result", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            else:
                try:
                    data = resp.json()
                    items = data.get("result", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                except Exception:
                    items = []

            for item in items[:limit]:
                job_id = str(item.get("id", "")).strip()
                if not job_id:
                    continue

                title = (item.get("jobOpeningName") or item.get("title") or "").strip()
                dept = (item.get("department") or "").strip()
                loc_raw = item.get("location")
                if isinstance(loc_raw, dict):
                    city = loc_raw.get("city") or ""
                    state = loc_raw.get("state") or ""
                    location = f"{city}, {state}".strip(", ") if city or state else ""
                else:
                    location = str(loc_raw or "").strip()
                
                emp_type = (item.get("employmentType") or "full-time").strip().lower()
                title_lower = title.lower()

                job_url = f"https://{subdomain}.bamboohr.com/careers/{job_id}"
                apply_url = job_url

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key=clean_key,
                    source_job_id=job_id,
                    title=title,
                    company=company_display,
                    department=dept,
                    location=location or "Multiple Locations",
                    work_mode="hybrid" if "hybrid" in title_lower else ("remote" if "remote" in title_lower else "on-site"),
                    employment_type=emp_type or "full-time",
                    description=f"Job opening for {title} in {dept or 'team'}.",
                    raw_description=f"<p>Job opening for {title} in {dept or 'team'}.</p>",
                    required_skills=[dept] if dept else [],
                    original_url=job_url,
                    apply_url=apply_url,
                    published_at=datetime.now(timezone.utc),
                    source_metadata={"bamboohr_id": job_id, "subdomain": subdomain, "department": dept}
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching BambooHR jobs for {clean_key}: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        return super().verify_job_live(original_url, apply_url or "")
