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


def test_voice_to_voice_interactive_simulator_apis(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"
        job = Job.query.first()

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    # 1. Personas endpoint
    resp_p = client.get("/interview/api/personas")
    assert resp_p.status_code == 200
    data_p = resp_p.get_json()
    assert data_p["success"] is True
    assert "technical_lead" in data_p["personas"]
    assert "hiring_manager" in data_p["personas"]
    assert "culture_lead" in data_p["personas"]
    assert data_p["personas"]["technical_lead"]["name"] == "Sarah Jenkins"

    # 2. Voice session init endpoint
    resp_init = client.post("/interview/api/voice-session-init", json={
        "job_id": job.id,
        "persona": "technical_lead"
    })
    assert resp_init.status_code == 200
    data_init = resp_init.get_json()
    assert data_init["success"] is True
    assert "greeting" in data_init
    assert "Sarah Jenkins" in data_init["greeting"]
    assert "persona" in data_init

    # 3. Voice turn endpoint (evaluation + spoken reaction + followup)
    resp_turn = client.post("/interview/api/voice-turn", json={
        "job_id": job.id,
        "question": "Tell me about a high scale system you designed.",
        "answer": "Basically, we had a major challenge with database lag. I architected a Redis distributed cache with Kafka queues, um, reducing query response times by 40%.",
        "duration_seconds": 32.5,
        "persona": "technical_lead"
    })
    assert resp_turn.status_code == 200
    data_turn = resp_turn.get_json()
    assert data_turn["success"] is True
    assert "evaluation" in data_turn
    assert "spoken_reaction" in data_turn
    assert "followup_question" in data_turn
    assert "speech_analytics" in data_turn
    assert data_turn["speech_analytics"]["total_filler_words"] >= 2  # 'basically', 'um'

    # 4. Check UI elements in simulator and hub
    resp_sim = client.get(f"/interview/{job.id}")
    assert resp_sim.status_code == 200
    sim_html = resp_sim.data.decode("utf-8")
    assert "Voice-to-Voice Interactive Mock Interview" in sim_html
    assert "voiceCallModal" in sim_html
    assert "voiceVisualizerCanvas" in sim_html
    assert "voice-hud-wpm" in sim_html
    assert "call-done-btn" in sim_html

    resp_hub = client.get("/interview/hub")
    assert resp_hub.status_code == 200
    hub_html = resp_hub.data.decode("utf-8")
    assert "Voice-to-Voice Interactive Mock Interview Simulator" in hub_html
    assert "Live Bi-Directional Audio" in hub_html


def test_technical_skill_tracks_and_topics(app_instance, client):
    """
    Tests the comprehensive technical skill tracks covering SQL, Python, C Language,
    DSA, Java, C++, JS/TS, and System Design.
    """
    from services.skill_tracks_data import get_all_skill_tracks, get_skill_track, get_topic_details

    # 1. Verify Catalog Completeness
    all_tracks = get_all_skill_tracks()
    expected_skills = ["sql", "python", "c_language", "dsa", "java", "cpp", "javascript_web", "system_design"]
    for sk in expected_skills:
        assert sk in all_tracks, f"Missing expected skill track: {sk}"
        track = all_tracks[sk]
        assert "name" in track
        assert "topics" in track
        assert len(track["topics"]) >= 2

    # Verify SQL topics
    sql_track = get_skill_track("sql")
    sql_topic_keys = [t["key"] for t in sql_track["topics"]]
    assert "window_functions" in sql_topic_keys
    assert "complex_joins" in sql_topic_keys
    assert "indexing_optimization" in sql_topic_keys
    assert "acid_transactions" in sql_topic_keys

    # Verify Python topics
    py_track = get_skill_track("python")
    py_topic_keys = [t["key"] for t in py_track["topics"]]
    assert "core_internals" in py_topic_keys
    assert "gil_concurrency" in py_topic_keys
    assert "asyncio_event_loop" in py_topic_keys

    # Verify C Language topics
    c_track = get_skill_track("c_language")
    c_topic_keys = [t["key"] for t in c_track["topics"]]
    assert "pointers_arithmetic" in c_topic_keys
    assert "dynamic_memory_valgrind" in c_topic_keys
    assert "structs_unions_alignment" in c_topic_keys
    assert "bitwise_manipulation" in c_topic_keys

    # 2. Test Question Generation for Specific Skill & Topic
    sim = InterviewSimulator()
    sql_questions = sim.generate_skill_interview_questions("sql", topic_key="window_functions")
    assert len(sql_questions) >= 4
    assert any("window" in q["question"].lower() or "d_rank" in q["question"].lower() or "row_number" in q["question"].lower() or "rank" in q["question"].lower() for q in sql_questions)

    c_questions = sim.generate_skill_interview_questions("c_language", topic_key="pointers_arithmetic")
    assert len(c_questions) >= 4
    assert any("pointer" in q["question"].lower() for q in c_questions)

    # 3. Test Web Routes for Skill Directory & Practice
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    # Check Skills JSON API
    resp_skills = client.get("/interview/skills?format=json")
    assert resp_skills.status_code == 200
    skills_json = resp_skills.get_json()
    assert skills_json["success"] is True
    assert "sql" in skills_json["skills"]
    assert "c_language" in skills_json["skills"]

    # Check Practice Skill Launch for SQL Window Functions
    resp_sql = client.get("/interview/practice/skill/sql?topic=window_functions")
    assert resp_sql.status_code == 302
    assert "/interview/" in resp_sql.headers.get("Location")

    # Follow redirect to simulator
    resp_sim_sql = client.get(resp_sql.headers.get("Location"))
    assert resp_sim_sql.status_code == 200
    sim_sql_html = resp_sim_sql.data.decode("utf-8")
    assert "Technical Skill Track" in sim_sql_html
    assert "SQL" in sim_sql_html

    # Check Practice Skill Launch for C Language Pointers
    resp_c = client.get("/interview/practice/skill/c_language?topic=pointers_arithmetic")
    assert resp_c.status_code == 302
    resp_sim_c = client.get(resp_c.headers.get("Location"))
    assert resp_sim_c.status_code == 200
    sim_c_html = resp_sim_c.data.decode("utf-8")
    assert "C Language" in sim_c_html

    # Check Coding Challenge Launch for C Language
    resp_code_c = client.get("/interview/coding/skill/c_language")
    assert resp_code_c.status_code == 302
    resp_code_page = client.get(resp_code_c.headers.get("Location"))
    assert resp_code_page.status_code == 200
    code_html = resp_code_page.data.decode("utf-8")
    assert "C Language" in code_html or "reverse_buffer" in code_html

    # Check Hub renders Skill Directory and Topics
    resp_hub = client.get("/interview/hub")
    assert resp_hub.status_code == 200
    hub_html = resp_hub.data.decode("utf-8")
    assert "Technical Skill Tracks &amp; Full Topics Directory" in hub_html or "Technical Skill Tracks & Full Topics Directory" in hub_html
    assert "SQL &amp; Database Engineering" in hub_html or "SQL & Database Engineering" in hub_html
    assert "C Language &amp; Systems Programming" in hub_html or "C Language & Systems Programming" in hub_html
    assert "Python Systems &amp; Backend Engineering" in hub_html or "Python Systems & Backend Engineering" in hub_html
    assert "Data Structures &amp; Algorithms (DSA)" in hub_html or "Data Structures & Algorithms (DSA)" in hub_html


