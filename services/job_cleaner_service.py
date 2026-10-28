"""
Job Repository Cleaner Service:
Purges duplicate jobs, inactive/closed jobs, and jobs returning 404/410/Page Not Found.
"""
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from extensions import db
from models.job import Job, VerificationLog
from utils.job_live_check import check_url_live
from utils.logging_config import logger

DIRECT_ATS_PLATFORMS = {
    "greenhouse", "lever", "ashby", "workday", "smartrecruiters",
    "workable", "recruitee", "bamboohr", "personio"
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())

class JobCleanerService:
    @staticmethod
    def purge_inactive_jobs() -> int:
        """
        Deletes all jobs where status is not 'active' (e.g. closed, expired, unavailable).
        """
        inactive = Job.query.filter(Job.status != "active").all()
        count = len(inactive)
        for job in inactive:
            db.session.delete(job)
        if count > 0:
            db.session.commit()
        logger.info(f"Purged {count} inactive/closed jobs from database.")
        return count

    @staticmethod
    def purge_duplicate_jobs() -> int:
        """
        Groups active jobs by (normalized_company, normalized_title).
        For groups with > 1 job, retains the best job (prefers direct ATS, freshest date,
        most complete information) and deletes duplicate instances.
        """
        active_jobs = Job.query.filter_by(status="active").all()
        groups: Dict[Tuple[str, str], List[Job]] = defaultdict(list)

        for j in active_jobs:
            c_norm = normalize_text(j.company)
            t_norm = normalize_text(j.title)
            groups[(c_norm, t_norm)].append(j)

        deleted_count = 0
        for (c_norm, t_norm), job_list in groups.items():
            if len(job_list) <= 1:
                continue

            # Sorting score: prefer Direct ATS > has salary > freshest date
            def job_rank(job: Job):
                is_direct_ats = 1 if (job.source_platform or "").lower() in DIRECT_ATS_PLATFORMS else 0
                has_sal = 1 if (job.salary_min or job.salary_max) else 0
                has_skills = 1 if (job.required_skills and len(job.required_skills) > 0) else 0
                date_val = job.published_at or job.created_at or datetime.min.replace(tzinfo=timezone.utc)
                ts = date_val.timestamp() if hasattr(date_val, "timestamp") else 0
                return (is_direct_ats, has_sal, has_skills, ts)

            sorted_jobs = sorted(job_list, key=job_rank, reverse=True)
            keeper = sorted_jobs[0]
            duplicates = sorted_jobs[1:]

            for dup in duplicates:
                db.session.delete(dup)
                deleted_count += 1

        if deleted_count > 0:
            db.session.commit()
        logger.info(f"Purged {deleted_count} duplicate jobs from database.")
        return deleted_count

    @staticmethod
    def purge_dead_and_not_found_jobs(max_workers: int = 35, timeout: int = 4) -> int:
        """
        Verifies active jobs against official live endpoints.
        Deletes any jobs returning 404, 410, or 'job not found' / 'page not found' closure signals.
        """
        active_jobs = Job.query.filter_by(status="active").all()
        dead_job_ids: Set[int] = set()

        def verify(job: Job):
            target = job.apply_url or job.original_url
            is_live, status_code, details = check_url_live(target, timeout=timeout, max_redirects=3)
            return job.id, is_live, status_code, details

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(verify, j) for j in active_jobs]
            for future in as_completed(futures):
                try:
                    jid, is_live, status_code, details = future.result()
                    if not is_live:
                        # Genuine 404, 410 or in-page closure phrases
                        low_details = details.lower()
                        is_dead = (
                            status_code in (404, 410)
                            or any(phrase in low_details for phrase in [
                                "job not found", "page not found", "no longer available",
                                "position is closed", "position has been closed", "does not exist",
                                "expired", "404"
                            ])
                        )
                        if is_dead:
                            dead_job_ids.add(jid)
                except Exception as e:
                    logger.debug(f"Error checking job during sweep: {e}")

        # Delete all identified dead jobs
        deleted_count = 0
        if dead_job_ids:
            for jid in dead_job_ids:
                j = Job.query.get(jid)
                if j:
                    db.session.delete(j)
                    deleted_count += 1
            db.session.commit()

        logger.info(f"Purged {deleted_count} dead / 404 / 'not found' jobs from database.")
        return deleted_count

    @classmethod
    def run_full_cleanup(cls) -> Dict[str, Any]:
        """
        Performs full end-to-end repository maintenance:
        1. Purges inactive/closed listings.
        2. Purges dead/404/not-found postings.
        3. Purges duplicate company + title postings.
        """
        inactive_purged = cls.purge_inactive_jobs()
        dead_purged = cls.purge_dead_and_not_found_jobs()
        duplicates_purged = cls.purge_duplicate_jobs()
        total_remaining = Job.query.filter_by(status="active").count()

        return {
            "inactive_purged": inactive_purged,
            "dead_not_found_purged": dead_purged,
            "duplicates_purged": duplicates_purged,
            "total_purged": inactive_purged + dead_purged + duplicates_purged,
            "total_remaining_active": total_remaining
        }
