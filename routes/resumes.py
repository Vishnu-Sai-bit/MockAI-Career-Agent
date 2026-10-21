"""
Endpoint alias for /resumes/upload
"""
from flask import Blueprint
from routes.resume_routes import upload_resume

resumes_bp = Blueprint("resumes", __name__, url_prefix="/resumes")
resumes_bp.add_url_rule("/upload", view_func=upload_resume, methods=["GET", "POST"])
