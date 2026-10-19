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
        Endpoint: https://{company_slug}.bamboohr.com/careers/list
        """
        company_slug = company_key.lower().strip()
        endpoint = f"https://{company_slug}.bamboohr.com/careers/list"
        jobs: List[RawJobRecord] = []

        try:
            resp = self.session.get(endpoint, timeout=self.timeout)
            if resp.status_code != 200:
                logger.info(f"BambooHR endpoint returned status {resp.status_code} for {company_slug}")
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

                title = item.get("jobOpeningName", item.get("title", "")).strip()
                dept = item.get("department", "")
                location = item.get("location", {}).get("city", "") if isinstance(item.get("location"), dict) else str(item.get("location", ""))
                
                job_url = f"https://{company_slug}.bamboohr.com/careers/{job_id}"
                apply_url = f"https://{company_slug}.bamboohr.com/careers/{job_id}/apply"

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key=company_slug,
                    source_job_id=job_id,
                    title=title,
                    company=company_slug.replace("-", " ").title(),
                    department=dept,
                    location=location or "Multiple Locations",
                    work_mode="hybrid" if "hybrid" in title.lower() else ("remote" if "remote" in title.lower() else "on-site"),
                    employment_type=item.get("employmentType", "full-time").lower(),
                    description=f"Job opening for {title} in {dept or 'team'}.",
                    raw_description=f"<p>Job opening for {title} in {dept or 'team'}.</p>",
                    required_skills=[dept] if dept else [],
                    original_url=job_url,
                    apply_url=apply_url,
                    published_at=datetime.now(timezone.utc),
                    source_metadata={"bamboohr_id": job_id, "department": dept}
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching BambooHR jobs for {company_slug}: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        target = apply_url or original_url
        try:
            resp = self.session.head(target, allow_redirects=True, timeout=self.timeout)
            is_active = resp.status_code in (200, 301, 302, 303, 307, 308)
            return is_active, resp.status_code, "Active" if is_active else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, 0, f"BambooHR live verification error: {str(e)}"
