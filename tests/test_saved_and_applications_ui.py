import pytest
from datetime import datetime, timezone
from app import create_app
from extensions import db
from models.user import User, CandidateProfile
from models.job import Job
from models.job_source import JobSource
from models.job_match import SavedJob
from models.application import Application

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
        headline="Senior Python Engineer",
        skills=["Python", "Flask", "PostgreSQL", "Docker"]
    )
    db.session.add(profile)

    source = JobSource(
        platform="workday",
        company_key="razorpay",
        name="Razorpay Careers",
        is_active=True
    )
    db.session.add(source)
    db.session.commit()

    job = Job(
        source_id=source.id,
        source_company_key="razorpay",
        source_job_id="rzp-eng-101",
        title="Full Stack Engineer",
        company="Razorpay",
        location="Bengaluru, India",
        country="India",
        work_mode="hybrid",
        source_platform="workday",
        description="Build payment infrastructure using Python and React.",
        required_skills=["Python", "React"],
        original_url="https://razorpay.wd3.myworkdayjobs.com/careers/job/1",
        apply_url="https://razorpay.wd3.myworkdayjobs.com/careers/job/1#apply",
        status="open",
        published_at=datetime.now(timezone.utc)
    )
    db.session.add(job)
    db.session.commit()

    return {"user": user, "job": job}

def test_saved_jobs_and_application_tracker_cohesion(client, test_setup):
    user = test_setup["user"]
    job = test_setup["job"]

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)

    # 1. Bookmark a job (Wishlist)
    saved = SavedJob(user_id=user.id, job_id=job.id, notes="Interested in backend role")
    db.session.add(saved)
    db.session.commit()

    # 2. View /saved-jobs page
    resp_saved = client.get("/saved-jobs")
    assert resp_saved.status_code == 200
    html_saved = resp_saved.get_data(as_text=True)
    assert "Saved Jobs" in html_saved
    assert job.title in html_saved
    assert "Wishlist Only" in html_saved or "Track in Pipeline" in html_saved

    # 3. View /applications page
    resp_apps = client.get("/applications")
    assert resp_apps.status_code == 200
    html_apps = resp_apps.get_data(as_text=True)
    assert "Application Tracker" in html_apps
    # Verify the active pipeline stages are present
    assert "Prepared / Drafting" in html_apps
    assert "Applied" in html_apps
    assert "Interviewing" in html_apps
    assert "Offer Received" in html_apps
    # Verify the Wishlist bridge is present
    assert "Bookmarked Opportunities" in html_apps

    # 4. Promote saved job to Active Pipeline (status="applied")
    create_payload = {"job_id": job.id, "status": "applied"}
    create_resp = client.post("/applications/api/create", json=create_payload)
    assert create_resp.status_code == 200
    app_data = create_resp.get_json()
    assert app_data["success"] is True
    assert app_data["status"] == "applied"

    # 5. Check /saved-jobs now reflects the active pipeline status
    resp_saved_after = client.get("/saved-jobs")
    assert resp_saved_after.status_code == 200
    html_saved_after = resp_saved_after.get_data(as_text=True)
    assert "In Pipeline: Applied" in html_saved_after

    # 6. Check /applications now shows the application in the Applied column
    resp_apps_after = client.get("/applications")
    assert resp_apps_after.status_code == 200
    html_apps_after = resp_apps_after.get_data(as_text=True)
    assert job.title in html_apps_after
