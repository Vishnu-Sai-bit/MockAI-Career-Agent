from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

class WorkdayCollector(BaseCollector):
    platform_name = "workday"

    def fetch_jobs(self, company_key: str, **kwargs) -> List[RawJobRecord]:
        """
        Workday provider adapter.
        Requires company_key and optional site-specific config passed in kwargs:
        - host: e.g. "nvidia.wd5.myworkdayjobs.com"
        - tenant: e.g. "NVIDIA"
        - site: e.g. "NVIDIAExternalCareerSite"
        Or falls back to standard discovery pattern if known in tenant registry.
        """
        config = kwargs.get("config", {})
        host = config.get("host") or f"{company_key}.myworkdayjobs.com"
        tenant = config.get("tenant") or company_key
        site = config.get("site") or f"{company_key}Careers"

        endpoint = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "appliedFacets": {},
            "limit": 20,
            "offset": 0,
            "searchText": ""
        }

        jobs: List[RawJobRecord] = []
        try:
            resp = self.session.post(endpoint, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.info(f"Workday CXS API returned {resp.status_code} for {host}")
                return jobs

            data = resp.json()
            postings = data.get("jobPostings", [])
            for item in postings:
                title = item.get("title", "").strip()
                ext_path = item.get("externalPath", "")
                
                # Extract source job id from externalPath (e.g. /job/San-Jose/Senior-Engineer_JR12345)
                job_id = ext_path.split("_")[-1] if "_" in ext_path else ext_path.strip("/")
                if not job_id:
                    job_id = str(abs(hash(ext_path)))

                base_site_url = f"https://{host}/en-US/{site}"
                original_url = urljoin(base_site_url, ext_path.lstrip("/"))
                apply_url = f"{original_url}/apply"
                
                loc = item.get("locationsText", "")
                work_mode = "remote" if "remote" in loc.lower() or "remote" in title.lower() else "on-site"

                job_record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key=company_key,
                    source_job_id=job_id,
                    title=title,
                    company=company_key.replace("-", " ").title(),
                    location=loc,
                    work_mode=work_mode,
                    description=f"{title} position at {company_key}. Location: {loc}. Review official listing for full details.",
                    original_url=original_url,
                    apply_url=apply_url,
                    source_metadata={"workday_ext_path": ext_path, "postedOn": item.get("postedOn")}
                )
                jobs.append(job_record)

        except Exception as e:
            logger.debug(f"Workday collector error for {company_key}: {e}")

        return jobs
