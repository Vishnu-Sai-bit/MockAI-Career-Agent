import pytest
from app import create_app
from extensions import db
from models.job_source import JobSource
from services.company_discovery_service import CompanyDiscoveryService, PLATFORM_COMPANY_CATALOG

@pytest.fixture
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_catalog_integrity(app_context):
    service = CompanyDiscoveryService()
    stats = service.get_catalog_stats()
    assert stats["total_supported_employers"] >= 100
    assert "greenhouse" in stats["platform_breakdown"]
    assert "lever" in stats["platform_breakdown"]
    assert "ashby" in stats["platform_breakdown"]
    assert "workday" in stats["platform_breakdown"]
    assert "smartrecruiters" in stats["platform_breakdown"]
    assert "workable" in stats["platform_breakdown"]
    assert "recruitee" in stats["platform_breakdown"]

def test_detect_platform_from_url(app_context):
    service = CompanyDiscoveryService()
    
    # Greenhouse
    assert service.detect_platform_from_url("https://boards.greenhouse.io/stripe/jobs/12345") == ("greenhouse", "stripe")
    assert service.detect_platform_from_url("https://boards.greenhouse.io/embed/job_board?for=airbnb") == ("greenhouse", "airbnb")
    
    # Lever
    assert service.detect_platform_from_url("https://jobs.lever.co/netflix/abcd-efgh") == ("lever", "netflix")
    
    # Ashby
    assert service.detect_platform_from_url("https://jobs.ashbyhq.com/cursor/1234") == ("ashby", "cursor")
    
    # Workday
    assert service.detect_platform_from_url("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite") == ("workday", "nvidia")
    
    # SmartRecruiters
    assert service.detect_platform_from_url("https://jobs.smartrecruiters.com/visa/743999") == ("smartrecruiters", "visa")
    
    # Workable
    assert service.detect_platform_from_url("https://apply.workable.com/deliveroo/j/1234") == ("workable", "deliveroo")
    
    # Recruitee
    assert service.detect_platform_from_url("https://bunq.recruitee.com/o/developer") == ("recruitee", "bunq")
    
    # Unknown/generic
    assert service.detect_platform_from_url("https://example.com/careers") is None

def test_register_all_catalog_sources(app_context):
    service = CompanyDiscoveryService()
    initial_count = JobSource.query.count()
    
    added = service.register_all_catalog_sources()
    # It should register the rest of catalog sources
    assert JobSource.query.count() >= 100
    
    # Running again should be idempotent (0 added)
    second_added = service.register_all_catalog_sources()
    assert second_added == 0
    
    assert JobSource.query.filter_by(platform="lever", company_key="netflix").first() is not None
    assert JobSource.query.filter_by(platform="ashby", company_key="cursor").first() is not None
    assert JobSource.query.filter_by(platform="greenhouse", company_key="stripe").first() is not None
