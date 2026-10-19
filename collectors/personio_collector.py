import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

class PersonioCollector(BaseCollector):
    platform_name = "personio"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIJobAgent/2.0",
            "Accept": "application/xml, text/xml, */*"
        })

    def fetch_jobs(self, company_key: str, limit: int = 25, **kwargs) -> List[RawJobRecord]:
        """
        Fetches job postings from Personio public XML feed.
        Endpoint: https://{company_slug}.jobs.personio.de/xml
        """
        company_slug = company_key.lower().strip()
        endpoint = f"https://{company_slug}.jobs.personio.de/xml"
        jobs: List[RawJobRecord] = []

        try:
            resp = self.session.get(endpoint, timeout=self.timeout)
            if resp.status_code != 200:
                logger.info(f"Personio XML feed returned status {resp.status_code} for {company_slug}")
                return jobs

            root = ET.fromstring(resp.content)
            # Standard Personio XML schema: <workzag-jobs><position>...
            positions = root.findall(".//position") or root.findall(".//job")

            for pos in positions[:limit]:
                job_id = pos.findtext("id", "").strip()
                if not job_id:
                    continue

                title = pos.findtext("name", "").strip() or pos.findtext("title", "").strip()
                dept = pos.findtext("department", "").strip()
                office = pos.findtext("office", "").strip()
                emp_type = pos.findtext("employmentType", "full-time").strip()

                # Description often in jobDescriptions / jobDescription
                desc_texts = [d.text for d in pos.findall(".//jobDescription/value") if d.text]
                raw_desc = "".join(desc_texts) if desc_texts else pos.findtext("description", "")
                plain_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n").strip() if raw_desc else ""

                job_url = f"https://{company_slug}.jobs.personio.de/job/{job_id}"
                apply_url = f"https://{company_slug}.jobs.personio.de/job/{job_id}#apply"

                record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key=company_slug,
                    source_job_id=job_id,
                    title=title,
                    company=company_slug.replace("-", " ").title(),
                    department=dept,
                    location=office or "European Union",
                    work_mode="remote" if "remote" in office.lower() or "remote" in title.lower() else "on-site",
                    employment_type=emp_type.lower(),
                    description=plain_desc or f"Role: {title} in {dept}",
                    raw_description=raw_desc,
                    required_skills=[dept] if dept else [],
                    original_url=job_url,
                    apply_url=apply_url,
                    published_at=datetime.now(timezone.utc),
                    source_metadata={"personio_id": job_id, "department": dept, "office": office}
                )
                jobs.append(record)

        except Exception as e:
            logger.error(f"Error fetching Personio jobs for {company_slug}: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: Optional[str] = None, **kwargs) -> Tuple[bool, int, str]:
        target = apply_url or original_url
        try:
            resp = self.session.head(target, allow_redirects=True, timeout=self.timeout)
            is_active = resp.status_code in (200, 301, 302, 303, 307, 308)
            return is_active, resp.status_code, "Active" if is_active else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, 0, f"Personio live verification error: {str(e)}"
