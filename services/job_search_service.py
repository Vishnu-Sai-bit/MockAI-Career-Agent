from typing import Optional, List, Dict, Any
from sqlalchemy import or_, and_, desc, case
from extensions import db
from models.job import Job
from models.job_match import JobMatch
from models.user import User

class JobSearchService:
    def search_jobs(
        self,
        user: Optional[User] = None,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        work_mode: Optional[str] = None,
        platform: Optional[str] = None,
        experience_level: Optional[str] = None,
        min_match_score: Optional[float] = None,
        date_posted: Optional[str] = None,
        status: str = "active",
        page: int = 1,
        per_page: int = 12,
        sort_by: str = "fresh"
    ) -> Dict[str, Any]:
        """
        Queries and filters jobs with match scores for the given candidate.
        Defaults to freshest jobs first.
        """
        from datetime import datetime, timezone, timedelta

        active_resume = user.get_active_resume() if user else None

        query = Job.query
        if status:
            query = query.filter(Job.status == status)

        # Multi-term keyword filtering
        if keyword:
            terms = [t.strip().lower() for t in keyword.split() if len(t.strip()) > 1]
            tech_terms = [t for t in terms if t not in ("developer", "engineer", "software", "jobs", "job", "position")]
            effective_terms = tech_terms if tech_terms else terms
            
            for term in effective_terms:
                kw = f"%{term}%"
                query = query.filter(
                    or_(
                        Job.title.ilike(kw),
                        Job.company.ilike(kw),
                        Job.department.ilike(kw),
                        Job.description.ilike(kw)
                    )
                )

        if location:
            loc = f"%{location.strip().lower()}%"
            query = query.filter(
                or_(
                    Job.location.ilike(loc),
                    Job.country.ilike(loc),
                    Job.city.ilike(loc)
                )
            )

        if work_mode and work_mode.lower() != "all":
            query = query.filter(Job.work_mode == work_mode.lower())

        if platform and platform.lower() != "all":
            query = query.filter(Job.source_platform == platform.lower())

        if experience_level and experience_level.lower() != "all":
            query = query.filter(Job.experience_level == experience_level.lower())

        # Date posted filtering (24h, 1d, 3d, 7d, 14d, 30d)
        if date_posted and date_posted.lower() != "all":
            now = datetime.now(timezone.utc)
            dp = date_posted.lower()
            cutoff = None
            if dp in ("24h", "1d", "24hours", "1day"):
                cutoff = now - timedelta(hours=24)
            elif dp in ("3d", "3days"):
                cutoff = now - timedelta(days=3)
            elif dp in ("7d", "1w", "week", "7days"):
                cutoff = now - timedelta(days=7)
            elif dp in ("14d", "2w", "14days"):
                cutoff = now - timedelta(days=14)
            elif dp in ("30d", "1m", "month", "30days"):
                cutoff = now - timedelta(days=30)

            if cutoff:
                query = query.filter(Job.published_at >= cutoff)

        if active_resume:
            query = query.outerjoin(
                JobMatch,
                and_(
                    JobMatch.job_id == Job.id,
                    JobMatch.user_id == user.id,
                    JobMatch.resume_id == active_resume.id
                )
            )
            if min_match_score is not None:
                query = query.filter(JobMatch.match_score >= float(min_match_score))

            # Determine candidate's experience years from resume or candidate profile
            cand_years = float(
                (active_resume.parsed_data or {}).get("experience_years") 
                or (user.candidate_profile.experience_years if user and user.candidate_profile else 0.0) 
                or 0.0
            )

            # Experience-tier priority:
            # - Fresher (0 to 1.5 yrs): Fresher / Entry-Level (0-2 Yrs) jobs appear FIRST!
            # - 2 Years Experience (1.5 to 5.0 yrs): 2-5 Yrs (Mid-Level) jobs appear FIRST!
            # - Senior (5.0 to 8.0 yrs): 5-8 Yrs (Senior) jobs appear FIRST!
            # - Lead (8.0+ yrs): 8+ Yrs (Lead) jobs appear FIRST!
            # All remaining jobs outside candidate's tier appear NEXT.
            if cand_years <= 1.5:
                # Fresher preference: entry-level jobs (0-2 yrs), strictly excluding senior or lead roles
                is_sr_or_lead = or_(
                    Job.experience_level.in_(["senior", "lead"]),
                    Job.title.ilike("%senior%"),
                    Job.title.ilike("%lead%"),
                    Job.title.ilike("%principal%"),
                    Job.title.ilike("%staff%"),
                    Job.title.ilike("%director%")
                )
                exp_fit = case(
                    (is_sr_or_lead, 0),
                    (or_(
                        Job.experience_level == "entry",
                        Job.title.ilike("%fresher%"),
                        Job.title.ilike("%internship%"),
                        Job.title.ilike("%junior%"),
                        Job.title.ilike("%jr.%"),
                        Job.title.ilike("%trainee%"),
                        Job.title.ilike("%graduate%")
                    ), 1),
                    else_=0
                )
            elif cand_years < 5.0:
                # 2 years or 2+ years mid-level preference (2-5 yrs)
                exp_fit = case(
                    (Job.experience_level == "mid", 1),
                    (or_(Job.experience_level == "entry", Job.experience_level == "senior"), 0),
                    else_=0
                )
            elif cand_years < 8.0:
                # Senior preference (5-8 yrs)
                exp_fit = case(
                    (Job.experience_level == "senior", 1),
                    else_=0
                )
            else:
                # Lead preference (8+ yrs)
                exp_fit = case(
                    (Job.experience_level == "lead", 1),
                    else_=0
                )

            # Relevance match indicator (match score >= 60%)
            is_matched = case(
                (and_(JobMatch.match_score.isnot(None), JobMatch.match_score >= 60.0), 1),
                else_=0
            )

            if sort_by == "match":
                query = query.order_by(
                    desc(exp_fit),
                    desc(is_matched),
                    desc(JobMatch.match_score),
                    desc(Job.published_at),
                    desc(Job.id)
                )
            elif sort_by == "salary":
                query = query.order_by(
                    desc(exp_fit),
                    desc(is_matched),
                    desc(Job.salary_max),
                    desc(Job.published_at),
                    desc(Job.id)
                )
            elif sort_by == "all_fresh":
                query = query.order_by(desc(Job.published_at), desc(Job.id))
            else:
                # Default: Candidate's experience-matching jobs first (fresher for fresher, 2+ yrs for 2 yrs),
                # ordered by highest relevance and freshness, followed by remaining jobs next
                query = query.order_by(
                    desc(exp_fit),
                    desc(is_matched),
                    desc(JobMatch.match_score),
                    desc(Job.published_at),
                    desc(Job.id)
                )
        else:
            query = query.order_by(desc(Job.published_at), desc(Job.id))

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        results = []
        user_saved_ids = set()
        user_applied_ids = set()
        user_dream_companies = set()

        if user:
            user_saved_ids = {s.job_id for s in user.saved_jobs.all()}
            user_applied_ids = {a.job_id for a in user.applications.all()}
            from services.dream_company_service import DreamCompanyService
            user_dream_companies = DreamCompanyService().get_dream_company_names(user.id)

        cand_years = 0.0
        if active_resume:
            cand_years = float(
                (active_resume.parsed_data or {}).get("experience_years") 
                or (user.candidate_profile.experience_years if user and user.candidate_profile else 0.0) 
                or 0.0
            )

        for job in paginated.items:
            match_obj = None
            if active_resume:
                match_obj = JobMatch.query.filter_by(
                    user_id=user.id,
                    resume_id=active_resume.id,
                    job_id=job.id
                ).first()

            is_job_matched = bool(match_obj and match_obj.match_score and match_obj.match_score >= 60.0)
            is_dream = bool(job.company and job.company.lower().strip() in user_dream_companies)

            # Check if this job specifically fits the candidate's experience tier
            is_job_exp_fit = False
            if active_resume:
                import re
                title_lower = (job.title or "").lower()
                lvl = (job.experience_level or "mid").lower()
                is_sr_lead = lvl in ("senior", "lead") or any(w in title_lower for w in ["senior", "lead", "principal", "staff", "director"])
                if cand_years <= 1.5:
                    is_job_exp_fit = (not is_sr_lead) and (
                        lvl == "entry" or 
                        bool(re.search(r"\b(entry|fresher|intern|internship|junior|jr|graduate|trainee)\b", title_lower))
                    )
                elif cand_years < 5.0:
                    is_job_exp_fit = (lvl == "mid") and not is_sr_lead
                elif cand_years < 8.0:
                    is_job_exp_fit = (lvl == "senior")
                else:
                    is_job_exp_fit = (lvl == "lead")

            results.append({
                "job": job,
                "match": match_obj,
                "is_matched": is_job_matched,
                "is_exp_fit": is_job_exp_fit,
                "is_dream_company": is_dream,
                "is_saved": job.id in user_saved_ids,
                "is_applied": job.id in user_applied_ids
            })

        return {
            "jobs": results,
            "items": results,
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev
        }
