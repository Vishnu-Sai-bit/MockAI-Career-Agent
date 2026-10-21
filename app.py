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
from utils.currency_formatter import format_job_salary, format_inr

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

    # Configure SQLite PRAGMAs for thread-safe concurrency without database locks
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        import sqlite3
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=30000")
            except Exception:
                pass
            finally:
                cursor.close()

    # Register Jinja Template Filters
    @app.template_filter("time_ago")
    @app.template_filter("relative_time")
    def jinja_relative_time(dt):
        return format_relative_time(dt)

    @app.template_filter("format_job_salary")
    @app.template_filter("format_salary")
    def jinja_format_salary(job):
        return format_job_salary(job)

    @app.template_filter("format_inr")
    @app.template_filter("rupee")
    def jinja_format_inr(amount):
        return format_inr(amount)

    # Context Processor for Topbar Notifications
    @app.context_processor
    def inject_navbar_data():
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            try:
                recent_notifs = current_user.notifications.order_by(db.desc("created_at")).limit(5).all()
                return {
                    "navbar_notifications": recent_notifs,
                    "navbar_notification_count": len(recent_notifs)
                }
            except Exception:
                return {"navbar_notifications": [], "navbar_notification_count": 0}
        return {"navbar_notifications": [], "navbar_notification_count": 0}

    # Register Route Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    from routes.resumes import resumes_bp
    app.register_blueprint(resumes_bp)
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
