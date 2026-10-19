from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models.job import Job
from services.interview_simulator import InterviewSimulator

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")
simulator = InterviewSimulator()

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
