import pytest
from collectors.workday_collector import WorkdayCollector, WORKDAY_TENANTS
from services.job_normalizer import JobNormalizer
from utils.url_validation import validate_external_job_url

def test_workday_tenants_registry():
    assert "nvidia" in WORKDAY_TENANTS
    assert "adobe" in WORKDAY_TENANTS
    assert "autodesk" in WORKDAY_TENANTS
    assert "target" in WORKDAY_TENANTS
    assert "myworkdayjobs.com" in WORKDAY_TENANTS["nvidia"]["host"]

def test_workday_fetch_jobs():
    collector = WorkdayCollector(timeout=10)
    jobs = collector.fetch_jobs("nvidia", limit=3)
    
    assert len(jobs) > 0
    first_job = jobs[0]
    assert first_job.source_platform == "workday"
    assert first_job.company == "NVIDIA"
    assert first_job.source_job_id != ""
    assert "nvidia.wd5.myworkdayjobs.com" in first_job.original_url
    assert first_job.apply_url != ""

    # Test URL validation passes for Workday
    is_valid, err_msg, clean_url = validate_external_job_url(
        first_job.apply_url,
        expected_platform="workday"
    )
    assert is_valid is True

def test_workday_normalization():
    collector = WorkdayCollector(timeout=10)
    jobs = collector.fetch_jobs("adobe", limit=2)
    assert len(jobs) > 0
    
    normalizer = JobNormalizer()
    normalized = normalizer.normalize(jobs[0])
    
    assert normalized["source_platform"] == "workday"
    assert normalized["company"] == "Adobe"
    assert normalized["apply_url"].startswith("https://")
    assert normalized["title"] != ""
    assert normalized["original_url"] != ""
