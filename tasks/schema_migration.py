from sqlalchemy import inspect, text
from extensions import db
from utils.logging_config import logger

def ensure_schema_upgrades():
    """
    Checks and safely applies non-destructive schema upgrades (e.g. newly added columns)
    to existing SQLite or PostgreSQL databases.
    """
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if "resumes" in tables:
            resume_cols = [c["name"] for c in inspector.get_columns("resumes")]
            with db.engine.connect() as conn:
                if "profile_title" not in resume_cols:
                    logger.info("Migrating schema: Adding resumes.profile_title")
                    conn.execute(text("ALTER TABLE resumes ADD COLUMN profile_title VARCHAR(100) DEFAULT 'Primary Profile'"))
                if "target_role" not in resume_cols:
                    logger.info("Migrating schema: Adding resumes.target_role")
                    conn.execute(text("ALTER TABLE resumes ADD COLUMN target_role VARCHAR(150) DEFAULT ''"))
                conn.commit()

        if "applications" in tables:
            app_cols = [c["name"] for c in inspector.get_columns("applications")]
            with db.engine.connect() as conn:
                if "is_integration_verified" not in app_cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN is_integration_verified BOOLEAN DEFAULT 0"))
                conn.commit()

    except Exception as e:
        logger.warning(f"Schema upgrade check note: {e}")
