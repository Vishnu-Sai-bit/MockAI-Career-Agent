import pytest
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from services.greenhouse_directory_service import greenhouse_directory
from services.bamboohr_directory_service import bamboohr_directory
from services.workday_directory_service import workday_directory
from services.company_discovery_service import CompanyDiscoveryService
from services.company_service import CompanyService
from collectors.greenhouse_collector import GreenhouseCollector
from collectors.bamboohr_collector import BambooHRCollector

@pytest.fixture
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_greenhouse_directory_loads_companies():
    stats = greenhouse_directory.get_stats()
    assert stats["total_companies"] >= 5000
    assert "companies-using-greenhouse.csv" in stats["csv_path"]

def test_greenhouse_directory_lookup():
    spacex = greenhouse_directory.get_company("spacex")
    assert spacex is not None
    assert spacex["board_token"] == "spacex"
    assert "Space" in spacex["company_name"]

    anthropic = greenhouse_directory.get_company("anthropic")
    assert anthropic is not None
    assert anthropic["board_token"] == "anthropic"

    anduril = greenhouse_directory.get_company("andurilindustries")
    assert anduril is not None
    assert anduril["board_token"] == "andurilindustries"

def test_greenhouse_directory_search():
    results = greenhouse_directory.search_companies(query="SpaceX", limit=5)
    assert len(results) >= 1
    assert any("spacex" in r["board_token"] for r in results)

def test_bamboohr_directory_loads_companies():
    stats = bamboohr_directory.get_stats()
    assert stats["total_companies"] >= 6000
    assert "companies-using-bamboohr.csv" in stats["csv_path"]

def test_bamboohr_directory_lookup():
    armstrong = bamboohr_directory.get_company("armstrongfluidtechnology")
    assert armstrong is not None
    assert armstrong["subdomain"] == "armstrongfluidtechnology"

    upike = bamboohr_directory.get_company("upike")
    assert upike is not None
    assert upike["subdomain"] == "upike"
    assert "Pikeville" in upike["company_name"]

def test_bamboohr_directory_search():
    results = bamboohr_directory.search_companies(query="Armstrong", limit=5)
    assert len(results) >= 1
    assert any("armstrongfluidtechnology" in r["subdomain"] for r in results)

def test_company_discovery_catalog_stats():
    service = CompanyDiscoveryService()
    stats = service.get_catalog_stats()
    assert stats["total_supported_employers"] >= 14000
    breakdown = stats["platform_breakdown"]
    assert breakdown["greenhouse_directory"] >= 5000
    assert breakdown["bamboohr_directory"] >= 6000
    assert breakdown["workday_directory"] >= 2500

def test_company_discovery_url_detection():
    service = CompanyDiscoveryService()
    gh = service.detect_platform_from_url("https://boards.greenhouse.io/spacex/jobs/12345")
    assert gh == ("greenhouse", "spacex")

    bb = service.detect_platform_from_url("https://armstrongfluidtechnology.bamboohr.com/careers/55")
    assert bb == ("bamboohr", "armstrongfluidtechnology")

def test_company_service_platform_filters(test_app):
    # Use unique keys to avoid unique constraint collisions
    src_gh = JobSource.query.filter_by(platform="greenhouse", company_key="test-spacex-unique").first()
    if not src_gh:
        src_gh = JobSource(platform="greenhouse", company_key="test-spacex-unique", name="Test SpaceX", is_active=True)
        db.session.add(src_gh)

    src_bb = JobSource.query.filter_by(platform="bamboohr", company_key="test-armstrong-unique").first()
    if not src_bb:
        src_bb = JobSource(platform="bamboohr", company_key="test-armstrong-unique", name="Test Armstrong", is_active=True)
        db.session.add(src_bb)

    src_wd = JobSource.query.filter_by(platform="workday", company_key="test-nvidia-unique").first()
    if not src_wd:
        src_wd = JobSource(platform="workday", company_key="test-nvidia-unique", name="Test NVIDIA", is_active=True)
        db.session.add(src_wd)

    db.session.commit()

    j1 = Job(
        source_id=src_gh.id,
        source_platform="greenhouse",
        source_company_key="test-spacex-unique",
        source_job_id="gh-unique-1",
        title="Falcon Avionics Engineer",
        company="SpaceX Unique",
        original_url="https://boards.greenhouse.io/spacex/jobs/1",
        apply_url="https://boards.greenhouse.io/spacex/jobs/1#app",
        status="active"
    )
    j2 = Job(
        source_id=src_bb.id,
        source_platform="bamboohr",
        source_company_key="test-armstrong-unique",
        source_job_id="bb-unique-1",
        title="Fluid Systems Engineer",
        company="Armstrong Unique",
        original_url="https://armstrongfluidtechnology.bamboohr.com/careers/1",
        apply_url="https://armstrongfluidtechnology.bamboohr.com/careers/1/apply",
        status="active"
    )
    j3 = Job(
        source_id=src_wd.id,
        source_platform="workday",
        source_company_key="test-nvidia-unique",
        source_job_id="wd-unique-1",
        title="GPU Architect",
        company="NVIDIA Unique",
        original_url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/1",
        apply_url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/1/apply",
        status="active"
    )
    db.session.add_all([j1, j2, j3])
    db.session.commit()

    service = CompanyService()
    gh_dir = service.get_companies_directory(filter_type="greenhouse")
    assert any(c["name"] == "SpaceX Unique" for c in gh_dir["companies"])

    bb_dir = service.get_companies_directory(filter_type="bamboohr")
    assert any(c["name"] == "Armstrong Unique" for c in bb_dir["companies"])

    wd_dir = service.get_companies_directory(filter_type="workday")
    assert any(c["name"] == "NVIDIA Unique" for c in wd_dir["companies"])
