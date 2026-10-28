import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from extensions import db
from models.job import Job
from models.job_source import JobSource
from services.workday_harvester_service import WorkdayHarvesterService
from services.workday_directory_service import workday_directory
from services.job_search_service import JobSearchService

@pytest.fixture
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_harvester_filters_out_404_and_not_found(test_app):
    with test_app.app_context():
        harvester = WorkdayHarvesterService()
        
        # Test with mock 404 response
        with patch("requests.Session.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_post.return_value = mock_resp

            res = harvester.harvest_batch(company_slugs=["cisco"], limit_companies=1)
            # Should have skipped dead 404 response without adding broken jobs
            assert res["total_not_found_skipped"] >= 1
            assert res["total_added"] == 0

def test_harvester_filters_closure_and_error_titles(test_app):
    with test_app.app_context():
        harvester = WorkdayHarvesterService()

        # Mock Workday returning jobs with closure and 'not found' phrases
        with patch("requests.Session.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "jobPostings": [
                    {
                        "title": "Job Not Found",
                        "externalPath": "/job/101",
                        "locationsText": "Remote"
                    },
                    {
                        "title": "Page Not Found - Requisition Closed",
                        "externalPath": "/job/102?not_found=true",
                        "locationsText": "Remote"
                    },
                    {
                        "title": "[Closed] Senior Architect",
                        "externalPath": "/job/103",
                        "locationsText": "San Jose, CA"
                    },
                    {
                        "title": "Lead Software Engineer",
                        "externalPath": "/job/104",
                        "locationsText": "Bangalore, India",
                        "bulletFields": ["REQ-104"]
                    }
                ]
            }
            mock_post.return_value = mock_resp

            res = harvester.harvest_batch(company_slugs=["cisco"], limit_companies=1)
            # Only the 1 real, valid, open job should be added
            assert res["total_added"] == 1
            
            added_job = Job.query.filter_by(source_job_id="REQ-104").first()
            assert added_job is not None
            assert added_job.title == "Lead Software Engineer"
            
            # Verify closure phrases never entered DB
            assert Job.query.filter(Job.title.ilike("%not found%")).count() == 0
            assert Job.query.filter(Job.title.ilike("%[closed]%")).count() == 0

def test_harvester_deduplicates_identical_postings(test_app):
    with test_app.app_context():
        harvester = WorkdayHarvesterService()

        with patch("requests.Session.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # Return identical duplicate jobs
            mock_resp.json.return_value = {
                "jobPostings": [
                    {
                        "title": "Data Analyst",
                        "externalPath": "/job/201",
                        "locationsText": "Mumbai, India",
                        "bulletFields": ["REQ-201"]
                    },
                    {
                        "title": "Data Analyst",
                        "externalPath": "/job/202",
                        "locationsText": "Mumbai, India",
                        "bulletFields": ["REQ-202"]
                    }
                ]
            }
            mock_post.return_value = mock_resp

            res = harvester.harvest_batch(company_slugs=["hitachi"], limit_companies=1)
            # 1 should be added, 1 duplicate dropped
            assert res["total_added"] == 1
            assert Job.query.filter_by(title="Data Analyst").count() == 1

def test_on_demand_search_dynamic_workday_ingestion(test_app):
    with test_app.app_context():
        # Verify Medtronic currently has 0 jobs in test DB
        assert Job.query.filter(Job.company.ilike("%Medtronic%")).count() == 0

        # Mock on-demand harvest returning 1 job
        with patch("requests.Session.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "jobPostings": [
                    {
                        "title": "Biomedical Systems Engineer",
                        "externalPath": "/job/901",
                        "locationsText": "Hyderabad, India",
                        "bulletFields": ["MED-901"]
                    }
                ]
            }
            mock_post.return_value = mock_resp

            search_service = JobSearchService()
            search_res = search_service.search_jobs(keyword="Medtronic")

            # Should have triggered on-demand ingestion and returned the job
            assert search_res["total"] >= 1
            returned_titles = [item["job"].title for item in search_res["jobs"]]
            assert "Biomedical Systems Engineer" in returned_titles
