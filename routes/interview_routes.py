from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models.job import Job
from services.interview_simulator import InterviewSimulator

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")
simulator = InterviewSimulator()

@interview_bp.route("/")
@interview_bp.route("/hub")
@login_required
def interview_hub():
    from models.application import Application
    from models.job import SavedJob
    app = Application.query.filter_by(user_id=current_user.id).order_by(Application.created_at.desc()).first()
    if app:
        return redirect(url_for("interview.start_interview", job_id=app.job_id))
    saved = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_at.desc()).first()
    if saved:
        return redirect(url_for("interview.start_interview", job_id=saved.job_id))
    job = Job.query.filter_by(status="active").order_by(Job.published_at.desc()).first()
    if job:
        return redirect(url_for("interview.start_interview", job_id=job.id))
    flash("No active jobs found for interview practice.", "warning")
    return redirect(url_for("jobs.list_jobs"))

@interview_bp.route("/<int:job_id>")
@login_required
def start_interview(job_id):
    job = Job.query.get_or_404(job_id)
    profile = current_user.candidate_profile
    resume = current_user.get_active_resume()

    questions = simulator.generate_interview_questions(job, profile)
    return render_template("interview_simulator.html", job=job, questions=questions)

@interview_bp.route("/api/evaluate", methods=["POST"])
@login_required
def evaluate_answer():
    data = request.get_json() or {}
    job_id = data.get("job_id")
    question = data.get("question", "")
    answer = data.get("answer", "")

    if not job_id or not question or not answer:
        return jsonify({"success": False, "error": "Missing question, answer or job ID"}), 400

    job = Job.query.get_or_404(int(job_id))
    evaluation = simulator.evaluate_star_answer(question, answer, job)
    return jsonify({"success": True, "evaluation": evaluation})
