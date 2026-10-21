import re
from typing import Dict, Any, List, Tuple

ACTION_VERBS = [
    "spearheaded", "architected", "engineered", "implemented", "developed", "designed",
    "optimized", "scaled", "automated", "reduced", "increased", "boosted", "delivered",
    "led", "managed", "deployed", "refactored", "built", "accelerated", "resolved"
]

HIGH_VALUE_TECH = [
    "aws", "azure", "gcp", "docker", "kubernetes", "python", "react", "flask",
    "django", "postgresql", "sql", "redis", "typescript", "graphql", "pytorch",
    "tensorflow", "ci/cd", "git", "terraform", "kafka", "spark", "microservices"
]

class ResumeAnalyzer:
    def analyze_resume_quality(self, raw_text: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates resume based on the two-tier ATS architecture:
        Tier 1: Intrinsic Resume Quality Score (0–100%)
        - Contact Information: 10%
        - Skills Section: 30%
        - Work Experience: 20%
        - Education: 15%
        - Projects: 15%
        - Certifications: 10%
        """
        raw_text_clean = (raw_text or "").strip()
        data = parsed_data or {}

        # 1. Contact Information (10%)
        # Name (2%), Professional Email (3%), Phone (3%), LinkedIn (1%), GitHub/Portfolio (1%)
        contact_score, contact_missing = self._evaluate_contact_info(data, raw_text_clean)

        # 2. Skills Section (30%)
        # Total normalized skills (>=10 skills = 20 pts) + high-value domain technical skills bonus (up to 10 pts)
        skills_score, skills_feedback = self._evaluate_skills(data, raw_text_clean)

        # 3. Work Experience (20%)
        # Documented experience tenure, role progression, and measurable responsibilities
        exp_score, exp_feedback = self._evaluate_experience(data, raw_text_clean)

        # 4. Education (15%)
        # Accredited degree, major, university, and graduation year
        edu_score, edu_feedback = self._evaluate_education(data, raw_text_clean)

        # 5. Projects (15%)
        # Demonstrated technical projects with tools, GitHub links, and quantifiable outcomes (>=3 projects = 15 pts)
        proj_score, proj_feedback = self._evaluate_projects(data, raw_text_clean)

        # 6. Certifications (10%)
        # Cloud or professional certifications (AWS, Azure, GCP, etc.)
        cert_score, cert_feedback = self._evaluate_certifications(data, raw_text_clean)

        # Legacy readability & formatting for backward compatibility
        readability_score, readability_feedback = self._evaluate_readability(raw_text_clean)
        completeness_score, legacy_missing = self._evaluate_completeness(data)
        impact_score, impact_feedback = self._evaluate_impact_and_metrics(raw_text_clean)
        formatting_score, formatting_feedback = self._evaluate_formatting(raw_text_clean)

        # Four-Dimension Quality Score Q = 0.30*R + 0.35*C + 0.20*I + 0.15*F
        quality_score_q = round(
            0.30 * readability_score +
            0.35 * completeness_score +
            0.20 * impact_score +
            0.15 * formatting_score,
            1
        )

        section_quality = round(
            contact_score + skills_score + exp_score + edu_score + proj_score + cert_score,
            1
        )
        section_quality = max(0.0, min(100.0, section_quality))

        # Overall Intrinsic ATS Quality Score is strictly the exact sum of the 6 core machine-readable sections:
        # Contact (10%) + Skills (30%) + Experience (20%) + Education (15%) + Projects (15%) + Certifications (10%) = 100%
        overall_quality = section_quality
        if not raw_text_clean and not data:
            overall_quality = 20.0

        all_feedback = []
        if contact_missing:
            all_feedback.append(f"Add missing contact details: {', '.join(contact_missing)}.")
        all_feedback.extend(skills_feedback)
        all_feedback.extend(exp_feedback)
        all_feedback.extend(edu_feedback)
        all_feedback.extend(proj_feedback)
        all_feedback.extend(cert_feedback)
        all_feedback.extend(impact_feedback)

        missing_sections = []
        if contact_missing:
            missing_sections.append("Contact Information")
        if len(data.get("skills", [])) < 3:
            missing_sections.append("Skills Section")
        if not data.get("experience") and data.get("experience_years", 0) == 0:
            missing_sections.append("Work Experience")
        if not data.get("education"):
            missing_sections.append("Education")
        if not data.get("projects"):
            missing_sections.append("Projects")
        if cert_score == 0:
            missing_sections.append("Certifications")

        return {
            "overall_quality_score": overall_quality,
            "breakdown": {
                # 6 core Intrinsic ATS sections
                "contact_info": round(contact_score, 1),
                "skills": round(skills_score, 1),
                "experience": round(exp_score, 1),
                "education": round(edu_score, 1),
                "projects": round(proj_score, 1),
                "certifications": round(cert_score, 1),
                # Legacy keys for backward compatibility
                "readability": readability_score,
                "completeness": completeness_score,
                "impact_and_metrics": impact_score,
                "structure_and_format": formatting_score
            },
            "readability_score": readability_score,
            "completeness_score": completeness_score,
            "impact_score": impact_score,
            "formatting_score": formatting_score,
            "missing_sections": missing_sections,
            "actionable_feedback": all_feedback[:6],
            "skills_count": len(data.get("skills", [])),
            "experience_years": data.get("experience_years", 0)
        }

    def _evaluate_contact_info(self, data: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
        pts = 0.0
        missing = []
        lowered = text.lower()

        # Name (2%)
        if data.get("name"):
            pts += 2.0
        else:
            missing.append("Full Name")

        # Professional Email (3%)
        if data.get("email") or "@" in lowered:
            pts += 3.0
        else:
            missing.append("Professional Email")

        # Phone (3%)
        if data.get("phone") or re.search(r"(\+?\d[\d\s\-\(\)]{8,}\d)", text):
            pts += 3.0
        else:
            missing.append("Phone Number")

        # LinkedIn (1%)
        if data.get("linkedin") or "linkedin.com" in lowered:
            pts += 1.0
        else:
            missing.append("LinkedIn Profile")

        # GitHub / Portfolio (1%)
        if data.get("github") or "github.com" in lowered or "portfolio" in lowered or "gitlab" in lowered:
            pts += 1.0
        else:
            missing.append("GitHub or Portfolio Link")

        return pts, missing

    def _evaluate_skills(self, data: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
        skills = data.get("skills", [])
        count = len(skills)
        feedback = []

        # Total normalized skills (>=10 skills = 20 pts)
        if count >= 10:
            base_pts = 20.0
        else:
            base_pts = round((count / 10.0) * 20.0, 1)
            feedback.append(f"Add more relevant normalized skills (currently {count}, recommend at least 10 for full ATS scoring).")

        # High-value domain technical skills bonus (up to 10 pts)
        lowered_text = text.lower()
        lowered_skills = [s.lower() for s in skills]
        bonus_count = 0
        for tech in HIGH_VALUE_TECH:
            if tech in lowered_skills or tech in lowered_text:
                bonus_count += 1
        bonus_pts = min(10.0, bonus_count * 2.0)

        total = min(30.0, base_pts + bonus_pts)
        return total, feedback

    def _evaluate_experience(self, data: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
        feedback = []
        pts = 0.0
        exp_list = data.get("experience", [])
        exp_years = float(data.get("experience_years", 0) or 0)

        if exp_list or exp_years > 0:
            pts += 10.0
            # Role progression & multiple titles
            if len(exp_list) >= 2 or exp_years >= 3:
                pts += 5.0
            else:
                pts += 3.0
            
            # Measurable responsibilities (action verbs & numbers)
            lowered = text.lower()
            verbs_count = sum(1 for v in ACTION_VERBS if v in lowered)
            has_numbers = bool(re.search(r"\b\d+[%kKxX]?\b", text))
            if verbs_count >= 3 and has_numbers:
                pts += 5.0
            else:
                pts += 3.0
                feedback.append("Use quantifiable metrics (e.g., 'reduced latency by 35%') under past roles.")
        else:
            feedback.append("Document your work experience tenure and role progression.")

        return min(20.0, pts), feedback

    def _evaluate_education(self, data: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
        feedback = []
        edu_list = data.get("education", [])
        pts = 0.0

        if edu_list:
            pts += 5.0  # Degree
            # Check major, university, year
            first = edu_list[0] if isinstance(edu_list[0], dict) else {}
            if first.get("major") or re.search(r"\b(computer science|engineering|information technology|data|business)\b", text, re.I):
                pts += 4.0
            if first.get("institution") or "university" in text.lower() or "college" in text.lower() or "institute" in text.lower():
                pts += 4.0
            if re.search(r"\b(20\d\d|19\d\d)\b", text):
                pts += 2.0
        elif re.search(r"\b(bachelor|master|b\.?tech|b\.?s|degree)\b", text, re.I):
            pts = 10.0
        else:
            feedback.append("Include your degree, major, university, and graduation year.")

        return min(15.0, pts), feedback

    def _evaluate_projects(self, data: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
        feedback = []
        projects = data.get("projects", [])
        count = len(projects)

        if count >= 3:
            pts = 15.0
        elif count == 2:
            pts = 10.0
            feedback.append("Add 1 more technical project with quantifiable outcomes to achieve maximum project score (>=3).")
        elif count == 1:
            pts = 6.0
            feedback.append("Add 2 more technical projects with GitHub links and quantifiable deliverables.")
        else:
            if "project" in text.lower():
                pts = 6.0
            else:
                pts = 0.0
                feedback.append("Demonstrate technical projects detailing tools, architecture, and quantifiable outcomes.")

        return min(15.0, pts), feedback

    def _evaluate_certifications(self, data: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
        feedback = []
        certs = data.get("certifications", [])
        lowered = text.lower()
        cert_patterns = [
            "aws certified", "azure", "gcp", "google cloud certified", "cka", "ckad",
            "pmp", "cissp", "comptia", "certified kubernetes", "hashicorp certified",
            "oracle certified", "scrum master", "tensorflow developer", "certified"
        ]
        detected = [c for c in cert_patterns if c in lowered]
        count = len(certs) or len(detected)

        if count >= 2:
            pts = 10.0
        elif count == 1:
            pts = 6.0
        else:
            pts = 0.0
            feedback.append("Consider adding cloud or professional certifications (AWS, Azure, GCP, etc.) for a 10% ATS boost.")

        return min(10.0, pts), feedback

    def _evaluate_readability(self, text: str) -> (float, List[str]):
        words = text.split()
        word_count = len(words)
        feedback = []

        if word_count < 150:
            return 40.0, ["Resume is very brief. Expand on your project accomplishments and responsibilities."]
        elif word_count > 1200:
            return 70.0, ["Resume is on the longer side. Aim for a concise 1-2 page presentation (400-800 words)."]
        
        score = 90.0
        # Check average word length or sentence length
        lines = [l for l in text.split("\n") if l.strip()]
        if len(lines) > 0 and (word_count / len(lines)) > 25:
            score -= 10
            feedback.append("Some sentences appear long and dense. Use shorter bullet points for clarity.")
        
        return max(score, 50.0), feedback

    def _evaluate_completeness(self, data: Dict[str, Any]) -> (float, List[str]):
        missing = []
        score = 100.0

        if not data.get("email"):
            missing.append("Email Address")
            score -= 15
        if not data.get("phone"):
            missing.append("Phone Number")
            score -= 10
        if not data.get("skills") or len(data.get("skills", [])) < 3:
            missing.append("Skills List")
            score -= 25
        if not data.get("experience") and data.get("experience_years", 0) == 0:
            missing.append("Work Experience")
            score -= 25
        if not data.get("education"):
            missing.append("Education")
            score -= 15
        if not data.get("projects"):
            missing.append("Projects")
            score -= 10

        return max(score, 20.0), missing

    def _evaluate_impact_and_metrics(self, text: str) -> (float, List[str]):
        lowered = text.lower()
        feedback = []
        
        # Check action verbs
        action_verb_count = sum(1 for verb in ACTION_VERBS if verb in lowered)
        
        # Check metrics/percentages/numbers (quantifiable results)
        metric_matches = re.findall(r"(\b\d+%\b|\$\d+[\w]*|\b\d+x\b|\b\d{2,}\+?\b)", text)
        metric_count = len(metric_matches)

        score = 50.0
        score += min(action_verb_count * 5, 25.0)
        score += min(metric_count * 5, 25.0)

        if action_verb_count < 3:
            feedback.append("Use strong action verbs (e.g., 'Architected', 'Engineered', 'Optimized') at the start of bullet points.")
        if metric_count < 2:
            feedback.append("Include quantifiable achievements (e.g., 'reduced latency by 35%', 'handled 10k+ daily users').")

        return min(score, 100.0), feedback

    def _evaluate_formatting(self, text: str) -> (float, List[str]):
        score = 85.0
        feedback = []
        
        # Check bullet points
        bullet_count = text.count("*") + text.count("-") + text.count("•")
        if bullet_count < 5:
            score -= 15
            feedback.append("Structure roles and project details with bullet points for higher ATS parsing accuracy.")

        return max(score, 50.0), feedback
