import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

class TheMuseCollector(BaseCollector):
    platform_name = "themuse"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIJobAgent/2.0",
            "Accept": "application/json"
        })

    def fetch_jobs(self, company_key: str = "all", limit: int = 20, **kwargs) -> List[RawJobRecord]:
        """
        Fetches public jobs from The Muse API:
        https://www.themuse.com/api/public/jobs?page=1&descending=true
        Verifies live link availability to strictly reject dead / 404 / 'not found' listings.
        """
        page = kwargs.get("page", 1)
        api_key = os.getenv("THEMUSE_API_KEY", "")
        params = {"page": page, "descending": "true"}
        if api_key:
            params["api_key"] = api_key

        url = "https://www.themuse.com/api/public/jobs"
        jobs: List[RawJobRecord] = []

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"The Muse API returned {resp.status_code}")
                return jobs

            data = resp.json()
            results = data.get("results", [])

            from utils.job_live_check import check_url_live

            for item in results:
                if len(jobs) >= limit:
                    break

                job_id = str(item.get("id", "")).strip()
                if not job_id:
                    continue

                landing_page = item.get("refs", {}).get("landing_page", "").strip()
                if not landing_page:
                    continue

                # Strictly verify link is live to prevent 404 / 'job not found' dead listings
                is_live, _, _ = check_url_live(landing_page, timeout=3)
                if not is_live:
                    continue

                title = item.get("name", "").strip()
                company_obj = item.get("company", {})
                company_name = company_obj.get("name", "Company").strip() if isinstance(company_obj, dict) else str(company_obj)

                locations = item.get("locations", [])
                loc_names = [l.get("name") for l in locations if isinstance(l, dict) and l.get("name")]
                location_str = ", ".join(loc_names) if loc_names else "United States"

                work_mode = "remote" if any("flexible" in (l or "").lower() or "remote" in (l or "").lower() for l in loc_names) else "on-site"

                raw_contents = item.get("contents", "")
                plain_desc = BeautifulSoup(raw_contents, "html.parser").get_text(separator="\n").strip() if raw_contents else ""

                # Categories / skills
                categories = item.get("categories", [])
                skills = [c.get("name") for c in categories if isinstance(c, dict) and c.get("name")]

                # Levels
                levels = item.get("levels", [])
                level_str = levels[0].get("name") if levels and isinstance(levels[0], dict) else "Mid Level"

                # Parse publication_date
                pub_date_str = item.get("publication_date", "")
                published_at = None
                if pub_date_str:
                    try:
                        clean_pub = pub_date_str.replace("Z", "+00:00")
                        published_at = datetime.fromisoformat(clean_pub)
                    except Exception:
                        published_at = None

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key="themuse-feed",
                    source_job_id=job_id,
                    title=title,
                    company=company_name,
                    location=location_str,
                    work_mode=work_mode,
                    employment_type="full-time",
                    experience_level=level_str,
                    description=plain_desc,
                    raw_description=raw_contents,
                    required_skills=skills,
                    original_url=landing_page,
                    apply_url=landing_page,
                    published_at=published_at,
                    source_metadata={
                        "short_name": item.get("short_name"),
                        "categories": skills,
                        "levels": [lvl.get("name") for lvl in levels if isinstance(lvl, dict)]
                    }
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching The Muse jobs: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        return super().verify_job_live(original_url, apply_url or "")
