import pytest
import os
from flask import url_for
from app import create_app
from extensions import db
from models.user import User, CandidateProfile
from models.resume import Resume

@pytest.fixture
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(test_app):
    return test_app.test_client()

def test_unauthenticated_requests_rejected(client):
    """
    Acceptance Checklist Item 1:
    Unauthenticated requests to candidate-specific endpoints must be rejected or redirected to login.
    """
    # Extension endpoints must require auth
    resp_ext = client.get("/api/v1/extension/profile")
    assert resp_ext.status_code in (302, 401)

    resp_quest = client.post("/api/v1/extension/answer-question", json={"question": "Why join?"})
    assert resp_quest.status_code in (302, 401)

    # Dashboard profile endpoint must require auth
    resp_prof = client.get("/api/candidate-profile")
    assert resp_prof.status_code in (302, 401)

    # Candidate views must require auth
    resp_dash = client.get("/dashboard")
    assert resp_dash.status_code == 302
    assert "/login" in resp_dash.headers.get("Location", "")

    resp_apps = client.get("/applications")
    assert resp_apps.status_code == 302

def test_authenticated_candidate_data_isolation(test_app, client):
    """
    Ensure each candidate accesses strictly their own profile data,
    and no fallback selects another user in the database.
    """
    with test_app.app_context():
        # Create User A
        user_a = User(email="candidate_a@example.com")
        user_a.set_password("SecurePass123!")
        db.session.add(user_a)
        db.session.flush()

        prof_a = CandidateProfile(
            user_id=user_a.id,
            full_name="Alice Candidate",
            headline="Backend Specialist",
            skills=["Python", "FastAPI"]
        )
        db.session.add(prof_a)

        # Create User B
        user_b = User(email="candidate_b@example.com")
        user_b.set_password("SecurePass123!")
        db.session.add(user_b)
        db.session.flush()

        prof_b = CandidateProfile(
            user_id=user_b.id,
            full_name="Bob Candidate",
            headline="Frontend Specialist",
            skills=["React", "TypeScript"]
        )
        db.session.add(prof_b)
        db.session.commit()

    # Log in as User B
    client.post("/login", data={"email": "candidate_b@example.com", "password": "SecurePass123!"})

    # Fetch extension profile
    resp = client.get("/api/v1/extension/profile")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    cand = data["candidate"]
    
    # Must belong strictly to User B (Bob)
    assert cand["email"] == "candidate_b@example.com"
    assert cand["fullName"] == "Bob Candidate"
    assert "React" in cand["skills"]
    assert "FastAPI" not in cand["skills"]
    assert cand["email"] != "candidate_a@example.com"

def test_production_secret_enforcement():
    """
    Verify production startup fails safely if default or insecure secret is used.
    """
    orig_env = os.environ.get("FLASK_ENV")
    orig_secret = os.environ.get("SECRET_KEY")

    try:
        os.environ["SECRET_KEY"] = "dev-ai-job-agent-secret-key-change-in-production-2026"
        with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
            create_app("production")

        # Must succeed with a strong secret
        os.environ["SECRET_KEY"] = "strong-random-production-token-98317283"
        prod_app = create_app("production")
        assert prod_app is not None
    finally:
        if orig_env:
            os.environ["FLASK_ENV"] = orig_env
        else:
            os.environ.pop("FLASK_ENV", None)
        if orig_secret:
            os.environ["SECRET_KEY"] = orig_secret
        else:
            os.environ.pop("SECRET_KEY", None)
