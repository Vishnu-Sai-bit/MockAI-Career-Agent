from typing import Optional, List, Dict, Any
from sqlalchemy import or_, and_, desc
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

            from sqlalchemy import case

            # Prioritize jobs matching candidate resume requirements (>= 60%) first, followed by remaining jobs next
            is_matched = case(
                (and_(JobMatch.match_score.isnot(None), JobMatch.match_score >= 60.0), 1),
                else_=0
            )

            if sort_by == "match":
                query = query.order_by(
                    desc(is_matched),
                    desc(JobMatch.match_score),
                    desc(Job.published_at),
                    desc(Job.id)
                )
            elif sort_by == "salary":
                query = query.order_by(
                    desc(is_matched),
                    desc(Job.salary_max),
                    desc(Job.published_at),
                    desc(Job.id)
                )
            elif sort_by == "all_fresh":
                query = query.order_by(desc(Job.published_at), desc(Job.id))
            else:
                # Default: Resume matched jobs first (highest match & freshest), followed by remaining jobs
                query = query.order_by(
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
            results.append({
                "job": job,
                "match": match_obj,
                "is_matched": is_job_matched,
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
