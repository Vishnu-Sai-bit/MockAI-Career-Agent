from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.job import Job
from models.job_match import JobMatch, SavedJob
from models.application import Application
from models.interview import InterviewSession, InterviewAnswer
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

    # Load user's past practice sessions & performance metrics
    past_sessions = InterviewSession.query.filter_by(user_id=current_user.id).order_by(InterviewSession.created_at.desc()).limit(10).all()
    avg_score = None
    if past_sessions:
        scores = [s.overall_score for s in past_sessions if s.overall_score and s.overall_score > 0]
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)

    personas = simulator.get_interviewer_personas()
    return render_template(
        "interview_hub.html",
        primary_job=primary_job,
        user_apps=user_apps,
        user_saved=user_saved,
        active_jobs=active_jobs,
        past_sessions=past_sessions,
        avg_score=avg_score,
        personas=personas
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

    personas = simulator.get_interviewer_personas()

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
        other_jobs=other_jobs,
        personas=personas
    )


def _get_candidate_display_name():
    if current_user.is_authenticated:
        if getattr(current_user, "name", None):
            return current_user.name.strip().split()[0].title()
        profile = getattr(current_user, "candidate_profile", None)
        if profile and getattr(profile, "full_name", None):
            return profile.full_name.strip().split()[0].title()
        if getattr(current_user, "email", None):
            return current_user.email.split("@")[0].replace(".", " ").title()
    return "Candidate"


@interview_bp.route("/api/personas")
@login_required
def get_personas():
    """Returns available AI interviewer persona profiles."""
    return jsonify({"success": True, "personas": simulator.get_interviewer_personas()})


@interview_bp.route("/api/voice-session-init", methods=["POST"])
@login_required
def voice_session_init():
    """Initializes a live voice call turn with the interviewer's opening greeting."""
    data = request.get_json() or {}
    job_id = data.get("job_id")
    persona_key = data.get("persona", "technical_lead")
    if not job_id:
        return jsonify({"success": False, "error": "Missing job_id"}), 400

    job = Job.query.get_or_404(int(job_id))
    candidate_name = _get_candidate_display_name()
    init_data = simulator.generate_interviewer_greeting(job, persona_key=persona_key, candidate_name=candidate_name)
    return jsonify({"success": True, **init_data})


@interview_bp.route("/api/voice-turn", methods=["POST"])
@login_required
def voice_turn():
    """
    Processes a live voice answer turn:
    - Runs STAR evaluation & speech delivery analytics
    - Generates conversational verbal reaction spoken out loud by the interviewer
    - Produces adaptive probing follow-up question
    """
    data = request.get_json() or {}
    job_id = data.get("job_id")
    question = data.get("question", "")
    answer = data.get("answer", "")
    duration_seconds = data.get("duration_seconds")
    persona_key = data.get("persona", "technical_lead")

    if not job_id or not question or not answer:
        return jsonify({"success": False, "error": "Missing question, answer or job ID"}), 400

    job = Job.query.get_or_404(int(job_id))
    parsed_duration = float(duration_seconds) if duration_seconds else None
    candidate_name = _get_candidate_display_name()

    turn_result = simulator.generate_voice_turn(
        job=job,
        question=question,
        user_answer=answer,
        duration_seconds=parsed_duration,
        persona_key=persona_key,
        candidate_name=candidate_name
    )
    return jsonify({"success": True, **turn_result})

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


@interview_bp.route("/api/followup", methods=["POST"])
@login_required
def generate_followup():
    """Generates an adaptive, probing follow-up question based on the candidate's answer."""
    data = request.get_json() or {}
    job_id = data.get("job_id")
    question = data.get("question", "")
    answer = data.get("answer", "")

    if not job_id or not question or not answer:
        return jsonify({"success": False, "error": "Missing question, answer or job ID"}), 400

    job = Job.query.get_or_404(int(job_id))
    followup = simulator.generate_followup_question(question, answer, job)
    return jsonify({"success": True, "followup": followup})


@interview_bp.route("/api/reverse-questions/<int:job_id>")
@login_required
def reverse_questions(job_id):
    """Returns high-impact questions the candidate can ask the interviewer."""
    job = Job.query.get_or_404(job_id)
    profile = current_user.candidate_profile
    questions = simulator.generate_questions_to_ask_interviewer(job, profile)
    return jsonify({"success": True, "company": job.company, "role": job.title, "questions": questions})


@interview_bp.route("/api/save-session", methods=["POST"])
@login_required
def save_interview_session():
    """Persists a completed or evaluated interview session to the database."""
    data = request.get_json() or {}
    job_id = data.get("job_id")
    overall_score = float(data.get("overall_score", 0))
    delivery_score = float(data.get("delivery_score", 0))
    average_wpm = float(data.get("average_wpm", 0))
    answers_data = data.get("answers", [])

    job = Job.query.get(int(job_id)) if job_id else None
    company = job.company if job else data.get("company", "Target Company")
    role_title = job.title if job else data.get("role_title", "Software Engineer")

    session = InterviewSession(
        user_id=current_user.id,
        job_id=job.id if job else None,
        company=company,
        role_title=role_title,
        overall_score=overall_score,
        delivery_score=delivery_score,
        average_wpm=average_wpm,
        questions_count=len(answers_data)
    )
    db.session.add(session)
    db.session.flush()

    for item in answers_data:
        ans = InterviewAnswer(
            session_id=session.id,
            question_text=item.get("question", ""),
            question_type=item.get("type", "Behavioral / STAR"),
            user_answer=item.get("answer", ""),
            overall_score=float(item.get("score", 0)),
            star_breakdown=item.get("star_breakdown", {}),
            strengths=item.get("strengths", []),
            areas_for_improvement=item.get("areas_for_improvement", []),
            speech_analytics=item.get("speech_analytics", {}),
            improved_exemplar_answer=item.get("improved_exemplar_answer"),
            followup_question=item.get("followup_question")
        )
        db.session.add(ans)

    db.session.commit()
    return jsonify({"success": True, "session_id": session.id, "message": "Interview session saved successfully!"})


@interview_bp.route("/cheat-sheet/<int:job_id>")
@login_required
def interview_cheat_sheet(job_id):
    """Renders a clean printable/exportable interview cheat sheet."""
    job = Job.query.get_or_404(job_id)
    profile = current_user.candidate_profile
    resume = current_user.get_active_resume()
    sheet_data = simulator.generate_interview_cheat_sheet(job, profile)
    return render_template("interview_cheat_sheet.html", job=job, profile=profile, resume=resume, sheet=sheet_data)


@interview_bp.route("/session/<int:session_id>")
@login_required
def view_session(session_id):
    """Reviews a past practice session and its evaluations."""
    session = InterviewSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    return render_template("interview_session_detail.html", session=session)

