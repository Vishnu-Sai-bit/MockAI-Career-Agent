from datetime import datetime, timezone
from extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class DreamCompany(db.Model):
    __tablename__ = "dream_companies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name = db.Column(db.String(150), nullable=False, index=True)
    domain = db.Column(db.String(150), default="")
    careers_url = db.Column(db.String(500), default="")
    ats_platform = db.Column(db.String(50), default="auto")  # greenhouse, lever, ashby, workday, smartrecruiters, etc.
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_scanned_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "company_name", name="uq_user_dream_company"),
    )

    def __repr__(self):
        return f"<DreamCompany user_id={self.user_id} company='{self.company_name}' platform='{self.ats_platform}'>"
