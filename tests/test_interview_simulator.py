import pytest
from app import create_app
from extensions import db
from models.user import User
from models.job import Job
from models.job_source import JobSource
from services.interview_simulator import InterviewSimulator

@pytest.fixture
def app_instance():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        yield app

@pytest.fixture
def client(app_instance):
    return app_instance.test_client()

def test_generate_interview_questions_with_none_profile(app_instance):
    with app_instance.app_context():
        sim = InterviewSimulator()
        job = Job.query.first()
        if not job:
            src = JobSource(name="Test", base_url="https://test.com", platform_type="greenhouse")
            db.session.add(src)
            db.session.commit()
            job = Job(source_id=src.id, source_platform="greenhouse", source_company_key="test",
                      source_job_id="1", title="Backend Engineer", company="Acme",
                      original_url="https://test.com/1", apply_url="https://test.com/1")
            db.session.add(job)
            db.session.commit()

        questions = sim.generate_interview_questions(job, None)
        assert len(questions) >= 1
        assert "question" in questions[0]
        assert "evaluation_criteria" in questions[0]

def test_interview_hub_redirect(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    resp = client.get("/interview/")
    assert resp.status_code == 302
    assert "/interview/" in resp.headers.get("Location")

def test_interview_evaluation_endpoint(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"
        job = Job.query.first()

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    resp = client.post("/interview/api/evaluate", json={
        "job_id": job.id,
        "question": "Tell me about a high scale system you designed.",
        "answer": "I architected an asynchronous event bus that handled 50k events per second with 99.99% availability.",
        "duration_seconds": 30.0
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "evaluation" in data
    assert "overall_score" in data["evaluation"]

def test_sidebar_career_coach_order(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    
    # Assert Salary Intelligence is removed from the sidebar
    # and AI Career Coach appears as the last item in AI Career Suite
    idx_ats = html.find("ATS Match Report")
    idx_interview = html.find("AI Mock Interview")
    idx_coach = html.find("AI Career Coach")

    assert idx_ats != -1
    assert idx_interview != -1
    assert idx_coach != -1
    assert idx_ats < idx_interview < idx_coach

    # Ensure Salary Intelligence is not present in the sidebar nav
    sidebar_part = html[html.find('id="appSidebar"'):html.find('</nav>')]
    assert "Salary Intelligence" not in sidebar_part

def test_interview_hub_page(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    resp = client.get("/interview/hub")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "AI Mock Interview Prep Center" in html
    assert "STAR Method Blueprint" in html
    assert "Behavioral & STAR Simulator" in html

def test_interview_simulator_page_details(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"
        job = Job.query.first()

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    resp = client.get(f"/interview/{job.id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Interview Progress:" in html
    assert "STAR Blueprint for This Question" in html
    assert "stopwatch-display" in html
    assert "switchJobModal" in html
    assert "Verified Live" in html
