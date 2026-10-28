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

def test_generate_followup_and_reverse_questions(app_instance):
    with app_instance.app_context():
        sim = InterviewSimulator()
        job = Job.query.first()

        # Followup question
        fu = sim.generate_followup_question(
            "Tell me about a high throughput architecture.",
            "I used Redis and Kafka to process 10,000 requests per second with microservices.",
            job
        )
        assert "followup_question" in fu
        assert "interviewer_intent" in fu

        # Reverse questions to ask interviewer
        rqs = sim.generate_questions_to_ask_interviewer(job, None)
        assert len(rqs) >= 3
        assert "question" in rqs[0]
        assert "why_ask" in rqs[0]

        # Cheat sheet
        cs = sim.generate_interview_cheat_sheet(job, None)
        assert "pre_interview_checklist" in cs
        assert "core_talking_points" in cs

def test_followup_and_save_session_api(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"
        job = Job.query.first()

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    # 1. Test followup API
    resp = client.post("/interview/api/followup", json={
        "job_id": job.id,
        "question": "Tell me about a time you optimized a slow query.",
        "answer": "I identified missing indices on a high-cardinality table in PostgreSQL, reducing query latency from 2400ms to 45ms."
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "followup" in data
    assert "followup_question" in data["followup"]

    # 2. Test reverse questions API
    resp_rq = client.get(f"/interview/api/reverse-questions/{job.id}")
    assert resp_rq.status_code == 200
    data_rq = resp_rq.get_json()
    assert data_rq["success"] is True
    assert len(data_rq["questions"]) >= 3

    # 3. Test save session API
    resp_save = client.post("/interview/api/save-session", json={
        "job_id": job.id,
        "overall_score": 85.5,
        "delivery_score": 90.0,
        "average_wpm": 138.0,
        "answers": [
            {
                "question": "Tell me about a time you optimized a slow query.",
                "type": "Technical Architecture",
                "answer": "I added composite indices and rewritten joins.",
                "score": 88.0,
                "star_breakdown": {"situation": {"score": 85, "feedback": "Clear context"}},
                "strengths": ["Clear metrics"],
                "areas_for_improvement": ["Elaborate on trade-offs"],
                "speech_analytics": {"delivery_score": 90, "estimated_wpm": 138}
            }
        ]
    })
    assert resp_save.status_code == 200
    data_save = resp_save.get_json()
    assert data_save["success"] is True
    assert "session_id" in data_save
    session_id = data_save["session_id"]

    # 4. Test view saved session
    resp_view = client.get(f"/interview/session/{session_id}")
    assert resp_view.status_code == 200
    assert "Practice Session Review" in resp_view.data.decode("utf-8")

    # 5. Test cheat sheet endpoint
    resp_cs = client.get(f"/interview/cheat-sheet/{job.id}")
    assert resp_cs.status_code == 200
    assert "Pre-Interview Briefing" in resp_cs.data.decode("utf-8")
