from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.alert import JobAlert, AlertNotification
from services.notification_service import NotificationService

alert_bp = Blueprint("alerts", __name__, url_prefix="/alerts")
notification_service = NotificationService()

@alert_bp.route("")
@login_required
def alerts_home():
    alerts = current_user.job_alerts.order_by(JobAlert.created_at.desc()).all()
    notifications = current_user.notifications.order_by(AlertNotification.created_at.desc()).limit(20).all()
    return render_template("alerts.html", alerts=alerts, notifications=notifications)

@alert_bp.route("/create", methods=["POST"])
@login_required
def create_alert():
    title = request.form.get("title", "High Match Alert")
    min_score = float(request.form.get("min_match_score", 75.0))
    keywords = request.form.get("keywords", "")
    channel = request.form.get("channel", "email")
    destination = request.form.get("destination", current_user.email)

    alert = JobAlert(
        user_id=current_user.id,
        title=title,
        min_match_score=min_score,
        keywords=keywords,
        channel=channel,
        destination=destination or current_user.email,
        is_active=True
    )
    db.session.add(alert)
    db.session.commit()
    flash("Job alert created successfully! You will be notified when matching jobs are discovered.", "success")
    return redirect(url_for("alerts.alerts_home"))

@alert_bp.route("/toggle/<int:alert_id>", methods=["POST"])
@login_required
def toggle_alert(alert_id):
    alert = JobAlert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    alert.is_active = not alert.is_active
    db.session.commit()
    return jsonify({"success": True, "is_active": alert.is_active})

@alert_bp.route("/trigger-check", methods=["POST"])
@login_required
def trigger_check():
    sent_count = notification_service.check_and_send_alerts()
    flash(f"Scanned all active alerts! {sent_count} notification(s) dispatched.", "info")
    return redirect(url_for("alerts.alerts_home"))

@alert_bp.route("/trigger-digest", methods=["POST"])
@login_required
def trigger_digest():
    digests = notification_service.generate_daily_morning_digest(user_id=current_user.id)
    count = digests[0]["job_count"] if digests else 0
    flash(f"Morning Digest compiled! Found {count} top matching job(s) for your profile.", "success")
    return redirect(url_for("alerts.alerts_home"))

