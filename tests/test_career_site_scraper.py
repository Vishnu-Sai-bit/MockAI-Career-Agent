import pytest
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from services.career_site_scraper_service import CareerSiteScraperService

@pytest.fixture
def app_ctx():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_detect_platform_and_key():
    service = CareerSiteScraperService()
    
    # Greenhouse URLs
    plat, key, name = service.detect_platform_and_key("https://boards.greenhouse.io/swiggy")
    assert plat == "greenhouse"
    assert key == "swiggy"
    
    plat, key, name = service.detect_platform_and_key("https://job-boards.greenhouse.io/embed/job_board?for=inmobi")
    assert plat == "greenhouse"
    assert key == "inmobi"
    
    # Lever URLs
    plat, key, name = service.detect_platform_and_key("https://jobs.lever.co/paytm")
    assert plat == "lever"
    assert key == "paytm"
    
    # Ashby URLs
    plat, key, name = service.detect_platform_and_key("https://jobs.ashbyhq.com/Tekion")
    assert plat == "ashby"
    assert key == "tekion"
    
    # Workday URLs
    plat, key, name = service.detect_platform_and_key("https://cisco.wd5.myworkdayjobs.com/CiscoJobs")
    assert plat == "workday"
    assert key == "cisco"
    
    # SmartRecruiters URLs
    plat, key, name = service.detect_platform_and_key("https://jobs.smartrecruiters.com/BoschGroup")
    assert plat == "smartrecruiters"
    assert key == "boschgroup"
    
    # Workable URLs
    plat, key, name = service.detect_platform_and_key("https://apply.workable.com/skroutz")
    assert plat == "workable"
    assert key == "skroutz"
    
    # BambooHR URLs
    plat, key, name = service.detect_platform_and_key("https://postman.bamboohr.com/careers")
    assert plat == "bamboohr"
    assert key == "postman"

def test_detect_from_company_name():
    service = CareerSiteScraperService()
    plat, key, name = service.detect_platform_and_key("Tekion")
    assert plat in ["ashby", "greenhouse", "lever"]
    assert "tekion" in key.lower()

def test_scrape_and_ingest_mock(app_ctx, monkeypatch):
    from collectors.base_collector import RawJobRecord
    
    service = CareerSiteScraperService()
    
    mock_records = [
        RawJobRecord(
            source_platform="lever",
            source_company_key="paytm",
            source_job_id="paytm-101",
            title="Senior Backend Engineer",
            company="Paytm",
            location="Noida, India",
            description="Build high-scale payments systems with Go and Java.",
            original_url="https://jobs.lever.co/paytm/101",
            apply_url="https://jobs.lever.co/paytm/101/apply"
        ),
        RawJobRecord(
            source_platform="lever",
            source_company_key="paytm",
            source_job_id="paytm-102",
            title="Data Scientist",
            company="Paytm",
            location="Bengaluru, Karnataka, India",
            description="Machine learning and predictive models.",
            original_url="https://jobs.lever.co/paytm/102",
            apply_url="https://jobs.lever.co/paytm/102/apply"
        )
    ]
    
    from collectors.lever_collector import LeverCollector
    monkeypatch.setattr(LeverCollector, "fetch_jobs", lambda self, company_key: mock_records)
    
    res = service.scrape_and_ingest("https://jobs.lever.co/paytm")
    assert res["success"] is True
    assert res["jobs_scraped"] == 2
    assert res["jobs_added"] == 2
    assert Job.query.count() == 2
    
    # Duplicate prevention: running again should not duplicate jobs
    res2 = service.scrape_and_ingest("https://jobs.lever.co/paytm")
    assert res2["success"] is True
    assert res2["jobs_added"] == 0
    assert Job.query.count() == 2
