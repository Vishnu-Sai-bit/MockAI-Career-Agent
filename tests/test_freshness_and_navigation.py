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


