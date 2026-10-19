import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

class JobicyCollector(BaseCollector):
    platform_name = "jobicy"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIJobAgent/2.0",
            "Accept": "application/json"
        })

    def fetch_jobs(self, company_key: str = "all", limit: int = 30, **kwargs) -> List[RawJobRecord]:
        """
        Fetches remote jobs from Jobicy public API:
        https://jobicy.com/api/v2/remote-jobs
        """
        count = min(limit, 50)
        url = f"https://jobicy.com/api/v2/remote-jobs?count={count}"
        jobs: List[RawJobRecord] = []

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"Jobicy API returned {resp.status_code}")
                return jobs

            data = resp.json()
            job_entries = data.get("jobs", [])

            for item in job_entries[:limit]:
                job_id = str(item.get("id", "")).strip()
                if not job_id:
                    continue

                title = item.get("jobTitle", "").strip()
                company_name = item.get("companyName", "Company").strip()
                job_url = item.get("url", "").strip()
                if not job_url:
                    continue

                geo = item.get("jobGeo", "").strip()
                location = geo if geo else "Anywhere (Remote)"

                # Job type
                jtype = item.get("jobType")
                if isinstance(jtype, list) and jtype:
                    emp_type = jtype[0]
                elif isinstance(jtype, str):
                    emp_type = jtype
                else:
                    emp_type = "full-time"

                raw_desc = item.get("jobDescription", "")
                plain_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n").strip() if raw_desc else ""

                # Parse pubDate (e.g. '2026-10-19T02:50:22+00:00')
                pub_date_str = item.get("pubDate", "")
                published_at = None
                if pub_date_str:
                    try:
                        clean_pub = pub_date_str.replace("Z", "+00:00")
                        published_at = datetime.fromisoformat(clean_pub)
                    except Exception:
                        published_at = None

                industry = item.get("jobIndustry")
                skills = []
                if isinstance(industry, list):
                    skills.extend([str(x) for x in industry])
                elif isinstance(industry, str) and industry:
                    skills.append(industry)

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key="jobicy-remote",
                    source_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location,
                    work_mode="remote",
                    employment_type=emp_type,
                    description=plain_desc,
                    raw_description=raw_desc,
                    required_skills=skills,
                    original_url=job_url,
                    apply_url=job_url,
                    published_at=published_at,
                    source_metadata={
                        "jobSlug": item.get("jobSlug"),
                        "jobLevel": item.get("jobLevel"),
                        "jobIndustry": industry
                    }
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching Jobicy jobs: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        target = apply_url or original_url
        try:
            resp = self.session.head(target, allow_redirects=True, timeout=self.timeout)
            is_active = resp.status_code in (200, 301, 302, 303, 307, 308)
            return is_active, resp.status_code, "Active" if is_active else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, 0, f"Jobicy live verification error: {str(e)}"
