import pytest
from datetime import datetime, timezone, timedelta
from app import create_app
from extensions import db
from models.user import User, CandidateProfile
from models.job import Job
from models.resume import Resume
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
def test_user(app_with_db):
    user = User(email="test_fresh@example.com")
    user.set_password("SecurePassword123!")
    profile = CandidateProfile(user=user, full_name="Fresh Candidate")
    db.session.add(user)
    db.session.add(profile)
    db.session.commit()
    return user

@pytest.fixture
def test_source(app_with_db):
    from models.job_source import JobSource
    source = JobSource(platform="greenhouse", company_key="testco", name="Test Co")
    db.session.add(source)
    db.session.commit()
    return source

def test_freshest_jobs_sorting_default(app_with_db, test_user, test_source):
    now = datetime.now(timezone.utc)
    j1 = Job(source_id=test_source.id, source_company_key="testco", title="Old Job", company="Tech A", location="Remote", source_platform="greenhouse", source_job_id="g1", original_url="https://example.com/1", apply_url="https://example.com/1", published_at=now - timedelta(days=5), status="active")
    j2 = Job(source_id=test_source.id, source_company_key="testco", title="Freshest Job", company="Tech B", location="Remote", source_platform="lever", source_job_id="l1", original_url="https://example.com/2", apply_url="https://example.com/2", published_at=now - timedelta(hours=2), status="active")
    j3 = Job(source_id=test_source.id, source_company_key="testco", title="Yesterday Job", company="Tech C", location="Remote", source_platform="ashby", source_job_id="a1", original_url="https://example.com/3", apply_url="https://example.com/3", published_at=now - timedelta(days=1), status="active")
    db.session.add_all([j1, j2, j3])
    db.session.commit()

    service = JobSearchService()
    results = service.search_jobs(user=test_user, sort_by="fresh")
    items = results["jobs"]
    assert len(items) == 3
    assert items[0]["job"].title == "Freshest Job"
    assert items[1]["job"].title == "Yesterday Job"
    assert items[2]["job"].title == "Old Job"

def test_date_posted_filter_24h(app_with_db, test_user, test_source):
    now = datetime.now(timezone.utc)
    j1 = Job(source_id=test_source.id, source_company_key="testco", title="Job 12 Hours Ago", company="Tech 1", location="Remote", source_platform="greenhouse", source_job_id="g10", original_url="https://example.com/10", apply_url="https://example.com/10", published_at=now - timedelta(hours=12), status="active")
    j2 = Job(source_id=test_source.id, source_company_key="testco", title="Job 2 Days Ago", company="Tech 2", location="Remote", source_platform="lever", source_job_id="l20", original_url="https://example.com/20", apply_url="https://example.com/20", published_at=now - timedelta(days=2), status="active")
    db.session.add_all([j1, j2])
    db.session.commit()

    service = JobSearchService()
    res_24h = service.search_jobs(user=test_user, date_posted="24h")
    assert len(res_24h["jobs"]) == 1
    assert res_24h["jobs"][0]["job"].title == "Job 12 Hours Ago"

    res_3d = service.search_jobs(user=test_user, date_posted="3d")
    assert len(res_3d["jobs"]) == 2

def test_sidebar_and_navigation_rendered(app_with_db):
    client = app_with_db.test_client()
    resp = client.get("/jobs")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="appSidebar"' in html
    assert 'data-bs-target="#appSidebar"' in html
    assert 'Relevant First' in html
    assert 'Past 24 Hours (1 Day)' in html

def test_auth_pages_no_sidebar_centered(app_with_db):
    """Ensure Login and Register pages do not show sidebar and render clean centered layout."""
    client = app_with_db.test_client()

    # Login Route
    login_resp = client.get("/login")
    assert login_resp.status_code == 200
    login_html = login_resp.get_data(as_text=True)
    assert 'id="appSidebar"' not in login_html
    assert 'auth-mode' in login_html
    assert 'auth-container' in login_html
    assert 'auth-card' in login_html
    assert 'togglePasswordVisibility' in login_html
    # Check that brand link replaced the sidebar hamburger toggle
    assert 'AI Job Agent' in login_html

    # Register Route
    reg_resp = client.get("/register")
    assert reg_resp.status_code == 200
    reg_html = reg_resp.get_data(as_text=True)
    assert 'id="appSidebar"' not in reg_html
    assert 'auth-mode' in reg_html
    assert 'auth-container' in reg_html
    assert 'auth-card' in reg_html
    assert 'togglePasswordVisibility' in reg_html

def test_matched_jobs_prioritized_first(app_with_db, test_user, test_source):
    from models.job_match import JobMatch
    now = datetime.now(timezone.utc)

    # Attach active resume to user
    resume = Resume(
        user=test_user,
        filename="test_resume.pdf",
        file_path="uploads/test_resume.pdf",
        file_type="pdf",
        raw_text="Python and AWS specialist",
        parsed_data={"skills": ["Python", "AWS"]}
    )
    db.session.add(resume)
    db.session.commit()

    # Job A: Unmatched, but published 10 minutes ago
    job_unmatched = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Unmatched Role (No Match)",
        company="Company A",
        location="Remote",
        source_platform="greenhouse",
        source_job_id="u1",
        original_url="https://example.com/u1",
        apply_url="https://example.com/u1",
        published_at=now - timedelta(minutes=10),
        status="active"
    )

    # Job B: Matched 88%, but published 3 days ago
    job_matched = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Matched Python Role",
        company="Company B",
        location="Remote",
        source_platform="lever",
        source_job_id="m1",
        original_url="https://example.com/m1",
        apply_url="https://example.com/m1",
        published_at=now - timedelta(days=3),
        status="active"
    )
    db.session.add_all([job_unmatched, job_matched])
    db.session.commit()

    # Add JobMatch record for Job B
    match_b = JobMatch(
        user_id=test_user.id,
        resume_id=resume.id,
        job_id=job_matched.id,
        match_score=88.0,
        match_explanation="88% alignment on Python and Cloud"
    )
    db.session.add(match_b)
    db.session.commit()

    service = JobSearchService()
    results = service.search_jobs(user=test_user, sort_by="fresh")
    jobs = results["jobs"]

    assert len(jobs) == 2
    # Matched job must come first even though unmatched is newer
    assert jobs[0]["job"].title == "Matched Python Role"
    assert jobs[0]["is_matched"] is True
    assert jobs[0]["match"].match_score == 88.0

    # Remaining unmatched job must come second
    assert jobs[1]["job"].title == "Unmatched Role (No Match)"
    assert jobs[1]["is_matched"] is False


def test_jobs_list_auto_computes_matches_for_active_resume(app_with_db, test_user, test_source):
    from flask_login import login_user
    from models.job_match import JobMatch

    now = datetime.now(timezone.utc)
    resume = Resume(
        user_id=test_user.id,
        filename="test_candidate.pdf",
        file_path="uploads/test_candidate.pdf",
        file_type="pdf",
        raw_text="Senior Python Engineer with 5 years experience in FastAPI, Docker, and PostgreSQL",
        parsed_data={"skills": ["Python", "FastAPI", "Docker", "PostgreSQL"], "experience_years": 5},
        is_active=True
    )
    db.session.add(resume)
    db.session.commit()

    job = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Python Backend Engineer",
        company="Fast Co",
        location="Remote",
        required_skills=["Python", "FastAPI"],
        source_platform="greenhouse",
        source_job_id="py-101",
        original_url="https://example.com/py-101",
        apply_url="https://example.com/py-101",
        published_at=now,
        status="active"
    )
    db.session.add(job)
    db.session.commit()

    # Verify no matches initially exist
    assert JobMatch.query.filter_by(user_id=test_user.id).count() == 0

    client = app_with_db.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_user.id)
        sess["_fresh"] = True

    # Hit /jobs
    resp = client.get("/jobs")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # JobMatch should now have been calculated automatically on the fly
    assert JobMatch.query.filter_by(user_id=test_user.id).count() >= 1
    match = JobMatch.query.filter_by(user_id=test_user.id, job_id=job.id).first()
    assert match is not None
    assert match.match_score > 0
    assert "Relevant" in html


def test_fresher_candidate_gets_fresher_jobs_first_remaining_next(app_with_db, test_user, test_source):
    """
    Verifies that when a candidate is a fresher (0 years experience),
    fresher / entry-level jobs appear FIRST, and remaining jobs appear NEXT.
    """
    now = datetime.now(timezone.utc)
    resume = Resume(
        user_id=test_user.id,
        filename="fresher_resume.pdf",
        file_path="uploads/fresher_resume.pdf",
        file_type="pdf",
        raw_text="Fresher Computer Science Graduate skilled in Python and SQL",
        parsed_data={"skills": ["Python", "SQL"], "experience_years": 0.0},
        is_active=True
    )
    test_user.candidate_profile.experience_years = 0.0
    test_user.candidate_profile.experience_level = "entry"
    db.session.add(resume)
    db.session.commit()

    # Create Senior Job (published 1 hour ago)
    job_senior = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Senior Tech Lead",
        company="Senior Co",
        location="Remote",
        experience_level="senior",
        source_platform="greenhouse",
        source_job_id="sr-100",
        original_url="https://example.com/sr-100",
        apply_url="https://example.com/sr-100",
        published_at=now - timedelta(hours=1),
        status="active"
    )
    # Create Fresher Job (published 2 days ago)
    job_fresher = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Junior Python Associate (Fresher)",
        company="Starter Co",
        location="Remote",
        experience_level="entry",
        source_platform="lever",
        source_job_id="jr-200",
        original_url="https://example.com/jr-200",
        apply_url="https://example.com/jr-200",
        published_at=now - timedelta(days=2),
        status="active"
    )
    db.session.add_all([job_senior, job_fresher])
    db.session.commit()

    service = JobSearchService()
    results = service.search_jobs(user=test_user, sort_by="fresh")
    items = results["jobs"]

    assert len(items) == 2
    # Fresher job must appear FIRST even though Senior job was published more recently
    assert items[0]["job"].title == "Junior Python Associate (Fresher)"
    assert items[0]["is_exp_fit"] is True

    # Remaining senior job must appear NEXT
    assert items[1]["job"].title == "Senior Tech Lead"
    assert items[1]["is_exp_fit"] is False


def test_two_years_experience_candidate_gets_mid_jobs_first_remaining_next(app_with_db, test_user, test_source):
    """
    Verifies that when a candidate has 2 years experience,
    2 years / mid-level jobs appear FIRST, and remaining jobs appear NEXT.
    """
    now = datetime.now(timezone.utc)
    resume = Resume(
        user_id=test_user.id,
        filename="mid_resume.pdf",
        file_path="uploads/mid_resume.pdf",
        file_type="pdf",
        raw_text="Software Engineer with 2 years experience in Python and APIs",
        parsed_data={"skills": ["Python", "APIs"], "experience_years": 2.0},
        is_active=True
    )
    test_user.candidate_profile.experience_years = 2.0
    test_user.candidate_profile.experience_level = "mid"
    db.session.add(resume)
    db.session.commit()

    # Create Lead Job (published 10 mins ago)
    job_lead = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Staff Architect (8+ Yrs)",
        company="Big Co",
        location="Remote",
        experience_level="lead",
        source_platform="greenhouse",
        source_job_id="lead-300",
        original_url="https://example.com/lead-300",
        apply_url="https://example.com/lead-300",
        published_at=now - timedelta(minutes=10),
        status="active"
    )
    # Create 2 Years / Mid-level Job (published yesterday)
    job_mid = Job(
        source_id=test_source.id,
        source_company_key="testco",
        title="Python Backend Developer (2–5 Yrs)",
        company="Scale Co",
        location="Remote",
        experience_level="mid",
        source_platform="lever",
        source_job_id="mid-400",
        original_url="https://example.com/mid-400",
        apply_url="https://example.com/mid-400",
        published_at=now - timedelta(days=1),
        status="active"
    )
    db.session.add_all([job_lead, job_mid])
    db.session.commit()

    service = JobSearchService()
    results = service.search_jobs(user=test_user, sort_by="fresh")
    items = results["jobs"]

    assert len(items) == 2
    # Mid-level (2 years) job must appear FIRST
    assert items[0]["job"].title == "Python Backend Developer (2–5 Yrs)"
    assert items[0]["is_exp_fit"] is True

    # Remaining lead job must appear NEXT
    assert items[1]["job"].title == "Staff Architect (8+ Yrs)"
    assert items[1]["is_exp_fit"] is False


def test_data_analyst_fresher_experience_progression_and_score_descending(app_with_db, test_user, test_source):
    from models.job_match import JobMatch
    now = datetime.now(timezone.utc)

    # 1. Candidate is Data Analyst fresher (0.5 years)
    test_user.candidate_profile.headline = "Data Analyst"
    test_user.candidate_profile.experience_years = 0.5
    resume = Resume(
        user_id=test_user.id,
        filename="da_fresher.pdf",
        file_path="uploads/da_fresher.pdf",
        file_type="pdf",
        target_role="Data Analyst",
        parsed_data={"experience_years": 0.5, "skills": ["Python", "SQL", "Tableau", "Power BI"], "headline": "Data Analyst"},
        is_active=True
    )
    db.session.add(resume)
    db.session.commit()

    # 2. Add jobs across experience tiers and domain fits
    j_da_entry_low = Job(
        source_id=test_source.id, source_company_key="testco", title="Data Analyst, Intern",
        company="Co A", location="Remote", experience_level="entry", source_platform="greenhouse",
        source_job_id="da-1", original_url="https://example.com/da-1", apply_url="https://example.com/da-1",
        published_at=now, status="active"
    )
    j_da_entry_high = Job(
        source_id=test_source.id, source_company_key="testco", title="Junior Data Analyst",
        company="Co B", location="Remote", experience_level="entry", source_platform="greenhouse",
        source_job_id="da-2", original_url="https://example.com/da-2", apply_url="https://example.com/da-2",
        published_at=now, status="active"
    )
    j_analytics_entry = Job(
        source_id=test_source.id, source_company_key="testco", title="Strategy & Analytics Analyst",
        company="Co C", location="Remote", experience_level="entry", source_platform="greenhouse",
        source_job_id="da-3", original_url="https://example.com/da-3", apply_url="https://example.com/da-3",
        published_at=now, status="active"
    )
    j_da_mid = Job(
        source_id=test_source.id, source_company_key="testco", title="Data Analyst (2-4 Yrs)",
        company="Co D", location="Remote", experience_level="mid", source_platform="greenhouse",
        source_job_id="da-4", original_url="https://example.com/da-4", apply_url="https://example.com/da-4",
        published_at=now, status="active"
    )
    j_lead_architect = Job(
        source_id=test_source.id, source_company_key="testco", title="Lead Data Architect",
        company="Co E", location="Remote", experience_level="lead", source_platform="greenhouse",
        source_job_id="da-5", original_url="https://example.com/da-5", apply_url="https://example.com/da-5",
        published_at=now, status="active"
    )
    db.session.add_all([j_da_entry_low, j_da_entry_high, j_analytics_entry, j_da_mid, j_lead_architect])
    db.session.commit()

    # 3. Add match scores:
    # Notice: j_lead_architect has 98% score, but being a Lead role, it must NOT precede fresher roles!
    m1 = JobMatch(user_id=test_user.id, resume_id=resume.id, job_id=j_da_entry_low.id, match_score=75.0)
    m2 = JobMatch(user_id=test_user.id, resume_id=resume.id, job_id=j_da_entry_high.id, match_score=92.0)
    m3 = JobMatch(user_id=test_user.id, resume_id=resume.id, job_id=j_analytics_entry.id, match_score=88.0)
    m4 = JobMatch(user_id=test_user.id, resume_id=resume.id, job_id=j_da_mid.id, match_score=85.0)
    m5 = JobMatch(user_id=test_user.id, resume_id=resume.id, job_id=j_lead_architect.id, match_score=98.0)
    db.session.add_all([m1, m2, m3, m4, m5])
    db.session.commit()

    service = JobSearchService()
    results = service.search_jobs(user=test_user, sort_by="fresh")
    items = results["jobs"]

    assert len(items) == 5
    # Tier 1: Fresher Data Analyst jobs ordered by match score High to Low %
    assert items[0]["job"].title == "Junior Data Analyst"  # 92.0%
    assert items[0]["match"].match_score == 92.0
    assert items[0]["is_exp_fit"] is True

    assert items[1]["job"].title == "Data Analyst, Intern"  # 75.0%
    assert items[1]["match"].match_score == 75.0
    assert items[1]["is_exp_fit"] is True

    # Tier 2: Fresher Analytics related jobs
    assert items[2]["job"].title == "Strategy & Analytics Analyst"  # 88.0%
    assert items[2]["match"].match_score == 88.0
    assert items[2]["is_exp_fit"] is True

    # Tier 3: Mid-level (2+ yrs) Data Analyst
    assert items[3]["job"].title == "Data Analyst (2-4 Yrs)"  # 85.0%

    # Tier 4: Lead role appears at the end for a fresher
    assert items[4]["job"].title == "Lead Data Architect"





def test_resume_related_first_with_fresh_and_india_then_remaining(app_with_db, test_user, test_source):
    """
    Verifies that:
    1. Resume-related jobs appear FIRST.
    2. Within resume-related jobs, India and freshly posted/updated jobs are prioritized.
    3. Remaining (unmatched/unrelated) jobs appear AFTER all resume-related jobs,
       and are also ordered by India and freshness.
    """
    now = datetime.now(timezone.utc)
    test_user.candidate_profile.headline = "Data Analyst"
    test_user.candidate_profile.experience_years = 1.0
    resume = Resume(
        user_id=test_user.id,
        filename="da_candidate.pdf",
        file_path="uploads/da_candidate.pdf",
        file_type="pdf",
        target_role="Data Analyst",
        parsed_data={"experience_years": 1.0, "skills": ["Python", "SQL", "Tableau", "Data Analysis"], "headline": "Data Analyst"},
        is_active=True
    )
    db.session.add(resume)
    db.session.commit()

    # Job A: Unrelated remaining job in India, but posted 5 minutes ago (very fresh)
    job_unrelated_india_fresh = Job(
        source_id=test_source.id, source_company_key="testco", title="Civil Site Engineer",
        company="Infra Ltd", location="Bengaluru, Karnataka, India", country="India", city="Bengaluru",
        experience_level="mid", source_platform="greenhouse", source_job_id="rel-1",
        original_url="https://example.com/rel-1", apply_url="https://example.com/rel-1",
        published_at=now - timedelta(minutes=5), status="active"
    )
    # Job B: Resume-related job in India, posted 2 hours ago
    job_related_india_fresh = Job(
        source_id=test_source.id, source_company_key="testco", title="Junior Data Analyst",
        company="Data Corp", location="Bengaluru, India", country="India", city="Bengaluru",
        experience_level="entry", source_platform="lever", source_job_id="rel-2",
        original_url="https://example.com/rel-2", apply_url="https://example.com/rel-2",
        published_at=now - timedelta(hours=2), status="active"
    )
    # Job C: Resume-related job in India, posted 1 day ago (older than Job B)
    job_related_india_older = Job(
        source_id=test_source.id, source_company_key="testco", title="Data Analyst, Associate",
        company="Analytics India", location="Pune, India", country="India", city="Pune",
        experience_level="entry", source_platform="ashby", source_job_id="rel-3",
        original_url="https://example.com/rel-3", apply_url="https://example.com/rel-3",
        published_at=now - timedelta(days=1), status="active"
    )
    # Job D: Unrelated remaining job Remote, posted 1 hour ago
    job_unrelated_remote = Job(
        source_id=test_source.id, source_company_key="testco", title="Executive Receptionist",
        company="Global Admin", location="Remote", country="US",
        experience_level="mid", source_platform="workable", source_job_id="rel-4",
        original_url="https://example.com/rel-4", apply_url="https://example.com/rel-4",
        published_at=now - timedelta(hours=1), status="active"
    )
    db.session.add_all([job_unrelated_india_fresh, job_related_india_fresh, job_related_india_older, job_unrelated_remote])
    db.session.commit()

    service = JobSearchService()
    results = service.search_jobs(user=test_user, sort_by="fresh")
    items = results["jobs"]

    assert len(items) == 4
    # 1. First Resume-Related role (India + Fresh 2h ago)
    assert items[0]["job"].title == "Junior Data Analyst"
    assert items[0]["is_resume_related"] is True

    # 2. Second Resume-Related role (India + 1 day ago)
    assert items[1]["job"].title == "Data Analyst, Associate"
    assert items[1]["is_resume_related"] is True

    # 3. Third: Remaining roles begin. India remaining role (5 mins ago) comes before Remote remaining role
    assert items[2]["job"].title == "Civil Site Engineer"
    assert items[2]["is_resume_related"] is False

    # 4. Fourth: Remaining Remote role (1 hour ago)
    assert items[3]["job"].title == "Executive Receptionist"
    assert items[3]["is_resume_related"] is False
