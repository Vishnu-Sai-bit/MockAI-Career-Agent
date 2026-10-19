from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.resume_routes import resume_bp
from routes.ats_routes import ats_bp
from routes.job_routes import jobs_bp
from routes.application_routes import applications_bp
from routes.assistant_routes import assistant_bp
from routes.interview_routes import interview_bp
from routes.salary_routes import salary_bp
from routes.alert_routes import alert_bp
from routes.watchlist_routes import watchlist_bp
from routes.extension_routes import extension_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "resume_bp",
    "ats_bp",
    "jobs_bp",
    "applications_bp",
    "assistant_bp",
    "interview_bp",
    "salary_bp",
    "alert_bp",
    "watchlist_bp",
    "extension_bp"
]
