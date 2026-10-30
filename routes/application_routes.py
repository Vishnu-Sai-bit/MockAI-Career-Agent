from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.application import Application, ApplicationDocument
from models.job import Job
from models.job_match import JobMatch
from services.application_service import ApplicationService
from services.cover_letter_service import CoverLetterService

applications_bp = Blueprint("applications", __name__, url_prefix="/applications")
app_service = ApplicationService()
cover_service = CoverLetterService()

@applications_bp.route("")
@login_required
def list_applications():
    from models.job_match import SavedJob
    grouped = app_service.get_applications_grouped_by_status(current_user.id)
    all_apps = current_user.applications.order_by(Application.updated_at.desc()).all()
    saved_entries = current_user.saved_jobs.order_by(SavedJob.saved_at.desc()).all()
    return render_template(
        "applications.html",
        grouped=grouped,
        all_applications=all_apps,
        saved_jobs=saved_entries
    )


@applications_bp.route("/prepare/<int:job_id>")
@login_required
def prepare_application(job_id):
    job = Job.query.get_or_404(job_id)
    resume = current_user.get_active_resume()
    if not resume:
        flash("Please upload a resume first to prepare application materials.", "info")
        return redirect(url_for("resume.upload_resume"))

    profile = current_user.candidate_profile
    app = app_service.get_or_create_application(current_user.id, job.id, status="prepared")

    # Generate tailored cover letter & interview prep
    cover_letter = cover_service.generate_tailored_cover_letter(profile, resume, job)
    interview_prep = cover_service.generate_interview_prep(profile, resume, job)

    match = JobMatch.query.filter_by(user_id=current_user.id, resume_id=resume.id, job_id=job.id).first()

    return render_template(
        "job_details.html",
        job=job,
        match=match,
        application=app,
        cover_letter=cover_letter,
        interview_prep=interview_prep,
        is_prepared=True
    )


@applications_bp.route("/api/update", methods=["POST"])
@login_required
def update_status():
    data = request.get_json() or request.form
    app_id = data.get("application_id")
    status = data.get("status")
    notes = data.get("notes")
    next_action_desc = data.get("next_action_desc")
    next_action_str = data.get("next_action_at")

    if not app_id:
        return jsonify({"success": False, "error": "Application ID required."}), 400

    next_action_at = None
    if next_action_str:
        try:
            next_action_at = datetime.fromisoformat(next_action_str)
        except Exception:
            pass

    try:
        app = app_service.update_application_status(
            user_id=current_user.id,
            application_id=int(app_id),
            status=status,
            notes=notes,
            next_action_at=next_action_at,
            next_action_desc=next_action_desc
        )
        return jsonify({
            "success": True,
            "status": app.status,
            "message": f"Application marked as {app.status}."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@applications_bp.route("/api/create", methods=["POST"])
@login_required
def create_application():
    data = request.get_json() or request.form
    job_id = data.get("job_id")
    status = data.get("status", "prepared")

    if not job_id:
        return jsonify({"success": False, "error": "Job ID required."}), 400

    app = app_service.get_or_create_application(current_user.id, int(job_id), status=status)
    return jsonify({"success": True, "application_id": app.id, "status": app.status})


@applications_bp.route("/tailored-resume/<int:job_id>")
@login_required
def view_tailored_resume(job_id):
    job = Job.query.get_or_404(job_id)
    resume = current_user.get_active_resume()
    if not resume:
        flash("Please upload a resume first.", "info")
        return redirect(url_for("resume.upload_resume"))

    from services.tailored_document_generator import TailoredDocumentGenerator
    doc_gen = TailoredDocumentGenerator()
    tailored_data = doc_gen.generate_tailored_resume(resume, current_user.candidate_profile, job)
    return render_template("tailored_resume.html", job=job, doc=tailored_data)


@applications_bp.route("/tailored-cover-letter/<int:job_id>")
@login_required
def view_tailored_cover_letter(job_id):
    job = Job.query.get_or_404(job_id)
    resume = current_user.get_active_resume()
    if not resume:
        flash("Please upload a resume first.", "info")
        return redirect(url_for("resume.upload_resume"))

    from services.tailored_document_generator import TailoredDocumentGenerator
    doc_gen = TailoredDocumentGenerator()
    cover_data = doc_gen.generate_tailored_cover_letter(resume, current_user.candidate_profile, job)
    return render_template("tailored_cover_letter.html", job=job, doc=cover_data)


@applications_bp.route("/outreach/<int:app_id>")
@login_required
def application_outreach(app_id):
    from services.outreach_service import OutreachService
    app = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    job = app.job
    profile = current_user.candidate_profile

    outreach_svc = OutreachService()
    personas = outreach_svc.generate_recruiter_personas(job.company, job.title)
    templates = outreach_svc.generate_outreach_templates(
        candidate_name=profile.full_name or current_user.email.split('@')[0],
        candidate_skills=profile.skills or [],
        company=job.company,
        job_title=job.title
    )
    followup_7d = outreach_svc.generate_followup_email(
        candidate_name=profile.full_name or current_user.email.split('@')[0],
        company=job.company,
        job_title=job.title,
        application_date=app.created_at,
        stage="7day"
    )
    followup_14d = outreach_svc.generate_followup_email(
        candidate_name=profile.full_name or current_user.email.split('@')[0],
        company=job.company,
        job_title=job.title,
        application_date=app.created_at,
        stage="14day"
    )
    followup_interview = outreach_svc.generate_followup_email(
        candidate_name=profile.full_name or current_user.email.split('@')[0],
        company=job.company,
        job_title=job.title,
        application_date=app.created_at,
        stage="post_interview"
    )

    return jsonify({
        "success": True,
        "application_id": app.id,
        "job_title": job.title,
        "company": job.company,
        "personas": personas,
        "templates": templates,
        "followups": {
            "7day": followup_7d,
            "14day": followup_14d,
            "post_interview": followup_interview
        }
    })


@applications_bp.route("/calendar/<int:app_id>")
@login_required
def application_calendar(app_id):
    from datetime import datetime, timezone, timedelta
    from flask import Response
    from services.career_analytics_service import CareerAnalyticsService

    app = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    job = app.job
    event_time = app.next_action_at or (datetime.now(timezone.utc) + timedelta(days=2))

    analytics_svc = CareerAnalyticsService()
    cal_data = analytics_svc.generate_calendar_links(
        job_title=job.title,
        company=job.company,
        event_time=event_time,
        event_type="Technical Interview" if app.status == "interviewing" else "Application Follow-up"
    )

    if request.args.get("download") == "1":
        return Response(
            cal_data["ics_content"],
            mimetype="text/calendar",
            headers={"Content-Disposition": f"attachment; filename=interview_{app.id}.ics"}
        )

    return jsonify({"success": True, "calendar": cal_data})


