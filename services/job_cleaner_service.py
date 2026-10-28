"""
Job Repository Cleaner Service:
Purges duplicate jobs, inactive/closed jobs, closure-signaled jobs, and jobs returning 404/410/Page Not Found.
"""
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import or_

from extensions import db
from models.job import Job, VerificationLog
from utils.job_live_check import check_url_live, CLOSED_URL_SIGNALS, CLOSED_PHRASES
from utils.url_validation import validate_external_job_url
from collectors import get_collector_for_platform
from utils.logging_config import logger

DIRECT_ATS_PLATFORMS = {
    "greenhouse", "lever", "ashby", "workday", "smartrecruiters",
    "workable", "recruitee", "bamboohr", "personio"
}

TITLE_CLOSURE_PHRASES = (
    "[closed]",
    "(closed)",
    "position closed",
    "job closed",
    "not found",
    "no longer accepting",
    "posting expired",
    "listing expired",
    "role closed",
    "filled position",
    "job expired",
    "404",
)

def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())

class JobCleanerService:
    @staticmethod
    def purge_inactive_jobs() -> int:
        """
        Deletes all jobs where status is not 'active' (e.g. closed, expired, unavailable, not_found).
        """
        inactive = Job.query.filter(or_(Job.status.is_(None), Job.status != "active")).all()
        count = len(inactive)
        for job in inactive:
            db.session.delete(job)
        if count > 0:
            db.session.commit()
        logger.info(f"Purged {count} inactive/closed jobs from database.")
        return count

    @staticmethod
    def purge_closure_signal_jobs() -> int:
        """
        Deletes jobs whose title or URL explicitly indicates closure or not-found status.
        """
        active_jobs = Job.query.filter_by(status="active").all()
        to_delete = []

        for j in active_jobs:
            low_title = (j.title or "").lower()
            u = (j.apply_url or j.original_url or "").lower()

            is_closure = any(phrase in low_title for phrase in TITLE_CLOSURE_PHRASES)
            is_url_closed = any(sig in u for sig in CLOSED_URL_SIGNALS)

            if is_closure or is_url_closed:
                to_delete.append(j)

        count = len(to_delete)
        for j in to_delete:
            db.session.delete(j)
        if count > 0:
            db.session.commit()
        logger.info(f"Purged {count} closure-signal / not-found jobs from database.")
        return count

    @staticmethod
    def purge_invalid_or_malformed_url_jobs() -> int:
        """
        Deletes jobs with invalid, malformed, or security-disallowed application URLs.
        """
        active_jobs = Job.query.filter_by(status="active").all()
        to_delete = []

        for j in active_jobs:
            target = j.apply_url or j.original_url
            if not target:
                to_delete.append(j)
                continue
            is_val, _, _ = validate_external_job_url(target, expected_platform=j.source_platform)
            if not is_val:
                to_delete.append(j)

        count = len(to_delete)
        for j in to_delete:
            db.session.delete(j)
        if count > 0:
            db.session.commit()
        logger.info(f"Purged {count} invalid/malformed URL jobs from database.")
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
        Verifies active jobs against official live endpoints and platform APIs.
        Deletes any jobs returning 404, 410, or 'job not found' / 'page not found' closure signals.
        """
        active_jobs = Job.query.filter_by(status="active").all()
        dead_job_ids: Set[int] = set()

        def verify(job: Job):
            target = job.apply_url or job.original_url
            if not target:
                return job.id, False, 0, "No URL provided"

            # Check fast URL signals first
            low_target = target.lower()
            for sig in CLOSED_URL_SIGNALS:
                if sig in low_target:
                    return job.id, False, 404, f"Closed URL signal: {sig}"

            # If Direct ATS collector has custom fast API verify, prefer it
            try:
                collector = get_collector_for_platform(job.source_platform)
                if hasattr(collector, "verify_job_live"):
                    is_live, status_code, details = collector.verify_job_live(
                        original_url=job.original_url,
                        apply_url=job.apply_url,
                        company_key=job.source_company_key,
                        job_id=job.source_job_id
                    )
                    return job.id, is_live, status_code, details
            except Exception:
                pass

            is_live, status_code, details = check_url_live(target, timeout=timeout, max_redirects=3)
            return job.id, is_live, status_code, details

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(verify, j) for j in active_jobs]
            for future in as_completed(futures):
                try:
                    jid, is_live, status_code, details = future.result()
                    if not is_live:
                        low_details = details.lower()
                        is_dead = (
                            status_code in (404, 410, 400)
                            or any(phrase in low_details for phrase in [
                                "job not found", "page not found", "no longer available",
                                "position is closed", "position has been closed", "does not exist",
                                "doesn't exist", "page you are looking for", "document not found",
                                "expired", "404", "closed", "not_found", "no longer open",
                                "position has been filled", "posting has expired", "unlisted"
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
    def run_full_cleanup(cls, check_network: bool = True, max_workers: int = 35) -> Dict[str, Any]:
        """
        Performs full end-to-end repository maintenance:
        1. Purges inactive/closed listings (status != 'active').
        2. Purges closure signal jobs (title/URL signals).
        3. Purges invalid/malformed URL jobs.
        4. (Optional) Purges live dead/404/not-found postings over network.
        5. Purges duplicate company + title postings.
        """
        inactive_purged = cls.purge_inactive_jobs()
        signals_purged = cls.purge_closure_signal_jobs()
        invalid_urls_purged = cls.purge_invalid_or_malformed_url_jobs()
        dead_purged = cls.purge_dead_and_not_found_jobs(max_workers=max_workers) if check_network else 0
        duplicates_purged = cls.purge_duplicate_jobs()
        total_remaining = Job.query.filter_by(status="active").count()

        return {
            "inactive_purged": inactive_purged,
            "signals_purged": signals_purged,
            "invalid_urls_purged": invalid_urls_purged,
            "dead_not_found_purged": dead_purged,
            "duplicates_purged": duplicates_purged,
            "total_purged": inactive_purged + signals_purged + invalid_urls_purged + dead_purged + duplicates_purged,
            "total_remaining_active": total_remaining
        }
