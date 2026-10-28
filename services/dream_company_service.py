import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
from extensions import db
from models.dream_company import DreamCompany
from models.job import Job
from utils.logging_config import logger

def utc_now():
    return datetime.now(timezone.utc)

class DreamCompanyService:
    """
    Manages candidate dream companies watchlist, auto-detects ATS platforms,
    and identifies matching openings in the verified database.
    """

    KNOWN_ATS_PATTERNS = {
        "greenhouse": [r"greenhouse\.io", r"gh_jid"],
        "lever": [r"jobs\.lever\.co"],
        "ashby": [r"ashbyhq\.com"],
        "workday": [r"myworkdayjobs\.com", r"workday"],
        "smartrecruiters": [r"smartrecruiters\.com"],
        "workable": [r"workable\.com"],
        "bamboohr": [r"bamboohr\.com"],
        "personio": [r"personio\.com", r"personio\.de"],
        "recruitee": [r"recruitee\.com"]
    }

    def detect_ats_for_company(self, company_name: str, domain: str = "", careers_url: str = "") -> str:
        """
        Auto-detects the company's ATS platform from URLs or from existing verified vacancies.
        """
        target_text = f"{domain} {careers_url}".lower()

        # 1. Match against known URL signatures
        for platform, patterns in self.KNOWN_ATS_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, target_text):
                    return platform

        # 2. Check if we already have jobs from this company in our DB
        cleaned_name = company_name.strip()
        existing_job = Job.query.filter(Job.company.ilike(f"%{cleaned_name}%")).first()
        if existing_job and existing_job.source_platform:
            return existing_job.source_platform

        # 3. Fallback
        return "company_careers"

    def add_dream_company(self, user_id: int, company_name: str, domain: str = "", careers_url: str = "", ats_platform: str = "auto") -> DreamCompany:
        """
        Adds a new dream company to the user's watchlist with auto-detected ATS platform.
        """
        clean_name = company_name.strip()
        if not clean_name:
            raise ValueError("Company name is required")

        existing = DreamCompany.query.filter_by(user_id=user_id, company_name=clean_name).first()
        if existing:
            existing.is_active = True
            if domain:
                existing.domain = domain.strip()
            if careers_url:
                existing.careers_url = careers_url.strip()
            if ats_platform != "auto":
                existing.ats_platform = ats_platform
            db.session.commit()
            return existing

        detected_ats = ats_platform if ats_platform != "auto" else self.detect_ats_for_company(clean_name, domain, careers_url)

        dc = DreamCompany(
            user_id=user_id,
            company_name=clean_name,
            domain=domain.strip(),
            careers_url=careers_url.strip(),
            ats_platform=detected_ats,
            is_active=True
        )
        db.session.add(dc)
        db.session.commit()
        return dc

    def remove_dream_company(self, user_id: int, company_id: int) -> bool:
        """
        Removes a dream company from the watchlist.
        """
        dc = DreamCompany.query.filter_by(id=company_id, user_id=user_id).first()
        if dc:
            db.session.delete(dc)
            db.session.commit()
            return True
        return False

    def toggle_dream_company(self, user_id: int, company_name: str) -> Dict[str, Any]:
        """
        Toggles follow/unfollow for a company by name for quick 1-click following from job cards.
        """
        clean_name = company_name.strip()
        if not clean_name:
            return {"success": False, "is_following": False, "message": "Company name is required."}

        existing = DreamCompany.query.filter(
            DreamCompany.user_id == user_id,
            DreamCompany.company_name.ilike(clean_name)
        ).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
            return {"success": True, "is_following": False, "message": f"Removed {clean_name} from your Dream Companies."}
        else:
            self.add_dream_company(user_id=user_id, company_name=clean_name)
            return {"success": True, "is_following": True, "message": f"Now tracking {clean_name} as a Dream Company!"}

    def get_user_watchlist(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Returns all tracked companies for a user along with active vacancies found in the DB.
        """
        companies = DreamCompany.query.filter_by(user_id=user_id, is_active=True).order_by(DreamCompany.created_at.desc()).all()
        results = []

        for c in companies:
            # Query active jobs matching this company
            matching_jobs = Job.query.filter(
                Job.status == "active",
                Job.company.ilike(f"%{c.company_name}%")
            ).order_by(Job.published_at.desc()).all()

            results.append({
                "id": c.id,
                "company_name": c.company_name,
                "domain": c.domain,
                "careers_url": c.careers_url,
                "ats_platform": c.ats_platform,
                "created_at": c.created_at,
                "active_jobs_count": len(matching_jobs),
                "latest_jobs": matching_jobs[:3]
            })

        return results

    def get_dream_company_names(self, user_id: int) -> Set[str]:
        """
        Returns lowercased set of active dream company names for fast lookup.
        """
        companies = DreamCompany.query.filter_by(user_id=user_id, is_active=True).all()
        return {c.company_name.lower().strip() for c in companies if c.company_name}

    def scan_dream_company_jobs(self, user_id: int) -> List[Job]:
        """
        Finds all active vacancies from companies on the candidate's watchlist.
        """
        names = self.get_dream_company_names(user_id)
        if not names:
            return []

        or_clauses = [Job.company.ilike(f"%{name}%") for name in names]
        from sqlalchemy import or_
        return Job.query.filter(Job.status == "active", or_(*or_clauses)).order_by(Job.published_at.desc()).all()
