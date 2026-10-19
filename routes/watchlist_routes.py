from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.dream_company_service import DreamCompanyService

watchlist_bp = Blueprint("watchlist", __name__, url_prefix="/watchlist")

@watchlist_bp.route("")
@login_required
def view_watchlist():
    service = DreamCompanyService()
    companies = service.get_user_watchlist(current_user.id)
    dream_jobs = service.scan_dream_company_jobs(current_user.id)
    return render_template("watchlist.html", companies=companies, dream_jobs=dream_jobs)

@watchlist_bp.route("/add", methods=["POST"])
@login_required
def add_company():
    company_name = request.form.get("company_name", "").strip()
    domain = request.form.get("domain", "").strip()
    careers_url = request.form.get("careers_url", "").strip()
    ats_platform = request.form.get("ats_platform", "auto").strip()

    if not company_name:
        flash("Company name is required.", "danger")
        return redirect(url_for("watchlist.view_watchlist"))

    service = DreamCompanyService()
    try:
        dc = service.add_dream_company(
            user_id=current_user.id,
            company_name=company_name,
            domain=domain,
            careers_url=careers_url,
            ats_platform=ats_platform
        )
        flash(f"Added {dc.company_name} to your Dream Companies watchlist (Platform: {dc.ats_platform.title()})!", "success")
    except Exception as e:
        flash(f"Failed to add company: {str(e)}", "danger")

    return redirect(url_for("watchlist.view_watchlist"))

@watchlist_bp.route("/delete/<int:company_id>", methods=["POST"])
@login_required
def delete_company(company_id):
    service = DreamCompanyService()
    success = service.remove_dream_company(current_user.id, company_id)
    if success:
        flash("Company removed from watchlist.", "info")
    else:
        flash("Company not found.", "warning")
    return redirect(url_for("watchlist.view_watchlist"))

@watchlist_bp.route("/api/scan")
@login_required
def api_scan():
    service = DreamCompanyService()
    jobs = service.scan_dream_company_jobs(current_user.id)
    return jsonify({
        "success": True,
        "count": len(jobs),
        "jobs": [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "platform": j.source_platform,
                "apply_url": j.apply_url,
                "published_at": j.published_at.isoformat() if j.published_at else None
            }
            for j in jobs
        ]
    })
