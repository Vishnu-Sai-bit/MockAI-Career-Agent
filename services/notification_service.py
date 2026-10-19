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
            elif alert.channel == "whatsapp" and alert.destination:
                self._send_whatsapp(alert.destination, full_message)

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

    def _send_whatsapp(self, destination: str, message: str) -> bool:
        """
        Dispatches WhatsApp notification via webhook or Twilio/Meta API if configured.
        """
        webhook_url = os.getenv("WHATSAPP_WEBHOOK_URL", "")
        if webhook_url:
            try:
                resp = requests.post(webhook_url, json={"to": destination, "message": message}, timeout=5)
                return resp.status_code in [200, 201, 202]
            except Exception as e:
                logger.warning(f"WhatsApp webhook dispatch error: {e}")
                return False
        logger.info(f"[WhatsApp Alert Recorded] To: {destination} | Msg: {message[:100]}...")
        return True

    def generate_daily_morning_digest(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Compiles the morning digest of top fresh jobs matching the user's active profile in the past 24 hours.
        """
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        users_query = User.query
        if user_id:
            users_query = users_query.filter_by(id=user_id)
        users = users_query.all()

        digests = []
        for u in users:
            resume = u.get_active_resume()
            if not resume:
                continue

            # Query jobs posted in past 24 hours with matches for user
            matches = (
                JobMatch.query.filter(
                    JobMatch.user_id == u.id,
                    JobMatch.match_score >= 60.0
                )
                .join(Job, Job.id == JobMatch.job_id)
                .filter(Job.status == "active", Job.published_at >= since)
                .order_by(JobMatch.match_score.desc())
                .limit(5)
                .all()
            )

            if not matches:
                # Fallback to top matches overall if no 24h jobs exist
                matches = (
                    JobMatch.query.filter(
                        JobMatch.user_id == u.id,
                        JobMatch.match_score >= 60.0
                    )
                    .join(Job, Job.id == JobMatch.job_id)
                    .filter(Job.status == "active")
                    .order_by(Job.published_at.desc(), JobMatch.match_score.desc())
                    .limit(5)
                    .all()
                )

            if not matches:
                continue

            digest_payload = {
                "user_id": u.id,
                "email": u.email,
                "job_count": len(matches),
                "generated_at": now.isoformat(),
                "jobs": [
                    {
                        "job_id": m.job.id,
                        "title": m.job.title,
                        "company": m.job.company,
                        "location": m.job.location,
                        "score": round(m.match_score, 1),
                        "apply_url": m.job.apply_url
                    }
                    for m in matches
                ]
            }

            # Record in-app notification
            subj = f"🌅 Morning Job Digest: {len(matches)} Top Matched Roles Today"
            msg = f"Good morning {u.email.split('@')[0]}!\n\nHere are your top {len(matches)} matched openings:\n" + "\n".join(
                [f"• {m.job.title} at {m.job.company} ({round(m.match_score, 0)}% Match) — {m.job.apply_url}" for m in matches]
            )
            notif = AlertNotification(
                user_id=u.id,
                job_id=matches[0].job.id,
                channel="email",
                subject=subj,
                message=msg,
                status="sent"
            )
            db.session.add(notif)
            digests.append(digest_payload)

        db.session.commit()
        return digests

