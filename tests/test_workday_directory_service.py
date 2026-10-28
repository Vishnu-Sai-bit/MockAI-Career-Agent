import pytest
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from services.workday_directory_service import WorkdayDirectoryService, workday_directory
from services.company_discovery_service import CompanyDiscoveryService
from services.company_service import CompanyService
from collectors.workday_collector import WorkdayCollector

@pytest.fixture
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_workday_directory_loads_companies():
    stats = workday_directory.get_stats()
    assert stats["total_companies"] >= 2500
    assert stats["india_companies_count"] >= 80
    assert stats["us_companies_count"] >= 1500

def test_workday_directory_company_lookup():
    # Test lookup by slug
    hitachi = workday_directory.get_company("hitachi")
    assert hitachi is not None
    assert hitachi["tenant"] == "hitachi"
    assert "hitachi" in hitachi["host"]

    # Test lookup by tenant
    cisco = workday_directory.get_company("cisco")
    assert cisco is not None
    assert "cisco" in cisco["host"]
    assert cisco["site"] == "Cisco_Careers"

    # Test lookup for IQVIA
    iqvia = workday_directory.get_company("iqvia")
    assert iqvia is not None
    assert "iqvia" in iqvia["host"]

def test_workday_directory_india_filter():
    india_comps = workday_directory.get_india_companies(limit=50)
    assert len(india_comps) >= 20
    for c in india_comps:
        assert c["main_country"] == "IN"

def test_workday_directory_search():
    results = workday_directory.search_companies(query="Wells Fargo", limit=10)
    assert len(results) >= 1
    assert any("wells fargo" in r["company_name"].lower() for r in results)

def test_workday_collector_dynamic_resolution():
    collector = WorkdayCollector()
    # Test resolving a company not in hardcoded dict, but in CSV
    comp = workday_directory.get_company("hitachi")
    assert comp is not None
    assert comp["host"] == "hitachi.wd1.myworkdayjobs.com"
    assert comp["site"] == "hitachi"

def test_company_discovery_service_with_workday():
    discovery = CompanyDiscoveryService()
    stats = discovery.get_catalog_stats()
    assert stats["total_supported_employers"] >= 2500
    assert "workday_directory" in stats["platform_breakdown"]
    assert stats["platform_breakdown"]["workday_directory"] >= 2500

    # Test URL detection
    plat, slug = discovery.detect_platform_from_url("https://cisco.wd5.myworkdayjobs.com/Cisco_Careers/job/123")
    assert plat == "workday"
    assert slug in ("cisco", "cisco-systems")

def test_company_service_workday_filter(test_app):
    with test_app.app_context():
        src = JobSource(platform="workday", company_key="hitachi", name="Hitachi (Workday)")
        db.session.add(src)
        db.session.commit()

        j = Job(
            source_id=src.id,
            source_platform="workday",
            source_company_key="hitachi",
            source_job_id="w-101",
            title="Senior C++ Developer",
            company="Hitachi",
            location="Bengaluru, India",
            country="IN",
            original_url="https://hitachi.wd1.myworkdayjobs.com/hitachi/job/101",
            apply_url="https://hitachi.wd1.myworkdayjobs.com/hitachi/job/101/apply",
            status="active"
        )
        db.session.add(j)
        db.session.commit()

        service = CompanyService()
        res = service.get_companies_directory(filter_type="workday")
        names = [c["name"] for c in res["companies"]]
        assert "Hitachi" in names
