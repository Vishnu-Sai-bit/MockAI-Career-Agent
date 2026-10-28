from datetime import datetime, timezone
from extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    company = db.Column(db.String(255), nullable=False)
    role_title = db.Column(db.String(255), nullable=False)
    overall_score = db.Column(db.Float, default=0.0)
    delivery_score = db.Column(db.Float, default=0.0)
    average_wpm = db.Column(db.Float, default=0.0)
    questions_count = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)

    job = db.relationship("Job", backref=db.backref("interview_sessions", lazy=True))
    answers = db.relationship("InterviewAnswer", backref="session", lazy=True, cascade="all, delete-orphan", order_by="InterviewAnswer.id")

    def __repr__(self):
        return f"<InterviewSession id={self.id} user_id={self.user_id} role='{self.role_title}' score={self.overall_score}>"

class InterviewAnswer(db.Model):
    __tablename__ = "interview_answers"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(100), default="Behavioral / STAR")
    user_answer = db.Column(db.Text, nullable=False)
    overall_score = db.Column(db.Float, default=0.0)
    star_breakdown = db.Column(db.JSON, default=dict)
    strengths = db.Column(db.JSON, default=list)
    areas_for_improvement = db.Column(db.JSON, default=list)
    speech_analytics = db.Column(db.JSON, default=dict)
    improved_exemplar_answer = db.Column(db.Text, nullable=True)
    followup_question = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<InterviewAnswer id={self.id} score={self.overall_score}>"
