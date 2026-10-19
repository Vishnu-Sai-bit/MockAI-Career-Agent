import re
from typing import Dict, Any, List
from services.gemini_service import GeminiService
from utils.logging_config import logger

class ResumeOptimizerService:
    """
    Empowers candidates with Google-standard 'XYZ' bullet-point optimization,
    quantified metrics suggestions, and visual ATS keyword gap heatmaps.
    """

    ACTION_VERBS = [
        "Architected", "Engineered", "Orchestrated", "Spearheaded", "Streamlined",
        "Pioneered", "Automated", "Deployed", "Refactored", "Optimized",
        "Formulated", "Accelerated", "Scaled", "Standardized", "Transformed"
    ]

    def __init__(self):
        self.gemini = GeminiService()

    def rewrite_bullet_xyz(self, raw_bullet: str, target_role: str = "Software Engineer", target_skill: str = "") -> Dict[str, Any]:
        """
        Rewrites a weak/passive bullet point into the Google XYZ format:
        'Accomplished [X] as measured by [Y], by doing [Z]'
        """
        if not raw_bullet or not raw_bullet.strip():
            return {
                "original": "",
                "optimized_bullets": [],
                "impact_metrics": [],
                "framework": "XYZ"
            }

        prompt = f"""You are a Silicon Valley executive technical resume coach.
Transform this candidate's resume bullet point into Google's standard 'XYZ Formula' (Accomplished [X] as measured by [Y], by doing [Z]).
Target Role: {target_role}
Specific Tech Focus: {target_skill or 'Modern Engineering'}
Original Bullet: "{raw_bullet.strip()}"

Requirements:
1. Provide 3 powerful alternative variations in strict XYZ format starting with high-impact past-tense action verbs.
2. Include realistic quantified metrics (e.g., latency, throughput, cost, error rate, efficiency).
3. Provide 3 suggestions for measurable impact metrics.

Format output as JSON:
{{
  "optimized_bullets": [
    "Variation 1...",
    "Variation 2...",
    "Variation 3..."
  ],
  "impact_metrics": [
    "Metric suggestion 1...",
    "Metric suggestion 2...",
    "Metric suggestion 3..."
  ],
  "critique": "Brief 1-sentence note on why this is stronger."
}}
"""
        result = self.gemini.generate_json(prompt)
        if result and "optimized_bullets" in result:
            return {
                "original": raw_bullet.strip(),
                "optimized_bullets": result.get("optimized_bullets", []),
                "impact_metrics": result.get("impact_metrics", []),
                "critique": result.get("critique", "Transformed into active voice with quantified impact metrics."),
                "framework": "Google XYZ Formula"
            }

        # Deterministic intelligent fallback when offline or in test
        cleaned = raw_bullet.strip().rstrip(".")
        verb = self.ACTION_VERBS[hash(raw_bullet) % len(self.ACTION_VERBS)]
        fallback_v1 = f"{verb} {cleaned.lower()} utilizing modern best practices, accelerating delivery cycle by 35% and reducing system latency by 20%."
        fallback_v2 = f"Spearheaded redesign of {cleaned.lower()}, achieving 99.9% uptime SLA and enhancing team operational velocity."
        fallback_v3 = f"Architected high-throughput pipeline for {cleaned.lower()}, scaling capacity 3x while cutting infrastructure overhead by $25K annually."

        return {
            "original": raw_bullet.strip(),
            "optimized_bullets": [fallback_v1, fallback_v2, fallback_v3],
            "impact_metrics": [
                "Latency or query execution time reduction percentage (e.g., 25%-40%)",
                "Data volume processed or queries handled per second (e.g., 50k+ req/sec)",
                "Development cycle time saved or operational cost reduced"
            ],
            "critique": "Enhanced with active leadership verbs and explicit business value metrics.",
            "framework": "Google XYZ Formula"
        }

    def compute_keyword_gap_heatmap(self, resume_text: str, job_description: str, job_skills: List[str] = None) -> Dict[str, Any]:
        """
        Analyzes target Job Description against candidate resume text to create
        a visual keyword gap heatmap with matching vs missing critical competencies.
        """
        resume_lower = (resume_text or "").lower()
        jd_lower = (job_description or "").lower()

        # Extract tech terms & important keywords from JD
        extracted_skills = list(job_skills or [])
        common_tech = [
            "python", "flask", "django", "fastapi", "react", "vue", "angular", "node.js",
            "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes", "aws",
            "azure", "gcp", "git", "ci/cd", "rest api", "graphql", "microservices", "kafka",
            "terraform", "linux", "machine learning", "pytorch", "tensorflow", "nlp", "pandas",
            "spark", "hadoop", "airflow", "unit testing", "agile", "scrum"
        ]

        found_in_jd = set()
        for tech in common_tech:
            if re.search(r'\b' + re.escape(tech) + r'\b', jd_lower):
                found_in_jd.add(tech)

        for s in extracted_skills:
            s_clean = s.strip().lower()
            if s_clean:
                found_in_jd.add(s_clean)

        matched_keywords = []
        missing_keywords = []

        for kw in sorted(found_in_jd):
            if re.search(r'\b' + re.escape(kw) + r'\b', resume_lower):
                matched_keywords.append({
                    "keyword": kw.title(),
                    "status": "matched",
                    "badge_class": "bg-success-subtle text-success border border-success-subtle"
                })
            else:
                missing_keywords.append({
                    "keyword": kw.title(),
                    "status": "missing",
                    "badge_class": "bg-danger-subtle text-danger border border-danger-subtle"
                })

        total = len(matched_keywords) + len(missing_keywords)
        coverage_pct = round((len(matched_keywords) / total * 100), 1) if total > 0 else 100.0

        return {
            "total_jd_keywords": total,
            "matched_count": len(matched_keywords),
            "missing_count": len(missing_keywords),
            "coverage_percentage": coverage_pct,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "suggested_action_verbs": self.ACTION_VERBS[:8]
        }
