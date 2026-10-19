from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.salary_intelligence import SalaryIntelligenceService
from models.job import Job

salary_bp = Blueprint("salary", __name__, url_prefix="/salary")
salary_service = SalaryIntelligenceService()

@salary_bp.route("")
@login_required
def salary_home():
    profile = current_user.candidate_profile
    resume = current_user.get_active_resume()
    skills = profile.skills if profile else []
    years = float(profile.experience_years or 2.0) if profile else 2.0
    title = profile.headline or "Software Engineer"
    location = profile.location or "Bengaluru, India"

    estimate = salary_service.estimate_market_salary(title, location, years, skills)
    return render_template("salary_intelligence.html", profile=profile, estimate=estimate)

@salary_bp.route("/api/estimate", methods=["POST"])
@login_required
def estimate_api():
    data = request.get_json() or {}
    title = data.get("title", "Software Engineer")
    location = data.get("location", "Remote")
    years = float(data.get("years", 3.0))
    skills = data.get("skills", ["Python", "Cloud"])

    estimate = salary_service.estimate_market_salary(title, location, years, skills)
    return jsonify({"success": True, "estimate": estimate})

@salary_bp.route("/api/counter-offer", methods=["POST"])
@login_required
def counter_offer_api():
    data = request.get_json() or {}
    company = data.get("company", "Company")
    role = data.get("role", "Software Engineer")
    current_base = float(data.get("current_base", 100000))
    target_base = float(data.get("target_base", 120000))
    justification = data.get("justification", "Strong competitive background and market percentile")

    result = salary_service.generate_counter_offer(company, role, current_base, target_base, justification)
    return jsonify({"success": True, "counter_offer": result})
