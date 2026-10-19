import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

class HimalayasCollector(BaseCollector):
    platform_name = "himalayas"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "AIJobAgent/2.0 (Career Intelligence Assistant)",
            "Accept": "application/json"
        })

    def fetch_jobs(self, company_key: str = "all", limit: int = 30, **kwargs) -> List[RawJobRecord]:
        """
        Fetches curated remote tech jobs from Himalayas public API:
        https://himalayas.app/jobs/api
        """
        count = min(limit, 50)
        url = f"https://himalayas.app/jobs/api?limit={count}"
        jobs: List[RawJobRecord] = []

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"Himalayas API returned {resp.status_code}")
                return jobs

            data = resp.json()
            job_entries = data.get("jobs", [])

            for item in job_entries[:limit]:
                title = item.get("title", "").strip()
                company_name = item.get("companyName", "Company").strip()
                app_link = item.get("applicationLink", "").strip()
                guid = item.get("guid", "").strip()
                target_url = app_link or guid
                if not target_url:
                    continue

                # Unique job identifier
                job_id = guid.split("/")[-1] if guid else app_link

                loc_restrictions = item.get("locationRestrictions", [])
                location_str = ", ".join(loc_restrictions) if loc_restrictions else "Remote Worldwide"

                raw_desc = item.get("description", "")
                plain_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n").strip() if raw_desc else ""

                categories = item.get("categories", [])
                skills = [str(c) for c in categories] if categories else []

                # Timestamp
                pub_ts = item.get("pubDate")
                published_at = None
                if pub_ts:
                    try:
                        published_at = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                    except Exception:
                        published_at = None

                min_salary = item.get("minSalary")
                max_salary = item.get("maxSalary")
                min_salary = float(min_salary) if min_salary is not None else None
                max_salary = float(max_salary) if max_salary is not None else None

                raw_seniority = item.get("seniority")
                if isinstance(raw_seniority, list):
                    seniority_str = ", ".join(str(s) for s in raw_seniority) if raw_seniority else "Mid Level"
                else:
                    seniority_str = str(raw_seniority) if raw_seniority else "Mid Level"

                raw_emp = item.get("employmentType")
                if isinstance(raw_emp, list):
                    emp_type_str = str(raw_emp[0]).lower() if raw_emp else "full-time"
                else:
                    emp_type_str = str(raw_emp).lower() if raw_emp else "full-time"

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key="himalayas-remote",
                    source_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_str,
                    work_mode="remote",
                    employment_type=emp_type_str,
                    experience_level=seniority_str,
                    salary_min=min_salary,
                    salary_max=max_salary,
                    currency=item.get("currency") or "USD",
                    description=plain_desc,
                    raw_description=raw_desc,
                    required_skills=skills,
                    original_url=target_url,
                    apply_url=target_url,
                    published_at=published_at,
                    source_metadata={
                        "companySlug": item.get("companySlug"),
                        "seniority": item.get("seniority"),
                        "guid": guid
                    }
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching Himalayas jobs: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        target = apply_url or original_url
        try:
            resp = self.session.head(target, allow_redirects=True, timeout=self.timeout)
            is_active = resp.status_code in (200, 301, 302, 303, 307, 308)
            return is_active, resp.status_code, "Active" if is_active else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, 0, f"Himalayas live verification error: {str(e)}"
