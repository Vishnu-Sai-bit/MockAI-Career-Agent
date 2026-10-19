from datetime import datetime, timezone, timedelta
import pytest
from utils.date_helpers import format_relative_time
from models.job import Job

def test_format_relative_time_boundaries():
    now = datetime.now(timezone.utc)

    # None and empty
    assert format_relative_time(None) == "Recently"

    # Seconds
    assert format_relative_time(now - timedelta(seconds=15)) == "Just now"

    # Minutes
    assert format_relative_time(now - timedelta(minutes=1)) == "1 min ago"
    assert format_relative_time(now - timedelta(minutes=24)) == "24 mins ago"

    # Hours
    assert format_relative_time(now - timedelta(hours=1)) == "1 hour ago"
    assert format_relative_time(now - timedelta(hours=5)) == "5 hours ago"

    # Days
    assert format_relative_time(now - timedelta(days=1)) == "1 day ago"
    assert format_relative_time(now - timedelta(days=3)) == "3 days ago"
    assert format_relative_time(now - timedelta(days=6)) == "6 days ago"

    # Weeks
    assert format_relative_time(now - timedelta(days=7)) == "1 week ago"
    assert format_relative_time(now - timedelta(days=21)) == "3 weeks ago"

    # Months
    assert format_relative_time(now - timedelta(days=32)) == "1 month ago"
    assert format_relative_time(now - timedelta(days=90)) == "3 months ago"

    # Years
    assert format_relative_time(now - timedelta(days=370)) == "1 year ago"
    assert format_relative_time(now - timedelta(days=750)) == "2 years ago"

def test_job_model_posted_relative_time_property():
    job = Job(
        source_id=1,
        source_platform="workday",
        source_company_key="nvidia",
        source_job_id="JR999",
        title="Software Engineer",
        company="NVIDIA",
        original_url="https://nvidia.wd5.myworkdayjobs.com/job/1",
        apply_url="https://nvidia.wd5.myworkdayjobs.com/job/1/apply",
        published_at=datetime.now(timezone.utc) - timedelta(hours=3)
    )
    assert job.posted_relative_time == "3 hours ago"

def test_naive_datetime_handling():
    # Verify naive datetimes are handled without timezone TypeError
    naive_dt = datetime.utcnow() - timedelta(days=2)
    result = format_relative_time(naive_dt)
    assert "2 days ago" in result or "1 day ago" in result
