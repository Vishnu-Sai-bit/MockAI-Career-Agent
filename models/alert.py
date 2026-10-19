from datetime import datetime, timezone
from extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class JobAlert(db.Model):
    __tablename__ = "job_alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(120), default="High-Match Daily Alert")
    min_match_score = db.Column(db.Float, default=75.0)
    keywords = db.Column(db.String(255), default="")
    channel = db.Column(db.String(50), default="email")  # email, telegram, in_app
    destination = db.Column(db.String(255), default="")  # email address or chat id
    frequency = db.Column(db.String(50), default="daily")  # instant, daily, weekly
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    last_triggered_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User", backref=db.backref("job_alerts", cascade="all, delete-orphan", lazy="dynamic"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "is_active" not in kwargs:
            self.is_active = True

    def __repr__(self):
        return f"<JobAlert user_id={self.user_id} min_score={self.min_match_score} channel={self.channel}>"


class AlertNotification(db.Model):
    __tablename__ = "alert_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    channel = db.Column(db.String(50), default="email")
    subject = db.Column(db.String(255), default="")
    message = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="sent")  # sent, failed, queued
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    user = db.relationship("User", backref=db.backref("notifications", cascade="all, delete-orphan", lazy="dynamic"))
    job = db.relationship("Job", backref="alert_notifications")

    def __repr__(self):
        return f"<AlertNotification user_id={self.user_id} subject='{self.subject}' status={self.status}>"
