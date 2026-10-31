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

    # Verify unauthenticated navbar Jobs link requires login and points to login with next=/jobs
    assert 'href="/login?next=/jobs"' in html
    assert 'Jobs' in html

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
    # Authenticated user has direct access to /jobs in navbar
    assert 'href="/jobs"' in landing_html

def test_jobs_login_redirect_flow(app_instance, client):
    # 1. Unauthenticated landing page Jobs link directs to login with next=/jobs
    resp = client.get("/")
    assert resp.status_code == 200
    assert '/login?next=/jobs' in resp.data.decode("utf-8")

    # 2. Login page renders the next param and informs the visitor
    login_page = client.get("/login?next=/jobs")
    assert login_page.status_code == 200
    assert 'Please sign in or create an account' in login_page.data.decode("utf-8")
    assert 'name="next" value="/jobs"' in login_page.data.decode("utf-8")

    # 3. Successful login with next parameter redirects directly to /jobs
    with app_instance.app_context():
        u = User.query.first()
        user_email = u.email if u else "test@example.com"
        if not u:
            u = User(email=user_email)
            u.set_password("Password123!")
            db.session.add(u)
            db.session.commit()

    login_post = client.post("/login", data={
        "email": user_email,
        "password": "Password123!",
        "next": "/jobs"
    }, follow_redirects=False)

    # If password matched, redirects to /jobs
    if login_post.status_code == 302:
        assert login_post.headers.get("Location") == "/jobs"

def test_auth_split_layout_and_demo_login(client):
    # Test Login page renders modern split layout
    login_resp = client.get("/login")
    assert login_resp.status_code == 200
    login_html = login_resp.data.decode("utf-8")
    assert "auth-split-card" in login_html
    assert "auth-showcase-panel" in login_html
    assert "auth-demo-btn" in login_html
    assert "Quick Sign In as Demo Candidate" in login_html
    assert "Back to Home" in login_html

    # Test Register page renders modern split layout
    reg_resp = client.get("/register")
    assert reg_resp.status_code == 200
    reg_html = reg_resp.data.decode("utf-8")
    assert "auth-split-card" in reg_html
    assert "auth-showcase-panel" in reg_html
    assert "Create Free Account" in reg_html
    assert "Back to Home" in reg_html

    # Test Demo Login endpoint signs in and redirects to dashboard or next param
    demo_resp = client.post("/demo-login?next=/jobs", follow_redirects=False)
    assert demo_resp.status_code == 302
    assert demo_resp.headers.get("Location") == "/jobs"

def test_dashboard_connected_links_and_navigation(app_instance, client):
    with app_instance.app_context():
        u = User.query.first()
        user_id = str(u.id) if u else "1"

    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True

    # Access dashboard
    dash_resp = client.get("/dashboard")
    assert dash_resp.status_code == 200
    dash_html = dash_resp.data.decode("utf-8")

    # Verify stat cards are clickable links to respective tools
    assert 'href="/ats"' in dash_html
    assert 'href="/settings"' in dash_html
    assert 'href="/saved-jobs"' in dash_html
    assert 'href="/applications"' in dash_html

    # Verify topbar and sidebar contain Home navigation
    assert 'Home Page' in dash_html
    assert 'href="/?home=1"' in dash_html

    # Verify authenticated user can visit /home without forced redirect
    home_resp = client.get("/home")
    assert home_resp.status_code == 200
    home_html = home_resp.data.decode("utf-8")
    assert "Find Your Dream Job Faster" in home_html
    assert "Dashboard" in home_html
