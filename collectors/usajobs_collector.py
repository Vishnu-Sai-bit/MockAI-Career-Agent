import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from config import Config
from utils.logging_config import logger

class USAJobsCollector(BaseCollector):
    platform_name = "usajobs"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        user_agent = os.getenv("USAJOBS_USER_AGENT", "ai-job-agent@career-platform.local")
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json"
        })

    def fetch_jobs(self, company_key: str = "software", limit: int = 25, **kwargs) -> List[RawJobRecord]:
        """
        Fetches official US Federal government job announcements from USAJOBS API.
        Endpoint: https://data.usajobs.gov/api/search
        """
        api_key = Config.USAJOBS_API_KEY or os.getenv("USAJOBS_API_KEY", "")
        if not api_key:
            logger.info("USAJOBS_API_KEY not provided. USAJobs requires an Authorization-Key header.")
            return []

        user_agent = os.getenv("USAJOBS_USER_AGENT", "ai-job-agent@career-platform.local")
        url = "https://data.usajobs.gov/api/search"
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": user_agent,
            "Authorization-Key": api_key
        }
        params = {
            "Keyword": company_key or "developer",
            "ResultsPerPage": min(limit, 25)
        }

        jobs: List[RawJobRecord] = []
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"USAJobs API returned {resp.status_code}")
                return jobs

            data = resp.json()
            search_result = data.get("SearchResult", {})
            items = search_result.get("SearchResultItems", [])

            for wrapper in items[:limit]:
                desc = wrapper.get("MatchedObjectDescriptor", {})
                job_id = desc.get("PositionID", "")
                if not job_id:
                    continue

                title = desc.get("PositionTitle", "").strip()
                dept = desc.get("DepartmentName", "US Government")
                agency = desc.get("OrganizationName", dept)
                apply_uri = desc.get("ApplyURI", [desc.get("PositionURI", "")])[0]
                pos_uri = desc.get("PositionURI", apply_uri)

                rem_eligible = desc.get("PositionRemoteJobOption", False)
                work_mode = "remote" if rem_eligible else "on-site"

                location_objs = desc.get("PositionLocation", [])
                locations = [l.get("LocationName") for l in location_objs if isinstance(l, dict) and l.get("LocationName")]
                location_str = ", ".join(locations[:2]) if locations else "United States"

                remun = desc.get("PositionRemuneration", [{}])[0]
                min_sal = float(remun.get("MinimumRange", 0)) or None
                max_sal = float(remun.get("MaximumRange", 0)) or None

                pub_date = desc.get("PublicationStartDate", "")
                published_at = None
                if pub_date:
                    try:
                        published_at = datetime.fromisoformat(pub_date)
                    except Exception:
                        published_at = None

                user_area = desc.get("UserArea", {}).get("Details", {})
                summary = user_area.get("JobSummary", f"Official vacancy: {title} at {agency}")

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key="federal-us",
                    source_job_id=str(job_id),
                    title=title,
                    company=agency,
                    department=dept,
                    location=location_str,
                    work_mode=work_mode,
                    employment_type="full-time",
                    salary_min=min_sal,
                    salary_max=max_sal,
                    currency="USD",
                    description=summary,
                    raw_description=summary,
                    required_skills=["Government", "Federal"],
                    original_url=pos_uri,
                    apply_url=apply_uri,
                    published_at=published_at,
                    source_metadata={"position_id": job_id, "control_number": desc.get("PositionID")}
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching USAJobs: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        target = apply_url or original_url
        try:
            resp = self.session.head(target, allow_redirects=True, timeout=self.timeout)
            is_active = resp.status_code in (200, 301, 302, 303, 307, 308)
            return is_active, resp.status_code, "Active" if is_active else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, 0, f"USAJobs live verification error: {str(e)}"
