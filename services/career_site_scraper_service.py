"""
Career Site Scraper & Ingestion Service:
Allows candidates and administrators to enter any company's official career site URL
(or company name) and directly scrape, normalize, verify, and ingest its live job postings.

Supports:
- Major ATS platforms: Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable,
  BambooHR, Personio, Recruitee, Breezy, Rippling.
- Direct company career portals containing Schema.org JSON-LD (JobPosting).
- Automatic detection of embedded ATS boards from custom career pages (e.g. careers.company.com).
"""
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import requests

from extensions import db
from models.job import Job
from models.job_source import JobSource
from collectors.greenhouse_collector import GreenhouseCollector
from collectors.lever_collector import LeverCollector
from collectors.ashby_collector import AshbyCollector
from collectors.smartrecruiters_collector import SmartRecruitersCollector
from collectors.workable_collector import WorkableCollector
from collectors.bamboohr_collector import BambooHRCollector
from collectors.personio_collector import PersonioCollector
from collectors.recruitee_collector import RecruiteeCollector
from collectors.company_careers_collector import CompanyCareersCollector
from collectors.base_collector import RawJobRecord
from services.job_normalizer import JobNormalizer
from services.job_deduplicator import JobDeduplicator
from services.unified_platform_directory_service import unified_directory
from utils.url_validation import validate_external_job_url
from utils.logging_config import logger

def utc_now():
    return datetime.now(timezone.utc)

class CareerSiteScraperService:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.normalizer = JobNormalizer()
        self.deduplicator = JobDeduplicator()

    def detect_platform_and_key(self, input_str: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Takes a URL or company name.
        Returns (platform, company_key, display_name).
        """
        clean = (input_str or "").strip()
        if not clean:
            return None, None, None

        # Case 1: Input is a URL
        if clean.startswith("http://") or clean.startswith("https://") or "myworkdayjobs.com" in clean or "greenhouse.io" in clean or "lever.co" in clean or "ashbyhq.com" in clean:
            url = clean if clean.startswith("http") else f"https://{clean}"
            parsed = urlparse(url.lower())
            host = parsed.netloc
            path = parsed.path.strip("/")
            qs = parse_qs(parsed.query)

            # Greenhouse
            if "greenhouse.io" in host:
                if "for" in qs and qs["for"]:
                    key = qs["for"][0].strip()
                    return "greenhouse", key, key.replace("-", " ").title()
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 1 and parts[0] != "embed":
                    return "greenhouse", parts[0], parts[0].replace("-", " ").title()
                elif len(parts) >= 2 and parts[0] == "embed":
                    return "greenhouse", parts[1], parts[1].replace("-", " ").title()

            # Lever
            if "lever.co" in host:
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 1:
                    return "lever", parts[0], parts[0].replace("-", " ").title()

            # Ashby
            if "ashbyhq.com" in host:
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 1:
                    return "ashby", parts[0], parts[0].replace("-", " ").title()

            # Workday
            if "myworkdayjobs.com" in host:
                sub = host.split(".")[0]
                return "workday", sub, sub.replace("-", " ").title()

            # SmartRecruiters
            if "smartrecruiters.com" in host:
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 1:
                    return "smartrecruiters", parts[0], parts[0].replace("-", " ").title()

            # Workable
            if "workable.com" in host:
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 1:
                    return "workable", parts[0], parts[0].replace("-", " ").title()

            # Recruitee
            if "recruitee.com" in host:
                sub = host.split(".")[0]
                return "recruitee", sub, sub.replace("-", " ").title()

            # BambooHR
            if "bamboohr.com" in host:
                sub = host.split(".")[0]
                return "bamboohr", sub, sub.replace("-", " ").title()

            # Personio
            if "personio.de" in host or "personio.com" in host:
                sub = host.split(".")[0]
                return "personio", sub, sub.replace("-", " ").title()

            # Direct company website - probe for embedded ATS or JSON-LD
            try:
                resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    text_lower = resp.text.lower()
                    # Check for embedded ATS links
                    m = re.search(r"https?://(?:boards\.)?greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", text_lower)
                    if m:
                        return "greenhouse", m.group(1), m.group(1).replace("-", " ").title()
                    m = re.search(r"https?://jobs\.lever\.co/([a-z0-9_-]+)", text_lower)
                    if m:
                        return "lever", m.group(1), m.group(1).replace("-", " ").title()
                    m = re.search(r"https?://jobs\.ashbyhq\.com/([a-z0-9_-]+)", text_lower)
                    if m:
                        return "ashby", m.group(1), m.group(1).replace("-", " ").title()
                    m = re.search(r"https?://([a-z0-9_-]+)\.wd\d+\.myworkdayjobs\.com", text_lower)
                    if m:
                        return "workday", m.group(1), m.group(1).replace("-", " ").title()

                    # Fallback to direct company career page
                    domain_name = host.replace("www.", "").replace("careers.", "").split(".")[0]
                    return "company_career", url, domain_name.title()
            except Exception as e:
                logger.debug(f"Error probing career page {url}: {e}")

            domain_name = host.replace("www.", "").replace("careers.", "").split(".")[0]
            return "company_career", url, domain_name.title()

        # Case 2: Input is a Company Name (e.g. "Paytm", "Tekion", "Swiggy", "Postman")
        match = unified_directory.get_company(clean)
        if match:
            plat = match["platform"].lower()
            slug = match["slug"]
            name = match["company_name"]
            careers = match.get("careers_page", "")
            if careers:
                detected_plat, detected_key, _ = self.detect_platform_and_key(careers)
                if detected_plat and detected_key:
                    return detected_plat, detected_key, name
            return plat, slug, name

        # Default fallback: treat as company key on greenhouse or direct
        return "greenhouse", clean.lower().replace(" ", "-"), clean.title()

    def scrape_and_ingest(self, input_str: str, max_jobs: int = 50) -> Dict[str, Any]:
        """
        Scrapes jobs from the specified official career site or company,
        normalizes, deduplicates, and saves them to the database.
        """
        platform, company_key, display_name = self.detect_platform_and_key(input_str)
        if not platform or not company_key:
            return {
                "success": False,
                "error": "Could not identify company or platform from the provided input.",
                "jobs_added": 0,
                "jobs_scraped": 0
            }

        display_name = display_name or company_key.replace("-", " ").title()
        raw_records: List[RawJobRecord] = []

        try:
            if platform == "greenhouse":
                collector = GreenhouseCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "lever":
                collector = LeverCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "ashby":
                collector = AshbyCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "smartrecruiters":
                collector = SmartRecruitersCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "workable":
                collector = WorkableCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "bamboohr":
                collector = BambooHRCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "personio":
                collector = PersonioCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "recruitee":
                collector = RecruiteeCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key)
            elif platform == "workday":
                from services.workday_harvester_service import WorkdayHarvesterService
                harvester = WorkdayHarvesterService()
                res = harvester.harvest_batch([company_key], limit_companies=1, jobs_per_company=max_jobs)
                total_in_db = Job.query.filter(Job.company.ilike(f"%{display_name}%"), Job.status == "active").count()
                return {
                    "success": True,
                    "platform": "Workday",
                    "company_name": display_name,
                    "company_key": company_key,
                    "jobs_scraped": res.get("total_fetched", 0),
                    "jobs_added": res.get("total_added", 0),
                    "total_in_db": total_in_db,
                    "message": f"Successfully scraped {res.get('total_added', 0)} jobs from {display_name} official Workday portal!"
                }
            else:
                # Direct Company Career Portal (JSON-LD)
                collector = CompanyCareersCollector(timeout=self.timeout)
                raw_records = collector.fetch_jobs(company_key=display_name, page_url=company_key if company_key.startswith("http") else input_str)

        except Exception as e:
            logger.error(f"Error scraping {display_name} on {platform}: {e}")
            return {
                "success": False,
                "error": f"Failed connecting to {display_name} official career portal: {str(e)}",
                "jobs_added": 0,
                "jobs_scraped": 0
            }

        total_scraped = len(raw_records)
        if not raw_records:
            return {
                "success": False,
                "error": f"No active public job postings found on {display_name}'s official {platform.title()} career board. The company may currently have 0 open positions or uses a private portal.",
                "jobs_scraped": 0,
                "jobs_added": 0
            }

        # Ensure JobSource
        source = JobSource.query.filter_by(platform=platform, company_key=company_key).first()
        if not source:
            source = JobSource(
                platform=platform,
                company_key=company_key,
                name=f"{display_name} ({platform.title()})",
                is_active=True,
                sync_status="active",
                last_sync_at=utc_now()
            )
            db.session.add(source)
            db.session.commit()
        else:
            source.last_sync_at = utc_now()
            source.sync_status = "active"
            db.session.commit()

        existing_jobs = Job.query.filter_by(status="active").all()
        new_jobs_added = 0
        added_samples = []

        for raw in raw_records[:max_jobs]:
            normalized = self.normalizer.normalize(raw)
            if not normalized.get("company"):
                normalized["company"] = display_name

            # Check duplicate
            dup = self.deduplicator.find_duplicate(normalized, existing_jobs)
            if dup:
                continue

            # Ensure apply URL exists
            target_url = normalized["apply_url"] or normalized["original_url"]
            if not target_url:
                continue

            new_job = Job(
                source_id=source.id,
                source_platform=platform,
                source_company_key=company_key,
                source_job_id=normalized["source_job_id"],
                title=normalized["title"],
                company=display_name,
                department=normalized.get("department", ""),
                location=normalized.get("location", ""),
                country=normalized.get("country", ""),
                city=normalized.get("city", ""),
                work_mode=normalized.get("work_mode", "on-site"),
                employment_type=normalized.get("employment_type", "full-time"),
                experience_level=normalized.get("experience_level", "mid"),
                salary_min=normalized.get("salary_min"),
                salary_max=normalized.get("salary_max"),
                currency=normalized.get("currency", "INR"),
                description=normalized.get("description", ""),
                raw_description=raw.raw_description or "",
                required_skills=normalized.get("required_skills", []),
                preferred_skills=normalized.get("preferred_skills", []),
                original_url=normalized["original_url"],
                apply_url=target_url,
                canonical_url=target_url,
                published_at=normalized.get("published_at") or utc_now(),
                status="active"
            )
            db.session.add(new_job)
            existing_jobs.append(new_job)
            new_jobs_added += 1

            if len(added_samples) < 5:
                added_samples.append({
                    "title": new_job.title,
                    "location": new_job.location or "Not specified",
                    "url": new_job.apply_url
                })

        db.session.commit()
        total_company_jobs = Job.query.filter(Job.company.ilike(f"%{display_name}%"), Job.status == "active").count()

        return {
            "success": True,
            "company_name": display_name,
            "company_key": company_key,
            "platform": platform.title(),
            "jobs_scraped": total_scraped,
            "jobs_added": new_jobs_added,
            "total_in_db": total_company_jobs,
            "sample_jobs": added_samples,
            "redirect_url": f"/jobs?q={display_name}&country=all",
            "message": f"Successfully scraped {total_scraped} live jobs from {display_name} official career portal ({new_jobs_added} new positions added)!"
        }

# Global Singleton
career_site_scraper = CareerSiteScraperService()
