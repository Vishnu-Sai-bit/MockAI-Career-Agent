import pytest
from collectors.adzuna_collector import AdzunaCollector
from collectors.jobicy_collector import JobicyCollector
from collectors.themuse_collector import TheMuseCollector
from collectors.himalayas_collector import HimalayasCollector
from collectors.bamboohr_collector import BambooHRCollector
from collectors.personio_collector import PersonioCollector
from collectors.usajobs_collector import USAJobsCollector
from collectors import get_collector_for_platform, COLLECTOR_REGISTRY
from utils.url_validation import validate_external_job_url

def test_registry_contains_all_phase2_collectors():
    for name in ["adzuna", "jobicy", "themuse", "himalayas", "bamboohr", "personio", "usajobs"]:
        assert name in COLLECTOR_REGISTRY
        col = get_collector_for_platform(name)
        assert col.platform_name == name

def test_adzuna_url_validation():
    sample_url = "https://www.adzuna.in/details/5845820602?utm_medium=api&utm_source=01f60413"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="adzuna")
    assert is_valid is True
    assert "adzuna.in" in norm

def test_jobicy_url_validation():
    sample_url = "https://jobicy.com/jobs/153612-conceptual-copywriter"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="jobicy")
    assert is_valid is True
    assert "jobicy.com" in norm

def test_themuse_url_validation():
    sample_url = "https://www.themuse.com/jobs/thelaurelsofkent/licensed-practical-nurse-lpn-sign-on-bonus-3baf6a"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="themuse")
    assert is_valid is True
    assert "themuse.com" in norm

def test_himalayas_url_validation():
    sample_url = "https://himalayas.app/companies/guardian/jobs/head-of-distribution-strategy"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="himalayas")
    assert is_valid is True
    assert "himalayas.app" in norm

def test_bamboohr_url_validation():
    sample_url = "https://postman.bamboohr.com/careers/123/apply"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="bamboohr")
    assert is_valid is True
    assert "bamboohr.com" in norm

def test_personio_url_validation():
    sample_url = "https://company.jobs.personio.de/job/987654#apply"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="personio")
    assert is_valid is True
    assert "personio.de" in norm

def test_usajobs_url_validation():
    sample_url = "https://www.usajobs.gov/job/789123400"
    is_valid, err, norm = validate_external_job_url(sample_url, expected_platform="usajobs")
    assert is_valid is True
    assert "usajobs.gov" in norm
