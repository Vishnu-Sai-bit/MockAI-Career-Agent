from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collectors.base_collector import BaseCollector, RawJobRecord
from utils.logging_config import logger

def utc_now():
    return datetime.now(timezone.utc)

# Well-known Workday tenants with verified CXS career endpoints
WORKDAY_TENANTS: Dict[str, Dict[str, str]] = {
    "nvidia": {
        "host": "nvidia.wd5.myworkdayjobs.com",
        "tenant": "nvidia",
        "site": "NVIDIAExternalCareerSite",
        "company_name": "NVIDIA"
    },
    "adobe": {
        "host": "adobe.wd5.myworkdayjobs.com",
        "tenant": "adobe",
        "site": "external_experienced",
        "company_name": "Adobe"
    },
    "autodesk": {
        "host": "autodesk.wd1.myworkdayjobs.com",
        "tenant": "autodesk",
        "site": "Ext",
        "company_name": "Autodesk"
    },
    "target": {
        "host": "target.wd5.myworkdayjobs.com",
        "tenant": "target",
        "site": "targetcareers",
        "company_name": "Target"
    },
    "salesforce": {
        "host": "salesforce.wd12.myworkdayjobs.com",
        "tenant": "salesforce",
        "site": "External_Career_Site",
        "company_name": "Salesforce"
    },
    "cisco": {
        "host": "cisco.wd5.myworkdayjobs.com",
        "tenant": "cisco",
        "site": "Cisco_Careers",
        "company_name": "Cisco"
    },
    "intel": {
        "host": "intel.wd1.myworkdayjobs.com",
        "tenant": "intel",
        "site": "External",
        "company_name": "Intel"
    },
    "walmart": {
        "host": "walmart.wd5.myworkdayjobs.com",
        "tenant": "walmart",
        "site": "walmart_careers",
        "company_name": "Walmart"
    },
    "mastercard": {
        "host": "mastercard.wd1.myworkdayjobs.com",
        "tenant": "mastercard",
        "site": "Mastercard_Careers",
        "company_name": "Mastercard"
    },
    "hp": {
        "host": "hp.wd5.myworkdayjobs.com",
        "tenant": "hp",
        "site": "ExternalCareerSite",
        "company_name": "HP"
    },
    "dell": {
        "host": "dell.wd1.myworkdayjobs.com",
        "tenant": "dell",
        "site": "External",
        "company_name": "Dell"
    },
    "nike": {
        "host": "nike.wd1.myworkdayjobs.com",
        "tenant": "nike",
        "site": "Nike_Careers",
        "company_name": "Nike"
    },
    "accenture": {
        "host": "accenture.wd103.myworkdayjobs.com",
        "tenant": "accenture",
        "site": "AccentureCareers",
        "company_name": "Accenture"
    }
}

class WorkdayCollector(BaseCollector):
    platform_name = "workday"

    def fetch_jobs(self, company_key: str, limit: int = 20, **kwargs) -> List[RawJobRecord]:
        """
        Workday provider adapter.
        Queries modern Workday CXS search endpoint and retrieves official job postings.
        Dynamically resolves company configurations across 3,700+ enterprise Workday tenants.
        """
        config = kwargs.get("config", {})
        tenant_info = WORKDAY_TENANTS.get(company_key.lower())
        if tenant_info:
            merged = dict(tenant_info)
            if config:
                for k, v in config.items():
                    if v and k not in ("host", "site"):  # preserve verified host and site
                        merged[k] = v
            config = merged
        elif not config:
            try:
                from services.workday_directory_service import workday_directory
                matched = workday_directory.get_company(company_key)
                if matched:
                    tenant_info = {
                        "host": matched["host"],
                        "tenant": matched["tenant"],
                        "site": matched["site"],
                        "company_name": matched["company_name"]
                    }
            except Exception:
                tenant_info = None
            config = tenant_info or {}

        host = config.get("host") or f"{company_key}.myworkdayjobs.com"
        tenant = config.get("tenant") or company_key
        site = config.get("site") or f"{company_key}Careers"
        company_display = config.get("company_name") or company_key.replace("-", " ").title()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        search_txt = kwargs.get("search_text") or config.get("search_text") or ""
        applied_facets = kwargs.get("applied_facets") or config.get("applied_facets") or {}
        payload = {
            "appliedFacets": applied_facets,
            "limit": min(limit, 20),
            "offset": 0,
            "searchText": search_txt
        }

        jobs: List[RawJobRecord] = []
        try:
        
            # Check primary site and standard fallbacks if primary site is dead/404
            site_candidates = [site]
            if site != "External":
                site_candidates.append("External")
            if site != f"{tenant}Careers":
                site_candidates.append(f"{tenant}Careers")

            postings = []
            active_site = site
            for candidate_site in site_candidates:
                endpoint = f"https://{host}/wday/cxs/{tenant}/{candidate_site}/jobs"
                try:
                    resp = self.session.post(endpoint, json=payload, headers=headers, timeout=self.timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict):
                            postings = data.get("jobPostings", [])
                            active_site = candidate_site
                            break
                except Exception:
                    continue

            if not postings:
                return jobs

            seen_in_batch = set()
            seen_batch_ids = set()

            for item in postings:
                title = item.get("title", "").strip()
                ext_path = item.get("externalPath", "")

                # Aggressively filter out 'not found' or closure signals
                if not title or len(title) < 2:
                    continue
                low_title = title.lower()
                if any(phrase in low_title for phrase in [
                    "not found", "page not found", "job not found",
                    "position closed", "job closed", "[closed]", "(closed)",
                    "no longer accepting", "expired", "404", "error"
                ]):
                    continue

                low_path = ext_path.lower()
                if any(sig in low_path for sig in [
                    "not_found=true", "job_closed=true", "/not-found",
                    "/page-not-found", "/404", "status=closed", "error"
                ]):
                    continue
                
                    # Extract requisition / job ID
                bullet_fields = item.get("bulletFields", [])
                job_id = bullet_fields[0] if bullet_fields else ""
                if not job_id and ext_path:
                    job_id = ext_path.split("_")[-1] if "_" in ext_path else ext_path.strip("/")
                if not job_id:
                    job_id = str(abs(hash(ext_path)))

                base_site_url = f"https://{host}/en-US/{site}"
                clean_path = ext_path.lstrip("/")
                original_url = f"https://{host}/{site}/{clean_path}"
                apply_url = f"https://{host}/{site}/{clean_path}/apply"

                loc = item.get("locationsText", "") or ""
                if not loc and ext_path:
                    parts = ext_path.strip("/").split("/")
                    if len(parts) >= 2 and parts[0] == "job":
                        loc_candidate = parts[1].replace("-", " ")
                        indian_cities = ["Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi", "Noida", "Gurgaon", "Gurugram", "Chennai", "Kolkata"]
                        matched_in_city = next((c for c in indian_cities if c.lower() in loc_candidate.lower()), None)
                        if matched_in_city:
                            loc = f"{matched_in_city}, India"
                        else:
                            loc = loc_candidate
                work_mode = "remote" if "remote" in loc.lower() or "remote" in title.lower() else "on-site"

                # Description and detail handling
                description = f"Official Workday vacancy for {title} at {company_display}. Location: {loc or 'Worldwide'}. Open position on {company_display}'s verified career board."
                raw_html = f"<p>{description}</p>"

                # Fetch full rich HTML if explicitly requested
                if kwargs.get("fetch_detail", False) and ext_path:
                    detail_endpoint = f"https://{host}/wday/cxs/{tenant}/{site}{ext_path}"
                    try:
                        detail_resp = self.session.get(detail_endpoint, headers=headers, timeout=2)
                        if detail_resp.status_code == 200:
                            detail_data = detail_resp.json()
                            info = detail_data.get("jobPostingInfo", {})
                            if info.get("externalUrl"):
                                original_url = info["externalUrl"]
                                apply_url = f"{original_url}/apply"
                            raw_desc = info.get("jobDescription", "")
                            if raw_desc:
                                raw_html = raw_desc
                                description = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n").strip()
                            if info.get("timeType"):
                                emp_type = info["timeType"].lower()
                            if info.get("location"):
                                loc = info["location"]
                    except Exception as ex:
                        logger.debug(f"Could not fetch full Workday detail for {job_id}: {ex}")

                # Intra-batch deduplication: prevent duplicate postings from same company
                norm_key = (title.lower().strip(), (loc or "").lower().strip())
                if norm_key in seen_in_batch or str(job_id) in seen_batch_ids:
                    continue
                seen_in_batch.add(norm_key)
                seen_batch_ids.add(str(job_id))

                job_record = RawJobRecord(
                    source_platform=self.platform_name,
                    source_company_key=company_key.lower(),
                    source_job_id=str(job_id),
                    title=title,
                    company=company_display,
                    location=loc or "Worldwide",
                    work_mode=work_mode,
                    description=description,
                    raw_description=raw_html,
                    original_url=original_url,
                    apply_url=apply_url,
                    published_at=utc_now(),
                    source_metadata={
                        "workday_ext_path": ext_path,
                        "postedOn": item.get("postedOn"),
                        "bulletFields": bullet_fields,
                        "host": host,
                        "site": active_site,
                        "tenant": tenant
                    }
                )
                jobs.append(job_record)

        except Exception as e:
            logger.error(f"Workday collector error for {company_key}: {e}")

        return jobs

    def verify_job_live(self, original_url: str, apply_url: str, company_key: str = "", job_id: str = "") -> Tuple[bool, int, str]:
        """
        Verify availability of Workday posting.
        """
        return super().verify_job_live(original_url, apply_url)
