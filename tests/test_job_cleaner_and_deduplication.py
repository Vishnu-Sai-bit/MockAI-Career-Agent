import pytest
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
