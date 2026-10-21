"""
Application CRM Tracking Service.
Automatically records candidate job submissions, tracks stage progression,
and manages interview/follow-up milestones.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from extensions import db
from models.application import Application
from models.job import Job

class ApplicationCRM:
    """
    Candidate Relationship Management (CRM) pipeline service.
    """

    def record_application(
        self,
        user_id: int,
        job: Job,
        status: str = "applied",
        notes: str = ""
    ) -> Application:
        """
        Records or updates an application in the user's CRM with
        status 'applied', company name, job title, and application timestamp.
        """
        app = Application.query.filter_by(user_id=user_id, job_id=job.id).first()
        now = datetime.now(timezone.utc)

        if not app:
            app = Application(
                user_id=user_id,
                job_id=job.id,
                status=status,
                submitted_at=now if status == "applied" else None,
                notes=notes or f"Application initiated for {job.title} at {job.company}."
            )
            db.session.add(app)
        else:
            if status == "applied" and app.status != "applied":
                app.status = "applied"
                app.submitted_at = now
            if notes:
                app.notes = (app.notes + "\n" + notes).strip()

        db.session.commit()
        return app

    def get_applications(self, user_id: int) -> List[Application]:
        return Application.query.filter_by(user_id=user_id).order_by(Application.updated_at.desc()).all()

application_crm = ApplicationCRM()
