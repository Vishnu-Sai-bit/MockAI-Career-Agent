import pytest
from models.job import Job
from models.resume import Resume
from models.user import User, CandidateProfile
from models.alert import JobAlert, AlertNotification
from services.tailored_document_generator import TailoredDocumentGenerator
from services.interview_simulator import InterviewSimulator
from services.salary_intelligence import SalaryIntelligenceService

def test_tailored_document_generator_deterministic():
    gen = TailoredDocumentGenerator()
    user = User(email="vishnu@example.com", password_hash="hash")
    profile = CandidateProfile(
        user=user,
        full_name="Vishnu Sai",
        headline="AI & Data Engineer",
        skills=["Python", "SQL", "Machine Learning"]
    )
    resume = Resume(
        user=user,
        filename="resume.pdf",
        parsed_data={
            "name": "Vishnu Sai",
            "skills": ["Python", "Flask", "SQL"],
            "work_experience": [{"title": "Data Engineer", "company": "Tech", "duration": "2023", "highlights": ["Built pipelines"]}]
        }
    )
    job = Job(
        source_id=1,
        source_platform="workday",
        source_company_key="nvidia",
        source_job_id="JR101",
        title="Senior Python Engineer",
        company="NVIDIA",
        location="Bengaluru",
        required_skills=["Python", "Distributed Systems"],
        description="Looking for senior engineer experienced in Python.",
        original_url="https://nvidia.wd5.myworkdayjobs.com/job",
        apply_url="https://nvidia.wd5.myworkdayjobs.com/job/apply"
    )

    tailored_resume = gen.generate_tailored_resume(resume, profile, job)
    assert tailored_resume is not None
    assert "candidate_name" in tailored_resume
    assert "tailored_summary" in tailored_resume

    cover_letter = gen.generate_tailored_cover_letter(resume, profile, job)
    assert cover_letter is not None
    assert "letter_body" in cover_letter
    assert "NVIDIA" in cover_letter["letter_body"]

def test_interview_simulator_star_evaluation():
    sim = InterviewSimulator()
    job = Job(
        source_id=1,
        source_platform="workday",
        source_company_key="nvidia",
        source_job_id="JR102",
        title="Data Engineer",
        company="NVIDIA",
        location="Bengaluru",
        description="Data engineering role with Python and SQL",
        original_url="https://nvidia.wd5.myworkdayjobs.com/job",
        apply_url="https://nvidia.wd5.myworkdayjobs.com/job/apply"
    )
    user = User(email="vishnu@example.com", password_hash="hash")
    profile = CandidateProfile(user=user, skills=["Python", "SQL"])

    questions = sim.generate_interview_questions(job, profile)
    assert len(questions) >= 3
    assert "question" in questions[0]

    q_text = questions[0]["question"]
    user_answer = "In my last project, our pipeline had high latency (Situation). My task was to optimize the processing time (Task). I refactored the SQL queries and added indexing (Action). This reduced query runtime by 45% and saved $10,000 monthly (Result)."

    eval_result = sim.evaluate_star_answer(q_text, user_answer, job)
    assert "overall_score" in eval_result
    assert "star_breakdown" in eval_result
    assert eval_result["overall_score"] >= 60

def test_salary_intelligence_estimation():
    sal = SalaryIntelligenceService()
    est_inr = sal.estimate_market_salary("Data Engineer", "Bengaluru, India", 3.5, ["Python", "SQL"])
    assert est_inr["currency"] == "INR"
    assert est_inr["median"] > 0
    assert est_inr["percentile_90"] >= est_inr["median"]

    est_usd = sal.estimate_market_salary("Software Engineer", "San Francisco, USA", 5.0, ["Python", "AWS"])
    assert est_usd["currency"] == "USD"
    assert est_usd["median"] >= 80000

    co = sal.generate_counter_offer("NVIDIA", "Senior Engineer", 120000, 140000, "Strong domain expertise")
    assert "email_body" in co
    assert "NVIDIA" in co["email_body"]

def test_job_alert_model():
    alert = JobAlert(
        user_id=1,
        title="Top AI Roles",
        min_match_score=80.0,
        channel="email",
        destination="test@example.com"
    )
    assert alert.min_match_score == 80.0
    assert alert.is_active is True
