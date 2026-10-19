import io
from typing import Dict, Any, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from models.resume import Resume
from models.user import CandidateProfile

class ResumeExportService:
    """
    Exports tailored and parsed resumes into ATS-friendly .docx and plain text formats.
    Designed without nested tables or multi-column text boxes to achieve 100% ATS readability.
    """

    def export_resume_docx(self, resume: Resume, profile: Optional[CandidateProfile] = None) -> io.BytesIO:
        doc = Document()

        # Set 0.75 in margins for balanced modern ATS layout
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        parsed = resume.parsed_data or {}
        candidate_name = (profile.full_name if profile and profile.full_name else parsed.get("name") or "Candidate Name").strip()
        headline = (resume.profile_title or (profile.headline if profile else "") or "Software & AI Professional").strip()
        email = (profile.user.email if profile and profile.user else parsed.get("email") or "").strip()
        phone = (profile.phone if profile and profile.phone else parsed.get("phone") or "").strip()
        location = (profile.location if profile and profile.location else parsed.get("location") or "").strip()

        # Header: Name
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(candidate_name)
        title_run.font.name = "Arial"
        title_run.font.size = Pt(20)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(15, 23, 42)

        # Headline
        if headline:
            h_p = doc.add_paragraph()
            h_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            h_run = h_p.add_run(headline)
            h_run.font.name = "Arial"
            h_run.font.size = Pt(12)
            h_run.font.color.rgb = RGBColor(71, 85, 105)

        # Contact line
        contact_parts = [p for p in [email, phone, location] if p]
        if contact_parts:
            c_p = doc.add_paragraph()
            c_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c_run = c_p.add_run(" | ".join(contact_parts))
            c_run.font.name = "Arial"
            c_run.font.size = Pt(9.5)
            c_run.font.color.rgb = RGBColor(100, 116, 139)

        # Helper to add section heading
        def add_heading(text: str):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(text.upper())
            run.font.name = "Arial"
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = RGBColor(30, 41, 59)

        # 1. Professional Summary
        summary_text = (profile.summary if profile and profile.summary else parsed.get("summary") or "").strip()
        if not summary_text and resume.raw_text:
            # take first 300 chars of raw text as fallback
            summary_text = resume.raw_text[:350].strip()

        if summary_text:
            add_heading("Professional Summary")
            sp = doc.add_paragraph()
            sp.paragraph_format.space_after = Pt(6)
            s_run = sp.add_run(summary_text)
            s_run.font.name = "Arial"
            s_run.font.size = Pt(10)
            s_run.font.color.rgb = RGBColor(51, 65, 85)

        # 2. Core Skills
        skills = (profile.skills if profile and profile.skills else parsed.get("skills") or [])
        if skills:
            add_heading("Technical & Core Skills")
            kp = doc.add_paragraph()
            kp.paragraph_format.space_after = Pt(6)
            k_run = kp.add_run(", ".join(skills))
            k_run.font.name = "Arial"
            k_run.font.size = Pt(10)
            k_run.font.color.rgb = RGBColor(51, 65, 85)

        # 3. Work Experience
        experiences = parsed.get("experience") or (profile.projects if profile else [])
        if experiences:
            add_heading("Professional Experience")
            if isinstance(experiences, list):
                for exp in experiences:
                    if isinstance(exp, dict):
                        role = exp.get("role") or exp.get("title") or "Software Engineer"
                        company = exp.get("company") or "Technology Co"
                        duration = exp.get("duration") or ""
                        ep = doc.add_paragraph()
                        ep.paragraph_format.space_before = Pt(4)
                        ep.paragraph_format.space_after = Pt(2)
                        
                        r_run = ep.add_run(f"{role} — {company}")
                        r_run.font.name = "Arial"
                        r_run.font.size = Pt(10.5)
                        r_run.font.bold = True

                        if duration:
                            d_run = ep.add_run(f" ({duration})")
                            d_run.font.name = "Arial"
                            d_run.font.size = Pt(9.5)
                            d_run.font.italic = True

                        desc = exp.get("description") or exp.get("details")
                        if desc:
                            dp = doc.add_paragraph(style="List Bullet")
                            dp.paragraph_format.space_after = Pt(2)
                            d_run2 = dp.add_run(str(desc))
                            d_run2.font.name = "Arial"
                            d_run2.font.size = Pt(9.5)
                    elif isinstance(exp, str):
                        bp = doc.add_paragraph(style="List Bullet")
                        bp.paragraph_format.space_after = Pt(2)
                        b_run = bp.add_run(exp)
                        b_run.font.name = "Arial"
                        b_run.font.size = Pt(9.5)

        # 4. Education
        education = parsed.get("education") or (profile.education if profile else [])
        if education:
            add_heading("Education")
            if isinstance(education, list):
                for edu in education:
                    ed_p = doc.add_paragraph(style="List Bullet")
                    ed_p.paragraph_format.space_after = Pt(2)
                    ed_str = f"{edu.get('degree', '')} from {edu.get('institution', '')}" if isinstance(edu, dict) else str(edu)
                    ed_run = ed_p.add_run(ed_str)
                    ed_run.font.name = "Arial"
                    ed_run.font.size = Pt(9.5)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def export_resume_ats_text(self, resume: Resume, profile: Optional[CandidateProfile] = None) -> str:
        parsed = resume.parsed_data or {}
        name = (profile.full_name if profile and profile.full_name else parsed.get("name") or "Candidate").strip()
        headline = (resume.profile_title or (profile.headline if profile else "") or "Software Professional").strip()
        email = (profile.user.email if profile and profile.user else parsed.get("email") or "").strip()
        phone = (profile.phone if profile and profile.phone else parsed.get("phone") or "").strip()
        location = (profile.location if profile and profile.location else parsed.get("location") or "").strip()

        lines = [
            name.upper(),
            headline,
            f"{email} | {phone} | {location}".strip(" |"),
            "",
            "=" * 50,
            "PROFESSIONAL SUMMARY",
            "=" * 50,
            (profile.summary if profile and profile.summary else parsed.get("summary") or resume.raw_text[:350]).strip(),
            "",
            "=" * 50,
            "TECHNICAL & CORE SKILLS",
            "=" * 50,
            ", ".join(profile.skills if profile and profile.skills else parsed.get("skills") or []),
            "",
            "=" * 50,
            "PROFESSIONAL EXPERIENCE",
            "=" * 50,
        ]

        experiences = parsed.get("experience") or []
        for exp in experiences:
            if isinstance(exp, dict):
                lines.append(f"• {exp.get('role', 'Engineer')} at {exp.get('company', 'Company')} ({exp.get('duration', '')})")
                if exp.get("description"):
                    lines.append(f"  {exp.get('description')}")
            else:
                lines.append(f"• {exp}")

        lines.extend([
            "",
            "=" * 50,
            "EDUCATION",
            "=" * 50
        ])
        education = parsed.get("education") or []
        for edu in education:
            if isinstance(edu, dict):
                lines.append(f"• {edu.get('degree', '')} — {edu.get('institution', '')}")
            else:
                lines.append(f"• {edu}")

        return "\n".join(lines)
