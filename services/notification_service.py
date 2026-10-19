import os
import requests
from typing import List, Dict, Any, Optional
from extensions import db
from models.user import User
from models.job import Job
from models.alert import JobAlert, AlertNotification
from models.job_match import JobMatch
from utils.logging_config import logger

class NotificationService:
    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def check_and_send_alerts(self, new_jobs: Optional[List[Job]] = None) -> int:
        """
        Scans active user job alerts and notifies candidates of new qualifying job vacancies.
        """
        active_alerts = JobAlert.query.filter_by(is_active=True).all()
        notifications_sent = 0

        for alert in active_alerts:
            user = alert.user
            if not user:
                continue

            # Query matches for user meeting or exceeding alert threshold
            query = (
                JobMatch.query.filter(
                    JobMatch.user_id == user.id,
                    JobMatch.match_score >= alert.min_match_score
                )
                .join(Job, Job.id == JobMatch.job_id)
                .filter(Job.status == "active")
            )

            # Optional keyword filtering
            if alert.keywords:
                kw_list = [k.strip().lower() for k in alert.keywords.split(",") if k.strip()]
                for kw in kw_list:
                    query = query.filter(Job.title.ilike(f"%{kw}%") | Job.description.ilike(f"%{kw}%"))

            top_matches = query.order_by(JobMatch.match_score.desc()).limit(5).all()
            if not top_matches:
                continue

            # Check if recently notified about these top jobs
            job_ids = [m.job_id for m in top_matches]
            already_notified = AlertNotification.query.filter(
                AlertNotification.user_id == user.id,
                AlertNotification.job_id.in_(job_ids)
            ).count()

            if already_notified >= len(job_ids):
                continue

            # Compose alert digest
            subject = f"🔔 {len(top_matches)} New High-Match Jobs Discovered for You ({alert.min_match_score}%+ ATS Score)"
            body_lines = [
                f"Hello {user.email.split('@')[0]},",
                f"",
                f"Our AI Job Agent discovered new verified opportunities matching your profile:",
                f""
            ]

            for m in top_matches:
                j = m.job
                body_lines.append(f"• {j.title} at {j.company} ({j.location})")
                body_lines.append(f"  ATS Compatibility: {round(m.match_score, 1)}% | Platform: {j.source_platform.title()}")
                body_lines.append(f"  Apply Directly: {j.apply_url}")
                body_lines.append("")

            body_lines.append("Best regards,\nYour AI Job Agent Assistant")
            full_message = "\n".join(body_lines)

            # Record in-app notification
            for m in top_matches:
                notif = AlertNotification(
                    user_id=user.id,
                    job_id=m.job_id,
                    channel=alert.channel,
                    subject=subject,
                    message=full_message,
                    status="sent"
                )
                db.session.add(notif)

            # Send via external channel if configured
            if alert.channel == "telegram" and alert.destination and self.telegram_bot_token:
                self._send_telegram(alert.destination, full_message)

            notifications_sent += 1

        db.session.commit()
        return notifications_sent

    def _send_telegram(self, chat_id: str, message: str) -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            resp = requests.post(url, json=payload, timeout=6)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Telegram notification dispatch error: {e}")
            return False
