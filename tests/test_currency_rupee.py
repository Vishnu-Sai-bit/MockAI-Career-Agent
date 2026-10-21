import pytest
from app import create_app
from models.job import Job
from models.user import CandidateProfile
from utils.currency_formatter import format_job_salary, format_inr
from services.salary_intelligence import SalaryIntelligenceService

def test_currency_rupee_formatting():
    # INR role with min and max
    job_inr = Job(
        source_id=1,
        source_platform="greenhouse",
        source_company_key="swiggy",
        source_job_id="SW101",
        title="Software Engineer",
        company="Swiggy",
        location="Bengaluru, India",
        salary_min=1200000,
        salary_max=1800000,
        currency="INR",
        original_url="https://swiggy.com/job",
        apply_url="https://swiggy.com/job/apply"
    )
    res_inr = format_job_salary(job_inr)
    assert "\u20b9" in res_inr
    assert "12.0" in res_inr and "18.0" in res_inr and "LPA" in res_inr

    # USD role converted to INR
    job_usd = Job(
        source_id=1,
        source_platform="remotive",
        source_company_key="automattic",
        source_job_id="AT202",
        title="Full Stack Engineer",
        company="Automattic",
        location="Remote",
        salary_min=30000,
        salary_max=None,
        currency="USD",
        original_url="https://automattic.com/job",
        apply_url="https://automattic.com/job/apply"
    )
    res_usd = format_job_salary(job_usd)
    assert "\u20b9" in res_usd
    assert "LPA" in res_usd
    assert "$30k+" in res_usd

    # format_inr helper
    formatted = format_inr(1500000)
    assert "\u20b9" in formatted
    assert "15.0 LPA" in formatted


def test_models_currency_defaults():
    profile = CandidateProfile()
    assert profile.currency == "INR"

    job = Job(
        source_id=1,
        source_platform="greenhouse",
        source_company_key="co",
        source_job_id="J1",
        title="Dev",
        company="Co",
        original_url="https://co.com/job",
        apply_url="https://co.com/job/apply"
    )
    assert job.currency == "INR"


def test_salary_intelligence_defaults_to_inr():
    sal = SalaryIntelligenceService()
    est = sal.estimate_market_salary("Backend Engineer", "Remote", 3.0, ["Python", "Docker"])
    assert est["currency"] == "INR"
    assert est["median"] >= 1000000
