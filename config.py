import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-ai-job-agent-secret-key-change-in-production-2026")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ai_job_agent.db'}")
    # Handle postgres:// vs postgresql:// if needed for newer SQLAlchemy versions
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads" / "resumes"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # Security & Link Verification
    ALLOWED_SCHEMES = {"https"}
    TRUSTED_JOB_HOSTS = {
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "remotive.com",
        "remoteok.com",
        "arbeitnow.com",
        "myworkdayjobs.com",
        "wd3.myworkday.com",
        "wd5.myworkday.com",
        "wd1.myworkday.com",
        "smartrecruiters.com",
        "jobs.smartrecruiters.com",
        "workable.com",
        "apply.workable.com",
        "recruitee.com",
        "adzuna.com",
        "adzuna.in",
        "adzuna.co.uk",
        "jobicy.com",
        "themuse.com",
        "himalayas.app",
        "bamboohr.com",
        "personio.de",
        "personio.com",
        "usajobs.gov"
    }

    # Job Refresher Configuration
    JOB_SYNC_INTERVAL_HOURS = int(os.getenv("JOB_SYNC_INTERVAL_HOURS", 6))
    VERIFY_LINK_TIMEOUT_SEC = 6
    MAX_REDIRECTS = 5

    # AI / LLM Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Job Platform APIs
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
    USAJOBS_API_KEY = os.getenv("USAJOBS_API_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = str(BASE_DIR / "uploads" / "test_resumes")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
