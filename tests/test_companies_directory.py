import pytest
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from models.user import User
from models.dream_company import DreamCompany
from services.company_service import CompanyService

@pytest.fixture
def comp_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        source = JobSource.query.filter_by(platform="greenhouse", company_key="stripe").first()
        if not source:
            source = JobSource(platform="greenhouse", company_key="stripe", name="Stripe Greenhouse")
            db.session.add(source)
            db.session.commit()

        # Seed sample active jobs across companies
        j1 = Job(
            source_id=source.id,
            source_platform="greenhouse",
            source_company_key="stripe",
            source_job_id="str-test-1",
            title="Backend Engineer",
            company="Stripe",
            location="Bengaluru, India",
            status="active",
            original_url="https://stripe.com/jobs/1",
            apply_url="https://stripe.com/jobs/1#app"
        )
        j2 = Job(
            source_id=source.id,
            source_platform="greenhouse",
            source_company_key="stripe",
            source_job_id="str-test-2",
            title="Frontend Engineer",
            company="Stripe",
            location="Remote",
            status="active",
            original_url="https://stripe.com/jobs/2",
            apply_url="https://stripe.com/jobs/2#app"
        )
        j3 = Job(
            source_id=source.id,
            source_platform="lever",
            source_company_key="spotify",
            source_job_id="spot-test-1",
            title="Data Scientist",
            company="Spotify",
            location="Stockholm, Sweden",
            status="active",
            original_url="https://jobs.lever.co/spotify/1",
            apply_url="https://jobs.lever.co/spotify/1"
        )
        db.session.add_all([j1, j2, j3])

        # Test user
        user = User(email="testcandidate@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        app.test_user_id = user.id
        yield app
        db.session.remove()
        db.drop_all()

def test_company_service_aggregation(comp_app):
    with comp_app.app_context():
        service = CompanyService()
        data = service.get_companies_directory()
        assert data["total_companies"] >= 2
        comp_names = [c["name"] for c in data["companies"]]
        assert "Stripe" in comp_names
        assert "Spotify" in comp_names
        stripe_data = next(c for c in data["companies"] if c["name"] == "Stripe")
        assert stripe_data["total_jobs"] >= 2
        assert stripe_data["has_india"] is True
        assert stripe_data["has_remote"] is True

def test_companies_route_get(comp_app):
    client = comp_app.test_client()
    resp = client.get("/companies")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Verified Companies & Employers" in html
    assert 'title="Stripe"' in html
    assert 'title="Spotify"' in html
    assert "Open Role" in html

def test_companies_route_search_filter(comp_app):
    client = comp_app.test_client()
    # Search for Stripe
    resp = client.get("/companies?q=Stripe")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'title="Stripe"' in html
    assert 'title="Spotify"' not in html

    # Filter for India
    resp_india = client.get("/companies?filter=india")
    assert resp_india.status_code == 200
    html_india = resp_india.get_data(as_text=True)
    assert 'title="Stripe"' in html_india
    assert 'title="Spotify"' not in html_india

def test_toggle_company_follow_api(comp_app):
    client = comp_app.test_client()
    # Login first
    client.post("/login", data={"email": "testcandidate@example.com", "password": "password123"})

    # Follow Stripe
    resp = client.post("/api/companies/toggle-follow", json={"company_name": "Stripe"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["is_following"] is True

    # Unfollow Stripe
    resp_unfollow = client.post("/api/companies/toggle-follow", json={"company_name": "Stripe"})
    assert resp_unfollow.status_code == 200
    data_unfollow = resp_unfollow.get_json()
    assert data_unfollow["success"] is True
    assert data_unfollow["is_following"] is False


def test_companies_route_mnc_filter_and_badge(comp_app):
    client = comp_app.test_client()
    resp = client.get("/companies?filter=mnc")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'title="Stripe"' in html
    assert 'title="Spotify"' in html
    assert "MNC" in html

    # Test /jobs?company_type=mnc
    jobs_resp = client.get("/jobs?company_type=mnc")
    assert jobs_resp.status_code == 200
    jobs_html = jobs_resp.get_data(as_text=True)
    assert "Top MNCs" in jobs_html
