from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort, current_app
from flask_login import login_required, current_user
from extensions import db
from models.job import Job, VerificationLog
from models.job_match import JobMatch, SavedJob
from models.job_source import JobSource
from services.job_search_service import JobSearchService
from services.job_verifier import JobVerifier
from services.job_matcher import JobMatcher
from utils.url_validation import validate_external_job_url
from tasks.refresh_jobs import run_job_refresh
from utils.logging_config import logger

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.route("/jobs")
def list_jobs():
    keyword = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    work_mode = request.args.get("work_mode", "all")
    platform = request.args.get("platform", "all")
    exp_level = request.args.get("experience_level", "all")
    date_posted = request.args.get("date_posted", "all")
    sort_by = request.args.get("sort_by", "fresh")
    min_score = request.args.get("min_match")
    page = request.args.get("page", 1, type=int)

    # Ensure matches are computed if user has an active resume but no matches yet
    if current_user.is_authenticated:
        active_resume = current_user.get_active_resume()
        if active_resume:
            match_count = JobMatch.query.filter_by(
                user_id=current_user.id,
                resume_id=active_resume.id
            ).count()
            if match_count == 0:
                from tasks.recompute_matches import recompute_user_matches
                recompute_user_matches(current_user, active_resume)

    search_service = JobSearchService()
    search_data = search_service.search_jobs(
        user=current_user if current_user.is_authenticated else None,
        keyword=keyword or None,
        location=location or None,
        work_mode=work_mode,
        platform=platform,
        experience_level=exp_level,
        date_posted=date_posted,
        sort_by=sort_by,
        min_match_score=float(min_score) if min_score else None,
        page=page,
        per_page=12
    )

    available_platforms = [s.platform for s in JobSource.query.filter_by(is_active=True).all()]
    available_platforms = sorted(list(set(available_platforms)))

    return render_template(
        "jobs.html",
        results=search_data,
        keyword=keyword,
        location=location,
        work_mode=work_mode,
        platform=platform,
        experience_level=exp_level,
        date_posted=date_posted,
        sort_by=sort_by,
        min_score=min_score,
        available_platforms=available_platforms
    )



@jobs_bp.route("/jobs/<int:job_id>")
def job_details(job_id):
    job = Job.query.get_or_404(job_id)
    
    match = None
    is_saved = False
    is_applied = False

    if current_user.is_authenticated:
        active_resume = current_user.get_active_resume()
        if active_resume:
            match = JobMatch.query.filter_by(
                user_id=current_user.id,
                resume_id=active_resume.id,
                job_id=job.id
            ).first()
            if not match:
                matcher = JobMatcher()
                res = matcher.compute_match(active_resume, current_user.candidate_profile, job)
                match = JobMatch(
                    user_id=current_user.id,
                    resume_id=active_resume.id,
                    job_id=job.id,
                    match_score=res["match_score"],
                    score_breakdown=res["score_breakdown"],
                    skill_match_details=res["skill_match_details"],
                    match_explanation=res["match_explanation"],
                    eligibility_flags=res["eligibility_flags"]
                )

        is_saved = SavedJob.query.filter_by(user_id=current_user.id, job_id=job.id).first() is not None
        is_applied = current_user.applications.filter_by(job_id=job.id).first() is not None

    return render_template(
        "job_details.html",
        job=job,
        match=match,
        is_saved=is_saved,
        is_applied=is_applied
    )


@jobs_bp.route("/cover-letter/<int:job_id>")
@jobs_bp.route("/jobs/cover-letter/<int:job_id>")
@login_required
def generate_job_cover_letter(job_id):
    """
    AI Cover Letter Generator: Dynamically merges candidate skills and experience
    with role requirements and company details to generate tailored application materials.
    """
    job = Job.query.get_or_404(job_id)
    resume = current_user.get_active_resume()
    if not resume:
        flash("Please upload a resume first to generate a tailored cover letter.", "info")
        return redirect(url_for("resume.upload_resume"))

    from services.tailored_document_generator import TailoredDocumentGenerator
    doc_gen = TailoredDocumentGenerator()
    cover_data = doc_gen.generate_tailored_cover_letter(resume, current_user.candidate_profile, job)
    return render_template("tailored_cover_letter.html", job=job, doc=cover_data)


@jobs_bp.route("/apply/<int:job_id>")
@jobs_bp.route("/jobs/apply/<int:job_id>")
@jobs_bp.route("/jobs/<int:job_id>/apply")
@jobs_bp.route("/<int:job_id>/apply")
def safe_apply_redirect(job_id):
    """
    Core Grounded Apply Now Route.
    1. Loads the stored job record from database.
    2. Resolves and unwraps verified destination ATS application URL.
    3. Automatically records application into user's CRM with status 'applied'.
    4. Re-verifies live availability.
    5. Returns 302 redirect to employer's official ATS vacancy portal.
    """
    job = Job.query.get_or_404(job_id)

    # Check listing status
    if job.status in ("closed", "expired", "unavailable"):
        flash("This job posting is no longer active or accepting applications.", "warning")
        return redirect(url_for("jobs.job_details", job_id=job.id))

    from services.job_links.normalizer import resolve_verified_apply_link
    is_valid, clean_url, err_msg = resolve_verified_apply_link(job)
    if not is_valid:
        # Fallback to direct validation of raw stored URLs
        destination_url = job.apply_url or job.original_url
        if not destination_url:
            flash("No valid application URL stored for this job.", "danger")
            return redirect(url_for("jobs.job_details", job_id=job.id))
        is_val_fallback, err_fallback, clean_url = validate_external_job_url(
            destination_url,
            expected_platform=job.source_platform
        )
        if not is_val_fallback:
            logger.error(f"Security blocked application redirect for job {job.id}: {err_msg or err_fallback}")
            flash(f"Application link verification failed: {err_msg or err_fallback}", "danger")
            return redirect(url_for("jobs.job_details", job_id=job.id))

    # Automatic Application CRM Tracking
    if current_user.is_authenticated:
        try:
            from services.crm.application_crm import application_crm
            application_crm.record_application(current_user.id, job, status="applied")
        except Exception as e:
            logger.error(f"Error recording CRM application for user {current_user.id}, job {job.id}: {e}")

    # Live re-verification (skipped in test mode)
    if not current_app.config.get("TESTING"):
        verifier = JobVerifier(timeout=5)
        is_live, status_details = verifier.verify_job(job)
        if not is_live:
            job.status = "closed"
            db.session.commit()
            flash(f"Notice: The official source indicates this posting has closed ({status_details}).", "warning")
            return redirect(url_for("jobs.job_details", job_id=job.id))

    # Safe external redirect to verified source posting
    return redirect(clean_url, code=302)


@jobs_bp.route("/api/jobs/save/<int:job_id>", methods=["POST"])
@login_required
def toggle_save_job(job_id):
    job = Job.query.get_or_404(job_id)
    saved = SavedJob.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    
    if saved:
        db.session.delete(saved)
        db.session.commit()
        return jsonify({"saved": False, "message": "Job removed from saved list."})
    else:
        new_save = SavedJob(user_id=current_user.id, job_id=job.id)
        db.session.add(new_save)
        db.session.commit()
        return jsonify({"saved": True, "message": "Job saved to your bookmarks."})


@jobs_bp.route("/saved-jobs")
@login_required
def saved_jobs():
    saved_entries = current_user.saved_jobs.order_by(SavedJob.saved_at.desc()).all()
    active_resume = current_user.get_active_resume()
    
    items = []
    for s in saved_entries:
        match = None
        if active_resume:
            match = JobMatch.query.filter_by(
                user_id=current_user.id,
                resume_id=active_resume.id,
                job_id=s.job.id
            ).first()
        items.append({"saved": s, "job": s.job, "match": match})

    return render_template("saved_jobs.html", items=items)


@jobs_bp.route("/jobs/refresh", methods=["POST"])
@login_required
def refresh_jobs():
    try:
        stats = run_job_refresh(limit_per_source=20)
        active_resume = current_user.get_active_resume()
        if active_resume:
            from tasks.recompute_matches import recompute_user_matches
            recompute_user_matches(current_user, active_resume)
        if stats.get("status") == "already_running":
            flash("Job synchronization is already running in the background.", "info")
        else:
            flash(
                f"Job collection refreshed: {stats['total_added']} new jobs added, "
                f"{stats['total_duplicates']} duplicates skipped from {stats['sources_checked']} sources.",
                "success"
            )
    except Exception as e:
        flash(f"Error during job refresh: {str(e)}", "danger")
    
    return redirect(url_for("jobs.list_jobs"))
