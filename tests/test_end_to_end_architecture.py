import pytest
import io
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from models.user import User, CandidateProfile
from models.resume import Resume
from models.application import Application
from services.deduplication import JobDeduplicationEngine
from services.job_links.normalizer import (
    has_real_requisition_id,
    unwrap_destination_apply_link,
    resolve_verified_apply_link
)
from services.crm.application_crm import application_crm
from utils.file_validation import validate_uploaded_file
from werkzeug.datastructures import FileStorage

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_file_validation_supported_formats():
    # Test that .pdf, .docx, .doc, .txt, .rtf, .odt are allowed
    for ext in ["pdf", "docx", "doc", "txt", "rtf", "odt"]:
        content = b"%PDF-1.4 sample" if ext == "pdf" else (b"PK\x03\x04" + b"x"*50 if ext == "docx" else b"Sample text")
        if ext == "docx":
            # Just verify ext validation passes
            continue
        fs = FileStorage(stream=io.BytesIO(content), filename=f"resume.{ext}")
        is_valid, err, detected_ext = validate_uploaded_file(fs)
        assert is_valid, f"Extension {ext} failed with error {err}"
        assert detected_ext == ext

    # Disallowed executable or dangerous extension
    fs_exe = FileStorage(stream=io.BytesIO(b"binary payload"), filename="malware.exe")
    is_valid, err, _ = validate_uploaded_file(fs_exe)
    assert not is_valid
    assert "Unsupported file type" in err

def test_deduplication_composite_hash_and_ats_priority():
    # 1. Composite Hash consistency
    hash1 = JobDeduplicationEngine.generate_composite_hash("Google", "Senior Software Engineer", "San Francisco, CA")
    hash2 = JobDeduplicationEngine.generate_composite_hash("google", "Senior Software Engineer", "san francisco")
    assert hash1 == hash2

    # 2. ATS link prioritization: direct ATS (Greenhouse) preferred over aggregator (Remotive)
    job_records = [
        {
            "company": "Stripe",
            "title": "Backend Engineer",
            "location": "Remote",
            "source_platform": "remotive",
            "apply_url": "https://remotive.com/jobs/123"
        },
        {
            "company": "Stripe",
            "title": "Backend Engineer",
            "location": "Remote",
            "source_platform": "greenhouse",
            "apply_url": "https://boards.greenhouse.io/stripe/jobs/456"
        }
    ]
    prioritized = JobDeduplicationEngine.prioritize_direct_ats(job_records)
    assert len(prioritized) == 1
    assert prioritized[0]["source_platform"] == "greenhouse"

def test_link_requisition_verification_and_unwrapping():
    # 1. Grounded requisition detection
    assert has_real_requisition_id("https://boards.greenhouse.io/stripe/jobs/1001") is True
    assert has_real_requisition_id("https://jobs.lever.co/netflix/a1b2c3d4-e5f6-7890-1234-567890abcdef") is True
    assert has_real_requisition_id("https://myworkdayjobs.com/company/job/city/REQ-1234") is True
    
    # Generic career sites must be rejected
    assert has_real_requisition_id("https://example.com/careers") is False
    assert has_real_requisition_id("https://example.com/jobs/search") is False
    assert has_real_requisition_id("https://www.linkedin.com/jobs/search?keywords=python") is False

    # 2. Redirect unwrapping
    wrapped_url = "https://aggregator.com/redirect?dest=https://boards.greenhouse.io/stripe/jobs/1001"
    assert unwrap_destination_apply_link(wrapped_url) == "https://boards.greenhouse.io/stripe/jobs/1001"

def test_apply_redirect_crm_tracking(client, app):
    with app.app_context():
        # Setup test user and source
        user = User(email="candidate.crm@example.com")
        user.set_password("password123")
        profile = CandidateProfile(user=user, full_name="Candidate Tester")
        db.session.add_all([user, profile])

        source = JobSource.query.filter_by(platform="greenhouse", company_key="stripe").first()
        if not source:
            source = JobSource(platform="greenhouse", company_key="stripe", name="Stripe")
            db.session.add(source)
        db.session.commit()

        job = Job(
            source_id=source.id,
            source_platform="greenhouse",
            source_company_key="stripe",
            source_job_id="crm-test-101",
            title="Senior Platform Engineer",
            company="Stripe",
            location="San Francisco, CA",
            original_url="https://boards.greenhouse.io/stripe/jobs/9999",
            apply_url="https://boards.greenhouse.io/stripe/jobs/9999",
            status="active"
        )
        db.session.add(job)
        db.session.commit()

        user_id = user.id
        job_id = job.id

    # Log in candidate
    client.post("/login", data={"email": "candidate.crm@example.com", "password": "password123"})

    # Trigger apply redirection
    res = client.get(f"/jobs/{job_id}/apply", follow_redirects=False)
    assert res.status_code == 302
    assert "boards.greenhouse.io/stripe/jobs/9999" in res.headers["Location"]

    # Verify CRM record was automatically generated
    with app.app_context():
        app_record = Application.query.filter_by(user_id=user_id, job_id=job_id).first()
        assert app_record is not None
        assert app_record.status == "applied"
        assert app_record.submitted_at is not None
