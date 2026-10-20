import os
from flask import Flask
from config import config
from extensions import db, migrate, login_manager
from routes import (
    auth_bp,
    dashboard_bp,
    resume_bp,
    ats_bp,
    jobs_bp,
    applications_bp,
    assistant_bp,
    interview_bp,
    salary_bp,
    alert_bp,
    watchlist_bp,
    extension_bp
)
from tasks.refresh_jobs import ensure_default_sources, run_job_refresh
from tasks.scheduler import init_job_scheduler
from tasks.schema_migration import ensure_schema_upgrades
from utils.date_helpers import format_relative_time

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    cfg_class = config.get(config_name, config["default"])
    app.config.from_object(cfg_class)
    if hasattr(cfg_class, "init_app"):
        cfg_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register Jinja Template Filters
    @app.template_filter("time_ago")
    @app.template_filter("relative_time")
    def jinja_relative_time(dt):
        return format_relative_time(dt)

    # Register Route Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(ats_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(extension_bp)

    # Register CLI Command for Scheduled / Manual Sync
    @app.cli.command("sync-jobs")
    def cli_sync_jobs():
        """Command to synchronize real vacancies from all connected ATS and job platforms."""
        print("Starting manual/scheduled job refresh across all platforms...")
        stats = run_job_refresh(limit_per_source=30)
        print("Sync results:", stats)

    # Initialize database tables and default job sources
    with app.app_context():
        db.create_all()
        ensure_schema_upgrades()
        try:
            ensure_default_sources()
        except Exception:
            pass

    # Initialize automatic background daily job refresh scheduler
    init_job_scheduler(app)

    return app

if __name__ == "__main__":
    application = create_app()
    port = int(os.getenv("PORT", 5000))
    application.run(host="127.0.0.1", port=port, debug=True)
