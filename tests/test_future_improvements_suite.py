import pytest
from datetime import datetime, timezone, timedelta
from app import create_app
from extensions import db
from models.user import User, CandidateProfile
from models.job import Job
from models.job_source import JobSource
from models.resume import Resume
from services.resume_optimizer_service import ResumeOptimizerService
from services.outreach_service import OutreachService
from services.interview_simulator import InterviewSimulator
from services.salary_normalizer_service import SalaryNormalizerService
from services.career_analytics_service import CareerAnalyticsService
from services.telegram_bot_service import TelegramBotService

@pytest.fixture
def app_with_db():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def test_user_and_job(app_with_db):
    user = User(email="future_tester@example.com")
    user.set_password("SecurePassword123!")
    profile = CandidateProfile(
        user=user,
        full_name="Vishnu Sai",
        headline="Senior AI & Backend Engineer",
        skills=["Python", "Flask", "Docker", "PostgreSQL", "Machine Learning"]
    )
    source = JobSource(platform="greenhouse", company_key="stripe", name="Stripe Greenhouse")
    db.session.add_all([user, profile, source])
    db.session.commit()

    job = Job(
        source_id=source.id,
        source_platform="greenhouse",
        source_company_key="stripe",
        source_job_id="str-901",
        title="Staff Software Engineer",
        company="Stripe",
        location="Remote",
        original_url="https://boards.greenhouse.io/stripe/jobs/901",
        apply_url="https://boards.greenhouse.io/stripe/jobs/901#app",
        description="Looking for an experienced engineer in Python, Docker, Kubernetes, AWS, and Microservices.",
        required_skills=["Python", "Docker", "AWS"],
        preferred_skills=["Kubernetes", "Microservices"],
        published_at=datetime.now(timezone.utc),
        status="active"
    )
    db.session.add(job)
    db.session.commit()
    return user, job

# 1. Test Resume Optimizer & Google XYZ Formula
def test_resume_optimizer_xyz():
    svc = ResumeOptimizerService()
    raw_bullet = "worked on building api and improved speed"
    res = svc.rewrite_bullet_xyz(raw_bullet, target_role="Backend Engineer", target_skill="Python")

    assert res["framework"] == "Google XYZ Formula"
    assert len(res["optimized_bullets"]) >= 3
    assert len(res["impact_metrics"]) >= 2
    # Verify active past-tense action verbs used
    assert any(b.split()[0] in svc.ACTION_VERBS for b in res["optimized_bullets"])

# 2. Test Visual Keyword Gap Heatmap
def test_keyword_gap_heatmap():
    svc = ResumeOptimizerService()
    resume_text = "Proficient in Python, Flask, Docker, and PostgreSQL databases."
    jd_text = "We require Python, Docker, Kubernetes, AWS, and Redis microservices."

    heatmap = svc.compute_keyword_gap_heatmap(resume_text, jd_text, job_skills=["Python", "Docker", "Kubernetes", "AWS"])

    assert heatmap["total_jd_keywords"] > 0
    matched_names = [k["keyword"].lower() for k in heatmap["matched_keywords"]]
    missing_names = [k["keyword"].lower() for k in heatmap["missing_keywords"]]

    assert "python" in matched_names
    assert "docker" in matched_names
    assert "kubernetes" in missing_names
    assert "aws" in missing_names
    assert 0 <= heatmap["coverage_percentage"] <= 100

# 3. Test Outreach & Anti-Ghosting Follow-up Service
def test_outreach_service():
    svc = OutreachService()
    personas = svc.generate_recruiter_personas("Stripe", "Staff Software Engineer")
    assert len(personas["search_targets"]) >= 3
    assert "linkedin.com/search" in personas["search_targets"][0]["linkedin_search_url"]

    templates = svc.generate_outreach_templates("Vishnu Sai", ["Python", "Flask"], "Stripe", "Staff Software Engineer")
    assert len(templates["linkedin_note"]) <= 300
    assert "Vishnu Sai" in templates["inmail_body"]

    fu_7d = svc.generate_followup_email("Vishnu Sai", "Stripe", "Staff Software Engineer", stage="7day")
    assert "Staff Software Engineer" in fu_7d["subject"]
    assert "Stripe" in fu_7d["body"]

    fu_post = svc.generate_followup_email("Vishnu Sai", "Stripe", "Staff Software Engineer", stage="post_interview")
    assert "interview" in fu_post["subject"].lower()

# 4. Test Spoken Speech Delivery & Filler Word Analytics
def test_speech_delivery_analytics():
    sim = InterviewSimulator()
    spoken_answer = "Well um basically our team had like a big issue and you know we actually fixed it in two days."
    analytics = sim.analyze_speech_delivery(spoken_answer, duration_seconds=15.0)

    assert analytics["total_filler_words"] >= 3
    assert "um" in analytics["detected_fillers"]
    assert "like" in analytics["detected_fillers"]
    assert analytics["estimated_wpm"] > 0
    assert 50 <= analytics["delivery_score"] <= 100

# 5. Test Global Currency & PPP Normalizer
def test_salary_ppp_normalizer():
    norm = SalaryNormalizerService()
    # Nominal conversion
    conv = norm.convert_salary(100000, "USD", "INR")
    assert conv["converted_nominal"] > 7000000 # 100k USD > 70 Lakhs INR

    # PPP conversion
    ppp = norm.calculate_ppp_equivalent(100000, "USD", "INR")
    assert ppp["ppp_multiplier"] > 1.0 # High purchasing power arbitrage
    assert ppp["local_ppp_buying_power"] > 0
    assert "lifestyle equivalent" in ppp["analysis"]

# 6. Test Career Funnel & Calendar Sync
def test_career_funnel_and_calendar():
    analytics = CareerAnalyticsService()
    counts = {"saved": 10, "applied": 8, "interviewing": 3, "offer": 1}
    funnel = analytics.compute_funnel_metrics(counts)

    assert funnel["applied_to_interview_rate"] == 50.0
    assert funnel["interview_to_offer_rate"] == 25.0
    assert len(funnel["stages"]) == 4

    now = datetime.now(timezone.utc)
    cal = analytics.generate_calendar_links("Staff Engineer", "Stripe", now)
    assert "calendar.google.com" in cal["google_calendar_url"]
    assert "BEGIN:VCALENDAR" in cal["ics_content"]
    assert "END:VCALENDAR" in cal["ics_content"]

# 7. Test Telegram Instant Alert Dispatch
def test_telegram_instant_alert():
    bot = TelegramBotService()
    job_info = {
        "title": "Lead AI Engineer",
        "company": "DeepMind",
        "source_platform": "direct",
        "location": "Remote",
        "apply_url": "https://example.com/deepmind",
        "salary_range": "$180,000 - $220,000"
    }
    res = bot.send_instant_job_alert("123456789", job_info, match_score=94.5)
    assert res["success"] is True
    assert res.get("simulated") is True
    assert "DeepMind" in res["message"]
    assert "94%" in res["message"]
