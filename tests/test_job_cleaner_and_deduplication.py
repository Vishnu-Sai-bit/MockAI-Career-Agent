import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from services.job_cleaner_service import JobCleanerService
from services.job_search_service import JobSearchService

@pytest.fixture
def clean_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        source = JobSource(platform="greenhouse", company_key="testco", name="Test Co")
        db.session.add(source)
        db.session.commit()
        app.test_source_id = source.id
        yield app
        db.session.remove()
        db.drop_all()

def test_purge_inactive_jobs(clean_app):
    with clean_app.app_context():
        # Create 1 active and 2 inactive jobs
        j1 = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="act-1",
            title="Data Analyst",
            company="Acme Corp",
            status="active",
            original_url="https://example.com/1",
            apply_url="https://example.com/1"
        )
        j2 = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="closed-1",
            title="Senior Data Analyst",
            company="Acme Corp",
            status="closed",
            original_url="https://example.com/2",
            apply_url="https://example.com/2"
        )
        j3 = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="exp-1",
            title="Expired Analyst",
            company="Acme Corp",
            status="expired",
            original_url="https://example.com/3",
            apply_url="https://example.com/3"
        )
        db.session.add_all([j1, j2, j3])
        db.session.commit()

        assert Job.query.count() == 3
        purged = JobCleanerService.purge_inactive_jobs()
        assert purged == 2
        assert Job.query.count() == 1
        assert Job.query.first().id == j1.id

def test_purge_closure_signal_jobs(clean_app):
    with clean_app.app_context():
        j_live = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="live-1",
            title="Frontend Engineer",
            company="Acme Corp",
            status="active",
            original_url="https://boards.greenhouse.io/testco/jobs/101",
            apply_url="https://boards.greenhouse.io/testco/jobs/101#app"
        )
        j_closed_title = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="closed-title-1",
            title="[Closed] Product Manager",
            company="Acme Corp",
            status="active",
            original_url="https://boards.greenhouse.io/testco/jobs/102",
            apply_url="https://boards.greenhouse.io/testco/jobs/102#app"
        )
        j_url_not_found = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="not-found-url-1",
            title="Cloud Architect",
            company="Acme Corp",
            status="active",
            original_url="https://boards.greenhouse.io/testco/jobs/103?not_found=true",
            apply_url="https://boards.greenhouse.io/testco/jobs/103?not_found=true"
        )
        db.session.add_all([j_live, j_closed_title, j_url_not_found])
        db.session.commit()

        purged = JobCleanerService.purge_closure_signal_jobs()
        assert purged == 2
        assert Job.query.count() == 1
        assert Job.query.first().id == j_live.id

def test_purge_invalid_or_malformed_url_jobs(clean_app):
    with clean_app.app_context():
        j_good = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="good-1",
            title="DevOps Engineer",
            company="Acme Corp",
            status="active",
            original_url="https://boards.greenhouse.io/testco/jobs/201",
            apply_url="https://boards.greenhouse.io/testco/jobs/201#app"
        )
        j_bad_url = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="bad-1",
            title="Security Engineer",
            company="Acme Corp",
            status="active",
            original_url="javascript:alert(1)",
            apply_url="javascript:alert(1)"
        )
        db.session.add_all([j_good, j_bad_url])
        db.session.commit()

        purged = JobCleanerService.purge_invalid_or_malformed_url_jobs()
        assert purged == 1
        assert Job.query.count() == 1
        assert Job.query.first().id == j_good.id

def test_purge_duplicate_jobs(clean_app):
    with clean_app.app_context():
        # Create duplicate jobs with identical company & title
        j_keeper = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="keep-1",
            title="Software Engineer",
            company="Google",
            salary_min=120000,
            status="active",
            original_url="https://example.com/google-se-1",
            apply_url="https://example.com/google-se-1"
        )
        j_dup = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="dup-1",
            title="Software Engineer",
            company="Google",
            salary_min=None,
            status="active",
            original_url="https://example.com/google-se-2",
            apply_url="https://example.com/google-se-2"
        )
        db.session.add_all([j_keeper, j_dup])
        db.session.commit()

        assert Job.query.count() == 2
        purged = JobCleanerService.purge_duplicate_jobs()
        assert purged == 1
        assert Job.query.count() == 1
        remaining = Job.query.first()
        assert remaining.id == j_keeper.id

def test_search_service_defensive_closure_filtering(clean_app):
    with clean_app.app_context():
        j_active = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="def-1",
            title="Python Developer",
            company="Netflix",
            status="active",
            original_url="https://jobs.lever.co/netflix/1",
            apply_url="https://jobs.lever.co/netflix/1"
        )
        j_closed_title = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="def-2",
            title="Python Developer [Closed]",
            company="Netflix",
            status="active",
            original_url="https://jobs.lever.co/netflix/2",
            apply_url="https://jobs.lever.co/netflix/2"
        )
        j_expired_url = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="def-3",
            title="Python Developer",
            company="Amazon",
            status="active",
            original_url="https://jobs.example.com/3?not_found=true",
            apply_url="https://jobs.example.com/3?not_found=true"
        )
        db.session.add_all([j_active, j_closed_title, j_expired_url])
        db.session.commit()

        service = JobSearchService()
        results = service.search_jobs(keyword="Python")
        # Ensure only the truly active, unclosed job is returned
        returned_ids = [item["job"].id for item in results["jobs"]]
        assert j_active.id in returned_ids
        assert j_closed_title.id not in returned_ids
        assert j_expired_url.id not in returned_ids

def test_search_service_runtime_deduplication(clean_app):
    with clean_app.app_context():
        j1 = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="s1",
            title="Backend Developer",
            company="Meta",
            status="active",
            original_url="https://example.com/meta-1",
            apply_url="https://example.com/meta-1"
        )
        j2 = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="s2",
            title="Backend Developer",
            company="Meta",
            status="active",
            original_url="https://example.com/meta-2",
            apply_url="https://example.com/meta-2"
        )
        db.session.add_all([j1, j2])
        db.session.commit()

        service = JobSearchService()
        res = service.search_jobs(keyword="Backend")
        # Ensure runtime deduplication collapses identical company + title
        assert len(res["jobs"]) == 1
        assert res["jobs"][0]["job"].company == "Meta"

def test_clean_jobs_endpoint(clean_app):
    client = clean_app.test_client()
    with clean_app.app_context():
        # Add an inactive job
        j = Job(
            source_id=clean_app.test_source_id,
            source_platform="greenhouse",
            source_company_key="testco",
            source_job_id="ep-1",
            title="Old Position",
            company="Acme Corp",
            status="closed",
            original_url="https://example.com/old",
            apply_url="https://example.com/old"
        )
        db.session.add(j)
        db.session.commit()

        response = client.get("/jobs/clean", headers={"X-Requested-With": "XMLHttpRequest"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["stats"]["inactive_purged"] >= 1
        assert Job.query.filter_by(id=j.id).first() is None
