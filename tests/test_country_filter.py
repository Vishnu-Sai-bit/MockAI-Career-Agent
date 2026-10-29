import pytest
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from services.job_search_service import JobSearchService
from services.company_service import CompanyService
from services.unified_platform_directory_service import unified_directory

@pytest.fixture
def app_and_ctx():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Create test source
        src = JobSource(name="Test Source", platform="greenhouse", company_key="test", is_active=True)
        db.session.add(src)
        db.session.commit()

        # Seed test jobs across various countries
        jobs = [
            Job(
                source_id=src.id, source_platform="greenhouse", source_company_key="swiggy",
                source_job_id="sw-1", title="Backend Engineer", company="Swiggy",
                location="Bengaluru, Karnataka, India", country="India", city="Bengaluru",
                work_mode="on-site", original_url="https://swiggy.com/1", apply_url="https://swiggy.com/1/apply",
                status="active"
            ),
            Job(
                source_id=src.id, source_platform="greenhouse", source_company_key="stripe",
                source_job_id="st-1", title="Infrastructure Engineer", company="Stripe",
                location="San Francisco, CA, USA", country="United States", city="San Francisco",
                work_mode="hybrid", original_url="https://stripe.com/1", apply_url="https://stripe.com/1/apply",
                status="active"
            ),
            Job(
                source_id=src.id, source_platform="greenhouse", source_company_key="monzo",
                source_job_id="mz-1", title="Platform Engineer", company="Monzo",
                location="London, UK", country="United Kingdom", city="London",
                work_mode="hybrid", original_url="https://monzo.com/1", apply_url="https://monzo.com/1/apply",
                status="active"
            ),
            Job(
                source_id=src.id, source_platform="greenhouse", source_company_key="zalando",
                source_job_id="zl-1", title="Software Engineer", company="Zalando",
                location="Berlin, Germany", country="Germany", city="Berlin",
                work_mode="on-site", original_url="https://zalando.com/1", apply_url="https://zalando.com/1/apply",
                status="active"
            ),
            Job(
                source_id=src.id, source_platform="greenhouse", source_company_key="shopify",
                source_job_id="sp-1", title="Full Stack Developer", company="Shopify",
                location="Toronto, Canada", country="Canada", city="Toronto",
                work_mode="remote", original_url="https://shopify.com/1", apply_url="https://shopify.com/1/apply",
                status="active"
            ),
            Job(
                source_id=src.id, source_platform="greenhouse", source_company_key="gitlab",
                source_job_id="gl-1", title="Staff Engineer", company="GitLab",
                location="Remote - Worldwide", country="Remote", city="",
                work_mode="remote", original_url="https://gitlab.com/1", apply_url="https://gitlab.com/1/apply",
                status="active"
            ),
        ]
        db.session.add_all(jobs)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

def test_country_filter_india(app_and_ctx):
    search_service = JobSearchService()
    results = search_service.search_jobs(country="India")
    assert results["total"] == 1
    assert results["jobs"][0]["job"].company == "Swiggy"

def test_country_filter_united_states(app_and_ctx):
    search_service = JobSearchService()
    results = search_service.search_jobs(country="United States")
    assert results["total"] == 1
    assert results["jobs"][0]["job"].company == "Stripe"

def test_country_filter_united_kingdom(app_and_ctx):
    search_service = JobSearchService()
    results = search_service.search_jobs(country="United Kingdom")
    assert results["total"] == 1
    assert results["jobs"][0]["job"].company == "Monzo"

def test_country_filter_germany(app_and_ctx):
    search_service = JobSearchService()
    results = search_service.search_jobs(country="Germany")
    assert results["total"] == 1
    assert results["jobs"][0]["job"].company == "Zalando"

def test_country_filter_canada(app_and_ctx):
    search_service = JobSearchService()
    results = search_service.search_jobs(country="Canada")
    assert results["total"] == 1
    assert results["jobs"][0]["job"].company == "Shopify"

def test_country_filter_remote(app_and_ctx):
    search_service = JobSearchService()
    results = search_service.search_jobs(country="Remote")
    # Shopify is work_mode='remote' and GitLab is work_mode='remote' / country='Remote'
    assert results["total"] >= 2
    companies = [j["job"].company for j in results["jobs"]]
    assert "GitLab" in companies
    assert "Shopify" in companies

def test_jobs_route_default_is_india(app_and_ctx):
    client = app_and_ctx.test_client()
    resp = client.get("/jobs")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Swiggy" in html
    assert "Stripe" not in html
    assert "India (Default)" in html

def test_jobs_route_country_param(app_and_ctx):
    client = app_and_ctx.test_client()
    resp = client.get("/jobs?country=India")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Swiggy" in html
    assert "Stripe" not in html
    assert "Country: India" in html

def test_company_service_country_filter(app_and_ctx):
    service = CompanyService()
    india_companies = service.get_companies_directory(filter_type="india")
    assert any(c["name"] == "Swiggy" for c in india_companies["companies"])
    assert not any(c["name"] == "Monzo" for c in india_companies["companies"])

    us_companies = service.get_companies_directory(filter_type="us")
    assert any(c["name"] == "Stripe" for c in us_companies["companies"])

def test_unified_directory_service_integrity():
    stats = unified_directory.get_stats()
    assert stats["total_companies"] > 35000
    assert len(stats["platform_breakdown"]) >= 13
    assert "workday" in stats["platform_breakdown"]
    assert "greenhouse" in stats["platform_breakdown"]
    assert "ashby" in stats["platform_breakdown"]
    assert "lever" in stats["platform_breakdown"]
    assert "smartrecruiters" in stats["platform_breakdown"]
