from flask import Blueprint, jsonify, request
from flask_login import current_user
from models.user import User, CandidateProfile
from models.resume import Resume
from services.gemini_service import GeminiService
from utils.logging_config import logger

extension_bp = Blueprint("extension", __name__, url_prefix="/api/v1/extension")

@extension_bp.route("/profile", methods=["GET"])
def get_extension_profile():
    """
    Returns candidate profile data for the Chrome extension autofill engine.
    """
    user = current_user if (current_user and current_user.is_authenticated) else User.query.first()
    if not user:
        return jsonify({"success": False, "error": "No user profile found"}), 404

    profile = user.candidate_profile or CandidateProfile(user_id=user.id)
    resume = user.get_active_resume()
    parsed = resume.parsed_data if resume else {}

    full_name = profile.full_name or parsed.get("name") or user.email.split("@")[0].title()
    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else "Candidate"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    return jsonify({
        "success": True,
        "candidate": {
            "fullName": full_name,
            "firstName": first_name,
            "lastName": last_name,
            "email": user.email,
            "phone": profile.phone or parsed.get("phone") or "",
            "location": profile.location or parsed.get("location") or "Bengaluru, India",
            "headline": profile.headline or parsed.get("headline") or "Software & AI Engineer",
            "summary": profile.summary or parsed.get("summary") or (resume.raw_text[:300] if resume else ""),
            "linkedin": parsed.get("linkedin") or "https://www.linkedin.com/in/vishnusai",
            "github": parsed.get("github") or "https://github.com/vishnusai",
            "website": parsed.get("website") or "https://portfolio.me",
            "skills": profile.skills or parsed.get("skills") or ["Python", "Machine Learning", "FastAPI", "SQL"],
            "experienceYears": profile.experience_years or 3.0,
            "education": profile.education or parsed.get("education") or [],
            "activeResumeId": resume.id if resume else None,
            "activeResumeTitle": resume.profile_title if resume else "Default"
        }
    })

@extension_bp.route("/answer-question", methods=["POST"])
def answer_screening_question():
    """
    Generates intelligent, grounded answers for custom job application screening questions.
    """
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    company = data.get("company", "").strip()
    job_title = data.get("job_title", "").strip()

    if not question:
        return jsonify({"success": False, "error": "Question is required"}), 400

    user = current_user if (current_user and current_user.is_authenticated) else User.query.first()
    profile = user.candidate_profile if user else None
    resume = user.get_active_resume() if user else None

    skills_str = ", ".join(profile.skills if (profile and profile.skills) else ["Software Engineering", "Python", "Cloud Systems"])
    candidate_name = profile.full_name if (profile and profile.full_name) else "Candidate"

    gemini = GeminiService()
    prompt = f"""You are an executive candidate assistant answering an employer screening question.
Candidate Name: {candidate_name}
Target Company: {company or 'The Company'}
Target Role: {job_title or 'Software Engineer'}
Candidate Skills: {skills_str}

SCREENING QUESTION:
"{question}"

Generate a polished, compelling, concise response (under 120 words) that demonstrates domain expertise, enthusiasm, and alignment with the team's mission.
Return response in JSON format:
{{
  "answer": "your generated response here"
}}
"""
    res = gemini.generate_json(prompt)
    if res and "answer" in res:
        return jsonify({"success": True, "answer": res["answer"]})

    # Deterministic fallback response tailored to standard questions
    q_lower = question.lower()
    if "why" in q_lower and ("join" in q_lower or "work" in q_lower or "company" in q_lower):
        answer = f"I am deeply inspired by {company or 'your team'}'s commitment to technological excellence and scalable innovation. My experience in {skills_str} aligns directly with your mission, and I am excited to contribute high-impact solutions to your engineering initiatives."
    elif "notice" in q_lower or "start" in q_lower or "available" in q_lower:
        answer = "I am available to join immediately or within a standard 2 to 4 week transition window."
    elif "salary" in q_lower or "compensation" in q_lower or "expectation" in q_lower:
        answer = "My compensation expectations are aligned with industry market standards for this role and location, and I am open to discussing a mutually beneficial package."
    elif "sponsor" in q_lower or "visa" in q_lower or "authorized" in q_lower:
        answer = "I am legally authorized to work, and happy to provide all necessary documentation."
    else:
        answer = f"Throughout my career in {skills_str}, I have focused on delivering scalable, reliable solutions with measurable business impact. I welcome the opportunity to bring that rigorous problem-solving approach to {company or 'this role'}."

    return jsonify({"success": True, "answer": answer})
