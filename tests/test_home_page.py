import pytest
from app import create_app
from extensions import db
from models.user import User
from models.job import Job

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

def test_home_page_connected_data_unauthenticated(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Verify hero title and feature pills
    assert "Find Your Dream Job Faster" in html
    assert "Verified Job Listings" in html
    assert "Smart Job Matching" in html

    # Verify real database counters & stats
    assert "Live Verified Jobs" in html
    assert "Direct Companies" in html
    assert "Official Apply Links" in html

    # Verify hero floating preview cards
    assert "Resume Score" in html
    assert "Interview Prep" in html

    # Verify trusted logos ticker and core features showcase
    assert "Google" in html
    assert "Powerful Features for Your Career Growth" in html

def test_home_page_authenticated_preview(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    # Standard authenticated visit redirects to dashboard
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers.get("Location")

    # With landing/home preview param, allows viewing the connected home page
    resp_landing = client.get("/?landing=1")
    assert resp_landing.status_code == 200
    landing_html = resp_landing.data.decode("utf-8")
    assert "Find Your Dream Job Faster" in landing_html
    assert "Dashboard" in landing_html
    assert "Logout" in landing_html
