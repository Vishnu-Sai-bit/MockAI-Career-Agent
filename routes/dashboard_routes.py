from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models.job import Job
from models.job_match import JobMatch
from models.job_source import JobSource
from models.application import Application
from tasks.recompute_matches import recompute_user_matches

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def index():
    if current_user.is_authenticated and not request.args.get("landing") and not request.args.get("home") and not request.args.get("preview"):
        return redirect(url_for("dashboard.dashboard"))
    
    # Real database statistics
    total_jobs = Job.query.filter_by(status="active").count()
    total_companies = db.session.query(Job.company).filter(Job.status == "active").distinct().count()
    total_sources = JobSource.query.filter_by(is_active=True).count()
    total_remote_jobs = Job.query.filter(Job.status == "active", Job.work_mode == "remote").count()
    total_india_jobs = Job.query.filter(Job.status == "active").filter(
        Job.country.ilike("%India%") | Job.location.ilike("%India%") | Job.location.ilike("%Bengaluru%")
    ).count()

    # Dynamic featured hero job
    featured_hero_job = Job.query.filter_by(status="active").filter(
        Job.title.ilike("%Software%") | Job.title.ilike("%Engineer%") | Job.title.ilike("%Developer%")
    ).order_by(Job.published_at.desc(), Job.created_at.desc()).first()
    if not featured_hero_job:
        featured_hero_job = Job.query.filter_by(status="active").order_by(Job.published_at.desc(), Job.created_at.desc()).first()

    # Dynamic sample personalized jobs for hero visual
    sample_matches = Job.query.filter_by(status="active").filter(
        Job.company.in_(["SpaceX", "Openai", "Stripe", "Databricks", "Google", "Amazon", "Microsoft", "Anduril Industries"])
    ).order_by(Job.published_at.desc(), Job.created_at.desc()).limit(3).all()
    if len(sample_matches) < 3:
        sample_matches = Job.query.filter_by(status="active").order_by(Job.published_at.desc(), Job.created_at.desc()).limit(3).all()

    # 6 Recent verified job postings for the live jobs section
    recent_jobs = Job.query.filter_by(status="active").order_by(Job.published_at.desc(), Job.created_at.desc()).limit(6).all()

    # Top hiring companies with real open vacancy counts
    top_companies_data = db.session.query(
        Job.company, db.func.count(Job.id).label("openings")
    ).filter(Job.status == "active").group_by(Job.company).order_by(db.desc("openings")).limit(8).all()

    return render_template(
        "index.html",
        total_jobs=total_jobs,
        total_companies=total_companies,
        total_sources=total_sources,
        total_remote_jobs=total_remote_jobs,
        total_india_jobs=total_india_jobs,
        featured_hero_job=featured_hero_job,
        sample_matches=sample_matches,
        recent_jobs=recent_jobs,
        top_companies=top_companies_data
    )


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    profile = current_user.candidate_profile
    active_resume = current_user.get_active_resume()
    
    # Calculate profile completeness
    completeness = 20
    if profile.full_name:
        completeness += 15
    if profile.skills and len(profile.skills) > 0:
        completeness += 25
    if active_resume:
        completeness += 25
    if profile.preferred_titles and len(profile.preferred_titles) > 0:
        completeness += 15
    completeness = min(100, completeness)

    # Top recommended jobs
    top_matches = []
    if active_resume:
        top_matches = JobMatch.query.filter_by(
            user_id=current_user.id,
            resume_id=active_resume.id
        ).join(Job).filter(Job.status == "active").order_by(JobMatch.match_score.desc()).limit(5).all()

    # Recent saved jobs
    saved_jobs = current_user.saved_jobs.order_by(db.desc("saved_at")).limit(5).all()

    # Application stage counts
    app_counts = {
        "saved": 0,
        "prepared": 0,
        "applied": 0,
        "interviewing": 0,
        "offer": 0,
        "rejected": 0
    }
    applications = current_user.applications.all()
    for app in applications:
        if app.status in app_counts:
            app_counts[app.status] += 1

    total_active_jobs = Job.query.filter_by(status="active").count()

    from services.career_analytics_service import CareerAnalyticsService
    analytics_svc = CareerAnalyticsService()
    funnel_metrics = analytics_svc.compute_funnel_metrics(app_counts)
    activity_streak = analytics_svc.compute_user_activity_streak(current_user.id)

    return render_template(
        "dashboard.html",
        profile=profile,
        resume=active_resume,
        completeness=completeness,
        top_matches=top_matches,
        saved_jobs=saved_jobs,
        app_counts=app_counts,
        funnel_metrics=funnel_metrics,
        activity_streak=activity_streak,
        total_applications=len(applications),
        total_active_jobs=total_active_jobs
    )


@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    profile = current_user.candidate_profile
    if not profile:
        profile = CandidateProfile(user=current_user)
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        profile.full_name = request.form.get("full_name", "").strip()
        profile.phone = request.form.get("phone", "").strip()
        profile.location = request.form.get("location", "").strip()
        profile.headline = request.form.get("headline", "").strip()
        profile.summary = request.form.get("summary", "").strip()
        
        # Parse titles
        titles_raw = request.form.get("preferred_titles", "")
        profile.preferred_titles = [t.strip() for t in titles_raw.split(",") if t.strip()]

        # Parse locations
        countries_raw = request.form.get("preferred_countries", "")
        profile.preferred_countries = [c.strip() for c in countries_raw.split(",") if c.strip()]

        cities_raw = request.form.get("preferred_cities", "")
        profile.preferred_cities = [c.strip() for c in cities_raw.split(",") if c.strip()]
        profile.open_to_relocation = ("open_to_relocation" in request.form)

        # Work modes
        modes = request.form.getlist("work_modes")
        profile.work_modes = modes if modes else ["remote", "hybrid", "on-site"]

        profile.experience_level = request.form.get("experience_level", "mid")
        profile.visa_sponsorship_required = bool(request.form.get("visa_sponsorship_required"))

        min_sal = request.form.get("min_salary")
        profile.min_salary = float(min_sal) if min_sal and min_sal.strip() else None
        profile.currency = request.form.get("currency", "INR")

        db.session.commit()

        # Recompute matches with updated preferences
        if current_user.get_active_resume():
            recompute_user_matches(current_user)

        flash("Profile and preferences updated successfully.", "success")
        return redirect(url_for("dashboard.settings"))

    active_resume = current_user.get_active_resume()
    return render_template("settings.html", profile=profile, active_resume=active_resume)


@dashboard_bp.route("/api/candidate-profile")
@login_required
def candidate_profile_api():
    p = current_user.candidate_profile
    resume = current_user.get_active_resume()
    parsed = resume.parsed_data if resume else {}
    full_name = (p.full_name if p else None) or parsed.get("name") or current_user.email.split("@")[0].title()
    return jsonify({
        "success": True,
        "full_name": full_name,
        "email": current_user.email,
        "phone": (p.phone if p else None) or parsed.get("phone") or "",
        "location": (p.location if p else None) or parsed.get("location") or "",
        "headline": (p.headline if p else None) or parsed.get("headline") or "Software Professional",
        "skills": (p.skills if p else None) or parsed.get("skills") or []
    })


@dashboard_bp.route("/sync-jobs", methods=["GET", "POST"])
@login_required
def sync_jobs():
    from tasks.refresh_jobs import run_job_refresh
    try:
        stats = run_job_refresh(limit_per_source=5)
        flash(f"Sync complete! Processed {stats.get('total_fetched', 0)} jobs ({stats.get('new_jobs_added', 0)} new, {stats.get('existing_updated', 0)} updated).", "success")
    except Exception as e:
        flash(f"Job sync completed with status: {str(e)}", "info")
    return redirect(request.referrer or url_for("jobs.list_jobs"))


