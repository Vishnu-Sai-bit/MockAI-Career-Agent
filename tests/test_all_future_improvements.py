import io
import json
from datetime import datetime, timezone, timedelta
import pytest
from app import create_app
from extensions import db
from models.user import User, CandidateProfile
from models.resume import Resume
from models.job import Job
from models.job_source import JobSource
from models.job_match import JobMatch
from models.application import Application
from models.dream_company import DreamCompany
from models.alert import JobAlert, AlertNotification
from services.resume_export_service import ResumeExportService
from services.dream_company_service import DreamCompanyService
from services.technical_assessment_service import TechnicalAssessmentService
from services.notification_service import NotificationService
from services.job_search_service import JobSearchService

@pytest.fixture
def app_with_db():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app_with_db):
    return app_with_db.test_client()

@pytest.fixture
def test_setup(app_with_db):
    user = User(email="visionary@example.com")
    user.set_password("SecurePass123!")
    db.session.add(user)
    db.session.commit()

    profile = CandidateProfile(
        user_id=user.id,
        full_name="Vishnu Sai Beere",
        phone="+91-9876543210",
        location="Bengaluru, India",
        headline="Senior AI & Distributed Systems Engineer",
        summary="Experienced engineer specializing in high-throughput systems and modern AI architectures.",
        skills=["Python", "FastAPI", "SQL", "Docker", "AWS", "PyTorch"],
        experience_years=4.5
    )
    db.session.add(profile)

    source = JobSource.query.filter_by(platform="greenhouse", company_key="stripe").first()
    if not source:
        source = JobSource(
            platform="greenhouse",
            company_key="stripe",
            name="Stripe Careers",
            is_active=True
        )
        db.session.add(source)
        db.session.commit()

    now = datetime.now(timezone.utc)
    job = Job(
        source_id=source.id,
        source_company_key="stripe",
        title="Senior Python Backend Engineer",
        company="Stripe",
        location="Remote",
        source_platform="greenhouse",
        source_job_id="stripe-backend-101",
        original_url="https://boards.greenhouse.io/stripe/jobs/101",
        apply_url="https://boards.greenhouse.io/stripe/jobs/101#apply",
        description="Build high-reliability distributed payment processing pipelines in Python and SQL.",
        required_skills=["Python", "SQL", "Distributed Systems"],
        published_at=now - timedelta(hours=2),
        status="active"
    )
    db.session.add(job)
    db.session.commit()

    return {"user": user, "profile": profile, "source": source, "job": job}


def test_multi_resume_profiles_and_docx_export(app_with_db, test_setup):
    user = test_setup["user"]
    profile = test_setup["profile"]

    # Create 2 specialized resumes
    resume1 = Resume(
        user_id=user.id,
        filename="backend_resume.pdf",
        file_path="uploads/backend.pdf",
        file_type="pdf",
        profile_title="Senior Backend Specialist",
        target_role="Backend Engineer",
        raw_text="Python Backend Engineer with 4 years experience in microservices.",
        parsed_data={"name": "Vishnu Sai", "skills": ["Python", "FastAPI", "SQL"], "experience": ["Built payment APIs"]}
    )
    resume2 = Resume(
        user_id=user.id,
        filename="ai_resume.pdf",
        file_path="uploads/ai.pdf",
        file_type="pdf",
        profile_title="AI & ML Systems Specialist",
        target_role="AI Engineer",
        raw_text="AI Engineer experienced with PyTorch and LLMs.",
        parsed_data={"name": "Vishnu Sai", "skills": ["PyTorch", "LLMs", "Python"]}
    )
    db.session.add_all([resume1, resume2])
    db.session.commit()

    # User helper methods
    all_resumes = user.get_all_resumes()
    assert len(all_resumes) == 2

    active = user.get_active_resume()
    assert active is not None

    # Test export service .docx generation
    export_svc = ResumeExportService()
    docx_buf = export_svc.export_resume_docx(resume1, profile)
    assert isinstance(docx_buf, io.BytesIO)
    assert docx_buf.getbuffer().nbytes > 1000

    # Test plain ATS text generation
    ats_text = export_svc.export_resume_ats_text(resume1, profile)
    assert "PROFESSIONAL SUMMARY" in ats_text
    assert "TECHNICAL & CORE SKILLS" in ats_text
    assert "Python" in ats_text


def test_dream_company_watchlist_and_discovery(app_with_db, test_setup):
    user = test_setup["user"]
    job = test_setup["job"]

    service = DreamCompanyService()

    # ATS Detection
    assert service.detect_ats_for_company("Uber", careers_url="https://boards.greenhouse.io/uber") == "greenhouse"
    assert service.detect_ats_for_company("Figma", careers_url="https://jobs.lever.co/figma") == "lever"
    assert service.detect_ats_for_company("Databricks", careers_url="https://jobs.ashbyhq.com/databricks") == "ashby"
    assert service.detect_ats_for_company("WorkdayCo", careers_url="https://company.myworkdayjobs.com/careers") == "workday"

    # Add Dream Company
    dc = service.add_dream_company(user.id, "Stripe", domain="stripe.com", careers_url="https://stripe.com/jobs")
    assert dc.id is not None
    assert dc.company_name == "Stripe"

    # Verify watchlist output
    watchlist = service.get_user_watchlist(user.id)
    assert len(watchlist) == 1
    assert watchlist[0]["active_jobs_count"] == 1
    assert watchlist[0]["latest_jobs"][0].title == "Senior Python Backend Engineer"

    # Verify search result tagging with is_dream_company
    search_svc = JobSearchService()
    res = search_svc.search_jobs(user=user)
    assert len(res["jobs"]) >= 1
    stripe_item = next(item for item in res["jobs"] if item["job"].company == "Stripe")
    assert stripe_item["is_dream_company"] is True


def test_extension_api_profile_and_screening_answers(client, test_setup):
    user = test_setup["user"]

    # Login user
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # 1. Test Extension Profile endpoint
    resp = client.get("/api/v1/extension/profile")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    cand = data["candidate"]
    assert cand["email"] == "visionary@example.com"
    assert cand["fullName"] == "Vishnu Sai Beere"
    assert "Python" in cand["skills"]

    # 2. Test Custom Screening Question Answerer
    q_payload = {
        "question": "Why are you interested in joining the Stripe engineering team?",
        "company": "Stripe",
        "job_title": "Senior Python Backend Engineer"
    }
    q_resp = client.post("/api/v1/extension/answer-question", json=q_payload)
    assert q_resp.status_code == 200
    q_data = q_resp.get_json()
    assert q_data["success"] is True
    assert "Stripe" in q_data["answer"] or "engineering" in q_data["answer"].lower()


def test_technical_assessment_sandbox(app_with_db, test_setup):
    job = test_setup["job"]
    profile = test_setup["profile"]

    svc = TechnicalAssessmentService()
    challenge = svc.generate_coding_challenge(job, profile)

    assert "title" in challenge
    assert "starter_code" in challenge
    assert "test_cases" in challenge
    assert len(challenge["test_cases"]) > 0

    # Test evaluation
    sample_code = """
class InMemoryCache:
    def __init__(self):
        self.store = {}
    def set(self, key, value, ttl):
        self.store[key] = value
    def get(self, key):
        return self.store.get(key)
    def size(self):
        return len(self.store)
"""
    evaluation = svc.evaluate_submission(challenge, sample_code)
    assert "score" in evaluation
    assert evaluation["score"] >= 50
    assert "complexity" in evaluation
    assert len(evaluation["strengths"]) > 0


def test_whatsapp_channel_and_morning_digest(app_with_db, test_setup):
    user = test_setup["user"]
    job = test_setup["job"]

    resume = Resume(
        user_id=user.id,
        filename="resume.pdf",
        file_path="uploads/resume.pdf",
        file_type="pdf",
        raw_text="Python Backend Specialist",
        is_active=True
    )
    db.session.add(resume)
    db.session.commit()

    match = JobMatch(
        user_id=user.id,
        resume_id=resume.id,
        job_id=job.id,
        match_score=92.0,
        match_explanation="92% compatibility on Python distributed systems"
    )
    db.session.add(match)

    alert = JobAlert(
        user_id=user.id,
        title="WhatsApp High Priority Alert",
        min_match_score=80.0,
        channel="whatsapp",
        destination="+919876543210",
        is_active=True
    )
    db.session.add(alert)
    db.session.commit()

    notif_svc = NotificationService()
    # Test alert dispatch
    sent = notif_svc.check_and_send_alerts()
    assert sent == 1

    # Test 24h morning digest compilation
    digests = notif_svc.generate_daily_morning_digest(user_id=user.id)
    assert len(digests) == 1
    assert digests[0]["job_count"] == 1
    assert digests[0]["jobs"][0]["title"] == "Senior Python Backend Engineer"

    # Verify AlertNotification recorded in database
    notifs = AlertNotification.query.filter_by(user_id=user.id).all()
    assert len(notifs) >= 1


def test_kanban_drag_and_drop_status_update_api(client, test_setup):
    user = test_setup["user"]
    job = test_setup["job"]

    app = Application(
        user_id=user.id,
        job_id=job.id,
        status="saved"
    )
    db.session.add(app)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # Move application to 'interviewing' stage via drag & drop API endpoint
    payload = {
        "application_id": app.id,
        "status": "interviewing"
    }
    resp = client.post("/applications/api/update", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["status"] == "interviewing"

    # Verify updated in DB
    updated_app = db.session.get(Application, app.id)
    assert updated_app.status == "interviewing"


def test_resume_parser_exact_experience_months_not_confused_by_college_years():
    from services.resume_parser import ResumeParser
    parser = ResumeParser()
    sample_text = """
    VISHNU SAI BEERE
    Email: vishnu@example.com | Phone: 9876543210
    
    EDUCATION
    B.Tech in Computer Science and Engineering
    CMR Technical Campus (2022 - 2026)
    CGPA: 8.5
    
    WORK EXPERIENCE
    Data Analyst Intern | ABC Solutions
    Oct 2025 - Mar 2026
    - Conducted exploratory data analysis on 500k+ records using Python and Pandas.
    - Designed interactive Tableau dashboards for executive leadership.
    
    SKILLS
    Python, SQL, Tableau, Power BI, Machine Learning
    """
    res = parser.parse(sample_text)
    assert res is not None
    # Must be 0.5 years (6 months), NOT 4 years from 2026 - 2022 college years!
    assert res["experience_years"] == 0.5
    assert len(res["experience"]) >= 1
    assert "Intern" in res["experience"][0]["title"]


def test_job_search_and_card_experience_level(client, test_setup):
    user = test_setup["user"]
    source = test_setup["source"]

    entry_job = Job(
        source_id=source.id,
        source_platform="greenhouse",
        source_company_key="stripe",
        source_job_id="stripe-entry-001",
        title="Associate Analyst",
        company="Stripe",
        location="Bengaluru",
        experience_level="entry",
        original_url="https://boards.greenhouse.io/stripe/jobs/stripe-entry-001",
        apply_url="https://boards.greenhouse.io/stripe/jobs/stripe-entry-001",
        status="active"
    )
    senior_job = Job(
        source_id=source.id,
        source_platform="greenhouse",
        source_company_key="stripe",
        source_job_id="stripe-senior-002",
        title="Staff Data Architect",
        company="Stripe",
        location="Bengaluru",
        experience_level="lead",
        original_url="https://boards.greenhouse.io/stripe/jobs/stripe-senior-002",
        apply_url="https://boards.greenhouse.io/stripe/jobs/stripe-senior-002",
        status="active"
    )
    db.session.add_all([entry_job, senior_job])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # 1. Search filter for 'entry' jobs
    resp = client.get("/jobs?experience_level=entry")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Associate Analyst" in html
    assert "0–2 Yrs (Entry)" in html

    # 2. View job details page for entry_job - Experience & Role Fit card present
    resp_details = client.get(f"/jobs/{entry_job.id}")
    assert resp_details.status_code == 200
    details_html = resp_details.get_data(as_text=True)
    assert "Experience &amp; Role Fit" in details_html or "Experience & Role Fit" in details_html
    assert "Target Seniority" in details_html
    assert "0 – 2 Years (Freshers &amp; Interns)" in details_html or "0 – 2 Years (Freshers & Interns)" in details_html


def test_collapsible_filter_controls_and_chips(client, test_setup):
    user = test_setup["user"]
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # When no filters active, compact search bar renders with collapsible filter toggle
    resp = client.get("/jobs")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="filtersSection"' in html
    assert 'data-bs-target="#filtersSection"' in html
    assert 'id="toggleFiltersBtn"' in html

    # When multiple filters active, badge count and quick chips render
    resp_filtered = client.get("/jobs?experience_level=entry&work_mode=remote&date_posted=24h")
    assert resp_filtered.status_code == 200
    f_html = resp_filtered.get_data(as_text=True)
    assert 'Active:' in f_html
    assert 'Exp: Entry' in f_html
    assert 'Mode: Remote' in f_html


def test_present_address_vs_preferred_locations_matching():
    from services.job_matcher import JobMatcher
    from services.resume_parser import ResumeParser

    # 1. Verify parser extracts present address without mistaking it for restrictive preferred cities
    parser = ResumeParser()
    resume_text = """
    BEERE VISHNU SAI
    Email: vishnu@example.com | Phone: 9182679641
    Present Address: Dharmavaram, Andhra Pradesh, India
    Preferred Locations: Bengaluru, Hyderabad, Remote
    
    WORK EXPERIENCE
    Data Analyst Intern | SmartBridge (Oct 2025 - Mar 2026)
    - Python, SQL data cleaning and analytics workflows.
    
    SKILLS
    Python, SQL, Tableau, Pandas
    """
    parsed = parser.parse(resume_text)
    assert "Dharmavaram" in parsed["location"]
    assert "Dharmavaram" in parsed["present_address"]
    assert "Bengaluru" in parsed["preferred_locations"]

    # 2. Verify JobMatcher does NOT penalize a candidate whose present address is a hometown
    # when applying for a job in a major tech hub (e.g. Bengaluru)
    matcher = JobMatcher()
    user = User(id=99, email="reloc@example.com")
    profile = CandidateProfile(
        user_id=99,
        full_name="Vishnu",
        location="Dharmavaram, Andhra Pradesh, India", # Present address
        preferred_cities=["Bengaluru", "Hyderabad", "Remote"],
        preferred_countries=["India"],
        open_to_relocation=True,
        work_modes=["remote", "hybrid", "on-site"],
        skills=["Python", "SQL", "Tableau", "Pandas"],
        experience_years=0.5
    )
    user.candidate_profile = profile
    resume = Resume(
        id=99,
        user_id=99,
        raw_text=resume_text,
        parsed_data=parsed
    )

    job_bengaluru = Job(
        id=501,
        source_id=1,
        source_platform="greenhouse",
        source_company_key="techcorp",
        source_job_id="beng-01",
        title="Junior Data Analyst",
        company="TechCorp",
        location="Bengaluru, Karnataka, India",
        work_mode="on-site",
        experience_level="entry",
        required_skills=["Python", "SQL"],
        description="Entry level data analyst in Bengaluru office.",
        original_url="https://example.com/beng-01",
        apply_url="https://example.com/beng-01",
        status="active"
    )

    result = matcher.compute_match(resume, profile, job_bengaluru)
    # Location must match candidate's preferred cities (100%) and not be penalized
    assert result["match_score"] >= 65.0
    # Flag must clearly indicate relocation / preferred city match
    flag_text = " ".join(result["eligibility_flags"])
    assert "preferred work city" in flag_text.lower() or "open to relocation" in flag_text.lower()


