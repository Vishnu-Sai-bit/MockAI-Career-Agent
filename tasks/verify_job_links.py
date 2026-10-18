from datetime import datetime, timedelta
from typing import Dict, Any
from extensions import db
from models.job import Job
from services.job_verifier import JobVerifier
from utils.logging_config import logger

def verify_active_jobs(batch_size: int = 20, max_age_hours: int = 12) -> Dict[str, Any]:
    """
    Periodically re-verifies stored job URLs, checks HTTP status codes,
    detects closed/expired listings, and records audit logs.
    """
    verifier = JobVerifier()
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    # Prioritize active jobs that haven't been verified recently
    jobs_to_verify = Job.query.filter(
        Job.status == "active",
        Job.last_verified_at <= cutoff
    ).order_by(Job.last_verified_at.asc()).limit(batch_size).all()

    active_count = 0
    closed_count = 0
    error_count = 0

    for job in jobs_to_verify:
        try:
            is_active, details = verifier.verify_job(job)
            if is_active:
                active_count += 1
            else:
                closed_count += 1
                logger.info(f"Job id {job.id} marked inactive: {details}")
        except Exception as e:
            error_count += 1
            logger.error(f"Verification error for job id {job.id}: {e}")

    return {
        "verified_count": len(jobs_to_verify),
        "still_active": active_count,
        "marked_closed": closed_count,
        "errors": error_count
    }
