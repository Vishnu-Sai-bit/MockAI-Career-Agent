import pytest
from unittest.mock import patch, MagicMock
from utils.job_live_check import check_url_live, CLOSED_PHRASES, CLOSED_URL_SIGNALS
from services.job_verifier import JobVerifier
from models.job import Job
from extensions import db
from app import create_app

@pytest.fixture
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_check_url_live_url_signal_not_found():
    is_live, code, details = check_url_live("https://apply.workable.com/company/?not_found=true")
    assert is_live is False
    assert code == 404
    assert "not_found=true" in details

def test_check_url_live_empty_url():
    is_live, code, details = check_url_live("")
    assert is_live is False
    assert code == 0

@patch("requests.Session.get")
def test_check_url_live_http_404(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    is_live, code, details = check_url_live("https://boards.greenhouse.io/company/jobs/12345")
    assert is_live is False
    assert code == 404
    assert "Expired/Not Found" in details

@patch("requests.Session.get")
def test_check_url_live_soft_closure_in_html(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>The job you are looking for is no longer available.</h1></body></html>"
    mock_get.return_value = mock_resp

    is_live, code, details = check_url_live("https://jobs.example.com/posting/999")
    assert is_live is False
    assert code == 200
    assert "no longer available" in details

@patch("requests.Session.get")
def test_check_url_live_active_job(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Senior Full Stack Engineer</h1><p>Join our fast-growing engineering team!</p></body></html>"
    mock_get.return_value = mock_resp

    is_live, code, details = check_url_live("https://jobs.example.com/posting/100")
    assert is_live is True
    assert code == 200
    assert "verified live" in details.lower()

def test_job_verifier_marks_closed_in_db(test_app):
    from models.job_source import JobSource
    with test_app.app_context():
        src = JobSource.query.filter_by(platform="workable", company_key="skroutz").first()
        if not src:
            src = JobSource(
                platform="workable",
                company_key="skroutz",
                name="Skroutz (Workable)",
                is_active=True
            )
            db.session.add(src)
            db.session.commit()

        job = Job(
            source_id=src.id,
            source_platform="workable",
            source_company_key="skroutz",
            source_job_id="dead-123",
            title="Expired Position",
            company="Skroutz",
            original_url="https://apply.workable.com/skroutz/?not_found=true",
            apply_url="https://apply.workable.com/skroutz/?not_found=true",
            status="active"
        )
        db.session.add(job)
        db.session.commit()

        verifier = JobVerifier()
        is_live, details = verifier.verify_job(job)

        assert is_live is False
        assert job.status == "closed"
        assert job.last_verified_at is not None
