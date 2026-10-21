from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models.job import Job
from models.job_match import JobMatch, SavedJob
from models.application import Application
from services.interview_simulator import InterviewSimulator
from services.job_matcher import JobMatcher

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")
simulator = InterviewSimulator()

@interview_bp.route("/")
@login_required
def interview_redirect():
    """Redirects to the most relevant active job practice or job search."""
    app = Application.query.filter_by(user_id=current_user.id).order_by(Application.created_at.desc()).first()
    if app:
        return redirect(url_for("interview.start_interview", job_id=app.job_id))
    saved = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_at.desc()).first()
    if saved:
        return redirect(url_for("interview.start_interview", job_id=saved.job_id))
    job = Job.query.filter_by(status="active").order_by(Job.published_at.desc(), Job.created_at.desc()).first()
    if not job:
        job = Job.query.order_by(Job.created_at.desc()).first()
    if job:
        return redirect(url_for("interview.start_interview", job_id=job.id))
    flash("No active jobs found for interview practice.", "warning")
    return redirect(url_for("jobs.list_jobs"))

@interview_bp.route("/hub")
@login_required
def interview_hub():
    """Mock Interview Practice Command Center & Track Directory."""
    user_apps = Application.query.filter_by(user_id=current_user.id).order_by(Application.created_at.desc()).limit(8).all()
    user_saved = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_at.desc()).limit(8).all()
    active_jobs = Job.query.filter_by(status="active").order_by(Job.published_at.desc()).limit(12).all()
    
    primary_job = None
    if user_apps and user_apps[0].job:
        primary_job = user_apps[0].job
    elif user_saved and user_saved[0].job:
        primary_job = user_saved[0].job
    elif active_jobs:
        primary_job = active_jobs[0]

    return render_template(
        "interview_hub.html",
        primary_job=primary_job,
        user_apps=user_apps,
        user_saved=user_saved,
        active_jobs=active_jobs
    )

@interview_bp.route("/<int:job_id>")
@login_required
def start_interview(job_id):
    job = Job.query.get_or_404(job_id)
    profile = current_user.candidate_profile
    resume = current_user.get_active_resume()

    questions = simulator.generate_interview_questions(job, profile)

    # Compute match score
    match = JobMatch.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    match_score = None
    if match:
        match_score = round(match.match_score)
    elif resume and profile:
        try:
            matcher = JobMatcher()
            match_res = matcher.compute_match(resume, profile, job)
            match_score = round(match_res.get("match_score", 0))
        except Exception:
            match_score = None

    # Candidate profile skills list
    candidate_skills = [s.strip() for s in (profile.skills if profile and profile.skills else [])]

    # Available jobs for instant switching in modal
    user_apps = Application.query.filter_by(user_id=current_user.id).order_by(Application.created_at.desc()).limit(8).all()
    user_saved = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_at.desc()).limit(8).all()
    other_jobs = Job.query.filter(Job.id != job.id, Job.status == "active").order_by(Job.published_at.desc()).limit(8).all()

    return render_template(
        "interview_simulator.html",
        job=job,
        questions=questions,
        profile=profile,
        resume=resume,
        match_score=match_score,
        candidate_skills=candidate_skills,
        user_apps=user_apps,
        user_saved=user_saved,
        other_jobs=other_jobs
    )

@interview_bp.route("/api/evaluate", methods=["POST"])
@login_required
def evaluate_answer():
    data = request.get_json() or {}
    job_id = data.get("job_id")
    question = data.get("question", "")
    answer = data.get("answer", "")
    duration_seconds = data.get("duration_seconds")

    if not job_id or not question or not answer:
        return jsonify({"success": False, "error": "Missing question, answer or job ID"}), 400

    job = Job.query.get_or_404(int(job_id))
    parsed_duration = float(duration_seconds) if duration_seconds else None
    evaluation = simulator.evaluate_star_answer(question, answer, job, duration_seconds=parsed_duration)
    return jsonify({"success": True, "evaluation": evaluation})


@interview_bp.route("/coding/<int:job_id>")
@login_required
def coding_challenge(job_id):
    from services.technical_assessment_service import TechnicalAssessmentService
    job = Job.query.get_or_404(job_id)
    profile = current_user.candidate_profile

    assessment_svc = TechnicalAssessmentService()
    challenge = assessment_svc.generate_coding_challenge(job, profile)
    return render_template("coding_challenge.html", job=job, challenge=challenge)


@interview_bp.route("/coding/<int:job_id>/evaluate", methods=["POST"])
@login_required
def evaluate_coding_challenge(job_id):
    from services.technical_assessment_service import TechnicalAssessmentService
    job = Job.query.get_or_404(job_id)
    data = request.get_json() or {}
    user_code = data.get("code", "")
    challenge = data.get("challenge", {})

    assessment_svc = TechnicalAssessmentService()
    evaluation = assessment_svc.evaluate_submission(challenge, user_code)
    return jsonify({"success": True, "evaluation": evaluation})

