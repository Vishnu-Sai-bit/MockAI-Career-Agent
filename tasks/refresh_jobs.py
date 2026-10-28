import threading
from datetime import datetime, timezone
from typing import List, Dict, Any
from extensions import db
from models.job_source import JobSource
from models.job import Job
from collectors import get_collector_for_platform
from services.job_normalizer import JobNormalizer
from services.job_deduplicator import JobDeduplicator
from utils.url_validation import validate_external_job_url
from utils.job_live_check import check_url_live
from utils.logging_config import logger

_refresh_lock = threading.Lock()

def utc_now():
    return datetime.now(timezone.utc)

DEFAULT_SOURCES = [
    {"platform": "workday", "company_key": "nvidia", "name": "NVIDIA (Workday)"},
    {"platform": "workday", "company_key": "adobe", "name": "Adobe (Workday)"},
    {"platform": "workday", "company_key": "autodesk", "name": "Autodesk (Workday)"},
    {"platform": "greenhouse", "company_key": "gitlab", "name": "GitLab (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "stripe", "name": "Stripe (Greenhouse)"},
    {"platform": "lever", "company_key": "spotify", "name": "Spotify (Lever)"},
    {"platform": "ashby", "company_key": "linear", "name": "Linear (Ashby)"},
    {"platform": "smartrecruiters", "company_key": "averydennison", "name": "Avery Dennison (SmartRecruiters)"},
    {"platform": "workable", "company_key": "skroutz", "name": "Skroutz (Workable)"},
    {"platform": "recruitee", "company_key": "bunq", "name": "bunq (Recruitee)"},
    {"platform": "ashby", "company_key": "openai", "name": "OpenAI (Ashby)"},
    {"platform": "greenhouse", "company_key": "figma", "name": "Figma (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "reddit", "name": "Reddit (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "airbnb", "name": "Airbnb (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "discord", "name": "Discord (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "databricks", "name": "Databricks (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "coinbase", "name": "Coinbase (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "cloudflare", "name": "Cloudflare (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "inmobi", "name": "InMobi (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "twilio", "name": "Twilio (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "robinhood", "name": "Robinhood (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "elastic", "name": "Elastic (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "pinterest", "name": "Pinterest (Greenhouse)"},
    {"platform": "greenhouse", "company_key": "instacart", "name": "Instacart (Greenhouse)"},
    {"platform": "lever", "company_key": "palantir", "name": "Palantir (Lever)"},
    {"platform": "ashby", "company_key": "supabase", "name": "Supabase (Ashby)"},
    {"platform": "ashby", "company_key": "ramp", "name": "Ramp (Ashby)"},
    {"platform": "greenhouse", "company_key": "anthropic", "name": "Anthropic (Claude AI)"},
    {"platform": "ashby", "company_key": "perplexity", "name": "Perplexity AI"},
    {"platform": "greenhouse", "company_key": "wikimedia", "name": "Wikimedia Foundation"},
    {"platform": "greenhouse", "company_key": "wise", "name": "Wise (TransferWise)"},
    {"platform": "greenhouse", "company_key": "brex", "name": "Brex"},
    {"platform": "greenhouse", "company_key": "groww", "name": "Groww (India)"},
    {"platform": "remotive", "company_key": "all", "name": "Remotive Remote Jobs Feed"},
    {"platform": "arbeitnow", "company_key": "all", "name": "Arbeitnow Global Jobs Feed"},
    {"platform": "remoteok", "company_key": "all", "name": "RemoteOK Tech Jobs Feed"},
    {"platform": "adzuna", "company_key": "in", "name": "Adzuna Jobs (India)"},
    {"platform": "adzuna", "company_key": "us", "name": "Adzuna Jobs (USA)"},
    {"platform": "jobicy", "company_key": "all", "name": "Jobicy Remote Tech Feed"},
    {"platform": "themuse", "company_key": "all", "name": "The Muse Careers Feed"},
    {"platform": "himalayas", "company_key": "all", "name": "Himalayas Curated Remote Feed"}
]

def ensure_default_sources():
    """Initializes standard supported job sources if table is empty."""
    for s in DEFAULT_SOURCES:
        existing = JobSource.query.filter_by(platform=s["platform"], company_key=s["company_key"]).first()
        if not existing:
            source = JobSource(
                platform=s["platform"],
                company_key=s["company_key"],
                name=s["name"],
                is_active=True
            )
            db.session.add(source)
    db.session.commit()

def run_job_refresh(limit_per_source: int = 25) -> Dict[str, Any]:
    """
    Executes end-to-end job collection pipeline:
    Source Fetch -> Normalize -> Deduplicate -> Live Verify -> Persist.
    Also reconciles closed vacancies from official employer ATS feeds.
    Thread-safe with non-blocking acquire to prevent concurrent database write locks.
    """
    if not _refresh_lock.acquire(blocking=False):
        logger.info("Another job refresh cycle is currently running. Skipping duplicate concurrent run.")
        return {
            "sources_checked": 0,
            "total_fetched": 0,
            "total_added": 0,
            "total_duplicates": 0,
            "total_invalid_urls": 0,
            "total_closed_reconciled": 0,
            "status": "already_running"
        }

    try:
        ensure_default_sources()
        active_sources = JobSource.query.filter_by(is_active=True).all()
        normalizer = JobNormalizer()
        deduplicator = JobDeduplicator()

        total_fetched = 0
        total_added = 0
        total_duplicates = 0
        total_invalid_urls = 0
        total_closed_reconciled = 0

        for source in active_sources:
            try:
                logger.info(f"Collecting jobs for source: {source.name} ({source.platform})")
                source.sync_status = "running"
                db.session.commit()

                collector = get_collector_for_platform(source.platform)
                raw_records = collector.fetch_jobs(source.company_key, limit=limit_per_source)
                total_fetched += len(raw_records)

                # Reconcile ATS feeds: if company-specific ATS source returned open vacancies,
                # any previously stored active jobs for this company not in the list are closed!
                if source.platform in ("greenhouse", "lever", "ashby", "workable", "recruitee", "smartrecruiters") and raw_records:
                    fetched_ids = {str(r.source_job_id) for r in raw_records if r.source_job_id}
                    if fetched_ids:
                        stale_active_jobs = Job.query.filter(
                            Job.source_platform == source.platform,
                            Job.source_company_key == source.company_key,
                            Job.status == "active",
                            ~Job.source_job_id.in_(fetched_ids)
                        ).all()
                        for stale in stale_active_jobs:
                            stale.status = "closed"
                            stale.last_verified_at = utc_now()
                            total_closed_reconciled += 1
                        if stale_active_jobs:
                            db.session.commit()

                existing_jobs = Job.query.filter_by(status="active").all()

                for raw in raw_records:
                    normalized = normalizer.normalize(raw)
                    
                    duplicate = deduplicator.find_duplicate(normalized, existing_jobs)
                    if duplicate:
                        total_duplicates += 1
                        continue

                    target_url = normalized["apply_url"] or normalized["original_url"]
                    is_valid, err_msg, clean_url = validate_external_job_url(target_url, expected_platform=source.platform)
                    if not is_valid:
                        logger.debug(f"Skipping job due to invalid URL: {err_msg} ({target_url})")
                        total_invalid_urls += 1
                        continue

                    new_job = Job(
                        source_id=source.id,
                        source_platform=normalized["source_platform"],
                        source_company_key=normalized["source_company_key"],
                        source_job_id=normalized["source_job_id"],
                        title=normalized["title"],
                        company=normalized["company"],
                        department=normalized["department"],
                        location=normalized["location"],
                        country=normalized["country"],
                        city=normalized["city"],
                        work_mode=normalized["work_mode"],
                        employment_type=normalized["employment_type"],
                        experience_level=normalized["experience_level"],
                        salary_min=normalized["salary_min"],
                        salary_max=normalized["salary_max"],
                        currency=normalized["currency"],
                        description=normalized["description"],
                        raw_description=normalized["raw_description"],
                        required_skills=normalized["required_skills"],
                        preferred_skills=normalized["preferred_skills"],
                        original_url=normalized["original_url"],
                        apply_url=normalized["apply_url"],
                        canonical_url=normalized["canonical_url"],
                        published_at=normalized["published_at"] or utc_now(),
                        created_at=utc_now(),
                        last_verified_at=utc_now(),
                        status="active",
                        source_metadata=normalized["source_metadata"]
                    )
                    db.session.add(new_job)
                    existing_jobs.append(new_job)
                    total_added += 1

                source.sync_status = "success"
                source.last_sync_at = utc_now()
                source.sync_error = None
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error in job refresh for source {source.name}: {e}")
                try:
                    source.sync_status = "failed"
                    source.sync_error = str(e)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        return {
            "sources_checked": len(active_sources),
            "total_fetched": total_fetched,
            "total_added": total_added,
            "total_duplicates": total_duplicates,
            "total_invalid_urls": total_invalid_urls,
            "total_closed_reconciled": total_closed_reconciled,
            "status": "success"
        }
    finally:
        _refresh_lock.release()

def prune_dead_jobs(batch_size: int = 50) -> Dict[str, Any]:
    """
    Scans a batch of active jobs with oldest last_verified_at,
    checks if they are still reachable and open, and flags closed ones.
    """
    from services.job_verifier import JobVerifier
    verifier = JobVerifier(timeout=5)
    
    jobs_to_check = Job.query.filter_by(status="active").order_by(Job.last_verified_at.asc()).limit(batch_size).all()
    closed_count = 0
    active_count = 0

    for job in jobs_to_check:
        is_live, _ = verifier.verify_job(job)
        if is_live:
            active_count += 1
        else:
            closed_count += 1

    return {
        "checked": len(jobs_to_check),
        "still_active": active_count,
        "marked_closed": closed_count
    }
