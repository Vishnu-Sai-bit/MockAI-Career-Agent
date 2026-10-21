from typing import Dict, Any
from services.resume_analyzer import ResumeAnalyzer

class ATSScorer:
    def __init__(self):
        self.analyzer = ResumeAnalyzer()

    def score_resume(self, raw_text: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes overall resume quality score and detailed diagnostic report.
        """
        analysis = self.analyzer.analyze_resume_quality(raw_text, parsed_data)
        
        # Determine performance tier
        overall = analysis["overall_quality_score"]
        if overall >= 85:
            tier = "Excellent"
            summary = "Your resume is well-structured, keyword-rich, and clearly details your technical impact."
        elif overall >= 75:
            tier = "Strong"
            summary = "Your resume meets standard ATS criteria with good clarity, but could benefit from more quantifiable achievements."
        elif overall >= 65:
            tier = "Moderate"
            summary = "Your resume conveys key skills, but lacks detail in key sections or certifications."
        else:
            tier = "Needs Improvement"
            summary = "Key resume sections are missing or brief. Expanding on technical skills, projects, and certifications is recommended."

        return {
            "overall_score": overall,
            "tier": tier,
            "summary": summary,
            "breakdown": analysis.get("breakdown", {
                "contact_info": 8.0,
                "skills": 25.0,
                "experience": 18.0,
                "education": 14.0,
                "projects": 12.0,
                "certifications": 6.0,
                "readability": analysis.get("readability_score", 85.0),
                "completeness": analysis.get("completeness_score", 85.0),
                "impact_and_metrics": analysis.get("impact_score", 75.0),
                "structure_and_format": analysis.get("formatting_score", 85.0)
            }),
            "actionable_feedback": analysis["actionable_feedback"],
            "missing_sections": analysis["missing_sections"]
        }

    def calculate_job_match(self, resume, profile, job) -> Dict[str, Any]:
        """
        Calculates the job-specific compatibility score against live openings:
        M = 0.35S + 0.20E + 0.15K + 0.10P + 0.10L + 0.10Q
        where Q is the Phase 2 Resume Quality Score.
        """
        from services.job_matcher import JobMatcher
        matcher = JobMatcher()
        return matcher.compute_match(resume, profile, job)
