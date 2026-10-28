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

        sort_by: str = "fresh",

        only_relevant: bool = False

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

            if dp in ("15m", "15min", "15mins", "15minutes"):

                cutoff = now - timedelta(minutes=15)

            elif dp in ("30m", "30min", "30mins", "30minutes"):

                cutoff = now - timedelta(minutes=30)

            elif dp in ("1h", "1hour", "hour", "60m"):

                cutoff = now - timedelta(hours=1)

            elif dp in ("6h", "6hours"):

                cutoff = now - timedelta(hours=6)

            elif dp in ("12h", "12hours"):

                cutoff = now - timedelta(hours=12)

            elif dp in ("24h", "1d", "24hours", "1day"):

                cutoff = now - timedelta(hours=24)

            elif dp in ("2d", "2days"):

                cutoff = now - timedelta(days=2)

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

        # Location priority: India jobs first (1), remaining global jobs next (0)

        is_india = case(

            (

                or_(

                    Job.country.ilike("%india%"),

                    Job.country.ilike("in"),

                    Job.city.ilike("%bengaluru%"),

                    Job.city.ilike("%bangalore%"),

                    Job.city.ilike("%hyderabad%"),

                    Job.city.ilike("%mumbai%"),

                    Job.city.ilike("%pune%"),

                    Job.city.ilike("%delhi%"),

                    Job.city.ilike("%noida%"),

                    Job.city.ilike("%gurgaon%"),

                    Job.city.ilike("%gurugram%"),

                    Job.city.ilike("%chennai%"),

                    Job.city.ilike("%kolkata%"),

                    Job.city.ilike("%ahmedabad%"),

                    Job.location.ilike("%india%"),

                    Job.location.ilike("%bengaluru%"),

                    Job.location.ilike("%bangalore%"),

                    Job.location.ilike("%hyderabad%"),

                    Job.location.ilike("%mumbai%"),

                    Job.location.ilike("%pune%"),

                    Job.location.ilike("%delhi%"),

                    Job.location.ilike("%noida%"),

                    Job.location.ilike("%gurgaon%"),

                    Job.location.ilike("%gurugram%"),

                    Job.location.ilike("%chennai%"),

                    Job.location.ilike("%kolkata%"),

                    Job.location.ilike("%ahmedabad%")

                ),

                1

            ),

            else_=0

        )

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

            # Target Domain / Role Affinity:

            # Check if candidate has a Data Analyst / Analytics / BI / Data Science focus

            candidate_target = (

                getattr(active_resume, "target_role", "")

                or (active_resume.parsed_data or {}).get("headline")

                or (user.candidate_profile.headline if user and user.candidate_profile else "")

                or ""

            ).lower().strip()

            candidate_skills_lower = [s.lower() for s in (active_resume.parsed_data or {}).get("skills", [])]

            is_data_domain = (

                any(w in candidate_target for w in ["data", "analyst", "analytics", "bi", "sql", "insights"]) or

                any(w in candidate_skills_lower for w in ["power bi", "tableau", "data analysis", "data engineering", "pandas", "numpy", "matplotlib", "seaborn"])

            )

            if is_data_domain:

                domain_fit = case(

                    (Job.title.ilike("%data analyst%"), 3),

                    (or_(

                        Job.title.ilike("%analyst%"),

                        Job.title.ilike("%analytics%"),

                        Job.title.ilike("%business intelligence%"),

                        Job.title.ilike("%bi developer%"),

                        Job.title.ilike("%bi analyst%")

                    ), 2),

                    (or_(

                        Job.title.ilike("%data%"),

                        Job.title.ilike("%machine learning%"),

                        Job.title.ilike("%sql%"),

                        Job.title.ilike("%reporting%")

                    ), 1),

                    else_=0

                )

            elif candidate_target and len(candidate_target) >= 3:

                domain_fit = case(

                    (Job.title.ilike(f"%{candidate_target}%"), 2),

                    else_=0

                )

            else:

                domain_fit = None

            # Strict "Only Relevant Roles" toggle:

            # When active, filters out all remaining/non-matching jobs

            if only_relevant:

                if domain_fit is not None:

                    query = query.filter(or_(domain_fit > 0, JobMatch.match_score >= 60.0))

                elif min_match_score is None:

                    query = query.filter(JobMatch.match_score >= 60.0)

            # Experience Level Detection (strictly identifies senior/lead/manager vs fresher/entry vs mid)

            is_senior_or_lead = or_(

                Job.experience_level.in_(["senior", "lead"]),

                Job.title.ilike("%senior%"),

                Job.title.ilike("%sr.%"),

                Job.title.ilike("%lead%"),

                Job.title.ilike("%staff%"),

                Job.title.ilike("%principal%"),

                Job.title.ilike("%director%"),

                Job.title.ilike("%manager%"),

                Job.title.ilike("%head%")

            )

            is_senior_only = and_(

                ~Job.experience_level.in_(["lead"]),

                ~Job.title.ilike("%lead%"),

                ~Job.title.ilike("%director%"),

                ~Job.title.ilike("%head%"),

                or_(

                    Job.experience_level == "senior",

                    Job.title.ilike("%senior%"),

                    Job.title.ilike("%sr.%")

                )

            )

            is_fresher_entry = and_(

                ~is_senior_or_lead,

                or_(

                    Job.experience_level == "entry",

                    Job.title.ilike("%fresher%"),

                    Job.title.ilike("%intern%"),

                    Job.title.ilike("%internship%"),

                    Job.title.ilike("%junior%"),

                    Job.title.ilike("%jr.%"),

                    Job.title.ilike("%trainee%"),

                    Job.title.ilike("%graduate%"),

                    Job.title.ilike("%working student%"),

                    Job.title.ilike("%associate%")

                )

            )

            is_mid = and_(

                ~is_senior_or_lead,

                ~is_fresher_entry,

                Job.experience_level == "mid"

            )

            # Combined Priority Hierarchy based on Candidate Experience Tier and Domain:

            # - Fresher (0 to 1.5 yrs):

            #     1. Fresher Data Analyst (Direct Target Role)

            #     2. Fresher Analytics / BI / Analyst Related

            #     3. Fresher Data / ML / SQL

            #     4. Mid-level (2-3 / 2-5 yrs) Data Analyst

            #     5. Mid-level Analytics / BI

            #     6. Mid-level Data / ML

            #     7. Other Fresher / Entry roles

            #     8. Other Mid-level roles

            #     9. Senior / Lead Data & Analytics roles

            #     10. All remaining roles

            # - Mid-Level (1.5 to 5.0 yrs): Mid-level Data Analyst first, then Fresher, then Senior

            # - Senior (5.0 to 8.0 yrs): Senior Data roles first

            # - Lead (8.0+ yrs): Lead Data roles first

            if domain_fit is not None:

                if cand_years <= 1.5:

                    priority_rank = case(

                        (and_(is_fresher_entry, domain_fit == 3), 1),

                        (and_(is_fresher_entry, domain_fit == 2), 2),

                        (and_(is_fresher_entry, domain_fit == 1), 3),

                        (and_(is_mid, domain_fit == 3), 4),

                        (and_(is_mid, domain_fit == 2), 5),

                        (and_(is_mid, domain_fit == 1), 6),

                        (is_fresher_entry, 7),

                        (is_mid, 8),

                        (domain_fit >= 1, 9),

                        (is_senior_only, 10),

                        else_=11

                    )

                elif cand_years < 5.0:

                    priority_rank = case(

                        (and_(is_mid, domain_fit == 3), 1),

                        (and_(is_mid, domain_fit == 2), 2),

                        (and_(is_mid, domain_fit == 1), 3),

                        (and_(is_fresher_entry, domain_fit == 3), 4),

                        (and_(is_fresher_entry, domain_fit == 2), 5),

                        (and_(is_fresher_entry, domain_fit == 1), 6),

                        (is_mid, 7),

                        (is_fresher_entry, 8),

                        (domain_fit >= 1, 9),

                        else_=10

                    )

                elif cand_years < 8.0:

                    priority_rank = case(

                        (and_(Job.experience_level == "senior", domain_fit == 3), 1),

                        (and_(Job.experience_level == "senior", domain_fit >= 1), 2),

                        (and_(Job.experience_level == "lead", domain_fit >= 1), 3),

                        (and_(is_mid, domain_fit >= 1), 4),

                        (Job.experience_level == "senior", 5),

                        (Job.experience_level == "lead", 6),

                        (is_mid, 7),

                        else_=8

                    )

                else:

                    priority_rank = case(

                        (and_(Job.experience_level == "lead", domain_fit == 3), 1),

                        (and_(Job.experience_level == "lead", domain_fit >= 1), 2),

                        (and_(Job.experience_level == "senior", domain_fit >= 1), 3),

                        (Job.experience_level == "lead", 4),

                        (Job.experience_level == "senior", 5),

                        else_=6

                    )

            else:

                if cand_years <= 1.5:

                    priority_rank = case(

                        (is_fresher_entry, 1),

                        (is_mid, 2),

                        else_=3

                    )

                elif cand_years < 5.0:

                    priority_rank = case(

                        (is_mid, 1),

                        (is_fresher_entry, 2),

                        else_=3

                    )

                else:

                    priority_rank = case(

                        (Job.experience_level == "senior", 1),

                        (Job.experience_level == "lead", 2),

                        else_=3

                    )

            is_matched_case = case(

                (JobMatch.match_score >= 60.0, 2),

                (JobMatch.match_score.isnot(None), 1),

                else_=0

            )

            if sort_by == "salary":

                query = query.order_by(

                    desc(is_india),

                    priority_rank.asc(),

                    desc(Job.salary_max),

                    desc(JobMatch.match_score),

                    desc(Job.published_at),

                    desc(Job.id)

                )

            elif sort_by == "match":

                query = query.order_by(

                    priority_rank.asc(),

                    desc(is_india),

                    desc(JobMatch.match_score),

                    desc(Job.published_at),

                    desc(Job.id)

                )

            elif sort_by == "all_fresh":

                query = query.order_by(

                    desc(is_india),

                    desc(Job.published_at),

                    desc(Job.id)

                )

            else:
                # Default (Recommended: India Jobs First, Priority/Exp Rank, Matched Roles First, Freshest Minutes/Hours/Days/Weeks):
                query = query.order_by(
                    desc(is_india),
                    priority_rank.asc(),
                    desc(is_matched_case),
                    desc(Job.published_at),
                    desc(JobMatch.match_score),
                    desc(Job.id)
                )

        else:

            query = query.order_by(desc(is_india), desc(Job.published_at), desc(Job.id))

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

        seen_dedup_keys = set()
        for job in paginated.items:
            # Defensive deduplication (never display duplicate company + title)
            c_key = ''.join(ch for ch in (job.company or '').lower() if ch.isalnum())
            t_key = ''.join(ch for ch in (job.title or '').lower() if ch.isalnum())
            dedup_pair = (c_key, t_key)
            if dedup_pair in seen_dedup_keys and c_key and t_key:
                continue
            seen_dedup_keys.add(dedup_pair)

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

                is_sr_lead = lvl in ("senior", "lead") or any(w in title_lower for w in ["senior", "sr.", "lead", "principal", "staff", "director", "manager", "head"])

                if cand_years <= 1.5:

                    is_job_exp_fit = (not is_sr_lead) and (

                        lvl == "entry" or 

                        bool(re.search(r"\b(entry|fresher|intern|internship|junior|jr|graduate|trainee|working student|associate)\b", title_lower))

                    )

                elif cand_years < 5.0:

                    is_job_exp_fit = (lvl == "mid") and not is_sr_lead

                elif cand_years < 8.0:

                    is_job_exp_fit = (lvl == "senior")

                else:

                    is_job_exp_fit = (lvl == "lead")

            loc_text = f"{job.location or ''} {job.country or ''} {job.city or ''}".lower()

            job_is_india = any(k in loc_text for k in ["india", "bengaluru", "bangalore", "hyderabad", "mumbai", "pune", "delhi", "noida", "gurgaon", "gurugram", "chennai", "kolkata", "ahmedabad", "jaipur", "kochi", "indore", "coimbatore"])

            results.append({

                "job": job,

                "match": match_obj,

                "is_matched": is_job_matched,

                "is_exp_fit": is_job_exp_fit,

                "is_india": job_is_india,

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

